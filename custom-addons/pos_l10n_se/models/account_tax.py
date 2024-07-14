# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class AccountTax(models.Model):
    _inherit = "account.tax"

    sweden_identification_letter = fields.Char(compute="_compute_sweden_identification_letter")

    @api.depends("amount_type", "amount")
    def _compute_sweden_identification_letter(self):
        for tax in self:
            if tax.type_tax_use == "sale" and (
                tax.amount_type == "percent" or tax.amount_type == "group"
            ):
                if tax.amount == 25:
                    tax.sweden_identification_letter = "A"
                elif tax.amount == 12:
                    tax.sweden_identification_letter = "B"
                elif tax.amount == 6:
                    tax.sweden_identification_letter = "C"
                elif tax.amount == 0:
                    tax.sweden_identification_letter = "D"
                else:
                    tax.sweden_identification_letter = False
            else:
                tax.sweden_identification_letter = False
