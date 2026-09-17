import pytest

from odoo.orm.fields._field_description import description_key


def test_a_selection_is_a_sorted_set_of_names():
    assert description_key(None) is None
    assert description_key(["string", "help", "string"]) == ("help", "string")


def test_a_bare_attribute_name_is_refused_as_a_selection():
    with pytest.raises(TypeError, match="collection of names"):
        description_key("string")
