# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
from odoo.addons import account


class AccountMoveLine(account.AccountMoveLine):

    l10n_ae_vat_amount = fields.Monetary(compute='_compute_vat_amount', string='VAT Amount')

    @api.depends('price_subtotal', 'price_total')
    def _compute_vat_amount(self):
        for record in self:
            record.l10n_ae_vat_amount = record.price_total - record.price_subtotal
