import discord
from discord import File, app_commands
from dotenv import load_dotenv
import os

# Charger les variables d'environnement
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Configurer les intents
intents = discord.Intents.default()
intents.message_content = True
intents.guild_reactions = True
intents.guilds = True
intents.members = True

# Initialiser le client Discord
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Dictionnaire global pour mapper les messages aux rôles
role_menu_mapping = {}

# Cache pour stocker les messages (utile pour les événements comme `on_message_delete`)
message_cache = {}

### Fonctionnalité pour créer un menu de rôles ###
@tree.command(name="rolemenu", description="Créer un menu pour attribuer des rôles via des emojis.")
async def rolemenu(interaction: discord.Interaction, roles: str, emojis: str):
    guild = interaction.guild

    # Diviser les rôles et les emojis
    role_names = [name.strip() for name in roles.split(",")]
    emoji_list = [emoji.strip() for emoji in emojis.split(",")]

    # Vérifier que le nombre de rôles et d'emojis correspond
    if len(role_names) != len(emoji_list):
        await interaction.response.send_message(
            "Le nombre de rôles et d'emojis doit être identique.", ephemeral=True
        )
        return

    # Vérifier l'existence des rôles
    role_objects = []
    for role_name in role_names:
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            role_objects.append(role)
        else:
            await interaction.response.send_message(
                f"Le rôle **{role_name}** n'existe pas sur ce serveur.", ephemeral=True
            )
            return

    # Créer le message d'attribution des rôles
    description = "Réagissez avec les emojis ci-dessous pour obtenir ou retirer les rôles associés :\n\n"
    for role, emoji in zip(role_objects, emoji_list):
        description += f"{emoji} : **{role.name}**\n"

    embed = discord.Embed(
        title="Menu des rôles",
        description=description,
        color=discord.Color.blue()
    )
    message = await interaction.channel.send(embed=embed)

    # Ajouter les réactions au message
    for emoji in emoji_list:
        await message.add_reaction(emoji)

    # Stocker l'association message-rôles
    role_menu_mapping[message.id] = {emoji: role for emoji, role in zip(emoji_list, role_objects)}
    await interaction.response.send_message("Le menu des rôles a été créé avec succès !", ephemeral=True)

### Gestion des réactions ###
@client.event
async def on_raw_reaction_add(payload):
    if payload.user_id == client.user.id:
        return

    if payload.message_id in role_menu_mapping:
        guild = client.get_guild(payload.guild_id)
        if not guild:
            return

        role_mapping = role_menu_mapping[payload.message_id]
        emoji = str(payload.emoji)
        role = role_mapping.get(emoji)

        if role:
            try:
                member = await guild.fetch_member(payload.user_id)
                if member:
                    await member.add_roles(role)
                    await log_action(guild, f"Rôle {role.name} attribué à {member.name}.")
            except Exception as e:
                await log_action(guild, f"Erreur lors de l'ajout du rôle : {e}")

@client.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == client.user.id:
        return

    if payload.message_id in role_menu_mapping:
        guild = client.get_guild(payload.guild_id)
        if not guild:
            return

        role_mapping = role_menu_mapping[payload.message_id]
        emoji = str(payload.emoji)
        role = role_mapping.get(emoji)

        if role:
            try:
                member = await guild.fetch_member(payload.user_id)
                if member:
                    await member.remove_roles(role)
                    await log_action(guild, f"Rôle {role.name} retiré de {member.name}.")
            except Exception as e:
                await log_action(guild, f"Erreur lors du retrait du rôle : {e}")

### Sauvegarde des messages dans un cache ###
@client.event
async def on_message(message):
    message_cache[message.id] = {
        "content": message.content,
        "author": message.author.name,
        "channel": message.channel.name if not isinstance(message.channel, discord.DMChannel) else "DM",
        "guild": message.guild.name if message.guild else "DM",
    }

### Message d'accueil et de départ ###
@client.event
async def on_member_join(member):
    embed = create_welcome_embed(member)
    channel = member.guild.system_channel
    if channel:
        await channel.send(embed=embed)
    await log_action(member.guild, f"{member.name} a rejoint le serveur.")

@client.event
async def on_member_remove(member):
    embed = create_goodbye_embed(member)
    channel = member.guild.system_channel
    if channel:
        await channel.send(embed=embed)
    await log_action(member.guild, f"{member.name} a quitté le serveur.")

### Logs et utilitaires ###
async def log_action(guild, message):
    log_channel = discord.utils.get(guild.text_channels, name="logs")
    if log_channel:
        await log_channel.send(f"[LOG] {message}")
    else:
        print(f"[LOG] {message}")

def create_welcome_embed(member):
    embed = discord.Embed(
        title=f"Bienvenue {member.name} ! 🎉",
        description=f"Bienvenue sur **{member.guild.name}** !",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    return embed

def create_goodbye_embed(member):
    embed = discord.Embed(
        title=f"{member.name} a quitté le serveur 😢",
        description=f"Au revoir **{member.guild.name}**.",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    return embed

### Démarrage du bot ###
@client.event
async def on_ready():
    await tree.sync()
    print(f"Connecté en tant que {client.user}")

client.run(TOKEN)
