import types
from types import SimpleNamespace
from typing import Any

import pytest

from odoo.http._cookies import FutureResponse
from odoo.http.application import _prepare_proxy_fix
from odoo.http.dispatcher import Dispatcher, HttpDispatcher
from odoo.http.wrappers import prepare_no_content_response


def _environ(forwarded_for, forwarded_host=None, forwarded_proto=None):
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/",
        "SERVER_NAME": "origin.example",
        "SERVER_PORT": "8069",
        "REMOTE_ADDR": "10.0.0.1",
        "wsgi.url_scheme": "http",
        "HTTP_X_FORWARDED_FOR": forwarded_for,
    }
    if forwarded_host:
        environ["HTTP_X_FORWARDED_HOST"] = forwarded_host
    if forwarded_proto:
        environ["HTTP_X_FORWARDED_PROTO"] = forwarded_proto
    return environ


def _noop(status, headers):
    pass


@pytest.mark.parametrize(
    ("hops", "expected"),
    [
        (1, "10.9.9.9"),
        (2, "203.0.113.7"),
        (3, "198.51.100.4"),
    ],
)
def test_the_trusted_hop_count_decides_the_client_address(hops, expected):
    environ = _environ("198.51.100.4, 203.0.113.7, 10.9.9.9")
    _prepare_proxy_fix(hops)(environ, _noop)
    assert environ["REMOTE_ADDR"] == expected


def test_asking_for_more_hops_than_the_header_holds_keeps_the_direct_peer():
    environ = _environ("203.0.113.7, 10.9.9.9")
    _prepare_proxy_fix(9)(environ, _noop)
    assert environ["REMOTE_ADDR"] == "10.0.0.1"


def test_over_counting_the_chain_is_still_forgeable_and_that_is_the_hazard():
    environ = _environ("192.0.2.1, 192.0.2.2")
    environ["HTTP_X_FORWARDED_FOR"] += ", 10.9.9.9"
    _prepare_proxy_fix(3)(environ, _noop)
    assert environ["REMOTE_ADDR"] == "192.0.2.1"

    honest = _environ("192.0.2.1, 192.0.2.2")
    honest["HTTP_X_FORWARDED_FOR"] += ", 10.9.9.9"
    _prepare_proxy_fix(1)(honest, _noop)
    assert honest["REMOTE_ADDR"] == "10.9.9.9"


def test_the_hop_count_applies_to_host_and_proto_too():
    environ = _environ(
        "198.51.100.4, 203.0.113.7, 10.9.9.9",
        forwarded_host="outer.example, inner.example",
        forwarded_proto="https, http",
    )
    _prepare_proxy_fix(2)(environ, _noop)
    assert environ["HTTP_HOST"] == "outer.example"
    assert environ["wsgi.url_scheme"] == "https"


def test_the_same_hop_count_reuses_one_wrapper():
    assert _prepare_proxy_fix(2) is _prepare_proxy_fix(2)
    assert _prepare_proxy_fix(2) is not _prepare_proxy_fix(3)


class _Session(dict):
    can_save = True


def _dispatch_request(routing, headers=None, method="GET"):
    request: Any = types.SimpleNamespace(
        future_response=FutureResponse(),
        session=_Session(),
        httprequest=types.SimpleNamespace(
            method=method,
            headers=headers or {},
        ),
    )
    rule = types.SimpleNamespace(endpoint=types.SimpleNamespace(routing=routing))
    HttpDispatcher(request).pre_dispatch(rule, {})
    return request.future_response.headers


def test_expose_headers_are_advertised_when_declared():
    headers = _dispatch_request(
        {
            "type": "http",
            "methods": ("GET",),
            "cors": "*",
            "cors_expose_headers": ("X-Total-Count", "X-Page"),
        }
    )
    assert headers["Access-Control-Expose-Headers"] == "X-Total-Count, X-Page"


def test_expose_headers_accepts_an_already_rendered_string():
    headers = _dispatch_request(
        {
            "type": "http",
            "methods": ("GET",),
            "cors": "*",
            "cors_expose_headers": "X-Total-Count",
        }
    )
    assert headers["Access-Control-Expose-Headers"] == "X-Total-Count"


def test_nothing_is_advertised_when_the_route_declares_none():
    headers = _dispatch_request({"type": "http", "methods": ("GET",), "cors": "*"})
    assert "Access-Control-Expose-Headers" not in headers


def test_expose_headers_are_not_advertised_without_cors():
    headers = _dispatch_request(
        {
            "type": "http",
            "methods": ("GET",),
            "cors_expose_headers": ("X-Total-Count",),
        }
    )
    assert "Access-Control-Expose-Headers" not in headers


