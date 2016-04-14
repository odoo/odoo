# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MrpWorkcenterBlockWizard(models.TransientModel):
    _name = "mrp.workcenter.block.wizard"
    _description = "Block Workcenter"

    reason_id = fields.Many2one('mrp.workcenter.block.reason')
    description = fields.Text('Description')

    @api.multi
    def button_block(self):
        self.ensure_one()
        workcenter = self.env['mrp.workcenter'].browse(self.env.context.get('active_id'))
        workcenter.block(self.reason_id, self.description)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'menu_id': self.env.ref('base.menu_mrp_root').id},
        }
