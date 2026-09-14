from odoo import fields, models
from odoo.orm.domain import Domain, DomainCondition, OptimizationLevel
from odoo.orm.model_test_env import model_test_env

_MOD = "test_search_defined_predicate"


class Thing(models.Model):
    _name = "sdp.thing"
    _module = _MOD
    _description = "thing"
    _log_access = False

    name = fields.Char()
    code = fields.Char()
    computed = fields.Char(compute="_compute_computed", search="_search_computed")
    parent_id = fields.Many2one("sdp.thing")
    parent_code = fields.Char(related="parent_id.code")
    parent_computed = fields.Char(related="parent_id.computed")

    def _compute_computed(self):
        for record in self:
            record.computed = (record.name or "") + "!"

    def _search_computed(self, operator, value):
        return [("code", operator, value)]


def _condition(env, field_expr, operator, value):
    model = env["sdp.thing"]
    condition = Domain(field_expr, operator, value)
    assert isinstance(condition, DomainCondition)
    return condition._optimize(model, OptimizationLevel.DYNAMIC_VALUES), model


def test_search_defined_flag_selects_the_delegating_path():
    with model_test_env(Thing) as env:
        plain, model = _condition(env, "name", "=", "x")
        searched, _ = _condition(env, "computed", "=", "x")
        assert plain._is_search_defined(model) is False
        assert searched._is_search_defined(model) is True


def test_plain_field_is_untouched():
    with model_test_env(Thing) as env:
        model = env["sdp.thing"]
        condition, _ = _condition(env, "name", "=", "x")
        assert condition._is_search_defined(model) is False


def test_a_related_field_delegates_for_a_user_and_reads_through_as_the_superuser():
    with model_test_env(Thing) as env:
        model = env["sdp.thing"]
        member = env["res.users"].create(
            {"name": "Member", "login": "member", "company_id": 1}
        )
        user_model = model.with_user(member.id)
        plain, _ = _condition(env, "parent_code", "=", "x")
        searched, _ = _condition(env, "parent_computed", "=", "x")
        # a record rule may narrow the path's sub-select for a user, never
        # for the superuser, who reads through the path in memory -- unless
        # the path ends on a field a search method defines
        assert plain._is_search_defined(user_model) is True
        assert plain._is_search_defined(model) is False
        assert searched._is_search_defined(user_model) is True
        assert searched._is_search_defined(model) is True


def test_expression_paths_do_not_delegate():
    with model_test_env(Thing) as env:
        model = env["sdp.thing"]
        condition = DomainCondition("computed.whatever", "=", "x")
        field = model._fields["computed"]
        assert field.search
        assert condition.field_expr != field.name
