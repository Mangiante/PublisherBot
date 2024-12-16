import discord
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
import os

# Dictionnaire des mudras (emoji -> chemin vers l'image PNG et nom du mudra)
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
cancel_emoji = "🚫"  # Emoji pour annuler
finish_emoji = "✅"  # Emoji pour finir
user_choices = {}  # Stocker les choix des utilisateurs

def setup_mudras_command(client, tree):
    @tree.command(name="mudras", description="Choisissez vos mudras et entrez un nom de technique.")
    async def mudras_command(interaction: discord.Interaction, technique: str):
        user_id = interaction.user.id
        user_choices[user_id] = {"mudras": [], "technique": technique}

        embed = discord.Embed(
            title="Choisissez vos mudras",
            description=f"Technique : **{technique}**\n\n"
                        "Réagissez avec les emojis pour sélectionner vos mudras.\n"
                        "Réagissez avec ✅ pour terminer ou 🚫 pour annuler.\n\n" +
                        "\n".join([f"{emoji} : {name}" for emoji, (_, name) in mudras.items()]),
            color=discord.Color.blue(),
        )
        message = await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        for emoji in mudras.keys():
            await message.add_reaction(emoji)
        await message.add_reaction(finish_emoji)
        await message.add_reaction(cancel_emoji)

    @client.event
    async def on_raw_reaction_add(payload):
        user_id = payload.user_id
        if user_id == client.user.id or user_id not in user_choices:
            return

        emoji = str(payload.emoji)
        guild = client.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        if emoji == cancel_emoji:
            await channel.send(f"**{client.get_user(user_id).mention}** a annulé la sélection des mudras.")
            user_choices.pop(user_id, None)
            await message.delete()
            return

        if emoji == finish_emoji:
            selected_mudras = user_choices[user_id]["mudras"]
            technique = user_choices[user_id]["technique"]
            if not selected_mudras:
                await channel.send(f"**{client.get_user(user_id).mention}**, vous n'avez sélectionné aucun mudra.")
                return

            combined_image_path = create_combined_image(selected_mudras, technique)
            user_choices.pop(user_id)

            await channel.send(
                content=f"**Récapitulatif :**\n**Technique** : {technique}\n**Mudras :** {', '.join([mudras[e][1] for e in selected_mudras])}",
                file=discord.File(combined_image_path),
            )
            await message.delete()
            return

        if emoji in mudras:
            user_choices[user_id]["mudras"].append(emoji)  # Conserver les doublons
            await channel.send(f"**{mudras[emoji][1]}** ajouté !", delete_after=1)  # Message temporaire

def create_combined_image(selected_emojis, technique_name):
    # Charger chaque image de mudra
    images = [(Image.open(mudras[emoji][0]), mudras[emoji][1]) for emoji in selected_emojis]

    # Calculer la largeur et la hauteur
    total_width = sum(img.width for img, _ in images)
    max_height = max(img.height for img, _ in images) + 50

    # Créer une image vide
    combined_image = Image.new("RGBA", (total_width, max_height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(combined_image)

    font_path = "arial.ttf"
    try:
        font = ImageFont.truetype(font_path, 20)
    except:
        font = ImageFont.load_default()

    x_offset = 0
    for img, name in images:
        combined_image.paste(img, (x_offset, 0))
        text_x = x_offset + (img.width - draw.textlength(name, font=font)) // 2
        text_y = img.height + 5
        draw.text((text_x, text_y), name, fill="black", font=font)
        x_offset += img.width

    draw.text((10, max_height - 30), f"Technique : {technique_name}", fill="black", font=font)
    output_path = "mudras/combined.png"
    combined_image.save(output_path)
    return output_path
