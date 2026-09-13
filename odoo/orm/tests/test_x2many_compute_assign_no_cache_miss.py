from unittest.mock import patch

from odoo import api, fields, models
from odoo.orm.fields import _field_cache_miss
from odoo.orm.model_test_env import model_test_env

_MOD = "test_x2many_compute_assign_no_cache_miss"


class Tag(models.Model):
    _name = "cm.tag"
    _module = _MOD
    _description = "tag"

    name = fields.Char()


class Holder(models.Model):
    _name = "cm.holder"
    _module = _MOD
    _description = "assigns a computed many2many inside its own compute"

    name = fields.Char()
    tag_ids = fields.Many2many("cm.tag")
    twin_ids = fields.Many2many("cm.tag", compute="_compute_twin_ids")

    @api.depends("tag_ids")
    def _compute_twin_ids(self):
        for record in self:
            record.twin_ids = record.tag_ids


def test_assigning_the_field_in_its_compute_does_not_read_it_first():
    with model_test_env(Tag, Holder) as env:
        tags = env["cm.tag"].create([{"name": "a"}, {"name": "b"}])
        holder = env["cm.holder"].create({"name": "h", "tag_ids": tags.ids})
        with patch.object(
            _field_cache_miss,
            "get_cache_miss_by_compute",
            wraps=_field_cache_miss.get_cache_miss_by_compute,
        ) as by_compute:
            assert holder.twin_ids == tags
        # one miss for the read that triggers the compute; the assignment inside
        # the compute must not read the protected field back through a second one
        assert [call.args[0].name for call in by_compute.call_args_list] == ["twin_ids"]


def test_the_old_relation_still_feeds_the_delta_when_cached():
    with model_test_env(Tag, Holder) as env:
        tags = env["cm.tag"].create([{"name": "a"}, {"name": "b"}])
        holder = env["cm.holder"].create({"name": "h", "tag_ids": tags[0].ids})
        assert holder.twin_ids == tags[0]
        holder.tag_ids = tags
        assert holder.twin_ids == tags
        holder.tag_ids = tags[1]
        assert holder.twin_ids == tags[1]


def test_assigning_an_empty_value_in_the_compute_still_lands_in_the_cache():
    with model_test_env(Tag, Holder) as env:
        holder = env["cm.holder"].create({"name": "h"})
        assert holder.twin_ids == env["cm.tag"]
        new = env["cm.holder"].new({"name": "n"})
        assert new.twin_ids == env["cm.tag"]
        assert env.cache.contains(new, new._fields["twin_ids"])
