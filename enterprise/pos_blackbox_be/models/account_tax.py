# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class AccountTax(models.Model):
    _inherit = "account.tax"

    identification_letter = fields.Selection(
        [("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
        compute="_compute_identification_letter",
    )

    @api.depends("amount_type", "amount")
    def _compute_identification_letter(self):
        for rec in self:
            if rec.type_tax_use == "sale" and (
                rec.amount_type == "percent" or rec.amount_type == "group"
            ):
                if rec.amount == 21:
                    rec.identification_letter = "A"
                elif rec.amount == 12:
                    rec.identification_letter = "B"
                elif rec.amount == 6:
                    rec.identification_letter = "C"
                elif rec.amount == 0:
                    rec.identification_letter = "D"
                else:
                    rec.identification_letter = False
            else:
                rec.identification_letter = False
