import pytest

from odoo import fields
from odoo.orm.fields.base import BOOLEAN_ATTRIBUTES


@pytest.mark.parametrize("attribute", BOOLEAN_ATTRIBUTES)
@pytest.mark.parametrize("value", ["True", "False", 1, 0, None])
def test_a_boolean_attribute_refuses_anything_but_a_bool(attribute, value):
    with pytest.raises(TypeError, match=f"{attribute} takes a bool"):
        fields.Char(**{attribute: value})


@pytest.mark.parametrize("attribute", BOOLEAN_ATTRIBUTES)
@pytest.mark.parametrize("value", [True, False])
def test_a_boolean_attribute_takes_a_bool(attribute, value):
    assert fields.Char(**{attribute: value})._args__[attribute] is value


def test_the_string_false_is_not_mistaken_for_false():
    with pytest.raises(TypeError, match="store='False'"):
        fields.Many2one("res.partner", related="order_id.partner_id", store="False")
