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

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    # Synchroniser les commandes slash avec le serveur
    await tree.sync()
    print(f"We have logged in as {client.user} and synced commands!")

# Commande /create
@tree.command(name="create", description="Créer un channel textuel ou vocal dans une catégorie.")
async def create(interaction: discord.Interaction,
                 type: str,
                 name: str,
                 category: str = None):
    """
    - type: `textuel` ou `vocal`
    - name: Nom du channel
    - category: (Optionnel) Nom de la catégorie où créer le channel
    """
    guild = interaction.guild

    # Vérification du type de channel
    if type.lower() not in ["textuel", "vocal"]:
        await interaction.response.send_message("Le type doit être `textuel` ou `vocal`.", ephemeral=True)
        return

    # Récupérer la catégorie si elle est spécifiée
    discord_category = None
    if category:
        discord_category = discord.utils.get(guild.categories, name=category)
        if not discord_category:
            await interaction.response.send_message(
                f"La catégorie **{category}** n'existe pas. Le channel sera créé sans catégorie.",
                ephemeral=True,
            )
            discord_category = None

    # Créer le channel
    if type.lower() == "textuel":
        await guild.create_text_channel(name, category=discord_category)
    else:
        await guild.create_voice_channel(name, category=discord_category)

    await interaction.response.send_message(
        f"Le channel **{name}** a été créé avec succès{' dans la catégorie ' + discord_category.name if discord_category else ''} !"
    )

client.run(TOKEN)
