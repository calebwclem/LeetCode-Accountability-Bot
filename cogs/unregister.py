import discord
from discord import app_commands
from discord.ext import commands


class Unregister(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="unregister",
        description="Unlink your LeetCode account and remove yourself from the leaderboard."
    )
    async def unregister(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_row = await self.bot.db.get_user(interaction.user.id, interaction.guild_id)
        if not user_row:
            await interaction.followup.send(
                "You're not registered in this server.", ephemeral=True
            )
            return

        deleted = await self.bot.db.unregister_user(interaction.user.id, interaction.guild_id)
        if deleted:
            await interaction.followup.send(
                "✅ You've been unregistered and removed from the leaderboard. "
                "Use `/register` anytime to rejoin.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "Something went wrong — please try again.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Unregister(bot))