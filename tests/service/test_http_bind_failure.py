import logging
from unittest.mock import MagicMock, patch

import pytest

from odoo.service import _threaded

from .conftest import threaded_server


def failing_bind():
    return patch.object(_threaded, "ThreadedHTTPServer", side_effect=SystemExit(1))


@pytest.fixture
def server():
    srv = threaded_server()
    srv.logger = logging.getLogger("odoo.service.server.ThreadedServer")
    srv.interface = "0.0.0.0"
    srv.port = 8069
    srv.app = MagicMock()
    srv.httpd = None
    return srv


class TestBindFailureIsLogged:
    def test_systemexit_is_reported_at_critical(self, server, caplog):
        with (
            failing_bind(),
            caplog.at_level(logging.CRITICAL, logger="odoo.service.server"),
            pytest.raises(SystemExit),
        ):
            server.spawn_http_server()

        critical = [r for r in caplog.records if r.levelno == logging.CRITICAL]
        assert critical, "a failed bind must produce a CRITICAL log record"
        assert "Failed to bind" in critical[0].getMessage()

    def test_the_message_names_the_address(self, server, caplog):
        server.interface, server.port = "127.0.0.1", 8899
        with (
            failing_bind(),
            caplog.at_level(logging.CRITICAL, logger="odoo.service.server"),
            pytest.raises(SystemExit),
        ):
            server.spawn_http_server()

        critical = [r for r in caplog.records if r.levelno == logging.CRITICAL]
        assert critical, "a failed bind must produce a CRITICAL log record"
        message = critical[0].getMessage()
        assert "127.0.0.1" in message
        assert "8899" in message

    def test_the_exit_still_propagates(self, server):
        with failing_bind():
            with pytest.raises(SystemExit) as excinfo:
                server.spawn_http_server()
        assert excinfo.value.code == 1

    def test_no_serving_thread_is_started_on_failure(self, server):
        with (
            failing_bind(),
            patch.object(_threaded.threading, "Thread") as thread,
            pytest.raises(SystemExit),
        ):
            server.spawn_http_server()
        thread.assert_not_called()


class TestSuccessfulSpawnIsUnchanged:
    def test_httpd_is_stored_and_served(self, server, caplog):
        httpd = MagicMock()
        with (
            patch.object(_threaded, "ThreadedHTTPServer", return_value=httpd),
            patch.object(_threaded.threading, "Thread") as thread,
            caplog.at_level(logging.CRITICAL, logger="odoo.service.server"),
        ):
            server.spawn_http_server()

        assert server.httpd is httpd
        thread.assert_called_once()
        assert thread.call_args.kwargs["target"] == httpd.serve_forever
        assert thread.call_args.kwargs["daemon"] is True
        assert not caplog.records, "a successful bind must log nothing here"
