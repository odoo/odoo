# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_in_reseller_partner_id = fields.Many2one('res.partner',
        string='Reseller', domain="[('vat', '!=', False), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", readonly=False)

    @api.depends('partner_id', 'partner_shipping_id')
    def _compute_fiscal_position_id(self):

        def _get_fiscal_state(order, foreign_state):
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
            elif order.partner_shipping_id.l10n_in_gst_treatment == 'special_economic_zone':
                # Special Economic Zone
                return foreign_state

            # Computing Place of Supply for particular order
            partner = (
                order.partner_id.commercial_partner_id == order.partner_shipping_id.commercial_partner_id
                and order.partner_shipping_id
                or order.partner_id
            )
            if partner.country_id and partner.country_id.code != 'IN':
                return foreign_state
            partner_state = partner.state_id or order.partner_id.commercial_partner_id.state_id or order.company_id.state_id
            country_code = partner_state.country_id.code or order.country_code
            return partner_state if country_code == 'IN' else foreign_state

        FiscalPosition = self.env['account.fiscal.position']
        foreign_state = self.env['res.country.state'].search([('code', '!=', 'IN')], limit=1)
        for state_id, orders in self.grouped(lambda order: _get_fiscal_state(order, foreign_state)).items():
            if state_id:
                virtual_partner = self.env['res.partner'].new({
                    'state_id': state_id.id,
                    'country_id': state_id.country_id.id,
                })
                # Group orders by company to avoid multi-company conflicts
                for company_id, company_orders in orders.grouped('company_id').items():
                    company_orders.fiscal_position_id = FiscalPosition.with_company(
                        company_id.id
                    )._get_fiscal_position(virtual_partner)
            else:
                super(SaleOrder, orders)._compute_fiscal_position_id()

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.country_code == 'IN':
            invoice_vals['l10n_in_reseller_partner_id'] = self.l10n_in_reseller_partner_id.id
        return invoice_vals

    def _create_account_invoices(self, invoice_vals_list, final):
        if self.env.company.country_code != 'IN':
            return super()._create_account_invoices(invoice_vals_list, final)

        Journal = self.env['account.journal'].with_company(self.company_id)
        journal_types = ['tax_invoice', 'bill_of_supply', 'invoice_cum_bill_of_supply']
        journal_map = {
            jt: Journal.search([('l10n_in_sale_journal_type', '=', jt)], limit=1).id
            for jt in journal_types
        }
        sale_journal_id = Journal.search([('type', '=', 'sale'), ('l10n_in_sale_journal_type', '=', False)], limit=1).id

        def split_exempt_lines(line_cmds):
            exempt, non_exempt = [], []
            Tax = self.env['account.tax']
            for line_cmd in line_cmds:
                line_vals = line_cmd[-1] if isinstance(line_cmd, (tuple, list)) else {}
                is_exempt = any(
                    Tax.browse(tax_id).l10n_in_tax_type == 'exempt'
                    for tax_cmd in line_vals.get('tax_ids', [])
                    for tax_id in (tax_cmd[-1] if isinstance(tax_cmd, (tuple, list)) else [])
                )
                (exempt if is_exempt else non_exempt).append(line_cmd)
            return exempt, non_exempt

        moves = []
        for vals in invoice_vals_list:
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            if partner.check_vat_in(partner.vat):
                invoice_lines = vals.get('invoice_line_ids') or []
                exempt_lines, non_exempt_lines = split_exempt_lines(invoice_lines)
                if exempt_lines:
                    moves.append({
                        **vals,
                        'invoice_line_ids': exempt_lines,
                        'journal_id': journal_map.get('bill_of_supply') or journal_map.get('tax_invoice') or sale_journal_id,
                    })
                if non_exempt_lines:
                    moves.append({
                        **vals,
                        'invoice_line_ids': non_exempt_lines,
                        'journal_id': journal_map.get('tax_invoice') or journal_map.get('bill_of_supply') or sale_journal_id,
                    })
            else:
                moves.append({
                    **vals,
                    'journal_id': journal_map.get('invoice_cum_bill_of_supply') or sale_journal_id,
                })
        return super()._create_account_invoices(moves, final)
