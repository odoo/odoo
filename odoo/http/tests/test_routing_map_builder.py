from unittest import mock

import werkzeug.routing

from odoo.http import prepare_routing_map
from odoo.http.routing import FasterRule


class _Endpoint:
    def __init__(self, url, **routing):
        self.url = url
        self.routing = {"routes": [url], "type": "http", **routing}

    def __call__(self):
        return self.url


def _endpoint(url, **routing):
    return _Endpoint(url, **routing)


def test_slash_handling_is_the_same_for_every_rule():
    routing_map = prepare_routing_map(
        [("/a", _endpoint("/a")), ("/b/<x>", _endpoint("/b/<x>"))]
    )
    assert routing_map.strict_slashes is False
    rules = list(routing_map.iter_rules())
    assert len(rules) == 2
    assert all(isinstance(rule, FasterRule) for rule in rules)
    assert all(rule.merge_slashes is False for rule in rules)


def test_a_double_slash_is_not_collapsed_into_a_match():
    routing_map = prepare_routing_map([("/a/b", _endpoint("/a/b"))])
    adapter = routing_map.bind("example.com")
    assert adapter.match("/a/b")[0]() == "/a/b"
    assert not routing_map.bind("example.com").test("/a//b")


def test_declared_methods_are_widened_to_let_options_through():
    routing_map = prepare_routing_map(
        [("/a", _endpoint("/a", methods=("POST",)))],
    )
    rule = next(iter(routing_map.iter_rules()))
    assert rule.methods == {"POST", "OPTIONS"}


def test_converters_are_handed_to_the_map():
    class Shouty(werkzeug.routing.BaseConverter):
        regex = r"[A-Z]+"

    routing_map = prepare_routing_map(
        [("/a/<shouty:x>", _endpoint("/a/<shouty:x>"))],
        converters={"shouty": Shouty},
    )
    adapter = routing_map.bind("example.com")
    assert adapter.match("/a/LOUD")[1] == {"x": "LOUD"}
    assert not adapter.test("/a/quiet")


def test_an_empty_rule_set_still_builds_a_usable_map():
    routing_map = prepare_routing_map([])
    assert list(routing_map.iter_rules()) == []


def test_the_nodb_map_reads_a_negative_int_as_the_db_map_does():
    from odoo.http.routing import SignedIntConverter

    routing_map = werkzeug.routing.Map(converters={"int": SignedIntConverter})
    routing_map.add(werkzeug.routing.Rule("/n/<int:n>", endpoint="n"))
    assert routing_map.bind("localhost").match("/n/-3") == ("n", {"n": -3})


def test_the_application_builds_its_nodb_map_with_the_signed_int_converter():
    from odoo.http.application import Application
    from odoo.http.routing import SignedIntConverter

    app = Application()
    with mock.patch("odoo.http.application._generate_routing_rules", return_value=[]):
        routing_map = app.nodb_routing_map
    assert routing_map.converters["int"] is SignedIntConverter
