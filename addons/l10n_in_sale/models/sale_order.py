# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_in_reseller_partner_id = fields.Many2one('res.partner',
        string='Reseller', domain="[('vat', '!=', False), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", readonly=False)
    l10n_in_gst_treatment = fields.Selection([
            ('regular', 'Registered Business - Regular'),
            ('composition', 'Registered Business - Composition'),
            ('unregistered', 'Unregistered Business'),
            ('consumer', 'Consumer'),
            ('overseas', 'Overseas'),
            ('special_economic_zone', 'Special Economic Zone'),
            ('deemed_export', 'Deemed Export'),
            ('uin_holders', 'UIN Holders'),
        ], string="GST Treatment", readonly=False, compute="_compute_l10n_in_gst_treatment", store=True)

    @api.depends('partner_id')
    def _compute_l10n_in_gst_treatment(self):
        for order in self:
            # set default value as False so CacheMiss error never occurs for this field.
            order.l10n_in_gst_treatment = False
            if order.country_code == 'IN':
                l10n_in_gst_treatment = order.partner_id.l10n_in_gst_treatment
                if not l10n_in_gst_treatment and order.partner_id.country_id and order.partner_id.country_id.code != 'IN':
                    l10n_in_gst_treatment = 'overseas'
                if not l10n_in_gst_treatment:
                    l10n_in_gst_treatment = order.partner_id.vat and 'regular' or 'consumer'
                order.l10n_in_gst_treatment = l10n_in_gst_treatment

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.country_code == 'IN':
            invoice_vals['l10n_in_reseller_partner_id'] = self.l10n_in_reseller_partner_id.id
            invoice_vals['l10n_in_gst_treatment'] = self.l10n_in_gst_treatment
        return invoice_vals
