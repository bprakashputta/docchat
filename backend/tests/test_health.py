"""Tests for GET /health. Requires the Docker database to be running."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_session
from backend.app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    # ASGITransport calls the app in-process: no server, no network port.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_health_ok(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "db": "ok"}


async def test_health_db_down(client: AsyncClient) -> None:
    class BrokenSession:
        async def execute(self, *args: object, **kwargs: object) -> None:
            raise ConnectionError("db down")

    async def broken_session() -> AsyncIterator[AsyncSession]:
        yield BrokenSession()  # type: ignore[misc]

    # Swap the real DB session for one that fails, to exercise the 503 path.
    app.dependency_overrides[get_session] = broken_session
    resp = await client.get("/health")
    assert resp.status_code == 503
    assert resp.json()["db"] == "unreachable"
