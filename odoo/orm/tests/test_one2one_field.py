import pytest

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_one2one_field"


class Seat(models.Model):
    _name = "o.seat"
    _module = _MOD
    _description = "seat"
    _log_access = False

    name = fields.Char()
    holder_id = fields.Many2one("o.holder", index="unique")


class Holder(models.Model):
    _name = "o.holder"
    _module = _MOD
    _description = "holder"
    _log_access = False

    name = fields.Char()
    seat_id = fields.One2one("o.seat", "holder_id")


def test_one2one_is_a_one2many_paired_with_its_inverse():
    with model_test_env(Seat, Holder) as env:
        field = env["o.holder"]._fields["seat_id"]
        assert field.type == "one2many"
        assert field.is_one2one
        assert field.inverse_name == "holder_id"
        inverse = env["o.seat"]._fields["holder_id"]
        assert inverse in env.registry.field_inverses[field]


def test_one2one_refuses_an_inverse_without_a_unique_index():
    class LooseSeat(models.Model):
        _name = "o.loose.seat"
        _module = _MOD + "_loose"
        _description = "loose seat"
        _log_access = False

        holder_id = fields.Many2one("o.loose.holder")

    class LooseHolder(models.Model):
        _name = "o.loose.holder"
        _module = _MOD + "_loose"
        _description = "loose holder"
        _log_access = False

        seat_id = fields.One2one("o.loose.seat", "holder_id")

    with pytest.raises(TypeError, match='index="unique"'):
        with model_test_env(LooseSeat, LooseHolder):
            pass


def test_one2one_refuses_an_inverse_that_is_not_a_many2one():
    class TagSeat(models.Model):
        _name = "o.tag.seat"
        _module = _MOD + "_tag"
        _description = "tag seat"
        _log_access = False

        holder_ids = fields.Many2many("o.tag.holder")

    class TagHolder(models.Model):
        _name = "o.tag.holder"
        _module = _MOD + "_tag"
        _description = "tag holder"
        _log_access = False

        seat_id = fields.One2one("o.tag.seat", "holder_ids")

    with pytest.raises(TypeError, match="inverts a many2one"):
        with model_test_env(TagSeat, TagHolder):
            pass


def test_a_many2one_related_may_end_on_a_one2one():
    class Badge(models.Model):
        _name = "o.badge"
        _module = _MOD + "_badge"
        _description = "badge"
        _log_access = False

        holder_id = fields.Many2one("o.holder")
        seat_id = fields.Many2one(related="holder_id.seat_id")

    with model_test_env(Seat, Holder, Badge) as env:
        field = env["o.badge"]._fields["seat_id"]
        assert field.type == "many2one"
        assert field.comodel_name == "o.seat"
        assert field.related_field is env["o.holder"]._fields["seat_id"]
