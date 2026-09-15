import contextlib
import logging
from typing import Any, cast

import pytest

from odoo.http import routing as routing_module
from odoo.http._params import coerce_params
from odoo.http._protocols import HasRouting
from odoo.http.controller import Controller
from odoo.http.routing import route


@pytest.fixture(autouse=True)
def _clean_registry():
    saved = {k: list(v) for k, v in Controller.children_classes.items()}
    Controller.children_classes.clear()
    yield
    Controller.children_classes.clear()
    for k, v in saved.items():
        Controller.children_classes[k].extend(v)


def _merge(*mod_cls):
    from odoo.http.routing import _generate_routing_rules

    Controller.children_classes.clear()
    for mod, cls in mod_cls:
        Controller.children_classes[mod].append(cls)
    mods = [m for m, _ in mod_cls]
    with contextlib.suppress(Exception):
        logging.disable(logging.CRITICAL)
    result = {url: ep.routing for url, ep in _generate_routing_rules(mods, False)}
    logging.disable(logging.NOTSET)
    return result


def test_bearer_route_is_stateless_by_default():
    class C(Controller):
        @route("/a", type="json2", auth="bearer")
        def x(self):
            return {}

    C.__module__ = "odoo.addons.ma.controllers"
    (routing,) = _merge(("ma", C)).values()
    assert routing["auth"] == "bearer"
    assert routing["save_session"] is False


def test_bearer_overridden_to_user_regains_session_persistence():

    class Parent(Controller):
        @route("/b", type="json2", auth="bearer")
        def x(self):
            return {}

    Parent.__module__ = "odoo.addons.ma.controllers"

    class Child(Parent):
        @route(auth="user")
        def x(self):
            return super().x()

    Child.__module__ = "odoo.addons.mb.controllers"

    for routing in _merge(("ma", Parent), ("mb", Child)).values():
        assert routing["auth"] == "user"
        assert routing["save_session"] is True


def test_explicit_save_session_false_is_preserved():
    class C(Controller):
        @route("/c", type="http", auth="user", save_session=False)
        def x(self):
            return None

    C.__module__ = "odoo.addons.ma.controllers"
    (routing,) = _merge(("ma", C)).values()
    assert routing["auth"] == "user"
    assert routing["save_session"] is False


def test_explicit_save_session_true_on_bearer_is_preserved():
    class C(Controller):
        @route("/d", type="json2", auth="bearer", save_session=True)
        def x(self):
            return {}

    C.__module__ = "odoo.addons.ma.controllers"
    (routing,) = _merge(("ma", C)).values()
    assert routing["save_session"] is True


def test_plain_user_route_persists_session():
    class C(Controller):
        @route("/e", type="http", auth="user")
        def x(self):
            return None

    C.__module__ = "odoo.addons.ma.controllers"
    (routing,) = _merge(("ma", C)).values()
    assert routing["save_session"] is True


def test_merge_never_mutates_declared_fragments():

    class Parent(Controller):
        @route("/m", type="http", auth="user", readonly=False)
        def x(self):
            return None

    Parent.__module__ = "odoo.addons.ma.controllers"

    class Child(Parent):
        @route(readonly=True)
        def x(self):
            return super().x()

    Child.__module__ = "odoo.addons.mb.controllers"

    parent_decl = dict(Parent.__dict__["x"].original_routing)
    child_decl = dict(Child.__dict__["x"].original_routing)

    for routing in _merge(("ma", Parent), ("mb", Child)).values():
        assert routing["type"] == "http"
        assert routing["readonly"] is False

    assert dict(Parent.__dict__["x"].original_routing) == parent_decl
    assert dict(Child.__dict__["x"].original_routing) == child_decl
    assert child_decl["readonly"] is True
    assert not hasattr(Parent.__dict__["x"], "_merged_route_type")
    assert not hasattr(Child.__dict__["x"], "_merged_route_type")

    for routing in _merge(("ma", Parent), ("mb", Child)).values():
        assert routing["type"] == "http"
        assert routing["readonly"] is False
    assert dict(Child.__dict__["x"].original_routing) == child_decl


def test_an_override_may_not_change_the_route_type():
    class Parent(Controller):
        @route("/typeconflict", type="jsonrpc", auth="none")
        def x(self):
            return {}

    Parent.__module__ = "odoo.addons.ma.controllers"

    class Child(Parent):
        @route(type="http")
        def x(self):
            return {}

    Child.__module__ = "odoo.addons.mb.controllers"

    Controller.children_classes.clear()
    Controller.children_classes["ma"].append(Parent)
    Controller.children_classes["mb"].append(Child)

    records = []

    class _Cap(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    handler = _Cap()
    routing_module._logger.addHandler(handler)
    try:
        rules = dict(routing_module._generate_routing_rules(["ma", "mb"], False))
    finally:
        routing_module._logger.removeHandler(handler)

    assert rules == {}
    assert any("overrides a type='jsonrpc' route" in m for m in records), records
    assert any("The route is not served." in m for m in records), records


def test_an_override_restating_the_same_type_is_fine():
    class Parent(Controller):
        @route("/same", type="jsonrpc", auth="none")
        def x(self):
            return {}

    Parent.__module__ = "odoo.addons.ma.controllers"

    class Child(Parent):
        @route(type="jsonrpc")
        def x(self):
            return {}

    Child.__module__ = "odoo.addons.mb.controllers"

    for routing in _merge(("ma", Parent), ("mb", Child)).values():
        assert routing["type"] == "jsonrpc"


def test_options_added_to_methods_allow_list():
    from odoo.http.routing import prepare_rule_kwargs

    def _endpoint(self): ...

    endpoint = cast("HasRouting", _endpoint)
    endpoint.routing = {"methods": ["GET"], "cors": "*"}
    kwargs = prepare_rule_kwargs(endpoint)
    assert "OPTIONS" in kwargs["methods"]


def test_unknown_route_parameter_warns(caplog):
    import logging

    from odoo.http.routing import register_routing_parameters, route

    with caplog.at_level(logging.WARNING, logger="odoo.http.routing"):

        @route("/probe/unknown-kwarg", type="http", auth="none", raedonly=True)
        def endpoint(self):
            return ""

    assert any(
        "unknown @route parameter" in rec.message and "raedonly" in str(rec.args)
        for rec in caplog.records
    )

    register_routing_parameters("probe_extension_key")
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="odoo.http.routing"):

        @route("/probe/known-kwarg", type="http", auth="none", probe_extension_key=1)
        def endpoint2(self):
            return ""

    assert not caplog.records


