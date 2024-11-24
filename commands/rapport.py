from discord import app_commands, Interaction
from datetime import datetime
import cohere
import os

# Initialisation de Cohere
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
co = cohere.Client(COHERE_API_KEY)

# Nom du fichier pour stocker les données
RAPPORT_COUNT_FILE = "rapport_counts.txt"

def read_counts():
    if not os.path.exists(RAPPORT_COUNT_FILE):
        return {}
    with open(RAPPORT_COUNT_FILE, "r") as file:
        lines = file.readlines()
    return {int(line.split(":")[0]): int(line.split(":")[1]) for line in lines}

def write_counts(counts):
    with open(RAPPORT_COUNT_FILE, "w") as file:
        for user_id, count in counts.items():
            file.write(f"{user_id}:{count}\n")

def increment_count(user_id):
    counts = read_counts()
    if user_id not in counts:
        counts[user_id] = 0
    counts[user_id] += 1
    write_counts(counts)
    return counts[user_id]

async def fetch_role(member):
    if not member.roles:
        return "Aucun"
    sorted_roles = sorted(member.roles, key=lambda r: r.position, reverse=True)
    for role in sorted_roles:
        if role.name.lower() in ["tokubetsu jonin", "kakunin", "chuunin", "genin confirmé", "genin", "apprenti genin"]:
            return role.name
    return "Aucun"

async def setup_rapport_command(tree: app_commands.CommandTree):
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

            if report_text.endswith("..."):
                report_text = report_text.rstrip("...") + " Cette mission m'a permis d'en apprendre davantage sur mes capacités et ma détermination."

            max_characters = 1500
            if len(report_text) > max_characters:
                report_text = report_text[:max_characters].rsplit('.', 1)[0] + "."

            rapport = (
                f"Rapport Journalier – {date_today} #{report_number}\n"
                f"Identité : {user.display_name}\n"
                f"Grade : {grade}\n"
                f"Escouade : (vide)\n\n"
                f"{report_text}"
            )

            await interaction.followup.send(f"```\n{rapport}\n```")

        except Exception as e:
            await interaction.followup.send(
                f"Une erreur est survenue lors de la génération du rapport : {str(e)}", ephemeral=True
            )
