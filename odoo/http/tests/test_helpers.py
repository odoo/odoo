import threading
import types
from typing import Any

import werkzeug.exceptions

from odoo.http import _cors, _dbfilter
from odoo.http._cors import is_cors_preflight
from odoo.http._dbfilter import _normalize_dbfilter_host
from odoo.http._rpc import _restore_thread_attr
from odoo.http.wrappers import prepare_content_disposition_header
from odoo.tools import config


def test_content_disposition_encodes_unicode_and_quotes():
    header = prepare_content_disposition_header('résumé "x".pdf')
    assert header.startswith("attachment; filename*=UTF-8''")
    assert "r%C3%A9sum%C3%A9" in header
    assert '"' not in header


def test_content_disposition_inline():
    assert prepare_content_disposition_header("a.pdf", "inline").startswith("inline; ")


def test_content_disposition_rejects_bad_type():
    import pytest

    with pytest.raises(ValueError, match="Invalid disposition_type"):
        prepare_content_disposition_header("a.pdf", "bogus")


def test_normalize_dbfilter_host_strips_port_www_and_lowercases():
    assert _normalize_dbfilter_host("WWW.Example.COM:8069") == "example.com"
    assert _normalize_dbfilter_host("example.com") == "example.com"
    assert _normalize_dbfilter_host("WWW.sub.example.com") == "sub.example.com"


def test_dbfilter_host_normalized_exactly_once():
    from odoo.http._dbfilter import _compile_dbfilter, filter_dbs_served
    from odoo.tools import config

    saved = config["dbfilter"]
    config["dbfilter"] = "^%h$"
    _compile_dbfilter.cache_clear()
    try:
        assert filter_dbs_served(["www.example.com"], host="www.www.example.com") == [
            "www.example.com"
        ]
        assert filter_dbs_served(["example.com"], host="www.www.example.com") == []
    finally:
        config["dbfilter"] = saved
        _compile_dbfilter.cache_clear()


def _fake_request(method):
    env = {"REQUEST_METHOD": method}
    httprequest = types.SimpleNamespace(method=method, environ=env)
    return types.SimpleNamespace(httprequest=httprequest)


def test_is_cors_preflight_returns_real_bool():
    endpoint = types.SimpleNamespace(routing={"cors": "https://example.com"})
    result = is_cors_preflight(_fake_request("OPTIONS"), endpoint)
    assert result is True
    assert is_cors_preflight(_fake_request("GET"), endpoint) is False
    no_cors = types.SimpleNamespace(routing={})
    assert is_cors_preflight(_fake_request("OPTIONS"), no_cors) is False


def test_db_filter_without_request_uses_empty_host():
    from odoo.http._dbfilter import filter_dbs_served
    from odoo.tools import config

    saved = config["dbfilter"]
    config["dbfilter"] = "^%d$"
    try:
        assert filter_dbs_served(["somedb"]) == []
    finally:
        config["dbfilter"] = saved


def test_restore_thread_attr_deletes_when_absent():
    sentinel = object()
    t: Any = threading.current_thread()
    if hasattr(t, "_probe_attr"):
        del t._probe_attr
    _restore_thread_attr(t, "_probe_attr", sentinel, sentinel)
    assert not hasattr(t, "_probe_attr")
    _restore_thread_attr(t, "_probe_attr", 42, sentinel)
    assert t._probe_attr == 42
    del t._probe_attr


def test_normalize_dbfilter_host_ipv6_keeps_brackets():
    assert _normalize_dbfilter_host("[::1]:8069") == "[::1]"
    assert _normalize_dbfilter_host("[2001:DB8::1]") == "[2001:db8::1]"
    assert _normalize_dbfilter_host("[::1") == "[::1"


def test_serialize_exception_masks_infra_errors_for_clients_only():
    import psycopg

    from odoo.http import _request_stack
    from odoo.http._error_serialization import serialize_exception

    secret_os = OSError("/srv/filestore/prod/.session/secret-layout")
    secret_pg = psycopg.OperationalError("UPDATE res_users SET password=...")

    assert "filestore" in serialize_exception(secret_os)["message"]
    assert "res_users" in serialize_exception(secret_pg)["message"]

    _request_stack.push(types.SimpleNamespace())
    try:
        for exc in (secret_os, secret_pg):
            data = serialize_exception(exc)
            assert data["message"] == "Internal Server Error"
            assert data["arguments"] == ()
            assert data["name"].endswith(type(exc).__name__)
        assert serialize_exception(ValueError("bad domain"))["message"] == "bad domain"
    finally:
        _request_stack.pop()


def test_select_db_prefixes_are_kept_startswith_ready():
    from odoo.http import constants

    before_paths = set(constants.SELECT_DB_PATHS)
    before_prefixes = constants.SELECT_DB_PATH_PREFIXES
    try:
        constants.register_select_db_paths("/t/one", prefixes=["/t/pre/"])
        constants.register_select_db_paths("/t/two", prefixes=["/t/pre/", "/t/other/"])

        assert isinstance(constants.SELECT_DB_PATH_PREFIXES, tuple)
        assert constants.SELECT_DB_PATH_PREFIXES.count("/t/pre/") == 1
        assert constants.is_select_db_path("/t/pre/x")
        assert constants.is_select_db_path("/t/one")
        assert constants.is_select_db_path("/t/two")
        assert not constants.is_select_db_path("/t/elsewhere")
    finally:
        constants.SELECT_DB_PATHS.clear()
        constants.SELECT_DB_PATHS.update(before_paths)
        constants.SELECT_DB_PATH_PREFIXES = before_prefixes


