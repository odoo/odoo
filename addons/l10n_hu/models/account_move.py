# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('country_code', 'move_type')
    def _compute_show_delivery_date(self):
        # EXTENDS 'account'
        super()._compute_show_delivery_date()
        for move in self:
            if move.country_code == 'HU':
                move.show_delivery_date = move.is_sale_document()

    def _post(self, soft=True):
        res = super()._post(soft)
        for move in self:
            if move.country_code == 'HU' and move.is_sale_document() and not move.delivery_date:
                move.delivery_date = move.invoice_date
        return res
