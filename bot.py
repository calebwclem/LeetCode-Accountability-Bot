import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
from db.database import Database

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")


class LeetCodeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.db = Database(DATABASE_URL)

    async def setup_hook(self):
        await self.db.connect()
        await self.db.init_schema()

        # Load all cogs
        await self.load_extension("cogs.registration")
        await self.load_extension("cogs.stats")
        await self.load_extension("cogs.leaderboard")
        await self.load_extension("cogs.unregister")

        # Sync slash commands globally (use guild-specific sync for faster testing)
        await self.tree.sync()
        print("Slash commands synced.")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="your LeetCode grind 👀"
            )
        )

    async def close(self):
        await self.db.close()
        await super().close()


async def main():
    bot = LeetCodeBot()
    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())