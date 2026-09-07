# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class Account(models.Model):
    _inherit = "account.move.line"

    hsn_quantity = fields.Float("HSN Quantity", compute="_compute_hsn_quantity", store=True, readonly=False)

    @api.depends('quantity')
    def _compute_hsn_quantity(self):
        for line in self:
            line.hsn_quantity = line.quantity
