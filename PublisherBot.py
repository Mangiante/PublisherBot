import discord
from discord import app_commands, Interaction
from discord.ext import commands
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import cohere
import os

# Charger les variables d'environnement
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
co = cohere.Client(COHERE_API_KEY)

# Configurer les intents
intents = discord.Intents.default()
intents.message_content = True
intents.guild_reactions = True
intents.guilds = True
intents.members = True

# Initialiser le bot
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Données pour les mudras
mudras = {
    "🐕": ("mudras/chien.png", "Chien"),
    "🐗": ("mudras/cochon.png", "Cochon"),
    "🐉": ("mudras/dragon.png", "Dragon"),
    "🐅": ("mudras/tigre.png", "Tigre"),
    "🐂": ("mudras/buffle.png", "Buffle"),
    "🐍": ("mudras/serpent.png", "Serpent"),
    "🐴": ("mudras/cheval.png", "Cheval"),
    "🐐": ("mudras/chevre.png", "Chèvre"),
    "🐀": ("mudras/rat.png", "Rat"),
    "🐇": ("mudras/lievre.png", "Lièvre"),
    "🐒": ("mudras/singe.png", "Singe"),
    "🐓": ("mudras/coq.png", "Coq"),
}
cancel_emoji = "🚫"
finish_emoji = "✅"

user_choices = {}
RAPPORT_COUNT_FILE = "rapport_counts.txt"

### Utilitaires ###
def read_counts():
    if not os.path.exists(RAPPORT_COUNT_FILE):
        return {}
    with open(RAPPORT_COUNT_FILE, "r") as file:
        return {int(line.split(":")[0]): int(line.split(":")[1]) for line in file.readlines()}

def write_counts(counts):
    with open(RAPPORT_COUNT_FILE, "w") as file:
        for user_id, count in counts.items():
            file.write(f"{user_id}:{count}\n")

def increment_count(user_id):
    counts = read_counts()
    counts[user_id] = counts.get(user_id, 0) + 1
    write_counts(counts)
    return counts[user_id]

### Commande /create ###
@tree.command(name="create", description="Créer un channel textuel ou vocal dans une catégorie.")
async def create(interaction: discord.Interaction, type: str, name: str, category: str = None):
    guild = interaction.guild
    if type.lower() not in ["textuel", "vocal"]:
        await interaction.response.send_message("Le type doit être `textuel` ou `vocal`.", ephemeral=True)
        return

    discord_category = None
    if category:
        discord_category = discord.utils.get(guild.categories, name=category)
        if not discord_category:
            await interaction.response.send_message(f"La catégorie **{category}** n'existe pas.", ephemeral=True)

    if type.lower() == "textuel":
        await guild.create_text_channel(name, category=discord_category)
    else:
        await guild.create_voice_channel(name, category=discord_category)

    await interaction.response.send_message(f"Le channel **{name}** a été créé avec succès !", ephemeral=True)

### Commande /logs ###
@tree.command(name="logs", description="Créer un channel de logs pour les admins.")
async def logs(interaction: discord.Interaction):
    guild = interaction.guild
    existing_logs_channel = discord.utils.get(guild.text_channels, name="logs")
    if existing_logs_channel:
        await interaction.response.send_message("Le channel de logs existe déjà.", ephemeral=True)
        return

    logs_channel = await guild.create_text_channel("logs")
    await logs_channel.set_permissions(guild.default_role, read_messages=False, send_messages=False)
    await interaction.response.send_message(f"Le channel de logs a été créé : {logs_channel.mention}")

