import discord
from discord import app_commands
from discord.ext import commands
from api.leetcode import leetcode, LeetCodeAPIError
import asyncio

MEDAL = {1: "🥇", 2: "🥈", 3: "🥉"}
PROBLEMS_PER_PAGE = 10


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="leaderboard",
        description="Show the server LeetCode leaderboard ranked by total problems solved."
    )
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()

        users = await self.bot.db.get_all_users_in_server(interaction.guild_id)

        if not users:
            await interaction.followup.send(
                "Nobody has registered yet! Use `/register` to get on the board.",
                ephemeral=True
            )
            return

        # Fetch stats for all users concurrently, with a small stagger
        # to be polite to the LeetCode API
        async def fetch_with_stagger(user, delay: float):
            await asyncio.sleep(delay)
            try:
                stats = await leetcode.get_user_stats(user["leetcode_username"])
                return {**user, **stats}
            except LeetCodeAPIError:
                # User may have gone private; skip gracefully
                return None

        tasks = [
            fetch_with_stagger(u, i * 0.3)  # 300ms stagger per user
            for i, u in enumerate(users)
        ]
        results = await asyncio.gather(*tasks)

        # Filter out failures and sort by total problems solved
        ranked = sorted(
            [r for r in results if r is not None],
            key=lambda x: x["total"],
            reverse=True
        )

        if not ranked:
            await interaction.followup.send(
                "Couldn't fetch stats for any registered users right now. Try again shortly.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🏆 {interaction.guild.name} LeetCode Leaderboard",
            color=discord.Color.gold()
        )

        lines = []
        for rank, entry in enumerate(ranked, start=1):
            medal = MEDAL.get(rank, f"`{rank:>2}.`")
            # Try to get Discord display name for the member
            member = interaction.guild.get_member(entry["discord_id"])
            display = member.display_name if member else entry["leetcode_username"]

            line = (
                f"{medal} **{display}** — "
                f"[{entry['username']}](https://leetcode.com/{entry['username']}/) "
                f"· {entry['total']} solved "
                f"({entry['easy']}E / {entry['medium']}M / {entry['hard']}H)"
            )
            lines.append(line)

        embed.description = "\n".join(lines)
        embed.set_footer(
            text=f"{len(ranked)} member{'s' if len(ranked) != 1 else ''} registered · "
                 "Use /register to join the leaderboard"
        )

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))