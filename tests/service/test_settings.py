import logging
from unittest.mock import patch

from odoo.service import settings as server_settings

_LIFECYCLE = "odoo.debug.lifecycle.service.settings"


def _events(caplog):
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == _LIFECYCLE and "settings.changed" in record.getMessage()
    ]


class TestTheLiveConfigIsLoggedWhenItChanges:
    def test_a_repeated_read_is_silent_and_a_changed_key_is_one_event(
        self, caplog, monkeypatch
    ):
        from odoo.tools import config

        monkeypatch.setattr(server_settings, "_last_seen", None)
        with (
            caplog.at_level(logging.DEBUG, logger=_LIFECYCLE),
            patch.dict(config.options, {"workers": 0, "max_cron_threads": 2}),
        ):
            server_settings.current()
            server_settings.current()
            first = _events(caplog)
            config.options["workers"] = 5
            config.options["max_cron_threads"] = 7
            server_settings.current()
            server_settings.current()
            events = _events(caplog)
        assert len(first) == 1 and "first=True" in first[0]
        assert len(events) == 2
        assert "changed=['max_cron_threads', 'workers']" in events[1]
        assert "workers=5" in events[1]

    def test_nothing_is_logged_while_the_channel_is_off(self, monkeypatch, caplog):
        caplog.set_level(logging.INFO, logger=_LIFECYCLE)
        monkeypatch.setattr(server_settings, "_last_seen", None)
        assert logging.getLogger(_LIFECYCLE).getEffectiveLevel() > logging.DEBUG
        snapshot = server_settings.current()
        assert server_settings._last_seen == snapshot
        assert _events(caplog) == []


class TestTheSnapshotIsDerivedOncePerChange:
    def test_a_repeated_read_is_the_same_object(self):
        assert server_settings.current() is server_settings.current()

    def test_a_config_write_re_derives(self):
        from odoo.tools import config

        before = server_settings.current()
        with patch.dict(config.options, {"workers": before.workers + 1}):
            during = server_settings.current()
            assert during is not before
            assert during.workers == before.workers + 1
        assert server_settings.current().workers == before.workers

    def test_the_socket_activation_environment_is_part_of_the_key(self):
        import os

        before = server_settings.current()
        with patch.dict(
            os.environ, {"LISTEN_FDS": "1", "LISTEN_PID": str(os.getpid())}
        ):
            during = server_settings.current()
            assert during is not before
            assert during.http_socket_activation is True
        assert server_settings.current().http_socket_activation is False
