from types import SimpleNamespace

import pytest
from werkzeug.exceptions import HTTPException

from odoo.http._cookies import FutureResponse
from odoo.http._protocols import RequestState
from odoo.http.constants import CORS_DEFAULT_ALLOWED_HEADERS
from odoo.http.dispatcher import (
    HttpDispatcher,
    Json2Dispatcher,
    JsonRPCDispatcher,
    get_dispatcher_for_unmatched_route,
)


class _FakeSession:
    can_save = True


def _request(method="GET", headers=None, mimetype="text/html"):
    return SimpleNamespace(
        session=_FakeSession(),
        future_response=FutureResponse(),
        httprequest=SimpleNamespace(
            method=method,
            path="/x",
            headers=headers or {},
            mimetype=mimetype,
            max_content_length=None,
        ),
    )


def _rule(**routing):
    routing.setdefault("type", "http")
    routing.setdefault("methods", None)
    routing.setdefault("routes", ["/x"])
    return SimpleNamespace(endpoint=SimpleNamespace(routing=routing))


def _pre_dispatch(request, rule):
    dispatcher = HttpDispatcher(request)
    try:
        dispatcher.pre_dispatch(rule, {})
    except HTTPException as exc:
        return exc.get_response()
    return None


def test_credentialed_cors_echoes_the_origin_a_resolver_allows():
    req = _request(headers={"Origin": "https://app.example"})
    _pre_dispatch(
        req,
        _rule(
            cors=lambda r: r.httprequest.headers.get("Origin"), cors_credentials=True
        ),
    )

    headers = req.future_response.headers
    assert headers["Access-Control-Allow-Origin"] == "https://app.example"
    assert headers["Access-Control-Allow-Credentials"] == "true"
    assert "Origin" in headers["Vary"]


def test_a_resolver_that_declines_grants_nothing():
    req = _request(headers={"Origin": "https://evil.example"})
    _pre_dispatch(req, _rule(cors=lambda r: None, cors_credentials=True))

    headers = req.future_response.headers
    assert "Access-Control-Allow-Origin" not in headers
    assert "Access-Control-Allow-Credentials" not in headers
    assert headers["Vary"] == "Origin"


def test_a_resolver_varies_on_origin_even_without_credentials():
    req = _request(headers={"Origin": "https://app.example"})
    _pre_dispatch(req, _rule(cors=lambda r: "https://app.example"))

    headers = req.future_response.headers
    assert headers["Access-Control-Allow-Origin"] == "https://app.example"
    assert headers["Vary"] == "Origin"


def test_plain_cors_still_emits_the_declared_value():
    req = _request(headers={"Origin": "https://app.example"})
    _pre_dispatch(req, _rule(cors="*"))

    headers = req.future_response.headers
    assert headers["Access-Control-Allow-Origin"] == "*"
    assert "Access-Control-Allow-Credentials" not in headers


def test_a_resolver_returning_a_wildcard_grants_no_credentials():
    req = _request(headers={"Origin": "*"})
    _pre_dispatch(req, _rule(cors=lambda r: "*", cors_credentials=True))

    headers = req.future_response.headers
    assert "Access-Control-Allow-Origin" not in headers
    assert "Access-Control-Allow-Credentials" not in headers
    assert headers["Vary"] == "Origin"


def test_credentialed_cors_emits_nothing_without_an_origin():
    req = _request()
    _pre_dispatch(req, _rule(cors="https://app.example", cors_credentials=True))

    headers = req.future_response.headers
    assert "Access-Control-Allow-Origin" not in headers
    assert "Access-Control-Allow-Credentials" not in headers
    assert headers["Vary"] == "Origin"


def test_credentialed_cors_refuses_an_origin_it_does_not_allow():
    req = _request(headers={"Origin": "https://evil.example"})
    _pre_dispatch(req, _rule(cors="https://app.example", cors_credentials=True))

    headers = req.future_response.headers
    assert "Access-Control-Allow-Origin" not in headers
    assert "Access-Control-Allow-Credentials" not in headers


def test_credentialed_preflight_varies_on_both_reasons():
    req = _request(
        method="OPTIONS",
        headers={
            "Origin": "https://app.example",
            "Access-Control-Request-Headers": "X-Foo",
        },
    )
    response = _pre_dispatch(
        req, _rule(cors="https://app.example", cors_credentials=True)
    )

    assert response.status_code == 204
    vary = req.future_response.headers["Vary"]
    assert "Origin" in vary
    assert "Access-Control-Request-Headers" in vary


def test_options_does_not_run_the_handler_on_an_unrestricted_route():
    req = _request(method="OPTIONS")
    response = _pre_dispatch(req, _rule())

    assert response is not None, "pre_dispatch must short-circuit"
    assert response.status_code == 204
    allow = response.headers["Allow"]
    assert "OPTIONS" in allow
    assert "POST" in allow


def test_options_still_reaches_a_route_that_declares_it():
    req = _request(method="OPTIONS")
    assert _pre_dispatch(req, _rule(methods=("POST", "OPTIONS"))) is None


