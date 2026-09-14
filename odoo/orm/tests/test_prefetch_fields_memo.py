from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_prefetch_fields_memo"


class Item(models.Model):
    _name = "memo.item"
    _module = _MOD
    _description = "prefetch and non-prefetch columns"
    _log_access = False

    name = fields.Char()
    note = fields.Text(prefetch=False)
    total = fields.Float(compute="_compute_total")
    secret = fields.Char(groups="base.group_system")

    def _compute_total(self):
        for item in self:
            item.total = 0.0


def test_the_registry_memoises_the_prefetch_fields_of_a_model():
    with model_test_env(Item) as env:
        registry = env.registry
        fields_ = registry.prefetch_fields("memo.item")
        assert [f.name for f in fields_] == ["name", "secret"]
        assert registry.prefetch_fields("memo.item") is fields_
        assert env["memo.item"]._fields["note"] in registry.prefetch_fields(
            "memo.item", False
        )


def test_a_superuser_fetch_takes_the_memo_as_is():
    with model_test_env(Item) as env:
        item = env["memo.item"].sudo()
        assert [f.name for f in item._get_fields_to_fetch()] == ["name", "secret"]
        assert item._get_fields_to_fetch() == list(
            env.registry.prefetch_fields("memo.item")
        )


class Guarded(models.Model):
    _name = "memo.guarded"
    _module = _MOD
    _description = "a model whose access override guards an ungrouped field"
    _log_access = False

    name = fields.Char()
    private = fields.Char()

    def _has_field_access(self, field, operation):
        if field.name == "private" and not self.env.su:
            return False
        return super()._has_field_access(field, operation)


def test_a_model_overriding_has_field_access_keeps_its_own_verdict():
    with model_test_env(Item, Guarded) as env:
        model = env["memo.guarded"].with_user(7)
        assert not model.env.su
        assert [f.name for f in model._readable_prefetch_fields(True)] == ["name"]
        assert [f.name for f in model._get_fields_to_fetch()] == ["name"]
        assert [f.name for f in model.sudo()._readable_prefetch_fields(True)] == [
            "name",
            "private",
        ]


def test_discarding_a_field_forgets_the_memo():
    with model_test_env(Item) as env:
        registry = env.registry
        before = registry.prefetch_fields("memo.item")
        registry.discard_fields([env["memo.item"]._fields["secret"]])
        assert registry.prefetch_fields("memo.item") is not before


def test_exists_keeps_the_prefetch_ids_of_the_batch():
    with model_test_env(Item) as env:
        items = env["memo.item"].create([{"name": str(i)} for i in range(5)])
        one = items[2]
        assert set(one._prefetch_ids) == set(items.ids)
        assert set(one.exists()._prefetch_ids) == set(items.ids)
        items[0].unlink()
        assert set(items.exists()._prefetch_ids) == set(items.ids)
        assert items.exists().ids == items.ids[1:]


def test_a_subset_of_a_batch_keeps_the_batch_as_its_prefetch():
    with model_test_env(Item) as env:
        items = env["memo.item"].create(
            [{"name": str(i), "note": "n" if i % 2 else ""} for i in range(6)]
        )
        batch = set(items.ids)
        assert set(items.filtered("note")._prefetch_ids) == batch
        assert set(items.filtered(lambda item: item.name > "2")._prefetch_ids) == batch
        assert (
            set(items.filtered_domain([("name", "in", ["1"])])._prefetch_ids) == batch
        )
        assert set((items - items[:2])._prefetch_ids) == batch
        assert set((items & items[1:3])._prefetch_ids) == batch
        # a union and a slice are new batches of their own
        assert set((items[:2] | items[4:])._prefetch_ids) == {
            *items[:2].ids,
            *items[4:].ids,
        }
        assert set(items[1:3]._prefetch_ids) == set(items[1:3].ids)
