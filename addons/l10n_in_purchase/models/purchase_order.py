# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    l10n_in_journal_id = fields.Many2one('account.journal', string="Journal", \
        states={'posted': [('readonly', True)]}, domain="[('type','=', 'purchase')]")

    @api.onchange('company_id')
    def l10n_in_onchange_company_id(self):
        domain = [('company_id', '=', self.company_id.id), ('type', '=', 'purchase')]

        journal = self.env['account.journal'].search(domain, limit=1)
        if journal:
            self.l10n_in_journal_id = journal.id
