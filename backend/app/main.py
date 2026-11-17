"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import engine, get_session, ping

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hook. On shutdown, close the pool's connections cleanly."""
    yield
    await engine.dispose()


app = FastAPI(title="DocChat", lifespan=lifespan)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@app.get("/health")
async def health(session: SessionDep) -> JSONResponse:
    """Liveness + DB check. Returns 503 if Postgres can't be reached."""
    try:
        await ping(session)
    except Exception:
        logger.exception("Health check: database unreachable")
        return JSONResponse(status_code=503, content={"status": "error", "db": "unreachable"})
    return JSONResponse(content={"status": "ok", "db": "ok"})