role_menu_mapping = {}  # Dictionnaire global pour stocker les associations message/rôles
### Commande /rolemenu ###
@tree.command(name="rolemenu", description="Créer un menu pour attribuer des rôles via des emojis.")
async def rolemenu(interaction: discord.Interaction, roles: str, emojis: str):
    guild = interaction.guild
    role_names = [name.strip() for name in roles.split(",")]
    emoji_list = [emoji.strip() for emoji in emojis.split(",")]

    # Vérifier la correspondance entre rôles et emojis
    if len(role_names) != len(emoji_list):
        await interaction.response.send_message("Le nombre de rôles et d'emojis doit être identique.", ephemeral=True)
        return

    # Vérifier que les rôles existent
    role_objects = []
    for role_name in role_names:
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            await interaction.response.send_message(f"Le rôle **{role_name}** n'existe pas.", ephemeral=True)
            return
        role_objects.append(role)

    # Créer un embed pour afficher le menu
    embed = discord.Embed(
        title="Menu des rôles",
        description="\n".join([f"{emoji} : **{role.name}**" for emoji, role in zip(emoji_list, role_objects)]),
        color=discord.Color.blue()
    )
    await interaction.response.defer(ephemeral=True)  # Déférer la réponse
    message = await interaction.channel.send(embed=embed)

    # Ajouter les réactions au message
    for emoji in emoji_list:
        await message.add_reaction(emoji)

    # Stocker les rôles associés aux emojis dans un dictionnaire global
    role_menu_mapping[message.id] = {emoji: role for emoji, role in zip(emoji_list, role_objects)}
    await interaction.followup.send("Menu des rôles créé avec succès !", ephemeral=True)

@tree.command(name="mudras", description="Choisissez vos mudras et entrez un nom de technique.")
async def mudras_command(interaction: discord.Interaction, technique: str):
    user_id = interaction.user.id
    user_choices[user_id] = {"mudras": [], "technique": technique}

    embed = discord.Embed(
        title="Choisissez vos mudras",
        description=f"Technique : **{technique}**\n\n"
                    "Réagissez avec les emojis pour sélectionner vos mudras.\n"
                    "✅ : Terminer | 🚫 : Annuler\n\n" +
                    "\n".join([f"{emoji} : {name}" for emoji, (_, name) in mudras.items()]),
        color=discord.Color.blue(),
    )
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()

    # Ajouter les réactions aux emojis
    for emoji in mudras.keys():
        await message.add_reaction(emoji)
    await message.add_reaction(finish_emoji)
    await message.add_reaction(cancel_emoji)

