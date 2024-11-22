import discord

def setup_logs_command(tree: discord.app_commands.CommandTree):
    @tree.command(name="logs", description="Créer un channel de logs pour les admins.")
    async def logs(interaction: discord.Interaction):
        """
        Commande `/logs` :
        - Crée un channel de logs pour les admins.
        """
        guild = interaction.guild

        # Vérifier si le channel de logs existe déjà
        existing_logs_channel = discord.utils.get(guild.text_channels, name="logs")
        if existing_logs_channel:
            await interaction.response.send_message(
                "Le channel de logs existe déjà.", ephemeral=True
            )
            return

        # Créer le channel de logs
        logs_channel = await guild.create_text_channel("logs")

        # Ajoute les permissions uniquement pour les administrateurs
        await logs_channel.set_permissions(
            guild.default_role, read_messages=False, send_messages=False
        )

        await interaction.response.send_message(
            f"Le channel de logs a été créé avec succès : {logs_channel.mention}"
        )

