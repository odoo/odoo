# -*- coding: utf-8 -*-

from odoo import api, fields, models


class BaseModuleUpdate(models.TransientModel):
    _name = 'base.module.update'
    _description = "Update Module"

    updated = fields.Integer('Number of modules updated', readonly=True)
    added = fields.Integer('Number of modules added', readonly=True)
    state = fields.Selection([('init', 'init'), ('done', 'done')], 'Status', readonly=True, default='init')

    def update_module(self):
        for this in self:
            updated, added = self.env['ir.module.module'].update_list()
            this.write({'updated': updated, 'added': added, 'state': 'done'})
        return False

    def action_module_open(self):
        res = {
            'domain': str([]),
            'name': 'Modules',
            'view_mode': 'list,form',
            'res_model': 'ir.module.module',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
        return res
