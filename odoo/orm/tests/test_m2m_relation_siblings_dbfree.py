from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_m2m_relation_siblings"


class Tag(models.Model):
    _name = "mrs.tag"
    _module = _MOD
    _description = "tag"
    _log_access = False

    name = fields.Char()


class Line(models.Model):
    _name = "mrs.line"
    _module = _MOD
    _description = "line"
    _log_access = False

    tag_ids = fields.Many2many(
        "mrs.tag", relation="mrs_line_tag_rel", column1="line_id", column2="tag_id"
    )
    other_tag_ids = fields.Many2many(
        "mrs.tag", relation="mrs_line_tag_rel", column1="line_id", column2="tag_id"
    )


def test_a_link_written_through_one_field_is_read_through_its_relation_sibling():
    with model_test_env(Tag, Line) as env:
        tag = env["mrs.tag"].create({"name": "a"})
        line = env["mrs.line"].create({"tag_ids": [(6, 0, tag.ids)]})
        assert line.other_tag_ids == tag
        other = env["mrs.tag"].create({"name": "b"})
        line.other_tag_ids = [(4, other.id)]
        assert line.tag_ids == tag | other
