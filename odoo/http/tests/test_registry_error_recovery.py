import types
from typing import Any
from unittest import mock

import pytest
import werkzeug.datastructures
from werkzeug.exceptions import InternalServerError, NotFound

from odoo.http import application, constants
from odoo.http.exceptions import RegistryError, get_error_response


def _recover(this, httprequest, exc):
    return application.Application._recover_from_registry_error(
        application.Application(), this, httprequest, exc
    )


class _Session:
    def __init__(self):
        self.can_save = True
        self.logged_out = False

    def logout(self, keep_db=False):
        self.logged_out = True


def _request(path="/whatever", args=None):
    served = []

    def _serve_nodb():
        served.append(1)
        return "nodb"

    httprequest: Any = types.SimpleNamespace(
        path=path,
        args=werkzeug.datastructures.MultiDict(args or {}),
    )

    this: Any = types.SimpleNamespace(
        db="db",
        session=_Session(),
        httprequest=httprequest,
        rerouted=None,
        _serve_nodb=_serve_nodb,
    )
    this.reroute = lambda p, q=None: setattr(this, "rerouted", (p, q))
    return this, httprequest


@pytest.mark.parametrize(
    ("db_absent", "transient", "durable"),
    [
        (True, False, True),
        (True, True, True),
        (False, False, True),
        (False, True, False),
        (None, False, False),
        (None, True, False),
    ],
)
def test_only_a_durable_failure_may_persist_the_logout(db_absent, transient, durable):
    this, httprequest = _request()
    exc = RegistryError("boom", db_absent=db_absent, transient=transient)

    assert _recover(this, httprequest, exc) == "nodb"
    assert this.db is None
    assert this.session.logged_out is True
    assert this.session.can_save is durable, (db_absent, transient)


@pytest.fixture
def select_db_path():
    saved = set(constants.SELECT_DB_PATHS)
    constants.register_select_db_paths("/probe/ensure-db")
    yield "/probe/ensure-db"
    constants.SELECT_DB_PATHS.clear()
    constants.SELECT_DB_PATHS.update(saved)


def test_a_select_db_path_is_rerouted_without_its_db_argument(select_db_path):
    this, httprequest = _request(
        "/probe/ensure-db", {"db": "gone", "keep": "1", "also": "2"}
    )
    exc = RegistryError("boom", db_absent=True)

    _recover(this, httprequest, exc)

    path, query = this.rerouted
    assert path == "/probe/ensure-db"
    assert "db=" not in query
    assert "keep=1" in query and "also=2" in query


def test_an_ordinary_path_is_not_rerouted():
    this, httprequest = _request("/probe/plain", {"db": "gone"})
    exc = RegistryError("boom", db_absent=True)

    _recover(this, httprequest, exc)

    assert this.rerouted is None


def test_a_dispatcher_that_cannot_build_an_error_response_still_yields_one():
    app = application.Application()
    request: Any = mock.Mock()
    request.dispatcher.prepare_error_response.side_effect = RuntimeError(
        "handler is broken"
    )

    exc = ValueError("original")
    app._get_or_create_error_response(exc, request)

    assert isinstance(get_error_response(exc), InternalServerError)


def test_an_existing_error_response_is_left_alone():
    app = application.Application()
    exc = NotFound()
    request: Any = mock.Mock()
    request.dispatcher.prepare_error_response.return_value = InternalServerError()
    exc.error_response = exc

    app._get_or_create_error_response(exc, request)

    assert get_error_response(exc) is exc
    request.dispatcher.prepare_error_response.assert_not_called()


def test_finalize_without_an_error_response_does_not_post_dispatch():
    app = application.Application()
    request: Any = mock.Mock()
    request._post_init_done = True

    app._finalize_error_response(ValueError("no response attached"), request, None)

    request.dispatcher.post_dispatch.assert_not_called()
