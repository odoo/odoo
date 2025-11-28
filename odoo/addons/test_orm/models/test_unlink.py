# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Test_OrmUnlink(models.Model):
    _name = 'test_orm.unlink'
    _description = 'Test Unlink'

    cascade_line_ids = fields.One2many('test_orm.unlink.cascade.line', 'container_id')
    null_line_ids = fields.One2many('test_orm.unlink.null.line', 'container_id')

    user_command = fields.Char(inverse='_inverse_user_command', store=False)

    def _inverse_user_command(self):
        for rec in self:
            if rec.user_command == 'remove lines':
                rec.cascade_line_ids = False


class Test_OrmUnlinkCascadeLine(models.Model):
    _name = 'test_orm.unlink.cascade.line'
    _description = 'Test Unlink cascade'
    _parent_store = True

    container_id = fields.Many2one('test_orm.unlink', ondelete="cascade")

    parent_id = fields.Many2one('test_orm.unlink.cascade.line', ondelete="set null")
    parent_path = fields.Char(index='btree')
    has_parent = fields.Boolean(compute='_compute_has_parent', store=True)

    @api.depends('parent_id')
    def _compute_has_parent(self):
        for rec in self:
            rec.has_parent = bool(rec.parent_id)


class Test_OrmUnlinkNullLine(models.Model):
    _name = 'test_orm.unlink.null.line'
    _description = 'Test Unlink null'

    container_id = fields.Many2one('test_orm.unlink', ondelete="set null")

    has_container = fields.Boolean(compute='_compute_has_container', store=True)

    @api.depends('container_id')
    def _compute_has_container(self):
        for rec in self:
            rec.has_container = bool(rec.container_id)
