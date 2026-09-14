from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_env_derive"


class Thing(models.Model):
    _name = "ed.thing"
    _module = _MOD
    _description = "thing"
    _log_access = False

    name = fields.Char()


def test_a_derived_environment_is_the_sudo_with_context_one_and_is_memoized():
    with model_test_env(Thing) as env:
        member = env["res.users"].create(
            {"name": "Member", "login": "member", "company_id": 1}
        )
        user_env = env(user=member.id, context={"default_name": "x", "lang": "en_US"})
        derived = user_env._derive(su=True, active_test=False)
        spelled = user_env["ed.thing"].sudo().with_context(active_test=False).env
        assert derived is spelled
        assert derived.su is True
        assert derived.context.get("active_test") is False
        assert "default_name" not in derived.context
        assert user_env._derive(su=True, active_test=False) is derived


def test_a_derivation_that_changes_nothing_answers_the_environment_itself():
    with model_test_env(Thing) as env:
        base = env(context={"active_test": False})
        assert base.su is True
        assert base._derive(su=True, active_test=False) is base
        assert base._derive() is base
        assert base._derive(prefetch_fields=False) is not base
        assert base._derive(prefetch_fields=False).context["prefetch_fields"] is False