def test_cors_expose_headers_is_a_declared_route_parameter():
    from odoo.http.routing import _KNOWN_ROUTING_PARAMETERS

    assert "cors_expose_headers" in _KNOWN_ROUTING_PARAMETERS


def test_a_bodyless_status_carries_no_content_type():
    response = prepare_no_content_response(headers=[("Allow", "GET, HEAD, OPTIONS")])
    assert response.status_code == 204
    assert "Content-Type" not in response.headers
    assert response.headers["Allow"] == "GET, HEAD, OPTIONS"


def test_the_headers_facade_can_delete():
    response = prepare_no_content_response()
    response.headers["X-Gone"] = "1"
    del response.headers["X-Gone"]
    assert "X-Gone" not in response.headers


def test_the_dispatcher_answers_options_without_a_content_type():
    import werkzeug.exceptions

    with pytest.raises(werkzeug.exceptions.HTTPException) as caught:
        _dispatch_request({"type": "http", "methods": ("POST",)}, method="OPTIONS")
    response = caught.value.response
    assert response is not None
    assert response.status_code == 204
    assert "Content-Type" not in response.headers
    assert response.headers["Allow"] == "POST, OPTIONS"


def test_the_cors_preflight_is_also_bodyless():
    import werkzeug.exceptions

    with pytest.raises(werkzeug.exceptions.HTTPException) as caught:
        _dispatch_request(
            {"type": "http", "methods": ("POST",), "cors": "*"},
            headers={"Origin": "https://x.example"},
            method="OPTIONS",
        )
    assert caught.value.response.status_code == 204
    assert "Content-Type" not in caught.value.response.headers


def test_the_abstract_dispatcher_still_declares_no_expose_headers():
    assert not hasattr(Dispatcher, "cors_expose_headers")


def test_cors_methods_resolves_each_step_with_is_none():
    from odoo.http._cors import _get_cors_methods
    from odoo.http.constants import DEFAULT_ALLOWED_METHODS

    # A route with no methods= is unrestricted at runtime: the preflight
    # advertises the full default set, not a GET/POST guess.
    assert tuple(_get_cors_methods(None, {})) == tuple(DEFAULT_ALLOWED_METHODS)
    assert tuple(_get_cors_methods(None, {"methods": None})) == tuple(
        DEFAULT_ALLOWED_METHODS
    )
    # An explicitly empty declaration accepts only OPTIONS at runtime; an
    # empty Allow-Methods header would be malformed, so OPTIONS is advertised.
    assert tuple(_get_cors_methods((), {"methods": ("PUT",)})) == ("OPTIONS",)
    assert tuple(_get_cors_methods(None, {"methods": ()})) == ("OPTIONS",)
    assert tuple(_get_cors_methods(("POST",), {"methods": ("PUT",)})) == ("POST",)
    assert tuple(_get_cors_methods(None, {"methods": ("PUT",)})) == ("PUT",)


class _Sec:
    def __init__(self, origin, host_url, is_secure=False):
        self.headers = {"Origin": origin} if origin is not None else {}
        self.host_url = host_url
        self.is_secure = is_secure


def _same_host(origin, host_url="http://app.example.com/", is_secure=False):
    from odoo.http._cors import resolve_cors_same_host

    return resolve_cors_same_host(
        SimpleNamespace(httprequest=_Sec(origin, host_url, is_secure))
    )


@pytest.mark.parametrize(
    ("origin", "host_url", "is_secure", "allowed"),
    [
        ("http://app.example.com", "http://app.example.com/", False, True),
        ("https://app.example.com", "https://app.example.com/", True, True),
        ("http://app.example.com:8069", "http://app.example.com:8069/", False, True),
        ("http://app.example.com:9999", "http://app.example.com/", False, False),
        ("http://app.example.com", "http://app.example.com:8069/", False, False),
        ("https://evil.example", "http://app.example.com/", False, False),
        ("http://localhost", "http://app.example.com/", False, False),
        ("http://app.example.com", "https://app.example.com/", True, False),
        ("https://app.example.com", "http://app.example.com/", False, True),
        ("http://app.example.com:80.evil.com", "http://app.example.com/", False, False),
        (None, "http://app.example.com/", False, False),
        ("", "http://app.example.com/", False, False),
        ("null", "http://app.example.com/", False, False),
    ],
)
def test_cors_same_host_compares_the_whole_origin(origin, host_url, is_secure, allowed):
    got = _same_host(origin, host_url, is_secure)
    expected = origin if allowed else None
    assert got == expected, f"{origin!r} vs {host_url!r}: got {got!r}"
