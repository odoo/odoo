import pytest

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_cache_dirty_guard"


class Widget(models.Model):
    _name = "x.widget"
    _module = _MOD
    _description = "widget"

    name = fields.Char()
    qty = fields.Integer()
    label = fields.Char(compute="_compute_label", store=False)

    def _compute_label(self):
        for record in self:
            record.label = f"{record.name}!"


@pytest.fixture
def env():
    # the tests plant cache values: no cache-against-rows check at the end
    with model_test_env(Widget, check_cache=False) as e:
        yield e


def _dirty_record(env):
    record = env["x.widget"].create({"name": "before", "qty": 1})
    env.flush_all()
    record.name = "pending"
    assert env.core.has_dirty_field(env["x.widget"]._fields["name"])
    return record


class TestUpdateCache:
    def test_overwriting_a_dirty_value_raises(self, env):
        record = _dirty_record(env)
        field = env["x.widget"]._fields["name"]

        with pytest.raises(ValueError, match="refusing to overwrite the dirty value"):
            field._update_cache(record, "clobbered")

        assert record.name == "pending", "the pending write must survive the refusal"

    def test_the_message_names_the_field_and_the_records(self, env):
        record = _dirty_record(env)
        field = env["x.widget"]._fields["name"]

        with pytest.raises(ValueError) as exc:
            field._update_cache(record, "clobbered")

        message = str(exc.value)
        assert "_update_cache" in message, "the message must name the caller"
        assert "x.widget.name" in message, "the message must name the field"
        assert str(record.id) in message, "the message must name the records"

    def test_dirty_true_is_the_sanctioned_overwrite(self, env):
        record = _dirty_record(env)
        field = env["x.widget"]._fields["name"]

        field._update_cache(record, "deliberate", dirty=True)

        assert record.name == "deliberate"

    def test_a_clean_record_is_not_guarded(self, env):
        record = env["x.widget"].create({"name": "clean"})
        env.flush_all()
        field = env["x.widget"]._fields["name"]

        field._update_cache(record, "fetched")

        assert record.name == "fetched"

    def test_a_disjoint_record_is_not_guarded(self, env):
        dirty = _dirty_record(env)
        other = env["x.widget"].create({"name": "other"})
        env.flush_all()
        field = env["x.widget"]._fields["name"]

        field._update_cache(other, "fetched")

        assert other.name == "fetched"
        assert dirty.name == "pending"

    def test_non_column_fields_are_not_guarded(self, env):
        record = env["x.widget"].create({"name": "x"})
        env.flush_all()
        field = env["x.widget"]._fields["label"]
        assert not field.is_column

        field._update_cache(record, "anything")

        assert record.label == "anything"


class TestUpdateCacheItems:
    def test_overwriting_a_dirty_value_raises(self, env):
        record = _dirty_record(env)
        field = env["x.widget"]._fields["name"]

        with pytest.raises(ValueError, match="refusing to overwrite the dirty value"):
            field._update_cache_items(env, [(record.id, "clobbered")])

        assert record.name == "pending"

    def test_the_message_names_this_caller(self, env):
        record = _dirty_record(env)
        field = env["x.widget"]._fields["name"]

        with pytest.raises(ValueError) as exc:
            field._update_cache_items(env, [(record.id, "clobbered")])

        assert "_update_cache_items" in str(exc.value), (
            "the two callers must remain distinguishable in the message -- that "
            "is the only thing the shared helper's `caller` argument is for"
        )

    def test_it_has_no_dirty_escape_hatch(self, env):

        def params(func):
            return func.__code__.co_varnames[: func.__code__.co_argcount]

        assert "dirty" not in params(fields.Field._update_cache_items)
        assert "dirty" in params(fields.Field._update_cache)

    def test_empty_items_short_circuit(self, env):
        _dirty_record(env)
        field = env["x.widget"]._fields["name"]

        field._update_cache_items(env, [])


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
