from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_field_default_literal"


class Thing(models.Model):
    _name = "default.literal.thing"
    _module = _MOD
    _description = "default literal thing"
    _log_access = False

    literal = fields.Integer(default=7)
    decided = fields.Integer(default=lambda model: 7)
    none = fields.Integer()


def test_only_a_declared_value_is_remembered_as_a_literal():
    with model_test_env(Thing) as env:
        model = env["default.literal.thing"]
        literal = model._fields["literal"]
        assert callable(literal.default)
        assert literal.default_literal == 7
        assert model._fields["decided"].default_literal is None
        assert model._fields["none"].default_literal is None


def test_an_override_with_a_callable_forgets_the_literal():
    class Override(models.Model):
        _inherit = "default.literal.thing"
        _module = _MOD + "_override"

        literal = fields.Integer(default=lambda model: 9)

    with model_test_env(Thing, Override) as env:
        field = env["default.literal.thing"]._fields["literal"]
        assert field.default(env["default.literal.thing"]) == 9
        assert field.default_literal is None
