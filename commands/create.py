import discord
from discord import app_commands

def setup_create_command(tree: discord.app_commands.CommandTree):
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
