# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.purchase.models.purchase import PurchaseOrder as Purchase


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    l10n_in_journal_id = fields.Many2one('account.journal', string="Journal", \
        states=Purchase.READONLY_STATES, domain="[('type', '=', 'purchase')]")
    l10n_in_gst_treatment = fields.Selection([
            ('regular', 'Registered Business - Regular'),
            ('composition', 'Registered Business - Composition'),
            ('unregistered', 'Unregistered Business'),
            ('consumer', 'Consumer'),
            ('overseas', 'Overseas'),
            ('special_economic_zone', 'Special Economic Zone'),
            ('deemed_export', 'Deemed Export')
        ], string="GST Treatment", states=Purchase.READONLY_STATES, compute="_compute_l10n_in_gst_treatment", store=True)
    l10n_in_company_country_code = fields.Char(related='company_id.country_id.code', string="Country code")

    @api.onchange('company_id')
    def l10n_in_onchange_company_id(self):
        if self.l10n_in_company_country_code == 'IN':
            domain = [('company_id', '=', self.company_id.id), ('type', '=', 'purchase')]
            journal = self.env['account.journal'].search(domain, limit=1)
            if journal:
                self.l10n_in_journal_id = journal.id

    @api.depends('partner_id')
    def _compute_l10n_in_gst_treatment(self):
        for order in self:
            # set default value as False so CacheMiss error never occurs for this field.
            order.l10n_in_gst_treatment = False
            if order.l10n_in_company_country_code == 'IN':
                l10n_in_gst_treatment = order.partner_id.l10n_in_gst_treatment
                if not l10n_in_gst_treatment and order.partner_id.country_id and order.partner_id.country_id.code != 'IN':
                    l10n_in_gst_treatment = 'overseas'
                if not l10n_in_gst_treatment:
                    l10n_in_gst_treatment = order.partner_id.vat and 'regular' or 'consumer'
                order.l10n_in_gst_treatment = l10n_in_gst_treatment
