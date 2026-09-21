"""The figures `doc/architecture/deployment.md` states, against the source.

`tooling/architecture/doc_restated_counts.py` used to do this for every prose
figure in every architecture page and went with `tooling/` in 7b0f58cb517f.
Nothing has checked them since, and an operator reading a default out of that
page is reading it to size a deployment.

This restores the slice that covers the service package, and it restores the
rule that made the gate worth having: **the expected value is never written
here**. Each entry builds the text the page must contain out of the live
constant, so a default that moves turns into a string the page does not hold
and fails by name. A test full of literals would just be a second copy of the
page, agreeing with it as it drifted.

Measured when this was written: 23 figures, none drifted.
"""

import os
import pathlib
from unittest.mock import patch

import pytest

from odoo.release import MIN_PG_VERSION
from odoo.service import _limits, _prefork, _threaded, _worker, lifecycle
from odoo.service import settings as server_settings
from odoo.service._prefork import _EXIT_OUTCOMES
from odoo.service._transport import TransportLimits, get_http_socket_timeout
from odoo.service.settings import ServerSettings

MIB = 1024 * 1024

PAGE = (
    pathlib.Path(lifecycle.__file__).resolve().parents[2]
    / "doc"
    / "architecture"
    / "deployment.md"
)


@pytest.fixture(scope="module")
def page() -> str:
    assert PAGE.is_file(), f"the deployment page moved from {PAGE}"
    return PAGE.read_text()


@pytest.fixture(scope="module")
def limits():
    """The transport's defaults, with any ODOO_HTTP_* the shell set removed.

    The page states defaults, so the test has to ask for defaults; read
    through an environment that overrides them it would pass against a page
    stating something else entirely.
    """
    with (
        patch.dict(os.environ, {}, clear=False),
        server_settings.override(test_enable=False),
    ):
        for name in list(os.environ):
            if name.startswith("ODOO_HTTP_"):
                del os.environ[name]
        yield TransportLimits.from_environment(), get_http_socket_timeout()


def _settings_figures() -> dict[str, str]:
    s = ServerSettings()
    return {
        "workers": f"| `workers` | `{s.workers}` |",
        "max_cron_threads": f"| `max_cron_threads` | `{s.max_cron_threads}` |",
        "limit_request": f"| `limit_request` | `{s.limit_request}` |",
        "limit_memory_soft": (
            f"| `limit_memory_soft` | `{s.limit_memory_soft // MIB} MB` |"
        ),
        "limit_time_cpu": f"| `limit_time_cpu` | `{s.limit_time_cpu} s` |",
        "limit_time_real": f"| `limit_time_real` | `{s.limit_time_real} s` |",
        "limit_time_worker_cron": (
            f"| `limit_time_worker_cron` | `{s.limit_time_worker_cron}` |"
        ),
        "db_maxconn": f"| `db_maxconn` | `{s.db_maxconn}` |",
    }


def _constant_figures() -> dict[str, str]:
    beat = int(_prefork.SUPERVISION_BEAT_S)
    return {
        "_CANCEL_GRACE_S": (
            f"`_CANCEL_GRACE_S` ({int(_worker.Worker._CANCEL_GRACE_S)} s)"
        ),
        "SUPERVISION_BEAT_S": f"`SUPERVISION_BEAT_S` ({beat} s)",
        "the master's beat in prose": f"The prefork master's beat is {beat} s",
        "DESCRIPTOR_HEADROOM": f"`DESCRIPTOR_HEADROOM` ({lifecycle.DESCRIPTOR_HEADROOM})",
        "graceful stop bound": (
            f"`ODOO_GRACEFUL_STOP_TIMEOUT`, {int(_limits.GRACEFUL_STOP_TIMEOUT_S)} s"
        ),
        "listener join floor": (
            f"(at least {int(_threaded.LISTENER_JOIN_TIMEOUT_S)} s)"
        ),
        "MIN_PG_VERSION": f"`MIN_PG_VERSION` (`odoo/release.py`) is {MIN_PG_VERSION}",
    }


def _transport_figures(limits) -> dict[str, str]:
    lim, socket_timeout = limits
    return {
        "socket timeout": (f"| `ODOO_HTTP_SOCKET_TIMEOUT` | `{int(socket_timeout)} s`"),
        "head timeout": (f"| `ODOO_HTTP_HEAD_TIMEOUT` | `{int(lim.head_timeout)} s` |"),
        "keepalive timeout": (
            f"| `ODOO_HTTP_KEEPALIVE_TIMEOUT` | `{int(lim.keepalive_timeout)} s` |"
        ),
        "idle connections": (
            f"| `ODOO_HTTP_MAX_IDLE_CONNECTIONS` | `{lim.max_idle_connections}` |"
        ),
        "drain bytes": (
            f"| `ODOO_HTTP_DRAIN_BYTES` | `{lim.drain_bytes // MIB} MiB` |"
        ),
    }


class TestThePageStatesWhatTheSourceDoes:
    def test_every_setting_default_it_quotes(self, page):
        for name, text in _settings_figures().items():
            assert text in page, (
                f"deployment.md does not state {name} as the source has it "
                f"({text!r}); an operator sizes a deployment from that table"
            )

    def test_every_constant_it_names(self, page):
        for name, text in _constant_figures().items():
            assert text in page, f"deployment.md and the source disagree on {name}"

    def test_every_transport_knob_it_documents(self, page, limits):
        for name, text in _transport_figures(limits).items():
            assert text in page, f"deployment.md and the source disagree on {name}"

    def test_the_worker_exit_outcomes_it_lists(self, page):
        """The metric grows labels; the row that explains them has to follow."""
        row = next(
            (l for l in page.splitlines() if "`odoo_worker_exits_total`" in l), ""
        )
        assert row, "the metrics table no longer mentions odoo_worker_exits_total"
        missing = [o for o in _EXIT_OUTCOMES if f"`{o}`" not in row]
        assert not missing, (
            f"the metric reports outcomes the page does not explain: {missing}. "
            f"A label nobody documents is a label nobody alerts on"
        )
