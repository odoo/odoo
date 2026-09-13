import logging

import pytest

from odoo import logutils
from odoo.service import _transport as transport

_TOUCHED = (
    "",
    "odoo",
    "odoo.db",
    "odoo.http.rpc",
    "odoo.http.rpc.request",
    "odoo.http.rpc.response",
    "fontTools",
    "werkzeug",
    logutils.ACCESS_LOGGER,
)


@pytest.fixture
def configure(monkeypatch):
    saved = {name: logging.getLogger(name).level for name in _TOUCHED}

    def apply(log_level="info", log_handler=()):
        monkeypatch.setattr(
            logutils.tools,
            "config",
            {"log_level": log_level, "log_handler": list(log_handler)},
        )
        logutils._apply_configured_levels()

    yield apply
    for name, level in saved.items():
        logging.getLogger(name).setLevel(level)


def _access_level():
    return logging.getLogger(logutils.ACCESS_LOGGER).getEffectiveLevel()


def test_the_transport_logs_on_the_configured_access_logger():
    assert transport._access_logger.name == logutils.ACCESS_LOGGER


def test_debug_level_does_not_print_static_access_lines(configure):
    configure("debug")
    assert logging.getLogger("odoo").getEffectiveLevel() == logging.DEBUG
    assert _access_level() == logging.INFO


@pytest.mark.parametrize(
    ("preset", "expected"),
    [
        ("runbot", logging.WARNING),
        ("warn", logging.WARNING),
        ("error", logging.ERROR),
        ("critical", logging.CRITICAL),
    ],
)
def test_quiet_presets_quiet_the_access_log(configure, preset, expected):
    configure(preset)
    assert _access_level() == expected


def test_log_handler_on_the_access_logger_applies_silently(configure, caplog):
    with caplog.at_level(logging.WARNING, logger=logutils.__name__):
        configure(log_handler=[f"{logutils.ACCESS_LOGGER}:WARNING"])
    assert _access_level() == logging.WARNING
    assert not caplog.records


def test_log_handler_naming_werkzeug_says_where_the_access_log_went(configure, caplog):
    with caplog.at_level(logging.WARNING, logger=logutils.__name__):
        configure(log_handler=["werkzeug:WARNING"])
    [record] = caplog.records
    assert logutils.ACCESS_LOGGER in record.getMessage()
    assert _access_level() == logging.INFO