def test_no_registered_prefix_matches_nothing():
    from odoo.http import constants

    before = constants.SELECT_DB_PATH_PREFIXES
    try:
        constants.SELECT_DB_PATH_PREFIXES = ()
        assert not constants.is_select_db_path("/anything")
    finally:
        constants.SELECT_DB_PATH_PREFIXES = before


def test_a_dbfilter_that_ignores_the_host_caches_one_regex_for_every_host():
    _dbfilter._compile_dbfilter.cache_clear()
    with config.patch(dbfilter=".*", db_name=[]):
        for i in range(600):
            _dbfilter.filter_dbs_served(["somedb"], host=f"attacker-{i}.example.com")

    assert _dbfilter._compile_dbfilter.cache_info().currsize == 1


def test_a_dbfilter_that_reads_the_host_still_gets_a_regex_per_host():
    _dbfilter._compile_dbfilter.cache_clear()
    with config.patch(dbfilter="^%d_", db_name=[]):
        assert _dbfilter.filter_dbs_served(["alpha_x"], host="alpha.example.com") == [
            "alpha_x"
        ]
        assert _dbfilter.filter_dbs_served(["alpha_x"], host="beta.example.com") == []

    assert _dbfilter._compile_dbfilter.cache_info().currsize == 2


def test_db_filter_orders_the_same_way_through_both_of_its_filters():
    catalogue = ["zeta", "alpha", "mid"]

    with config.patch(dbfilter=".*", db_name=[]):
        _reset_dbfilter_caches()
        by_pattern = _dbfilter.filter_dbs_served(catalogue, host="x.example")
    with config.patch(dbfilter="", db_name=list(catalogue)):
        _reset_dbfilter_caches()
        by_name = _dbfilter.filter_dbs_served(catalogue, host="x.example")
    with config.patch(dbfilter=".*", db_name=list(catalogue)):
        _reset_dbfilter_caches()
        by_both = _dbfilter.filter_dbs_served(catalogue, host="x.example")

    assert by_pattern == catalogue
    assert by_name == catalogue
    assert by_both == catalogue


def test_db_filter_applies_both_filters_when_both_are_set():
    with config.patch(dbfilter="a.*", db_name=["alpha", "zeta"]):
        _reset_dbfilter_caches()
        assert _dbfilter.filter_dbs_served(
            ["zeta", "alpha", "abc"], host="x.example"
        ) == ["alpha"]


def _reset_dbfilter_caches():
    _dbfilter._compile_dbfilter.cache_clear()
    _dbfilter._has_host_placeholder.cache_clear()


HOSTILE_STRINGS = [
    "",
    " ",
    "\x00",
    "a\x00b",
    "\n",
    "\r\n",
    "..",
    "../" * 50,
    "/",
    "//",
    "///",
    "\\",
    ":",
    "::",
    "[",
    "]",
    "[]",
    "[::1",
    "[::1]:x",
    "a:b:c",
    "http://[",
    "http://[x",
    "http://a[b",
    "//[",
    "//[/static/x",
    "http://x:99999999999",
    "http://x:y",
    "http:///",
    "https://x@y:z",
    "%",
    "%%",
    "%zz",
    "%2e%2e",
    "=",
    ";",
    ",",
    '"',
    "`",
    "%h",
    "%d",
    "%(x)s",
    "{}",
    "$(x)",
    "é",
    "日本",
    "🙂",
    "a" * 10000,
    "www.",
    "WWW.X",
]


def _hostile_probe(fn):
    escapes = []
    for value in HOSTILE_STRINGS:
        try:
            fn(value)
        except werkzeug.exceptions.HTTPException:
            pass
        except Exception as exc:
            escapes.append(f"{value!r} -> {type(exc).__name__}: {exc}")
    return escapes


def test_no_hostile_host_header_escapes_the_dbfilter_path():
    assert _hostile_probe(_normalize_dbfilter_host) == []
    assert (
        _hostile_probe(lambda h: _dbfilter.filter_dbs_served(["a", "b"], host=h)) == []
    )


def test_no_hostile_origin_escapes_cors_same_host():
    def resolve(origin):
        return _cors.resolve_cors_same_host(
            types.SimpleNamespace(
                httprequest=types.SimpleNamespace(
                    headers={"Origin": origin},
                    host_url="http://app.example/",
                    is_secure=False,
                )
            )
        )

    assert _hostile_probe(resolve) == []
    assert resolve("http://[") is None
    assert resolve("http://app.example") == "http://app.example"


def test_no_hostile_url_escapes_get_static_file():
    from odoo.http.application import Application

    assert _hostile_probe(Application().get_static_file_path) == []
    assert Application().get_static_file_path("//[/static/x") is None


def test_no_hostile_cookie_or_filename_escapes():
    from odoo.http.wrappers import get_cookie_name

    assert _hostile_probe(get_cookie_name) == []
    assert _hostile_probe(prepare_content_disposition_header) == []
