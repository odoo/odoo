# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api
from openerp.tools.translate import _

class stock_immediate_transfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    @api.multi
    def process(self):
        super(stock_immediate_transfer, self).process()
        pick = self.pick_id.id
        context = dict(self.env.context, active_model='stock.picking', active_id=pick, active_ids=[pick])
        print context
        return {
            'name': _('Create Invoice'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.invoice.onshipping',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }


class stock_backorder_confirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    @api.multi
    def process(self):
        res = super(stock_backorder_confirmation, self).process()
        context = dict(self.env.context, active_model='stock.picking', active_id=self.pick_id.id, active_ids=[self.pick_id.id])
        return {
            'name': _('Create Invoice'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.invoice.onshipping',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }

    @api.multi
    def process_cancel_backorder(self):
        res = super(stock_backorder_confirmation, self).process_cancel_backorder()
        context = dict(self.env.context, active_model='stock.picking', active_id=self.pick_id.id, active_ids=[self.pick_id.id])
        return {
            'name': _('Create Invoice'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.invoice.onshipping',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }