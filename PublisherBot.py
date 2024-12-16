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

### Commande pour créer un menu de rôles ###
@tree.command(name="rolemenu", description="Créer un menu pour attribuer des rôles via des emojis.")
async def rolemenu(interaction: discord.Interaction, roles: str, emojis: str):
    guild = interaction.guild

    # Diviser les rôles et les emojis
    role_names = [name.strip() for name in roles.split(",")]
    emoji_list = [emoji.strip() for emoji in emojis.split(",")]

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

    await interaction.response.defer(ephemeral=True)
    message = await interaction.channel.send(embed=embed)

    # Ajouter les réactions au message
    for emoji in emoji_list:
        await message.add_reaction(emoji)

    # Stocker l'association message-rôles
    role_menu_mapping[message.id] = {emoji: role for emoji, role in zip(emoji_list, role_objects)}
    print(f"[DEBUG] Role Menu Mapping : {role_menu_mapping}")
    await interaction.followup.send("Le menu des rôles a été créé avec succès !", ephemeral=True)

### Gestion des réactions pour les rôles ###
@client.event
async def on_raw_reaction_add(payload):
    if payload.user_id == client.user.id:
        return  # Ignorer les réactions du bot

    if payload.message_id in role_menu_mapping:
        guild = client.get_guild(payload.guild_id)
        if not guild:
            return

        role_mapping = role_menu_mapping[payload.message_id]
        emoji = str(payload.emoji)

        # Corriger le format pour les emojis personnalisés
        if isinstance(payload.emoji, discord.PartialEmoji) and payload.emoji.id:
            emoji = f"<:{payload.emoji.name}:{payload.emoji.id}>"

        role = role_mapping.get(emoji)
        if role:
            try:
                member = await guild.fetch_member(payload.user_id)
                if member:
                    # Vérifier la hiérarchie des rôles
                    if role.position >= guild.me.top_role.position:
                        return
                    await member.add_roles(role)
            except Exception as e:
                print(f"[ERROR] Erreur lors de l'ajout du rôle : {e}")

@client.event
async def on_raw_reaction_remove(payload):

    if payload.user_id == client.user.id:
        return  # Ignorer les réactions du bot

    if payload.message_id in role_menu_mapping:
        guild = client.get_guild(payload.guild_id)
        if not guild:
            return

        role_mapping = role_menu_mapping[payload.message_id]
        emoji = str(payload.emoji)

        # Corriger le format pour les emojis personnalisés
        if isinstance(payload.emoji, discord.PartialEmoji) and payload.emoji.id:
            emoji = f"<:{payload.emoji.name}:{payload.emoji.id}>"

        role = role_mapping.get(emoji)
        if role:
            try:
                member = await guild.fetch_member(payload.user_id)
                if member:
                    await member.remove_roles(role)
            except Exception as e:
                print(f"[ERROR] Erreur lors du retrait du rôle : {e}")

### Logs ###
async def log_action(guild, message):
    print(f"[LOG] {message}")

# Charger les commandes supplémentaires
from commands.create import setup_create_command
from commands.mudras import setup_mudras_command
from commands.logs import setup_logs_command
from commands.rapport import setup_rapport_command
setup_create_command(tree)  # Commande create
setup_mudras_command(client, tree)  # Commande mudras
setup_logs_command(tree)  # Commande logs
setup_rapport_command(tree)  # Commande rapport

### Démarrage du bot ###
@client.event
async def on_ready():
    await setup_rapport_command(tree)
    await tree.sync()
    print(f"Connecté en tant que {client.user}")

client.run(TOKEN)
