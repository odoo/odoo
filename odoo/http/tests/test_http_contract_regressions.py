import io
from types import SimpleNamespace

import pytest
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import MethodNotAllowed, RequestEntityTooLarge
from werkzeug.test import EnvironBuilder

from odoo.http import Controller, _generate_routing_rules, route
from odoo.http._params import coerce_params
from odoo.http.core import _request_stack
from odoo.http.geoip import GeoIP
from odoo.http.openapi import prepare_openapi_from_map
from odoo.http.request_class import Request
from odoo.http.routing import prepare_routing_map
from odoo.http.stream import Stream
from odoo.http.wrappers import HTTPRequest, Response


@pytest.fixture
def req():
    return Request(HTTPRequest(EnvironBuilder().get_environ()), SimpleNamespace())


@pytest.mark.parametrize("attribute", ["path", "domain", "partitioned"])
def test_cookie_replacement_preserves_distinct_scopes(req, attribute):
    first = {"path": "/one"} if attribute == "path" else {}
    second = (
        {"path": "/two"}
        if attribute == "path"
        else {attribute: True if attribute == "partitioned" else "example.com"}
    )
    response = Response()
    response.set_cookie("preference", "one", **first)
    response.set_cookie("preference", "two", **second)
    assert len(response.headers.getlist("Set-Cookie")) == 2
    response = Response()
    response.set_cookie("preference", "one", **first)
    req.future_response.set_cookie("preference", "two", **second)
    req._update_response_from_future(response)
    assert len(response.headers.getlist("Set-Cookie")) == 2


@pytest.mark.parametrize("scope", [{"domain": "täst.example"}, {"path": "/café"}])
def test_cookie_replacement_uses_the_serialized_scope(scope):
    response = Response()
    response.set_cookie("choice", "first", **scope)
    response.set_cookie("choice", "second", **scope)
    cookies = response.headers.getlist("Set-Cookie")
    assert len(cookies) == 1
    assert cookies[0].startswith("choice=second;")


def test_invalid_cookie_replacement_preserves_the_existing_cookie():
    response = Response()
    response.set_cookie("choice", "first")
    original = response.headers.getlist("Set-Cookie")
    with pytest.raises(ValueError):
        response.set_cookie("choice", "second", samesite="invalid")
    assert response.headers.getlist("Set-Cookie") == original


def test_geoip_country_survives_a_missing_city_database():
    from odoo.http import geoip as module

    if module.geoip2 is None:
        pytest.skip("geoip2 unavailable")
    country = SimpleNamespace(country=SimpleNamespace(iso_code="MX"))
    app = SimpleNamespace(
        geoip_city_db=None, geoip_country_db=SimpleNamespace(country=lambda ip: country)
    )
    first = GeoIP("192.0.2.1", app)
    assert first.country_code == "MX"
    second = GeoIP("192.0.2.1", app)
    assert second.location.time_zone is None
    assert second.country_code == "MX"


def test_geoip_country_reader_is_authoritative_regardless_of_access_order():
    from odoo.http import geoip as module

    if module.geoip2 is None:
        pytest.skip("geoip2 unavailable")
    country = SimpleNamespace(country=SimpleNamespace(iso_code="MX"))
    city = SimpleNamespace(
        country=SimpleNamespace(iso_code="US"),
        location=SimpleNamespace(time_zone="America/Chicago"),
    )
    app = SimpleNamespace(
        geoip_city_db=SimpleNamespace(city=lambda ip: city),
        geoip_country_db=SimpleNamespace(country=lambda ip: country),
    )
    first, second = GeoIP("192.0.2.1", app), GeoIP("192.0.2.1", app)
    assert first.country_code == "MX"
    assert second.location.time_zone == "America/Chicago"
    assert second.country_code == first.country_code


@pytest.mark.parametrize(
    "token", [FileStorage(io.BytesIO(b"bad")), 1, {}, [], b"token"]
)
def test_non_string_csrf_input_is_rejected_without_reading_the_database(req, token):
    assert req.env is None
    assert req.is_valid_csrf(token) is False


