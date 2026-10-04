# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Test_OrmUnlink(models.Model):
    _name = 'test_orm.unlink'
    _description = 'Test Unlink'

    cascade_ids = fields.One2many('test_orm.unlink.cascade', 'container_id')
    null_ids = fields.One2many('test_orm.unlink.null', 'container_id')

    user_command = fields.Char(inverse='_inverse_user_command', store=False)

    def _inverse_user_command(self):
        for rec in self:
            if rec.user_command == 'remove lines':
                rec.cascade_ids = False


class Test_OrmUnlinkCascade(models.Model):
    _name = 'test_orm.unlink.cascade'
    _description = 'Test Unlink cascade'
    _parent_store = True

    container_id = fields.Many2one('test_orm.unlink', ondelete="cascade")

    parent_id = fields.Many2one('test_orm.unlink.cascade', ondelete="set null")
    parent_path = fields.Char(index='btree')
    has_parent = fields.Boolean(compute='_compute_has_parent', store=True)

    null_id = fields.Many2one('test_orm.unlink.null')

    @api.depends('parent_id')
    def _compute_has_parent(self):
        for rec in self:
            rec.has_parent = bool(rec.parent_id)

    def _delete_extra(self):
        # Add null_id record to be deleted
        yield from super()._delete_extra()
        yield self.null_id


class Test_OrmUnlinkNull(models.Model):
    _name = 'test_orm.unlink.null'
    _description = 'Test Unlink null'

    container_id = fields.Many2one('test_orm.unlink', ondelete="set null")
    has_container = fields.Boolean(compute='_compute_has_container', store=True)

    cascade_ids = fields.Many2many('test_orm.unlink.cascade')
    cascade_count = fields.Integer(compute='_compute_cascade_count', store=True)

    @api.depends('container_id')
    def _compute_has_container(self):
        for rec in self:
            rec.has_container = bool(rec.container_id)

    @api.depends('cascade_ids')
    def _compute_cascade_count(self):
        for rec in self:
            rec.cascade_count = len(rec.cascade_ids)