def _endpoints(*mod_cls):
    from odoo.http.routing import _generate_routing_rules

    Controller.children_classes.clear()
    for mod, cls in mod_cls:
        Controller.children_classes[mod].append(cls)
    with contextlib.suppress(Exception):
        logging.disable(logging.CRITICAL)
    result = dict(_generate_routing_rules([m for m, _ in mod_cls], False))
    logging.disable(logging.NOTSET)
    return result


def test_typed_is_inherited_by_an_override_that_does_not_restate_it():
    seen = {}

    class Parent(Controller):
        __module__ = "odoo.addons.merge_typed"

        @route("/merge/typed", type="http", auth="none", typed=True)
        def hit(self, n: int, **kw):
            seen["v"] = (n, type(n).__name__)
            return "ok"

    class Child(Parent):
        __module__ = "odoo.addons.merge_typed"

        @route()
        def hit(self, n: int, **kw):
            seen["v"] = (n, type(n).__name__)
            return "ok"

    endpoint = _endpoints(("merge_typed", Parent), ("merge_typed", Child))[
        "/merge/typed"
    ]
    assert endpoint.routing.get("typed") is True
    endpoint(**coerce_params({"n": "5"}, endpoint._param_specs))
    assert seen["v"] == (5, "int"), "the override must coerce, not pass the raw string"


def test_an_override_can_still_opt_out_of_typed():
    seen: dict[str, tuple[Any, str]] = {}

    class Parent(Controller):
        __module__ = "odoo.addons.merge_untyped"

        @route("/merge/untyped", type="http", auth="none", typed=True)
        def hit(self, n: int, **kw):
            return "ok"

    class Child(Parent):
        __module__ = "odoo.addons.merge_untyped"

        @route(typed=False)
        def hit(self, n: int, **kw):
            seen["v"] = (n, type(n).__name__)
            return "ok"

    endpoint = _endpoints(("merge_untyped", Parent), ("merge_untyped", Child))[
        "/merge/untyped"
    ]
    assert endpoint._param_specs is None
    endpoint(n="9")
    assert seen["v"] == ("9", "str")


def test_typed_specs_are_stable_across_repeated_map_builds():
    seen = {}

    class Parent(Controller):
        __module__ = "odoo.addons.merge_rebuild"

        @route("/merge/rebuild", type="http", auth="none", typed=True)
        def hit(self, n: int, **kw):
            seen["v"] = (n, type(n).__name__)
            return "ok"

    args = (("merge_rebuild", Parent),)
    for raw, want in (("3", 3), ("4", 4)):
        endpoint = _endpoints(*args)["/merge/rebuild"]
        endpoint(**coerce_params({"n": raw}, endpoint._param_specs))
        assert seen["v"] == (want, "int")
    assert not hasattr(Parent.__dict__["hit"], "_param_specs")


def test_a_plain_helper_method_is_neither_a_route_nor_a_warning(caplog):
    from odoo.http.routing import _generate_routing_rules

    class Base(Controller):
        @route("/a", auth="none")
        def a(self):
            return self._helper()

        def _helper(self):
            return "base"

    Base.__module__ = "odoo.addons.ma.controllers"

    class Child(Base):
        def _helper(self):
            return "child"

    Child.__module__ = "odoo.addons.mb.controllers"

    Controller.children_classes.clear()
    Controller.children_classes["ma"].append(Base)
    with caplog.at_level(logging.WARNING, logger="odoo.http.routing"):
        rules = dict(_generate_routing_rules(["ma", "mb"], False))
    assert set(rules) == {"/a"}
    assert "without @route()" not in caplog.text
    assert rules["/a"]().data == b"child"


def test_an_undecorated_override_of_a_route_is_refused_once(caplog):
    from odoo.http.routing import _generate_routing_rules

    class Base(Controller):
        @route("/a", auth="none")
        def a(self):
            return "base"

    Base.__module__ = "odoo.addons.ma.controllers"

    class Child(Base):
        def a(self):
            return "child"

    Child.__module__ = "odoo.addons.mb.controllers"

    Controller.children_classes.clear()
    Controller.children_classes["ma"].append(Base)
    with caplog.at_level(logging.ERROR, logger="odoo.http.routing"):
        rules = dict(_generate_routing_rules(["ma", "mb"], False))
    assert rules == {}
    assert caplog.text.count("overrides a route without @route()") == 1
