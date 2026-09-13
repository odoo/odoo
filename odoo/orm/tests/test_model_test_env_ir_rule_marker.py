import pytest

from odoo import fields, models
from odoo.orm.model_test_env import (
    InMemoryRecordRulesNotSupported,
    model_test_env,
)

_MOD = "test_ir_rule_marker"


class Widget(models.Model):
    _name = "irm.widget"
    _module = _MOD
    _description = "widget"
    _log_access = False

    name = fields.Char()


class IrRuleStub(models.AbstractModel):
    _name = "ir.rule"
    _description = "ir.rule (caller stub)"
    _register = False
    _module = None

    def _get_domain_accessible_records(self, model_name, mode="read"):
        return []


def test_env_ir_rule_access_raises_loud_marker():
    with model_test_env(Widget) as env:
        with pytest.raises(InMemoryRecordRulesNotSupported) as excinfo:
            env["ir.rule"]
        message = str(excinfo.value)
        assert "record rules are NOT enforced" in message
        assert "access_policy" in message
        assert "TransactionCase" in message
        with pytest.raises(InMemoryRecordRulesNotSupported):
            env.registry["ir.rule"]


def test_membership_probes_stay_false_and_quiet():
    with model_test_env(Widget) as env:
        assert "ir.rule" not in env
        assert "ir.rule" not in env.registry
        with pytest.raises(KeyError):
            env.registry["no.such.model"]


def test_caller_provided_ir_rule_model_is_served():
    with model_test_env(Widget, IrRuleStub) as env:
        assert "ir.rule" in env.registry
        rule_model = env["ir.rule"]
        assert rule_model._name == "ir.rule"
        assert rule_model._get_domain_accessible_records("irm.widget", "read") == []


def test_harness_crud_untouched_by_marker():
    with model_test_env(Widget) as env:
        record = env["irm.widget"].create({"name": "w"})
        assert record.name == "w"
        assert env["irm.widget"].search([("name", "=", "w")]) == record