def create_combined_image(selected_emojis, technique_name):
    # Générer une liste des images avec les doublons pris en compte
    mudra_images = []
    for emoji in selected_emojis:
        image_path, name = mudras[emoji]
        mudra_images.append((Image.open(image_path), name))

    # Calculer largeur et hauteur
    total_width = sum(img.width for img, _ in mudra_images)
    max_height = max(img.height for img, _ in mudra_images) + 50

    # Créer l'image combinée
    combined_image = Image.new("RGBA", (total_width, max_height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(combined_image)

    font_path = "arial.ttf"
    try:
        font = ImageFont.truetype(font_path, 20)
    except:
        font = ImageFont.load_default()

    # Coller chaque image avec les doublons inclus
    x_offset = 0
    for img, name in mudra_images:
        combined_image.paste(img, (x_offset, 0))
        draw.text((x_offset + 10, img.height + 5), name, fill="black", font=font)
        x_offset += img.width

    # Ajouter le nom de la technique
    draw.text((10, max_height - 30), f"Technique : {technique_name}", fill="black", font=font)

    # Enregistrer et retourner le chemin de l'image
    output_path = "mudras/combined.png"
    combined_image.save(output_path)
    return output_path

@tree.command(name="rapport", description="Générer un rapport journalier basé sur une mission.")
async def rapport_command(interaction: Interaction, texte: str):
    await interaction.response.defer()

    user = interaction.user
    member = interaction.guild.get_member(user.id)

    # Incrémenter le compteur pour l'utilisateur
    report_number = increment_count(user.id)

    date_today = datetime.now().strftime("%d/%m")
    grade = await fetch_role(member)

    prompt = (
        f"Je suis un ninja en mission et je rédige mon rapport journalier.\n"
        f"Mission : {texte}\n\n"
        f"Rédige un rapport immersif et captivant à la première personne, en 3 à 5 paragraphes maximum. "
        f"Assure-toi de terminer le rapport avec une conclusion naturelle et claire."
    )

    try:
        response = co.generate(
            model='command-xlarge-nightly',
            prompt=prompt,
            max_tokens=800,
            temperature=0.7,
            k=0,
            p=0.75,
            frequency_penalty=0.1
        )

        report_text = response.generations[0].text.strip()

        # Nettoyer le texte s'il finit par "..."
        if report_text.endswith("..."):
            report_text = report_text.rstrip("...") + " Cette mission m'a permis d'en apprendre davantage sur mes capacités et ma détermination."

        # Construire le rapport
        header = (
            f"Rapport Journalier – {date_today} #{report_number}\n"
            f"Identité : {user.display_name}\n"
            f"Grade : {grade}\n"
            f"Escouade : (vide)\n\n"
        )

        # Tronquer si le message complet dépasse 2000 caractères
        max_length = 2000 - len("```\n\n```") - len(header)
        truncated_report_text = report_text[:max_length].rsplit('.', 1)[0] + "."

        rapport = f"```\n{header}{truncated_report_text}\n```"

        await interaction.followup.send(rapport)

    except Exception as e:
        await interaction.followup.send(
            f"Une erreur est survenue lors de la génération du rapport : {str(e)}", ephemeral=True
        )

async def fetch_role(member):
    """
    Retourne le grade le plus élevé attribué à un utilisateur basé sur ses rôles Discord.
    """
    if not member.roles:
        return "Aucun"
    sorted_roles = sorted(member.roles, key=lambda r: r.position, reverse=True)
    for role in sorted_roles:
        if role.name.lower() in ["tokubetsu jonin", "kakunin", "chuunin", "genin confirmé", "genin", "apprenti genin"]:
            return role.name
    return "Aucun"

@client.event
async def on_raw_reaction_add(payload):
    user_id = payload.user_id
    if user_id == client.user.id:
        return  # Ignorer les réactions du bot

    # Récupérer les informations du serveur
    guild = client.get_guild(payload.guild_id)
    channel = guild.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    emoji = str(payload.emoji)

    ### Gestion des rôles (rolemenu) ###
    if payload.message_id in role_menu_mapping:
        role = role_menu_mapping[payload.message_id].get(emoji)
        if role:
            member = await guild.fetch_member(payload.user_id)
            if role not in member.roles:
                await member.add_roles(role)
                print(f"[DEBUG] Rôle ajouté : {role.name} à {member.name}")
        return  # Ne pas exécuter le reste si c'était un rôle

    ### Gestion des mudras ###
    if user_id in user_choices:  # Vérifier si l'utilisateur sélectionne des mudras
        if emoji == cancel_emoji:
            await channel.send(f"**{client.get_user(user_id).mention}** a annulé la sélection des mudras.", delete_after=5)
            user_choices.pop(user_id, None)
            await message.delete()
            return

        if emoji == finish_emoji:
            selected_mudras = user_choices[user_id]["mudras"]
            technique = user_choices[user_id]["technique"]
            if not selected_mudras:
                await channel.send(f"**{client.get_user(user_id).mention}**, vous n'avez sélectionné aucun mudra.")
                return

            # Créer l'image combinée
            combined_image_path = create_combined_image(selected_mudras, technique)
            user_choices.pop(user_id)

            # Envoyer l'image avec le récapitulatif
            mudra_names = [mudras[e][1] for e in selected_mudras]
            await channel.send(
                content=f"**Récapitulatif :**\n**Technique** : {technique}\n**Mudras :** {', '.join(mudra_names)}",
                file=discord.File(combined_image_path),
            )
            await message.delete()
            return

        if emoji in mudras:
            user_choices[user_id]["mudras"].append(emoji)

@client.event
async def on_raw_reaction_remove(payload):
    if payload.message_id in role_menu_mapping:
        guild = client.get_guild(payload.guild_id)
        role = role_menu_mapping[payload.message_id].get(str(payload.emoji))
        if role:
            member = await guild.fetch_member(payload.user_id)
            await member.remove_roles(role)

### Démarrage ###
@client.event
async def on_ready():
    await tree.sync()
    print(f"Connecté en tant que {client.user}")

client.run(TOKEN)
