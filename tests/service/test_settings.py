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

    def test_nothing_is_tracked_while_the_channel_is_off(self, monkeypatch):
        monkeypatch.setattr(server_settings, "_last_seen", None)
        assert logging.getLogger(_LIFECYCLE).getEffectiveLevel() > logging.DEBUG
        server_settings.current()
        assert server_settings._last_seen is None
