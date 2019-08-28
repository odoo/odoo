# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_in_reseller_partner_id = fields.Many2one('res.partner',
        string='Reseller', domain="[('vat', '!=', False), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", states={'posted': [('readonly', True)]})
    l10n_in_journal_id = fields.Many2one('account.journal', string="Journal", states={'posted': [('readonly', True)]})

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.l10n_in_journal_id:
            invoice_vals['journal_id'] = self.l10n_in_journal_id.id
        return invoice_vals

    @api.onchange('company_id')
    def l10n_in_onchange_company_id(self):
        company_id = self._context.get('default_company_id')
        company = False
        if company_id:
            company = self.env['res.company'].browse(company_id)
        else:
            company = self.env.company

        domain = [('company_id', '=', company.id), ('type', '=', 'sale')]

        journal = self.env['account.journal'].search(domain, limit=1)
        if journal:
            self.l10n_in_journal_id = journal.id
