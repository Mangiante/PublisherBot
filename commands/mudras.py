import discord
from PIL import Image, ImageDraw, ImageFont  # Pour manipuler les images
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

# Stocker les choix des utilisateurs
user_choices = {}

def setup_mudras_command(client, tree):
    @tree.command(name="mudras", description="Choisissez 3 mudras et entrez un nom de technique.")
    async def mudras_command(interaction: discord.Interaction, technique: str):
        """
        Commande `/mudras` :
        - technique : Nom de la technique saisie par l'utilisateur.
        """
        user_id = interaction.user.id
        user_choices[user_id] = {"mudras": [], "technique": technique}  # Stocker le nom de la technique et les choix

        embed = discord.Embed(
            title="Choisissez vos mudras",
            description=f"Technique : **{technique}**\n\n"
                        "Réagissez avec les emojis pour sélectionner vos 3 mudras !\n\n" +
                        "\n".join([f"{emoji} : {name}" for emoji, (_, name) in mudras.items()]),
            color=discord.Color.blue(),
        )
        message = await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()  # Récupérer le message envoyé

        # Ajouter les réactions
        for emoji in mudras.keys():
            await message.add_reaction(emoji)

    @client.event
    async def on_raw_reaction_add(payload):
        # Vérifier si l'utilisateur fait partie des choix actifs
        user_id = payload.user_id
        if user_id not in user_choices:
            return

        emoji = str(payload.emoji)
        if emoji not in mudras:
            return

        # Ajouter le mudra choisi
        user_choices[user_id]["mudras"].append(emoji)
        if len(user_choices[user_id]["mudras"]) == 3:
            # Lorsque 3 choix sont faits, créer l'image combinée
            selected_mudras = user_choices[user_id]["mudras"]
            technique = user_choices[user_id]["technique"]
            combined_image_path = create_combined_image(selected_mudras, technique)
            user_choices.pop(user_id)  # Réinitialiser après la création

            guild = client.get_guild(payload.guild_id)
            channel = guild.get_channel(payload.channel_id)
            await channel.send(
                content=f"**Récapitulatif :**\n**Technique** : {technique}\n**Mudras :** {', '.join([mudras[e][1] for e in selected_mudras])}",
                file=discord.File(combined_image_path),
            )


def create_combined_image(selected_emojis, technique_name):
    # Charger les images sélectionnées
    images = [(Image.open(mudras[emoji][0]), mudras[emoji][1]) for emoji in selected_emojis]

    # Calculer la largeur et la hauteur combinées
    total_width = sum(img.width for img, _ in images)
    max_height = max(img.height for img, _ in images) + 50  # Ajouter de l'espace pour le texte

    # Créer une nouvelle image vide
    combined_image = Image.new("RGBA", (total_width, max_height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(combined_image)

    # Charger une police (par défaut si pas de fichier TTF)
    font_path = "arial.ttf"  # Remplacez par le chemin vers une police valide si nécessaire
    try:
        font = ImageFont.truetype(font_path, 20)
    except:
        font = ImageFont.load_default()

    # Coller les images sélectionnées avec leur nom
    x_offset = 0
    for img, name in images:
        combined_image.paste(img, (x_offset, 0))
        text_bbox = draw.textbbox((0, 0), name, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        text_x = x_offset + (img.width - text_width) // 2
        text_y = img.height + 5
        draw.text((text_x, text_y), name, fill="black", font=font)
        x_offset += img.width

    # Ajouter le nom de la technique en haut
    draw.text((10, max_height - 30), f"Technique : {technique_name}", fill="black", font=font)

    # Enregistrer l'image finale
    output_path = "mudras/combined.png"
    combined_image.save(output_path)
    return output_path
