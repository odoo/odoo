import types
import typing
from typing import Any
from unittest.mock import patch

import psycopg
import pytest

import odoo.http
from odoo.http import _dbfilter
from odoo.http.request_class import Request


@pytest.fixture
def fresh_monodb_cache():
    _dbfilter.invalidate_db_catalog_cache()
    yield
    _dbfilter.invalidate_db_catalog_cache()


def _catalog(dbs):
    return patch.object(_dbfilter.odoo.service.db, "list_dbs", return_value=list(dbs))


def _passthrough_filter():
    return patch.object(
        _dbfilter, "filter_dbs_served", side_effect=lambda dbs, host=None: list(dbs)
    )


def test_monodb_dblist_filters_the_catalog(fresh_monodb_cache):
    with _catalog(["a", "b"]), _passthrough_filter():
        assert odoo.http.get_dbs_served(force=True, host="h") == ["a", "b"]
        assert odoo.http.get_dbs_served(force=True, host="h") == ["a", "b"]


def test_monodb_dblist_degrades_when_postgres_unreachable(fresh_monodb_cache):
    boom = psycopg.OperationalError("connection refused")
    with patch.object(_dbfilter.odoo.service.db, "list_dbs", side_effect=boom):
        assert odoo.http.get_dbs_served(force=True, host="h") == []

    with _catalog(["only"]), _passthrough_filter():
        assert odoo.http.get_dbs_served(force=True, host="h") == ["only"]


def test_monodb_dblist_degrades_on_any_psycopg_error(fresh_monodb_cache):
    for exc in (
        psycopg.Error("boom"),
        psycopg.OperationalError("refused"),
        psycopg.errors.InsufficientPrivilege("denied"),
    ):
        _dbfilter.invalidate_db_catalog_cache()
        with patch.object(_dbfilter.odoo.service.db, "list_dbs", side_effect=exc):
            assert odoo.http.get_dbs_served(force=True, host="h") == []


def test_db_list_degrades_on_any_psycopg_error(fresh_monodb_cache):
    with patch.object(
        _dbfilter.odoo.service.db, "list_dbs", side_effect=psycopg.Error("boom")
    ):
        assert _dbfilter.get_dbs_served(force=True, host="h") == []


class _App:
    def __init__(self, served):
        self.served = list(served)
        self.asked = []

    def get_dbs_served(self, host):
        self.asked.append(("list", host))
        return list(self.served)

    def filter_dbs_served(self, dbs, host):
        self.asked.append(("filter", tuple(dbs), host))
        return [db for db in dbs if db in self.served]


def _selecting_request(app, *, cookie_db=None, header_db=None):
    headers = {"X-Odoo-Database": header_db} if header_db else {}
    httprequest: Any = types.SimpleNamespace(
        remote_addr=None,
        session_id=None,
        environ={"HTTP_HOST": "h.example"},
        headers=headers,
        accept_languages=types.SimpleNamespace(best=None),
    )
    request = Request(httprequest, app=app)
    session: Any = types.SimpleNamespace(
        db=cookie_db, uid=None, is_new=True, should_rotate=False, can_save=True
    )
    session.mark_clean = lambda: None
    session.logout = lambda keep_db=False: setattr(session, "db", None)
    return request, session


def test_the_single_served_database_is_resolved_through_the_application():
    app = _App(["only"])
    request, session = _selecting_request(app)
    assert request._select_dbname(session) == "only"
    assert app.asked == [("list", "h.example")]


def test_the_session_database_is_filtered_through_the_application():
    app = _App(["kept"])
    request, session = _selecting_request(app, cookie_db="kept")
    assert request._select_dbname(session) == "kept"
    assert app.asked == [("filter", ("kept",), "h.example")]


def test_a_header_database_is_filtered_through_the_application():
    app = _App(["named"])
    request, session = _selecting_request(app, header_db="named")
    assert request._select_dbname(session) == "named"
    assert app.asked == [("filter", ("named",), "h.example")]
    assert session.can_save is False


def test_http_adds_no_second_cache_over_the_catalogue(fresh_monodb_cache):
    with _catalog(["a", "b"]) as lister, _passthrough_filter():
        for _ in range(5):
            assert odoo.http.get_dbs_served(force=True, host="h") == ["a", "b"]
    assert lister.call_count == 5, "every call reaches the one cache that exists"


def test_force_reaches_list_dbs_rather_than_a_cached_answer(fresh_monodb_cache):
    with _catalog(["a"]) as lister, _passthrough_filter():
        odoo.http.get_dbs_served(force=True)
        odoo.http.get_dbs_served(force=True)

    assert [c.args for c in lister.call_args_list] == [(True,), (True,)]


def test_each_host_gets_its_own_filtered_answer(fresh_monodb_cache):
    with (
        _catalog(["a_one", "b_two"]),
        patch.object(
            _dbfilter,
            "filter_dbs_served",
            side_effect=lambda dbs, host=None: [
                db for db in dbs if db.startswith(host)
            ],
        ),
    ):
        assert odoo.http.get_dbs_served(force=True, host="a") == ["a_one"]
        assert odoo.http.get_dbs_served(force=True, host="b") == ["b_two"]
        assert odoo.http.get_dbs_served(force=True, host="a") == ["a_one"]


def test_the_caller_cannot_mutate_what_the_next_caller_sees(fresh_monodb_cache):
    with _catalog(["a"]):
        first = odoo.http.get_dbs_served()
        first.append("smuggled")
        assert odoo.http.get_dbs_served() == ["a"]


