import pytest

from odoo import fields, models
from odoo.orm.model_test_env import (
    InMemoryAccessRightsNotSupported,
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


class Report(models.Model):
    _name = "marker.report"
    _module = _MOD
    _description = "a report with a field for system users"
    _log_access = False

    name = fields.Char()
    secret = fields.Char(groups="base.group_system")
    total = fields.Float(compute="_compute_total")

    def _compute_total(self):
        for report in self:
            report.total = 1.0


def test_the_users_stub_holds_groups_by_external_id():
    with model_test_env(Report) as env:
        Users = env["res.users"]
        user = Users.create(
            {"name": "u", "login": "u", "group_xmlids": "base.group_user"}
        )
        admin = Users.create(
            {
                "name": "a",
                "login": "a",
                "group_xmlids": "base.group_user,base.group_system",
            }
        )
        assert user.has_group("base.group_user") and not user.has_group(
            "base.group_system"
        )
        assert admin.has_groups("base.group_system,!base.group_public")
        assert not admin.has_groups("!base.group_user")
        assert user.has_groups("!base.group_system")
        assert not user.has_groups(".")
        assert admin._is_system() and not user._is_system()
        assert env.user._is_admin() and not user._is_admin()
        # fields_get answers the caller's groups, and the ormcache keyed on
        # the user's groups tells the two apart
        report = env["marker.report"].create({"name": "r", "secret": "s"})
        assert "secret" not in report.with_user(user).fields_get()
        assert "secret" in report.with_user(admin).fields_get()
        described = report.with_user(user).fields_get(["total"])["total"]
        assert (described["groupable"], described["sortable"]) == (False, False)


def test_an_access_check_by_a_plain_user_raises_the_loud_marker():
    with model_test_env(Report) as env:
        user = env["res.users"].create({"name": "u", "login": "u"})
        report = env["marker.report"].create({"name": "r"})
        with pytest.raises(InMemoryAccessRightsNotSupported) as excinfo:
            report.with_user(user).read(["name"])
        assert "access rights are NOT enforced" in str(excinfo.value)
        assert "TransactionCase" in str(excinfo.value)
