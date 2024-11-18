import discord
from dotenv import load_dotenv
import os
from keep_alive import keep_alive  # Import du fichier keep_alive

# Charger les variables d'environnement
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Intents nécessaires
intents = discord.Intents.default()
intents.message_content = True

# Client Discord
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Commande `/create`
    if message.content.startswith('/create'):
        # Envoie le sondage
        poll_message = await message.channel.send(
            "Voulez-vous créer un channel **textuel** ou **vocal** ? Réagissez avec 📝 pour textuel ou 🎤 pour vocal."
        )

        # Ajoute les réactions pour le sondage
        await poll_message.add_reaction("📝")
        await poll_message.add_reaction("🎤")

        # Attend les réactions
        def check_reaction(reaction, user):
            return user == message.author and str(reaction.emoji) in ["📝", "🎤"]

        try:
            reaction, user = await client.wait_for("reaction_add", timeout=60.0, check=check_reaction)
        except TimeoutError:
            await message.channel.send("Temps écoulé ! Réessayez avec `/create`.")
            return

        # Détermine le type de canal
        channel_type = "textuel" if str(reaction.emoji) == "📝" else "vocal"

        # Demande le nom du canal
        await message.channel.send(f"Vous avez choisi un channel {channel_type}. Veuillez entrer le nom du channel.")

        def check_message(m):
            return m.author == message.author and m.channel == message.channel

        try:
            name_message = await client.wait_for("message", timeout=60.0, check=check_message)
            channel_name = name_message.content
        except TimeoutError:
            await message.channel.send("Temps écoulé ! Réessayez avec `/create`.")
            return

        # Crée le channel
        guild = message.guild
        if channel_type == "textuel":
            await guild.create_text_channel(channel_name)
        else:
            await guild.create_voice_channel(channel_name)

        await message.channel.send(f"Le channel **{channel_name}** a été créé avec succès !")

# Garder le bot en ligne
keep_alive()

# Démarrer le bot
client.run(TOKEN)
