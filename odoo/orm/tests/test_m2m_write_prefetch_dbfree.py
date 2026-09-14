from unittest import mock

from odoo import api, fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_m2m_write_prefetch"


class Tag(models.Model):
    _name = "mwp.tag"
    _module = _MOD
    _description = "tag"
    _log_access = False

    name = fields.Char()


class Line(models.Model):
    _name = "mwp.line"
    _module = _MOD
    _description = "line"
    _log_access = False

    code = fields.Char()
    tag_ids = fields.Many2many("mwp.tag", compute="_compute_tag_ids", store=True)

    @api.depends("code")
    def _compute_tag_ids(self):
        tags = self.env["mwp.tag"].search([])
        for line in self:
            code = line.code
            line.tag_ids = tags.filtered(lambda tag, code=code: tag.name == code)


def test_a_compute_assigning_a_many2many_per_record_reads_the_batch_once():
    with model_test_env(Tag, Line) as env:
        env["mwp.tag"].create([{"name": "a"}, {"name": "b"}])
        lines = env["mwp.line"].create([{"code": "a"} for _ in range(30)])
        env.flush_all()
        env.invalidate_all()
        backend = env.backend
        with mock.patch.object(
            type(backend), "read_m2m_groups", wraps=backend.read_m2m_groups
        ) as read:
            lines.write({"code": "b"})
            env.flush_all()
        assert read.call_count == 1
        assert all(line.tag_ids.mapped("name") == ["b"] for line in lines)
