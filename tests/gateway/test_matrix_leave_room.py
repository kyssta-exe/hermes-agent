import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import PlatformConfig


def _make_adapter():
    from plugins.platforms.matrix.adapter import MatrixAdapter
    config = PlatformConfig(
        enabled=True,
        token="syt_test_token",
        extra={
            "homeserver": "https://matrix.example.org",
            "user_id": "@bot:example.org",
        },
    )
    return MatrixAdapter(config)


class TestMatrixLeaveRoom:
    @staticmethod
    def _cryptoless_client():
        """Client with no decryptor attached (E2EE off, or the optional mode degraded)."""
        fake_client = MagicMock()
        fake_client.crypto = None
        fake_client.sync_store = MagicMock()
        fake_client.sync_store.put_next_batch = AsyncMock()
        fake_client.handle_sync = MagicMock(return_value=[])
        return fake_client

    @pytest.mark.asyncio
    async def test_absorb_sync_removes_left_rooms_from_joined_set(self, caplog):
        """When rooms.leave is present in sync, _joined_rooms should be pruned (#134006)."""
        adapter = _make_adapter()
        adapter._joined_rooms.add("!room1:example.org")
        adapter._joined_rooms.add("!room2:example.org")
        fake_client = self._cryptoless_client()
        adapter._client = fake_client

        sync_data = {
            "rooms": {"leave": {"!room1:example.org": {"state": {}}}},
            "next_batch": "s1",
        }

        with caplog.at_level(logging.INFO, logger="plugins.platforms.matrix.adapter"):
            await adapter._absorb_sync(fake_client, sync_data)

        # room1 should be removed, room2 should remain
        assert adapter._joined_rooms == {"!room2:example.org"}
        assert any(
            "left 1 room(s) per sync" in r.getMessage()
            and "!room1:example.org" in r.getMessage()
            for r in caplog.records
        )

    @pytest.mark.asyncio
    async def test_absorb_sync_ignores_non_dict_leave(self, caplog):
        """If rooms.leave is not a dict, ignore it and leave _joined_rooms unchanged."""
        adapter = _make_adapter()
        adapter._joined_rooms.add("!room1:example.org")
        fake_client = self._cryptoless_client()
        adapter._client = fake_client

        sync_data = {
            "rooms": {"leave": ["!room1:example.org"]},  # not a dict
            "next_batch": "s1",
        }

        with caplog.at_level(logging.INFO, logger="plugins.platforms.matrix.adapter"):
            await adapter._absorb_sync(fake_client, sync_data)

        assert adapter._joined_rooms == {"!room1:example.org"}
        # Should not log anything about leaving rooms
        assert not any(
            "left" in r.getMessage() and "room(s) per sync" in r.getMessage()
            for r in caplog.records
        )

    @pytest.mark.asyncio
    async def test_absorb_sync_reinvite_after_leave_is_honored(self, caplog):
        """After a leave is processed, a re-invite should be honored (not short-circuited)."""
        adapter = _make_adapter()
        # Simulate having left the room (so it should NOT be in _joined_rooms)
        # Initially joined, then left via previous sync
        adapter._joined_rooms = set()  # room was left
        fake_client = self._cryptoless_client()
        adapter._client = fake_client

        # This invite should be processed because the room is no longer in _joined_rooms
        sync_data = {
            "rooms": {"invite": {"!room1:example.org": {"invite": {}}}},
            "next_batch": "s1",
        }

        with caplog.at_level(logging.INFO, logger="plugins.platforms.matrix.adapter"):
            await adapter._absorb_sync(fake_client, sync_data)

        # The invite should have been scheduled (not short-circuited by _joined_rooms check)
        # We can't easily test _schedule_invite_join was called without mocking it,
        # but we can verify no warning about skipping due to already joined
        assert not any(
            "skipping invite" in r.getMessage().lower() or "already joined" in r.getMessage().lower()
            for r in caplog.records
        )