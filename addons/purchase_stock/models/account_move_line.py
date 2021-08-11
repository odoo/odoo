# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMoveLine(models.Model):
    """ Override AccountInvoice_line to add the link to the purchase order line it is related to"""
    _inherit = 'account.move.line'

    def _is_eligible_cogs_purchase(self):
        if self.product_id.type != 'product' or self.product_id.valuation != 'real_time' or not self.purchase_line_id:
            return False
        return True
