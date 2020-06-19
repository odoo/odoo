# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_in_reseller_partner_id = fields.Many2one('res.partner',
        string='Reseller', domain="[('vat', '!=', False), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", readonly=True, states={'draft': [('readonly', False)]})
    l10n_in_journal_id = fields.Many2one('account.journal', string="Journal", readonly=True, states={'draft': [('readonly', False)]})
    l10n_in_gst_treatment = fields.Selection([
            ('regular', 'Registered Business - Regular'),
            ('composition', 'Registered Business - Composition'),
            ('unregistered', 'Unregistered Business'),
            ('consumer', 'Consumer'),
            ('overseas', 'Overseas'),
            ('special_economic_zone', 'Special Economic Zone'),
            ('deemed_export', 'Deemed Export'),
        ], string="GST Treatment", readonly=True, states={'draft': [('readonly', False)]})
    l10n_in_company_country_code = fields.Char(related='company_id.country_id.code', string="Country code")

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.l10n_in_company_country_code == 'IN':
            invoice_vals['l10n_in_reseller_partner_id'] = self.l10n_in_reseller_partner_id.id
            if self.l10n_in_journal_id:
                invoice_vals['journal_id'] = self.l10n_in_journal_id.id
            invoice_vals['l10n_in_gst_treatment'] = self.l10n_in_gst_treatment
        return invoice_vals

    @api.onchange('company_id')
    def l10n_in_onchange_company_id(self):
        if self.l10n_in_company_country_code == 'IN':
            domain = [('company_id', '=', self.company_id.id), ('type', '=', 'sale')]
            journal = self.env['account.journal'].search(domain, limit=1)
            if journal:
                self.l10n_in_journal_id = journal.id

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.l10n_in_company_country_code == 'IN':
            self.l10n_in_gst_treatment = self.partner_id.l10n_in_gst_treatment
        return super().onchange_partner_id()
