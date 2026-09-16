import types

import werkzeug.exceptions

from odoo.http import _cors, _dbfilter
from odoo.http._dbfilter import _normalize_dbfilter_host
from odoo.http.wrappers import prepare_content_disposition_header

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
    from odoo.http._cookies import get_cookie_name

    assert _hostile_probe(get_cookie_name) == []
    assert _hostile_probe(prepare_content_disposition_header) == []