def test_options_on_a_cors_route_is_still_the_preflight():
    req = _request(method="OPTIONS", headers={"Origin": "https://app.example"})
    response = _pre_dispatch(req, _rule(cors="*", methods=("GET", "PUT")))

    assert response.status_code == 204
    assert req.future_response.headers["Access-Control-Max-Age"]
    assert response.headers["Allow"] == "GET, PUT, HEAD, OPTIONS"


def test_a_refused_preflight_still_says_which_methods_the_url_takes():
    req = _request(method="OPTIONS", headers={"Origin": "https://evil.example"})
    response = _pre_dispatch(
        req, _rule(cors=lambda r: None, cors_credentials=True, methods=("POST",))
    )

    assert response.status_code == 204
    assert "Access-Control-Allow-Origin" not in req.future_response.headers
    assert response.headers["Allow"] == "POST, OPTIONS"


@pytest.mark.parametrize(
    ("mimetype", "expected"),
    [
        ("application/json-rpc", JsonRPCDispatcher),
        ("application/json", Json2Dispatcher),
        ("text/html", HttpDispatcher),
        ("application/x-www-form-urlencoded", HttpDispatcher),
        ("", HttpDispatcher),
    ],
)
def test_unmatched_dispatcher_is_inferred_from_content_type(mimetype, expected):
    assert get_dispatcher_for_unmatched_route(_request(mimetype=mimetype)) is expected


def test_json_dispatchers_both_claim_application_json():
    assert "application/json" in JsonRPCDispatcher.mimetypes
    assert "application/json" in Json2Dispatcher.mimetypes


def test_unmatched_json_error_keeps_the_status_code():
    from werkzeug.exceptions import NotFound

    captured = {}

    class _Req(RequestState):
        def prepare_json_response(self, data, headers=None, cookies=None, status=200):
            captured["status"] = status
            return data

    dispatcher = Json2Dispatcher(_Req())
    dispatcher.prepare_error_response(NotFound())
    assert captured["status"] == 404


def test_extending_a_dispatcher_is_not_a_warning(caplog):
    import logging

    from odoo.http.dispatcher import JsonRPCDispatcher, _dispatchers

    saved = dict(_dispatchers)
    try:
        with caplog.at_level(logging.DEBUG, logger="odoo.http.dispatcher"):

            class _Extended(JsonRPCDispatcher):
                pass

        levels = {r.levelno for r in caplog.records}
        assert logging.WARNING not in levels, [r.getMessage() for r in caplog.records]
        assert any("extends" in r.getMessage() for r in caplog.records)
        assert _dispatchers["jsonrpc"] is _Extended
    finally:
        _dispatchers.clear()
        _dispatchers.update(saved)


def test_an_unrelated_class_claiming_a_routing_type_still_warns(caplog):
    import logging

    from odoo.http.dispatcher import Dispatcher, _dispatchers

    saved = dict(_dispatchers)
    try:
        with caplog.at_level(logging.DEBUG, logger="odoo.http.dispatcher"):

            class _Impostor(Dispatcher):
                routing_type = "jsonrpc"

                @classmethod
                def is_compatible_with_request(cls, request):
                    return True

                def dispatch(self, endpoint, args):
                    return None

                def prepare_error_response(self, exc):
                    return None

        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert warnings, [r.getMessage() for r in caplog.records]
        assert "unrelatedly replaces" in warnings[0].getMessage()
    finally:
        _dispatchers.clear()
        _dispatchers.update(saved)


def test_preflight_echoes_the_requested_headers_when_the_route_declares_none():
    req = _request(
        method="OPTIONS",
        headers={
            "Origin": "https://app.example",
            "Access-Control-Request-Headers": "X-Wild",
        },
    )
    _pre_dispatch(req, _rule(cors="*"))

    headers = req.future_response.headers
    assert headers["Access-Control-Allow-Headers"] == "X-Wild"
    assert "Access-Control-Request-Headers" in headers["Vary"]


def test_preflight_falls_back_to_the_default_header_list():
    req = _request(method="OPTIONS", headers={"Origin": "https://app.example"})
    _pre_dispatch(req, _rule(cors="*"))

    assert (
        req.future_response.headers["Access-Control-Allow-Headers"]
        == CORS_DEFAULT_ALLOWED_HEADERS
    )


@pytest.mark.parametrize(
    "declared", ["X-Api-Key, Content-Type", ("X-Api-Key", "Content-Type")]
)
def test_cors_allow_headers_narrows_the_preflight(declared):
    req = _request(
        method="OPTIONS",
        headers={
            "Origin": "https://app.example",
            "Access-Control-Request-Headers": "Authorization, X-Wild",
        },
    )
    _pre_dispatch(req, _rule(cors="*", cors_allow_headers=declared))

    headers = req.future_response.headers
    assert headers["Access-Control-Allow-Headers"] == "X-Api-Key, Content-Type"
    assert "Access-Control-Request-Headers" not in headers.get("Vary", "")


def test_cors_allow_headers_is_a_declared_routing_parameter():
    from odoo.http.routing import _KNOWN_ROUTING_PARAMETERS

    assert "cors_allow_headers" in _KNOWN_ROUTING_PARAMETERS
