import asyncpg
import logging
from datetime import date, datetime
import pytz

from config import SUPABASE_DB_URL

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None

MOSCOW_TZ = pytz.timezone("Europe/Moscow")


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            SUPABASE_DB_URL,
            min_size=1,
            max_size=5,
            statement_cache_size=0,  # required for Supabase Transaction Pooler (pgbouncer)
        )
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id BIGINT PRIMARY KEY,
                username TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                total_generations INT DEFAULT 0,
                paid_tokens INT DEFAULT 0,
                last_free_used DATE,
                easter_egg1 BOOLEAN DEFAULT FALSE
            )
        """)
    logger.info("Database initialized")


async def get_or_create_user(tg_id: int, username: str | None = None) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE tg_id = $1", tg_id
        )
        if row is None:
            await conn.execute(
                """
                INSERT INTO users (tg_id, username)
                VALUES ($1, $2)
                ON CONFLICT (tg_id) DO NOTHING
                """,
                tg_id, username,
            )
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE tg_id = $1", tg_id
            )
        elif username and row["username"] != username:
            await conn.execute(
                "UPDATE users SET username = $1 WHERE tg_id = $2",
                username, tg_id,
            )
    return dict(row)


def today_moscow() -> date:
    return datetime.now(MOSCOW_TZ).date()


async def can_use_free(tg_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT last_free_used FROM users WHERE tg_id = $1", tg_id
        )
        if row is None:
            return True
        last = row["last_free_used"]
        return last is None or last < today_moscow()


async def use_free_token(tg_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET last_free_used = $1 WHERE tg_id = $2",
            today_moscow(), tg_id,
        )


async def get_paid_tokens(tg_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT paid_tokens FROM users WHERE tg_id = $1", tg_id
        )
        return row["paid_tokens"] if row else 0


async def deduct_paid_token(tg_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET paid_tokens = paid_tokens - 1 WHERE tg_id = $1 AND paid_tokens > 0",
            tg_id,
        )


async def add_paid_tokens(tg_id: int, amount: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET paid_tokens = paid_tokens + $1 WHERE tg_id = $2",
            amount, tg_id,
        )


async def increment_total_generations(tg_id: int) -> int:
    """Increment total_generations and return the new count."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE users
            SET total_generations = total_generations + 1
            WHERE tg_id = $1
            RETURNING total_generations
            """,
            tg_id,
        )
        return row["total_generations"] if row else 0


async def unuse_free_token(tg_id: int):
    """Refund free token by resetting last_free_used to yesterday."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET last_free_used = NULL WHERE tg_id = $1 AND last_free_used = $2",
            tg_id, today_moscow(),
        )


async def set_easter_egg1(tg_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET easter_egg1 = TRUE WHERE tg_id = $1", tg_id
        )


async def get_user(tg_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE tg_id = $1", tg_id
        )
        return dict(row) if row else None


async def upsert_user_from_csv(tg_id: int, username: str | None, gens_count: int, easter_egg1: bool = False):
    """Used by migrate_users.py to insert or update a user from CSV data."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (tg_id, username, total_generations, easter_egg1)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (tg_id) DO UPDATE
                SET username = EXCLUDED.username,
                    total_generations = EXCLUDED.total_generations,
                    easter_egg1 = EXCLUDED.easter_egg1
            """,
            tg_id, username, gens_count, easter_egg1,
        )