def test_invalidate_db_list_cache_drops_the_catalogue_service_db_holds():
    from odoo.service.db import listing

    listing._catalog_cache = (float("inf"), ["stale"])
    _dbfilter.invalidate_db_catalog_cache()
    assert listing._catalog_cache is None


def test_a_listener_that_raises_does_not_break_the_mutation():
    from odoo.service.db import listing

    def boom():
        raise RuntimeError("boom")

    listing.register_catalog_listener(boom)
    try:
        listing.invalidate_catalog_caches()
    finally:
        listing._catalog_listeners.remove(boom)


def _httprequest(**attrs: Any) -> Any:
    return types.SimpleNamespace(remote_addr=None, **attrs)


def _params_request():
    return Request(_httprequest(), app=None)


def test_params_is_an_ordinary_dict_until_a_source_is_deferred():
    request = _params_request()
    assert request.params == {}

    request.params = {"a": 1}
    assert request.params == {"a": 1}

    request.params["b"] = 2
    assert request.params == {"a": 1, "b": 2}, "mutation through the getter sticks"


def test_a_deferred_source_runs_once_on_first_read():
    request = _params_request()
    calls = []

    def source():
        calls.append(1)
        return {"from": "body"}

    request._params_source = source
    assert calls == [], "declaring a source must not read the body"

    assert request.params == {"from": "body"}
    assert request.params == {"from": "body"}
    assert calls == [1], "the body is decoded once, not once per read"


def test_assigning_params_discards_a_pending_source():
    request = _params_request()
    request._params_source = lambda: {"from": "body"}
    request.params = {"from": "caller"}

    assert request.params == {"from": "caller"}


def _json_request(body: bytes):
    reads = []

    def get_data():
        reads.append(1)
        return body

    request = Request(
        _httprequest(get_data=get_data, content_length=len(body)), app=None
    )
    return request, reads


def test_the_json_body_is_decoded_once_per_httprequest():
    request, reads = _json_request(b'{"params": {"model": "res.users"}}')

    first = request.get_json_data()
    second = request.get_json_data()

    assert first == {"params": {"model": "res.users"}}
    assert second is first, "a readonly resolver and the dispatcher share one decode"
    assert reads == [1]


def test_a_rerouted_httprequest_is_decoded_afresh():
    request, reads = _json_request(b'{"a": 1}')
    assert request.get_json_data() == {"a": 1}

    request.httprequest = types.SimpleNamespace(
        get_data=lambda: b'{"b": 2}', content_length=8
    )
    assert request.get_json_data() == {"b": 2}, "the memo is keyed on the httprequest"
    assert reads == [1]


def test_an_invalid_body_is_not_memoized():
    request, reads = _json_request(b"{not json")
    with pytest.raises(ValueError):
        request.get_json_data()
    with pytest.raises(ValueError):
        request.get_json_data()
    assert reads == [1, 1], "nothing was cached, so the second call read again"


def test_the_fallback_defers_the_body_instead_of_decoding_it():
    from werkzeug.exceptions import NotFound

    decoded: list[int] = []

    def _decode():
        decoded.append(1)
        return {"a": "x" * 1000}

    class _IrHttp:
        def _apply_max_upload_size(self):
            pass

        def _authenticate_explicit(self, auth):
            assert auth == "public"

        def _serve_fallback(self):
            return None

        def _handle_error(self, exc):
            return "error-response"

    this: Any = Request(
        _httprequest(max_content_length=None, content_length=1000), app=None
    )
    this.registry = {"ir.http": _IrHttp()}
    this.get_http_params = _decode

    with pytest.raises(NotFound):
        this._serve_ir_http_fallback(NotFound())

    assert decoded == [], "a fallback that ignores params must not decode the body"
    assert this._params_source is not None, "but it stays available to one that does"
    assert this._params_source() == {"a": "x" * 1000}


@pytest.mark.parametrize(
    ("limit", "length", "refused"),
    [
        (1000, 1001, True),
        (1000, 1000, False),
        (1000, None, False),
        (None, 10**9, False),
    ],
)
def test_an_unmatched_path_refuses_an_oversized_body_by_its_declared_length(
    limit, length, refused
):
    from werkzeug.exceptions import RequestEntityTooLarge

    from odoo.http import _serve

    this: Any = types.SimpleNamespace(
        httprequest=types.SimpleNamespace(
            max_content_length=limit, content_length=length
        )
    )
    if refused:
        with pytest.raises(RequestEntityTooLarge):
            _serve._RequestServeMixin._check_body_size(this)
    else:
        _serve._RequestServeMixin._check_body_size(this)


def test_update_context_with_nothing_new_rebuilds_no_environment():
    calls = []

    class _Transaction:
        default_env = None

    class _Env:
        context = {"lang": "en_US"}
        uid = 2
        su = False
        transaction = _Transaction()

        def __call__(self, *args):
            calls.append(args)
            return self

    request = Request(_httprequest(), app=None)
    env = _Env()
    env.transaction.default_env = env
    request.env = typing.cast("Any", env)

    request.update_context()
    request.update_context(lang="en_US")
    assert calls == [], "identical context and a bound default env: nothing to do"

    request.update_context(lang="fr_FR")
    assert calls == [(None, None, {"lang": "fr_FR"}, None)]
