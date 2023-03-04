# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pl_invoice_sale_date = fields.Date(
        string='Sale Date',
        compute='_compute_l10n_pl_invoice_sale_date',
        store=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False,
    )

    @api.depends('invoice_date')
    def _compute_l10n_pl_invoice_sale_date(self):
        for move in self:
            if not move.l10n_pl_invoice_sale_date:
                move.l10n_pl_invoice_sale_date = move.invoice_date
