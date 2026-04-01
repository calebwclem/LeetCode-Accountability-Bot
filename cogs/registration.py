import discord
from discord import app_commands
from discord.ext import commands
from api.leetcode import leetcode, LeetCodeAPIError


class Registration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="register",
        description="Link your Discord account to your LeetCode profile."
    )
    @app_commands.describe(username="Your LeetCode username (case-sensitive)")
    async def register(self, interaction: discord.Interaction, username: str):
        await interaction.response.defer(ephemeral=True)

        # Validate the username against LeetCode before saving
        try:
            stats = await leetcode.get_user_stats(username)
        except LeetCodeAPIError as e:
            await interaction.followup.send(
                f"❌ Couldn't verify that LeetCode account: `{e}`\n"
                "Make sure your profile is public and the username is correct.",
                ephemeral=True
            )
            return

        # Save to DB
        await self.bot.db.register_user(
            discord_id=interaction.user.id,
            server_id=interaction.guild_id,
            leetcode_username=stats["username"],  # use canonical casing from API
        )

        embed = discord.Embed(
            title="✅ Registered!",
            description=(
                f"Linked **{interaction.user.mention}** → "
                f"[{stats['username']}](https://leetcode.com/{stats['username']}/)"
            ),
            color=discord.Color.green()
        )
        embed.add_field(name="Problems Solved", value=str(stats["total"]), inline=True)
        embed.add_field(name="Global Rank", value=f"#{stats['ranking']:,}", inline=True)
        embed.set_footer(text="Use /stats to see your full breakdown anytime.")

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Registration(bot))