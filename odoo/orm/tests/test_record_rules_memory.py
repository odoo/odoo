import pytest

from odoo import fields, models
from odoo.orm.model_test_env import (
    InMemoryRecordRulesNotSupported,
    model_test_env,
)

_MOD = "test_record_rules_memory"


class Doc(models.Model):
    _name = "rr.doc"
    _module = _MOD
    _description = "doc"
    _log_access = False

    name = fields.Char()
    confidential = fields.Boolean()


class IrModelAccess(models.AbstractModel):
    _name = "ir.model.access"
    _module = _MOD + "_access"
    _description = "ir.model.access (test stub)"

    def check(self, model, mode="read", raise_exception=True):
        return True


class IrRule(models.AbstractModel):
    _name = "ir.rule"
    # its own module name: model_test_env gathers every class of a module it is
    # handed, and the marker test below must build a registry without this one
    _module = _MOD + "_rules"
    _description = "ir.rule (test stub)"

    def _get_domain_accessible_records(self, model_name, mode="read"):
        from odoo.orm.domain import Domain

        if model_name == "rr.doc":
            return Domain("confidential", "=", False)
        return Domain.TRUE


def _docs(env):
    Doc = env["rr.doc"]
    return Doc.create({"name": "public"}), Doc.create(
        {"name": "secret", "confidential": True}
    )


def test_rules_filter_a_user_search_and_not_a_superuser_one():
    with model_test_env(Doc, IrModelAccess, IrRule) as env:
        public, secret = _docs(env)
        user_env = env(user=2, su=False)
        assert user_env["rr.doc"].search([]) == public.with_env(user_env)
        assert env["rr.doc"].search([]) == public + secret


def test_without_an_ir_rule_model_a_user_search_still_trips_the_marker():
    with model_test_env(Doc, IrModelAccess) as env:
        _docs(env)
        user_env = env(user=2, su=False)
        with pytest.raises(InMemoryRecordRulesNotSupported):
            user_env["rr.doc"].search([])
