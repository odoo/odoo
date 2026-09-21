import pytest

from odoo.orm.fields._field_description import description_key


def test_a_selection_is_a_sorted_set_of_names():
    assert description_key(None) is None
    assert description_key(["string", "help", "string"]) == ("help", "string")


def test_a_bare_attribute_name_is_refused_as_a_selection():
    with pytest.raises(TypeError, match="collection of names"):
        description_key("string")


def test_a_non_column_field_sorts_and_groups_per_user():
    from odoo import fields, models
    from odoo.orm.model_test_env import model_test_env

    class Thing(models.Model):
        _name = "description.thing"
        _module = "test_field_description_dbfree"
        _description = "description thing"
        _log_access = False

        name = fields.Char()
        upper = fields.Char(compute="_compute_upper")

        def _compute_upper(self):
            for record in self:
                record.upper = (record.name or "").upper()

    with model_test_env(Thing) as env:
        model = env["description.thing"]
        column = model._fields["name"]
        assert column.is_column
        assert column._dynamic_description_attrs(env) == frozenset()
        computed = model._fields["upper"]
        assert not computed.is_column
        assert {"sortable", "groupable"} <= computed._dynamic_description_attrs(env)
