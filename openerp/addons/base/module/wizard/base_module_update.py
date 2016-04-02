# -*- coding: utf-8 -*-

from openerp import models, fields, api

class base_module_update(models.TransientModel):
    _name = "base.module.update"
    _description = "Update Module"

    updated = fields.Integer('Number of modules updated', readonly=True)
    added = fields.Integer('Number of modules added', readonly=True)
    state = fields.Selection([('init', 'init'), ('done', 'done')], 'Status', readonly=True, default='init')

    @api.one
    def update_module(self):
        self.updated, self.added = self.env['ir.module.module'].update_list()
        self.state = 'done'
        return False

    @api.multi
    def action_module_open(self):
        res = {
            'domain': str([]),
            'name': 'Modules',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'ir.module.module',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
        return res
