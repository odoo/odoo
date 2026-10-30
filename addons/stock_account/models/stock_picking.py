# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    country_code = fields.Char(related="company_id.account_fiscal_country_id.code")

    def _prepare_return_move_default_values(self, move_id):
        vals = super()._prepare_return_move_default_values(move_id)
        vals['to_refund'] = move_id.to_refund
        return vals
