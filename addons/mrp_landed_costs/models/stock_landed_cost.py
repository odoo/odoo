# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    target_model = fields.Selection(selection_add=[
        ('manufacturing', "Manufacturing Orders")
    ], ondelete={'manufacturing': 'set default'})
    mrp_production_ids = fields.Many2many(
        'mrp.production', string='Manufacturing order',
        copy=False, states={'done': [('readonly', True)]}, groups='stock.group_stock_manager')

    @api.onchange('target_model')
    def _onchange_target_model(self):
        super()._onchange_target_model()
        if self.target_model != 'manufacturing':
            self.mrp_production_ids = False

    def _get_targeted_move_ids(self):
        return super()._get_targeted_move_ids() | self.mrp_production_ids.move_finished_ids


class AdjustmentLines(models.Model):
    _inherit = 'stock.valuation.adjustment.lines'

    def _create_account_move_line(self, move, credit_account_id, debit_account_id, qty_out, already_out_account_id):
        """
            The accounting journal entries for recording costs related to inventory issued for sale and issued for production are different.
        """
        if qty_out > 0 and self.move_id.production_id and self.move_id.location_id.usage == 'production':
            already_out_account_id = self.move_id.location_id.valuation_out_account_id.id or already_out_account_id
        return super(AdjustmentLines, self)._create_account_move_line(move, credit_account_id, debit_account_id, qty_out, already_out_account_id)
