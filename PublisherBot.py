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

@client.event
async def on_raw_reaction_add(payload):
    print(f"[DEBUG] Reaction added: {payload.emoji}, user: {payload.user_id}, message_id: {payload.message_id}")

    # Ignorer les réactions du bot
    if payload.user_id == client.user.id:
        print("[DEBUG] Ignoré : réaction ajoutée par le bot.")
        return

    # Vérifier si le message est un menu de rôles
    if payload.message_id in role_menu_mapping:
        guild = client.get_guild(payload.guild_id)
        if not guild:
            print(f"[DEBUG] Guild introuvable pour l'ID {payload.guild_id}.")
            return

        role_mapping = role_menu_mapping[payload.message_id]
        emoji = str(payload.emoji)
        role = role_mapping.get(emoji)

        if role:
            try:
                member = await guild.fetch_member(payload.user_id)
                if not member:
                    print(f"[DEBUG] Membre introuvable pour l'ID {payload.user_id}.")
                    return

                print(f"[DEBUG] Vérification du rôle {role.name} pour {member.name}.")
                bot_member = guild.get_member(client.user.id)
                if role.position >= bot_member.top_role.position:
                    print(f"[ERROR] Le rôle {role.name} est trop élevé pour être attribué par le bot.")
                    await log_action(
                        guild,
                        f"Erreur : Le bot n'a pas les permissions pour attribuer le rôle {role.name}."
                    )
                    return

                await member.add_roles(role)
                print(f"[DEBUG] Rôle {role.name} attribué à {member.name}.")
                await log_action(guild, f"Rôle {role.name} attribué à {member.name}.")
            except Exception as e:
                print(f"[DEBUG] Erreur lors de l'ajout du rôle : {e}")
                await log_action(guild, f"Erreur lors de l'ajout du rôle : {e}")
        else:
            print(f"[DEBUG] Aucun rôle trouvé pour l'emoji {emoji}.")


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
    # Ajouter le message au cache pour une éventuelle récupération
    if isinstance(message.channel, discord.DMChannel):
        channel_name = "DM"
        guild_name = "DM"
    else:
        channel_name = message.channel.name
        guild_name = message.guild.name

    message_cache[message.id] = {
        "content": message.content,
        "author": message.author.name,
        "channel": channel_name,
        "guild": guild_name,
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

@client.event
async def on_member_update(before, after):
    if before.nick != after.nick:
        await log_action(
            after.guild,
            f"Pseudo changé : {before.nick or before.name} -> {after.nick or after.name}."
        )

@client.event
async def on_message_delete(message):
    cached_message = message_cache.pop(message.id, None)
    if cached_message:
        await log_action(
            message.guild,
            f"Message supprimé : '{cached_message['content']}' par {cached_message['author']} "
            f"dans #{cached_message['channel']}."
        )
    else:
        await log_action(message.guild, f"Message supprimé, mais aucune information disponible.")

@client.event
async def on_message_edit(before, after):
    await log_action(
        before.guild,
        f"Message édité :\nAvant : {before.content}\nAprès : {after.content}."
    )

### Utilitaire pour les logs ###
async def log_action(guild, message):
    """
    Envoie un message de log dans le channel nommé "logs".
    """
    if not guild:
        print(f"[LOG] {message}")
        return

    log_channel = discord.utils.get(guild.text_channels, name="logs")
    if log_channel:
        await log_channel.send(f"[LOG] {message}")
    else:
        print(f"[LOG] {message}")

### Messages d'accueil ###
def create_welcome_embed(member):
    embed = discord.Embed(
        title=f"Bienvenue {member.name} ! 🎉",
        description=f"Nous sommes ravis de t'accueillir sur **{member.guild.name}** !\n\n"
                    f"Assure-toi de lire les règles et de te présenter dans le channel approprié.",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.set_footer(text=f"ID : {member.id}")
    return embed

def create_goodbye_embed(member):
    embed = discord.Embed(
        title=f"{member.name} a quitté le serveur 😢",
        description=f"Nous espérons te revoir bientôt sur **{member.guild.name}**.\n\n"
                    f"Bonne continuation !",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.set_footer(text=f"ID : {member.id}")
    return embed

# Charger les commandes supplémentaires
from commands.create import setup_create_command
from commands.mudras import setup_mudras_command
from commands.logs import setup_logs_command

setup_create_command(tree)  # Commande create
setup_mudras_command(client, tree)  # Commande mudras
setup_logs_command(tree)  # Commande logs

# Démarrer le bot
@client.event
async def on_ready():
    await tree.sync()
    print(f"We have logged in as {client.user} and synced commands!")

client.run(TOKEN)
