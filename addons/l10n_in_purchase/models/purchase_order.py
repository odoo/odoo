# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    l10n_in_journal_id = fields.Many2one('account.journal', string="Journal", \
        states={'posted': [('readonly', True)]}, domain="[('type','=', 'purchase')]")

    @api.onchange('company_id')
    def l10n_in_onchange_company_id(self):
        company_id = self._context.get('default_company_id')
        company = False
        if company_id:
            company = self.env['res.company'].browse(company_id)
        else:
            company = self.env.company

        domain = [('company_id', '=', company.id), ('type', '=', 'purchase')]

        journal = self.env['account.journal'].search(domain, limit=1)
        if journal:
            self.l10n_in_journal_id = journal.id
