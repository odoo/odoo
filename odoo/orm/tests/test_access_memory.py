import pytest

from odoo import fields, models
from odoo.orm.domain import Domain
from odoo.orm.model_test_env import (
    InMemoryAccessNotSupported,
    model_test_env,
)

_MOD = "test_access_memory"


class Doc(models.Model):
    _name = "rr.doc"
    _module = _MOD
    _description = "doc"
    _log_access = False

    name = fields.Char()
    confidential = fields.Boolean()


class IrAccess(models.AbstractModel):
    _name = "ir.access"
    # its own module name: model_test_env gathers every class of a module it is
    # handed, and the marker test below must build a registry without this one
    _module = _MOD + "_access"
    _description = "ir.access (test stub)"

    def _policy_signature(self):
        return (self.env.uid, *self._get_access_context())

    def _get_access_context(self):
        company_ids = self.env.context.get("allowed_company_ids")
        yield tuple(company_ids) if company_ids else company_ids

    def _bound_access_rows(self, model_name, operation):
        if model_name == "rr.doc":
            return [Domain("confidential", "=", False)], []
        return [Domain.TRUE], []


def _docs(env):
    Doc = env["rr.doc"]
    return Doc.create({"name": "public"}), Doc.create(
        {"name": "secret", "confidential": True}
    )


def test_rows_filter_a_user_search_and_not_a_superuser_one():
    with model_test_env(Doc, IrAccess) as env:
        public, secret = _docs(env)
        user_env = env(user=2, su=False)
        assert user_env["rr.doc"].search([]) == public.with_env(user_env)
        assert env["rr.doc"].search([]) == public + secret


def test_without_an_ir_access_model_a_user_search_trips_the_marker():
    with model_test_env(Doc) as env:
        _docs(env)
        user_env = env(user=2, su=False)
        with pytest.raises(InMemoryAccessNotSupported):
            user_env["rr.doc"].search([])
