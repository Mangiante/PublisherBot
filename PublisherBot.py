import discord
from discord import app_commands
from dotenv import load_dotenv
import os

# Charger les variables d'environnement
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Configurer les intents
intents = discord.Intents.default()
intents.message_content = True
intents.guild_reactions = True
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Dictionnaire global pour mapper les messages aux rôles
role_menu_mapping = {}

@client.event
async def on_ready():
    await tree.sync()
    print(f"We have logged in as {client.user} and synced commands!")

# Commande pour créer un menu de rôles
@tree.command(name="rolemenu", description="Créer un menu pour attribuer des rôles via des emojis.")
async def rolemenu(interaction: discord.Interaction, roles: str, emojis: str):
    """
    - roles: Une liste des noms de rôles séparés par des virgules (par exemple: "Rôle1,Rôle2,Rôle3").
    - emojis: Une liste des emojis correspondants séparés par des virgules (par exemple: "😀,👍,🔥").
    """
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
    print(f"[DEBUG] role_menu_mapping : {role_menu_mapping}")

    await interaction.response.send_message("Le menu des rôles a été créé avec succès !", ephemeral=True)

# Gestion des événements pour les réactions
@client.event
async def on_raw_reaction_add(payload):
    print("[DEBUG] Event on_raw_reaction_add triggered")
    if payload.user_id == client.user.id:
        return  # Ignorer les réactions ajoutées par le bot

    if payload.message_id in role_menu_mapping:
        guild = client.get_guild(payload.guild_id)
        if not guild:
            return

        role_mapping = role_menu_mapping[payload.message_id]
        emoji = str(payload.emoji)
        if payload.emoji.is_custom_emoji():
            emoji = f"<:{payload.emoji.name}:{payload.emoji.id}>"

        role = role_mapping.get(emoji)
        if role:
            try:
                member = await guild.fetch_member(payload.user_id)
                if member:
                    await member.add_roles(role)
                    print(f"[DEBUG] Role {role.name} added to {member.name}.")
            except Exception as e:
                print(f"[DEBUG] Error adding role: {e}")

@client.event
async def on_raw_reaction_remove(payload):
    print("[DEBUG] Event on_raw_reaction_remove triggered")
    if payload.user_id == client.user.id:
        return  # Ignorer les réactions retirées par le bot

    if payload.message_id in role_menu_mapping:
        guild = client.get_guild(payload.guild_id)
        if not guild:
            return

        role_mapping = role_menu_mapping[payload.message_id]
        emoji = str(payload.emoji)
        if payload.emoji.is_custom_emoji():
            emoji = f"<:{payload.emoji.name}:{payload.emoji.id}>"

        role = role_mapping.get(emoji)
        if role:
            try:
                member = await guild.fetch_member(payload.user_id)
                if member:
                    await member.remove_roles(role)
                    print(f"[DEBUG] Role {role.name} removed from {member.name}.")
            except Exception as e:
                print(f"[DEBUG] Error removing role: {e}")

client.run(TOKEN)