def test_reroute_preserves_the_body_limit(req):
    req.httprequest = HTTPRequest(
        EnvironBuilder(method="POST", data=b"0123456789").get_environ()
    )
    req.httprequest.max_content_length = 5
    req.reroute("/different")
    assert req.httprequest.max_content_length == 5
    with pytest.raises(RequestEntityTooLarge):
        req.httprequest.get_data()


def test_stream_uses_the_servers_file_wrapper(req, tmp_path):
    path = tmp_path / "asset.bin"
    path.write_bytes(b"payload")
    calls = []

    def wrapper(file, block_size):
        calls.append(block_size)
        from werkzeug.wsgi import FileWrapper

        return FileWrapper(file, block_size)

    raw = req.httprequest.raw_environ
    raw["wsgi.file_wrapper"] = wrapper
    _request_stack.push(req)
    try:
        response = Stream._from_trusted_path(str(path)).prepare_response()
        assert b"".join(response.response) == b"payload"
        assert len(calls) == 1
        response._wrapped__.close()
    finally:
        _request_stack.pop()


@pytest.fixture
def controller_registry():
    saved = {k: list(v) for k, v in Controller.children_classes.items()}
    yield
    Controller.children_classes.clear()
    Controller.children_classes.update(saved)


def test_an_undecorated_override_is_a_definition_error_and_the_route_is_not_served(
    controller_registry, caplog
):
    import logging

    class Parent(Controller):
        __module__ = "odoo.addons.audit_routing_skip"

        @route("/audit/skip", auth="none", typed=True)
        def hit(self, count: int):
            return str(count + 1)

    class Child(Parent):
        __module__ = "odoo.addons.audit_routing_skip"

        def hit(self, count):
            raise AssertionError("the undecorated override ran")

    with caplog.at_level(logging.ERROR, logger="odoo.http.routing"):
        rules = dict(_generate_routing_rules(["audit_routing_skip"], True))
    assert "/audit/skip" not in rules, (
        "neither body is served: the parent's would be stale behaviour behind a "
        "warning, the child's would mask the missing decorator"
    )
    assert "overrides a route without @route()" in caplog.text
    assert "The route is not served" in caplog.text


def test_forwarding_overrides_preserve_inherited_coercion(controller_registry):
    class Parent(Controller):
        __module__ = "odoo.addons.audit_routing_forward"

        @route("/audit/forward", auth="none", typed=True)
        def hit(self, count: int):
            return str(count + 1)

    class Child(Parent):
        __module__ = "odoo.addons.audit_routing_forward"

        @route()
        def hit(self, **kwargs):
            return super().hit(**kwargs)

    endpoint = dict(_generate_routing_rules(["audit_routing_forward"], True))[
        "/audit/forward"
    ]
    assert endpoint._param_specs is not None
    response = endpoint(**coerce_params({"count": "4"}, endpoint._param_specs))
    assert response.get_data(as_text=True) == "5"


def test_unannotated_override_defaults_change_requiredness():
    from odoo.http._params import get_param_specs

    def parent(self, count: int):
        pass

    def child(self, count=5):
        pass

    specs = get_param_specs(child, get_param_specs(parent))
    assert not specs["count"].required
    assert coerce_params({}, specs) == {}
    assert coerce_params({"count": "6"}, specs) == {"count": 6}


def test_default_methods_agree_with_the_router_and_document(controller_registry):
    class Api(Controller):
        __module__ = "odoo.addons.audit_routing_methods"

        @route("/audit/methods", type="json2", auth="none")
        def hit(self):
            return {}

    routing_map = prepare_routing_map(
        _generate_routing_rules(["audit_routing_methods"], True)
    )
    router = routing_map.bind("localhost")
    documented = prepare_openapi_from_map(routing_map)["paths"]["/audit/methods"]
    assert set(documented) == {"get", "post", "put", "patch", "delete"}
    for method in documented:
        router.match("/audit/methods", method=method.upper())
    with pytest.raises(MethodNotAllowed):
        router.match("/audit/methods", method="CONNECT")


def test_a_method_string_is_rejected_at_definition_time():
    with pytest.raises(ValueError, match="collection"):

        @route("/bad", methods="POST")
        def hit(self):
            pass
