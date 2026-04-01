import discord
from discord import app_commands
from discord.ext import commands
from api.leetcode import leetcode, LeetCodeAPIError

# Difficulty bar config
DIFFICULTY_COLORS = {
    "easy":   ("🟢", discord.Color.green()),
    "medium": ("🟡", discord.Color.gold()),
    "hard":   ("🔴", discord.Color.red()),
}

# Rough total problems per difficulty as of early 2025 (for progress bars)
DIFFICULTY_TOTALS = {"easy": 820, "medium": 1720, "hard": 740}


def progress_bar(solved: int, total: int, length: int = 12) -> str:
    filled = round((solved / total) * length) if total else 0
    return "█" * filled + "░" * (length - filled)


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="stats",
        description="Show LeetCode stats for yourself or another server member."
    )
    @app_commands.describe(member="The Discord member to look up (defaults to you)")
    async def stats(
        self,
        interaction: discord.Interaction,
        member: discord.Member = None
    ):
        await interaction.response.defer()

        target = member or interaction.user

        # Look up their registered LeetCode username
        user_row = await self.bot.db.get_user(target.id, interaction.guild_id)
        if not user_row:
            msg = (
                "You haven't registered yet. Use `/register` to link your account."
                if target == interaction.user
                else f"{target.mention} hasn't registered yet."
            )
            await interaction.followup.send(msg, ephemeral=True)
            return

        lc_username = user_row["leetcode_username"]

        try:
            stats = await leetcode.get_user_stats(lc_username)
        except LeetCodeAPIError as e:
            await interaction.followup.send(
                f"❌ Couldn't fetch stats for `{lc_username}`: {e}", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"📊 {lc_username}'s LeetCode Stats",
            url=f"https://leetcode.com/{lc_username}/",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(
            name="Total Solved",
            value=f"**{stats['total']}** problems",
            inline=False
        )

        for diff in ("easy", "medium", "hard"):
            emoji, _ = DIFFICULTY_COLORS[diff]
            solved = stats[diff]
            total = DIFFICULTY_TOTALS[diff]
            bar = progress_bar(solved, total)
            pct = round((solved / total) * 100) if total else 0
            embed.add_field(
                name=f"{emoji} {diff.capitalize()}",
                value=f"`{bar}` {solved}/{total} ({pct}%)",
                inline=False
            )

        embed.add_field(name="Global Rank", value=f"#{stats['ranking']:,}", inline=True)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Stats(bot))