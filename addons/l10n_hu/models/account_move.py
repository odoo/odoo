# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _is_delivery_date_expected(self):
        # EXTENDS 'account'
        return self.country_code == 'HU' or super()._is_delivery_date_expected()

    def _post(self, soft=True):
        res = super()._post(soft)
        for move in self:
            if move.country_code == 'HU' and move.is_sale_document() and not move.delivery_date:
                move.delivery_date = move.invoice_date
        return res
