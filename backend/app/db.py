"""Database engine and session setup (async SQLAlchemy over asyncpg)."""

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.config import get_settings

# One engine per process. It owns a connection pool; sessions borrow connections from it.
# pool_pre_ping checks a connection is alive before handing it out (survives DB restarts).
engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)

# expire_on_commit=False keeps loaded objects usable after commit, which is what you
# want in async code (otherwise touching an attribute would trigger a hidden DB call).
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request, closed when the request ends."""
    async with SessionLocal() as session:
        yield session


async def ping(session: AsyncSession) -> None:
    """Run a trivial query; raises if the database is unreachable."""
    await session.execute(text("SELECT 1"))
