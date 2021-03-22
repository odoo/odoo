# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    batch_id = fields.Many2one(
        'stock.picking.batch', string='Batch Transfer',
        check_company=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help='Batch associated to this transfer', copy=False)

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if vals.get('batch_id'):
            res.batch_id._sanity_check()
        return res

    def write(self, vals):
        batches = self.batch_id
        res = super().write(vals)
        if vals.get('batch_id'):
            batches.filtered(lambda b: not b.picking_ids).state = 'cancel'
            if not self.batch_id.picking_type_id:
                self.batch_id.picking_type_id = self.picking_type_id[0]
            self.batch_id._sanity_check()
        return res

    def _should_show_transfers(self):
        if len(self.batch_id) == 1 and self == self.batch_id.picking_ids:
            return False
        return super()._should_show_transfers()
