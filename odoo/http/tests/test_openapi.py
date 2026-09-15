import functools
import logging
from typing import TYPE_CHECKING, Any, cast

import pytest
import werkzeug.routing

from odoo.http.openapi import (
    RouteInfo,
    _get_methods_effective,
    _prepare_operation_id,
    prepare_openapi_document,
    prepare_openapi_from_map,
)
from odoo.http.routing import prepare_routing_map

if TYPE_CHECKING:
    from odoo.http._protocols import Endpoint


def _route(rule, *, methods=frozenset(), routing=None, handler=None):
    return RouteInfo(
        rule=rule,
        methods=frozenset(methods),
        routing=routing or {"type": "http", "auth": "public"},
        handler=handler or (lambda self: None),
    )


def test_effective_methods_defaults_when_no_allow_list():
    http_route = _route("/v", methods=frozenset(), routing={"type": "http"})
    assert _get_methods_effective(http_route) == frozenset({"GET", "POST"})
    rpc_route = _route("/rpc", methods=frozenset(), routing={"type": "jsonrpc"})
    assert _get_methods_effective(rpc_route) == frozenset({"POST"})


def test_effective_methods_strips_implicit_verbs():
    r = _route("/v", methods=frozenset({"GET", "HEAD", "OPTIONS"}))
    assert _get_methods_effective(r) == frozenset({"GET"})
    only_implicit = _route("/v", methods=frozenset({"HEAD", "OPTIONS"}))
    assert _get_methods_effective(only_implicit) == frozenset({"GET", "POST"})


def test_methods_none_route_emits_operations():
    doc = prepare_openapi_document([_route("/web/version", methods=frozenset())])
    assert sorted(doc["paths"]["/web/version"]) == ["get", "post"]


def test_effective_methods_distinguishes_unset_from_explicitly_empty():
    unset = _route("/v", methods=frozenset(), routing={"type": "http"})
    assert _get_methods_effective(unset) == frozenset({"GET", "POST"})
    explicitly_empty = _route(
        "/v",
        methods=frozenset({"OPTIONS"}),
        routing={"type": "http", "methods": []},
    )
    assert _get_methods_effective(explicitly_empty) == frozenset()


def test_operation_id_disambiguates_realistic_collision():
    used: set[str] = set()
    first = _prepare_operation_id("GET", "/shop/cart", used)
    second = _prepare_operation_id("GET", "/shop-cart", used)
    assert first == "get_shop_cart"
    assert second == "get_shop_cart_2"
    assert first != second


def test_build_openapi_no_duplicate_operation_ids():
    doc = prepare_openapi_document(
        [
            _route("/shop/cart", methods=frozenset({"GET"})),
            _route("/shop-cart", methods=frozenset({"GET"})),
        ]
    )
    ids = [op["operationId"] for path in doc["paths"].values() for op in path.values()]
    assert len(ids) == len(set(ids)) == 2


def test_typed_route_documents_query_params_and_400():
    def handler(self, n: int, flag: bool = False):
        pass

    handler.__doc__ = "List things."

    route = _route(
        "/typed",
        methods=frozenset({"GET"}),
        routing={"type": "http", "auth": "public", "typed": True},
        handler=handler,
    )
    op = prepare_openapi_document([route])["paths"]["/typed"]["get"]
    assert op["summary"] == "List things."
    names = {p["name"]: p for p in op["parameters"]}
    assert names["n"]["required"] is True
    assert names["n"]["schema"] == {"type": "integer"}
    assert names["flag"]["required"] is False
    assert "400" in op["responses"]


def test_typed_jsonrpc_documents_the_enveloped_request_body():
    def handler(self, n: int): ...

    route = _route(
        "/rpc",
        methods=frozenset({"POST"}),
        routing={"type": "jsonrpc", "auth": "user", "typed": True},
        handler=handler,
    )
    op = prepare_openapi_document([route])["paths"]["/rpc"]["post"]
    envelope = op["requestBody"]["content"]["application/json"]["schema"]
    assert envelope["properties"]["jsonrpc"] == {"type": "string", "const": "2.0"}
    assert envelope["required"] == ["params"]
    params = envelope["properties"]["params"]
    assert params["properties"]["n"] == {"type": "integer"}
    assert params["required"] == ["n"]


def test_typed_jsonrpc_documents_the_400_its_dispatcher_answers():
    def handler(self, n: int): ...

    route = _route(
        "/rpc",
        methods=frozenset({"POST"}),
        routing={"type": "jsonrpc", "auth": "user", "typed": True},
        handler=handler,
    )
    op = prepare_openapi_document([route])["paths"]["/rpc"]["post"]
    assert op["responses"]["400"] == {"description": "Invalid request parameters"}, (
        "JsonRPCDispatcher answers a ParameterError with the same HTTP 400 "
        "envelope as a malformed body, so the document says so"
    )


def test_typed_jsonrpc_envelope_without_required_params_does_not_require_params():
    def handler(self, n: int = 0): ...

    route = _route(
        "/rpc",
        methods=frozenset({"POST"}),
        routing={"type": "jsonrpc", "auth": "user", "typed": True},
        handler=handler,
    )
    op = prepare_openapi_document([route])["paths"]["/rpc"]["post"]
    envelope = op["requestBody"]["content"]["application/json"]["schema"]
    assert "required" not in envelope
    assert "required" not in envelope["properties"]["params"]


def test_path_param_not_duplicated_as_query_param():
    def handler(self, ident: int, q: str | None = None):
        pass

    route = _route(
        "/item/<int:ident>",
        methods=frozenset({"GET"}),
        routing={"type": "http", "auth": "public", "typed": True},
        handler=handler,
    )
    op = prepare_openapi_document([route])["paths"]["/item/{ident}"]["get"]
    ident_params = [p for p in op["parameters"] if p["name"] == "ident"]
    assert len(ident_params) == 1
    assert ident_params[0]["in"] == "path"
    assert {p["name"] for p in op["parameters"]} == {"ident", "q"}


def test_path_param_not_duplicated_in_request_body():
    def handler(self, ident: int, name: str):
        pass

    route = _route(
        "/item/<int:ident>",
        methods=frozenset({"POST"}),
        routing={"type": "json2", "auth": "bearer", "typed": True},
        handler=handler,
    )
    op = prepare_openapi_document([route])["paths"]["/item/{ident}"]["post"]
    body = op["requestBody"]["content"]["application/json"]["schema"]
    assert set(body["properties"]) == {"name"}
    assert body["required"] == ["name"]
    assert [p["name"] for p in op["parameters"] if p["in"] == "path"] == ["ident"]


def test_typed_only_filters_untyped_routes():
    typed = _route(
        "/typed",
        methods=frozenset({"GET"}),
        routing={"type": "http", "auth": "public", "typed": True},
    )
    untyped = _route("/plain", methods=frozenset({"GET"}))
    doc = prepare_openapi_document([typed, untyped], typed_only=True)
    assert set(doc["paths"]) == {"/typed"}


def test_security_schemes_registered_per_auth():
    bearer = _route(
        "/b", methods=frozenset({"GET"}), routing={"type": "http", "auth": "bearer"}
    )
    doc = prepare_openapi_document([bearer])
    assert "bearerAuth" in doc["components"]["securitySchemes"]
    assert doc["paths"]["/b"]["get"]["security"] == [{"bearerAuth": []}]


def test_openapi_from_map_roundtrip():
    m = werkzeug.routing.Map()

    def _handler(self, ident): ...

    handler: Any = _handler
    handler.routing = {"type": "http", "auth": "public"}
    handler.original_endpoint = handler
    m.add(werkzeug.routing.Rule("/a/<int:ident>", endpoint=handler, methods=["GET"]))
    doc = prepare_openapi_from_map(m, title="T", version="9")
    op = doc["paths"]["/a/{ident}"]["get"]
    assert doc["info"] == {"title": "T", "version": "9"}
    assert op["parameters"][0]["schema"] == {"type": "integer"}


def test_a_colliding_path_template_keeps_the_first_and_warns(caplog):
    routes = [
        _route("/a/<int:x>", methods={"GET"}),
        _route("/a/<string:x>", methods={"GET"}),
    ]
    with caplog.at_level(logging.WARNING, logger="odoo.http.openapi"):
        doc = prepare_openapi_document(routes)

    assert list(doc["paths"]) == ["/a/{x}"]
    assert list(doc["paths"]["/a/{x}"]) == ["get"]
    assert doc["paths"]["/a/{x}"]["get"]["operationId"] == "get_a_x"
    assert "already described by" in caplog.text
    assert "/a/<string:x>" in caplog.text


def test_a_collision_does_not_burn_an_operation_id():
    doc = prepare_openapi_document(
        [
            _route("/a/<int:x>", methods={"GET"}),
            _route("/a/<string:x>", methods={"GET"}),
            _route("/b", methods={"GET"}),
        ]
    )
    ids = sorted(
        op["operationId"] for item in doc["paths"].values() for op in item.values()
    )
    assert ids == ["get_a_x", "get_b"]


def test_two_verbs_on_one_template_are_both_kept():
    doc = prepare_openapi_document(
        [
            _route("/a", methods={"GET"}),
            _route("/a", methods={"POST"}),
        ]
    )
    assert sorted(doc["paths"]["/a"]) == ["get", "post"]


def _endpoint(rule, handler=None, **routing):
    def default(self, **kw):
        pass

    handler = handler or default
    partial = functools.partial(handler)
    functools.update_wrapper(partial, handler)
    routing.setdefault("type", "http")
    routing.setdefault("auth", "public")
    routing.setdefault("methods", None)
    routing["routes"] = [rule]
    endpoint = cast("Endpoint", partial)
    endpoint.routing = routing
    endpoint.original_endpoint = handler
    endpoint._param_specs = None
    return endpoint


def test_a_rule_repeating_a_path_parameter_is_skipped_not_emitted():
    routes = [
        RouteInfo(
            rule="/dup/<int:id>/<int:id>",
            methods=frozenset({"GET"}),
            routing={"type": "http", "auth": "public"},
            handler=lambda self, **kw: None,
        ),
        RouteInfo(
            rule="/fine/<int:id>",
            methods=frozenset({"GET"}),
            routing={"type": "http", "auth": "public"},
            handler=lambda self, **kw: None,
        ),
    ]

    doc = prepare_openapi_document(routes)

    assert "/dup/{id}/{id}" not in doc["paths"]
    assert "/fine/{id}" in doc["paths"], "one bad rule must not cost the good ones"
    for path_item in doc["paths"].values():
        for operation in path_item.values():
            seen = [(p["name"], p["in"]) for p in operation.get("parameters", [])]
            assert len(seen) == len(set(seen))


def test_the_lazy_builder_lets_a_duplicate_parameter_rule_into_the_map():
    with pytest.raises(SyntaxError):
        werkzeug.routing.Map(
            [werkzeug.routing.Rule("/dup/<int:id>/<int:id>", endpoint="e")]
        )

    routing_map = prepare_routing_map(
        [("/dup/<int:id>/<int:id>", _endpoint("/dup/<int:id>/<int:id>"))]
    )

    assert [r.rule for r in routing_map.iter_rules()] == ["/dup/<int:id>/<int:id>"]
    assert "/dup/{id}/{id}" not in prepare_openapi_from_map(routing_map)["paths"]
