# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_in_reseller_partner_id = fields.Many2one('res.partner',
        string='Reseller', domain="[('vat', '!=', False), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", readonly=False)

    @api.depends('partner_invoice_id')
    def _compute_fiscal_position_id(self):

        def _get_partner_fiscal(order):
            order = order.with_company(order.company_id)
            return (
                order.partner_shipping_id.property_account_position_id
                or order.partner_invoice_id.property_account_position_id
                or order.partner_id.property_account_position_id
            )

        def _get_fiscal_state(order):
            """
            Maps each order to its corresponding fiscal state based on its type,
            fiscal conditions, and the state of the associated partner or company.
            """

            partner_to_consider = order.partner_invoice_id or order.partner_id
            if partner_to_consider.l10n_in_gst_treatment == 'special_economic_zone':
                # Special Economic Zone
                return sez_state

            # Computing Place of Supply for particular order
            partner = (
                partner_to_consider.commercial_partner_id == order.partner_shipping_id.commercial_partner_id
                and order.partner_shipping_id
                or partner_to_consider
            )
            if partner.country_id and partner.country_id.code != 'IN':
                return foreign_state
            partner_state = partner.state_id or partner_to_consider.commercial_partner_id.state_id or order.company_id.state_id
            country_code = partner_state.country_id.code or order.country_code
            return partner_state if country_code == 'IN' else foreign_state

        # Handle non-Indian orders using standard logic
        FiscalPosition = self.env['account.fiscal.position']
        non_in_orders = self.filtered(lambda o: o.country_code != 'IN')
        super(SaleOrder, non_in_orders)._compute_fiscal_position_id()

        in_orders = self - non_in_orders
        orders_group_by_fp = in_orders.grouped(_get_partner_fiscal)
        orders_without_fiscal = orders_group_by_fp.pop(FiscalPosition, False)
        for fiscal_position, orders in orders_group_by_fp.items():
            orders.fiscal_position_id = fiscal_position

        if not orders_without_fiscal:
            return

        foreign_state = self.env['res.country.state'].search([('country_id.code', '!=', 'IN')], limit=1)
        sez_state = self.env.ref('l10n_in.state_in_oc', raise_if_not_found=False)
        for state, orders in orders_without_fiscal.grouped(_get_fiscal_state).items():
            virtual_partner = self.env['res.partner'].new({
                'state_id': state.id,
                'country_id': state.country_id.id,
            })
            # Group orders by company to avoid multi-company conflicts
            for company, company_orders in orders.grouped('company_id').items():
                company_orders.fiscal_position_id = FiscalPosition.with_company(
                    company.id
                )._get_fiscal_position(virtual_partner)

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.country_code == 'IN':
            invoice_vals['l10n_in_reseller_partner_id'] = self.l10n_in_reseller_partner_id.id
        return invoice_vals
