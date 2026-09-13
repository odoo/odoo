import pytest

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_properties_read_empty_shape"


class PropParent(models.Model):
    _name = "prop.parent"
    _module = _MOD
    _description = "Prop Parent"

    name = fields.Char()
    child_properties = fields.PropertiesDefinition()


class PropChild(models.Model):
    _name = "prop.child"
    _module = _MOD
    _description = "Prop Child"

    parent_id = fields.Many2one("prop.parent")
    props = fields.Properties(
        definition="parent_id.child_properties", definition_record="parent_id"
    )


@pytest.fixture
def env():
    gen = model_test_env(PropParent, PropChild)
    yield gen.__enter__()
    gen.__exit__(None, None, None)


def test_convert_to_read_on_an_empty_record_returns_the_list_shape(env):
    empty = env["prop.child"]
    field = empty._fields["props"]
    assert field.convert_to_read({"raw": 1}, empty) == []
    assert field.convert_to_read_multi([{"a": 1}, {"b": 2}], empty) == [[], []]


def test_stale_properties_are_dropped_when_the_container_is_gone(env):
    parent = env["prop.parent"].create(
        {"name": "p", "child_properties": [{"name": "size", "type": "char"}]}
    )
    child = env["prop.child"].create(
        {
            "parent_id": parent.id,
            "props": [{"name": "size", "type": "char", "value": "L"}],
        }
    )
    assert child.props._values == {"size": "L"}
    # an import row that carries values for a record whose container is gone
    child.write({"parent_id": False})
    child.write({"props": {"size": "L", "old": "x"}})
    assert child.props._values == {"size": "L", "old": "x"}
    child._remove_stale_properties()
    assert child.props._values == {}
