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
    l10n_in_sale_state_id = fields.Many2one('res.country.state', string="Place of supply",
        compute="_compute_l10n_in_sale_state_id", store=True, copy=True, precompute=True)
    l10n_in_sale_is_gst_registered_enabled = fields.Boolean(related='company_id.l10n_in_is_gst_registered')

    @api.depends('partner_id', 'partner_shipping_id', 'company_id')
    def _compute_l10n_in_sale_state_id(self):
        for order in self:
            if order.country_code == 'IN':
                partner_state = (
                    order.partner_id.commercial_partner_id == order.partner_shipping_id.commercial_partner_id
                    and order.partner_shipping_id.state_id
                    or order.partner_id.state_id
                )
                if not partner_state:
                    partner_state = order.partner_id.commercial_partner_id.state_id or order.company_id.state_id
                if partner_state.country_id.code == 'IN':
                    order.l10n_in_sale_state_id = partner_state
                else:
                    order.l10n_in_sale_state_id = self.env.ref('l10n_in.state_in_oc', raise_if_not_found=False)
            else:
                order.l10n_in_sale_state_id = False

    @api.depends('l10n_in_sale_state_id')
    def _compute_fiscal_position_id(self):

        def _get_fiscal_state(order):
            """
            Maps each order to its corresponding fiscal state based on its type,
            fiscal conditions, and the state of the associated partner or company.
            """

            if (
                order.country_code != 'IN'
                # Partner's FP takes precedence through super
                or order.partner_shipping_id.property_account_position_id
                or order.partner_id.property_account_position_id
            ):
                return False
            elif order.l10n_in_gst_treatment == 'special_economic_zone':
                # Special Economic Zone
                return self.env.ref('l10n_in.state_in_oc')
            return order.l10n_in_sale_state_id

        for state_id, orders in self.grouped(_get_fiscal_state).items():
            if state_id:
                virtual_partner = self.env['res.partner'].new({
                    'state_id': state_id.id,
                    'country_id': state_id.country_id.id,
                })
                orders.fiscal_position_id = self.env['account.fiscal.position']._get_fiscal_position(virtual_partner)
            else:
                super(SaleOrder, orders)._compute_fiscal_position_id()

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
