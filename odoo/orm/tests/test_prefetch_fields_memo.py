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
        fields_, guarded = registry.prefetch_fields("memo.item")
        assert [f.name for f in fields_] == ["name", "secret"]
        assert guarded is True
        assert registry.prefetch_fields("memo.item")[0] is fields_


def test_a_superuser_fetch_takes_the_memo_as_is():
    with model_test_env(Item) as env:
        item = env["memo.item"].sudo()
        assert [f.name for f in item._get_fields_to_fetch()] == ["name", "secret"]
        assert item._get_fields_to_fetch() == list(
            env.registry.prefetch_fields("memo.item")[0]
        )
