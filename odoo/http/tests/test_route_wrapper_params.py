import logging

import pytest
from werkzeug.exceptions import BadRequest

from odoo.http.controller import Controller
from odoo.http.routing import route


@pytest.fixture
def ctrl():
    saved = {k: list(v) for k, v in Controller.children_classes.items()}

    class _Ctrl(Controller):
        @route("/echo", type="jsonrpc", auth="none")
        def echo(self, db, login, password=None, **kw):
            return (db, login, password, kw)

        @route("/strict", type="jsonrpc", auth="none")
        def strict(self, a, b=1):
            return (a, b)

        @route("/positional", type="jsonrpc", auth="none")
        def positional(self, a, b):
            return (a, b)

    yield _Ctrl()
    Controller.children_classes.clear()
    for k, v in saved.items():
        Controller.children_classes[k].extend(v)


def test_a_missing_required_parameter_is_a_bad_request_not_a_type_error(ctrl):
    with pytest.raises(BadRequest, match=r"missing required parameter\(s\) \['db'\]"):
        ctrl.echo(login="x")


def test_every_missing_name_is_reported_sorted(ctrl):
    with pytest.raises(BadRequest, match=r"\['db', 'login'\]"):
        ctrl.echo(extra=1)


def test_a_complete_call_passes_defaults_and_extras_through(ctrl):
    assert ctrl.echo(db="d", login="l", extra=1) == ("d", "l", None, {"extra": 1})


def test_optional_parameters_are_never_required(ctrl):
    assert ctrl.strict(a=1) == (1, 1)


def test_a_surplus_parameter_is_still_dropped_with_a_warning(ctrl, caplog):
    with caplog.at_level(logging.WARNING, logger="odoo.http.routing"):
        assert ctrl.strict(a=1, zzz=2) == (1, 1)
    assert "ignoring args" in caplog.text


def test_positional_calls_bypass_the_check(ctrl):
    assert ctrl.positional(1, 2) == (1, 2)
    assert ctrl.positional(1, b=2) == (1, 2)


def test_the_method_typo_with_a_single_string_is_repaired_not_raised(caplog):
    with caplog.at_level(logging.WARNING, logger="odoo.http.routing"):

        @route("/typo", type="http", auth="none", method="POST")
        def ep(self): ...

    assert ep.original_routing["methods"] == ("POST",)
    assert any("assuming 'methods'" in r.message for r in caplog.records)
