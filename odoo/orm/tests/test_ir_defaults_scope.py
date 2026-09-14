from odoo import fields, models
from odoo.orm.model_test_env import model_test_env
from odoo.orm.primitives import SUPERUSER_ID

_MOD = "test_ir_defaults_scope"


class Thing(models.Model):
    _name = "ids.thing"
    _module = _MOD
    _description = "thing"
    _log_access = False

    name = fields.Char()


class IrDefault(models.AbstractModel):
    _name = "ir.default"
    _module = _MOD
    _description = "ir.default (scope stub)"

    asked: list = []

    def _get_model_defaults(self, model_name, condition=False):
        if model_name == "ids.thing":
            self.asked.append((self.env.uid, self.env.su, self.env.company.id))
        return {"name": "fallback"} if model_name == "ids.thing" else {}


def _fallbacks(env):
    return env.registry.metaschema.company_dependent_fallbacks(env, "ids.thing")


def test_the_fallbacks_are_read_as_the_superuser_in_the_environment_company():
    with model_test_env(Thing, IrDefault) as env:
        IrDefault.asked.clear()
        member = env["res.users"].create(
            {"name": "Member", "login": "member", "company_id": 1}
        )
        user_env = env(user=member.id, context={"allowed_company_ids": [1]})
        assert user_env.su is False
        assert _fallbacks(user_env) == {"name": "fallback"}
        assert IrDefault.asked == [(SUPERUSER_ID, True, 1)]


def test_the_fallbacks_follow_a_context_selected_company():
    with model_test_env(Thing, IrDefault) as env:
        IrDefault.asked.clear()
        other = env["res.company"].create({"name": "Other"})
        scoped = env(context={"allowed_company_ids": [other.id, 1]})
        assert scoped.company.id == other.id
        _fallbacks(scoped)
        _fallbacks(env)
        assert [asked[2] for asked in IrDefault.asked] == [other.id, env.company.id]
