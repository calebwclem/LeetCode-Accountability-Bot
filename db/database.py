import asyncpg
from typing import Optional


class Database:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.database_url, min_size=2, max_size=10)
        print("Connected to PostgreSQL.")

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def init_schema(self):
        """Create tables if they don't exist."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id              SERIAL PRIMARY KEY,
                    discord_id      BIGINT NOT NULL,
                    server_id       BIGINT NOT NULL,
                    leetcode_username TEXT NOT NULL,
                    created_at      TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE (discord_id, server_id)
                );

                CREATE TABLE IF NOT EXISTS servers (
                    server_id           BIGINT PRIMARY KEY,
                    digest_channel_id   BIGINT,
                    config              JSONB DEFAULT '{}',
                    created_at          TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS goals (
                    id              SERIAL PRIMARY KEY,
                    user_id         INT REFERENCES users(id) ON DELETE CASCADE,
                    daily_target    INT DEFAULT 1,
                    weekly_target   INT DEFAULT 5,
                    updated_at      TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS submissions (
                    id              SERIAL PRIMARY KEY,
                    user_id         INT REFERENCES users(id) ON DELETE CASCADE,
                    date            DATE NOT NULL,
                    problems_solved INT DEFAULT 0,
                    streak          INT DEFAULT 0,
                    UNIQUE(user_id, date)
                );
            """)
        print("Schema initialized.")

    # ── User queries ──────────────────────────────────────────────────────────

    async def register_user(self, discord_id: int, server_id: int, leetcode_username: str) -> dict:
        """Insert or update a user's LeetCode username. Returns the row."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO users (discord_id, server_id, leetcode_username)
                VALUES ($1, $2, $3)
                ON CONFLICT (discord_id, server_id)
                DO UPDATE SET leetcode_username = EXCLUDED.leetcode_username
                RETURNING *;
            """, discord_id, server_id, leetcode_username)
        return dict(row)

    async def get_user(self, discord_id: int, server_id: int) -> Optional[dict]:
        """Fetch a single user by Discord ID and server."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM users
                WHERE discord_id = $1 AND server_id = $2;
            """, discord_id, server_id)
        return dict(row) if row else None

    async def unregister_user(self, discord_id: int, server_id: int) -> bool:
        """Delete a user from the database. Returns True if a row was deleted."""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM users
                WHERE discord_id = $1 AND server_id = $2;
            """, discord_id, server_id)
        return result == "DELETE 1"

    async def get_all_users_in_server(self, server_id: int) -> list[dict]:
        """Fetch all registered users in a server."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM users WHERE server_id = $1
                ORDER BY created_at ASC;
            """, server_id)
        return [dict(r) for r in rows]