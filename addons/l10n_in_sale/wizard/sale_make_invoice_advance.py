# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models
from odoo.tools import float_is_zero


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    l10n_in_warning = fields.Json(compute='_compute_l10n_in_warning')

    @api.depends(
        'sale_order_ids',
        'advance_payment_method',
        'deduct_down_payments',
        'consolidated_billing',
        'invoice_overages',
    )
    def _compute_l10n_in_warning(self):
        for wizard in self:
            warning = {}
            if flagged_orders := wizard._l10n_in_get_mixed_tax_orders(wizard.sale_order_ids._origin):
                if wizard.count > 1:
                    warning['l10n_in_mixed_tax_supply'] = {
                        'message': self.env._(
                            "Some of the selected orders contain both taxable and non-taxable items. Please create"
                            " separate invoices for the non-taxable items.",
                        ),
                        'level': 'warning',
                        'action_text': self.env._("View Sales Orders"),
                        'action': {
                            'type': 'ir.actions.act_window',
                            'name': self.env._("Sales Orders"),
                            'res_model': 'sale.order',
                            'views': [(False, 'list'), (False, 'form')],
                            'domain': [('id', 'in', flagged_orders.ids)],
                            'target': 'current',
                            'context': {},
                        },
                    }
                else:
                    warning['l10n_in_mixed_tax_supply'] = {
                        'message': self.env._(
                            "Taxable and non-taxable items cannot be combined in the same invoice for a registered"
                            " customer. Please create a separate invoice for the non-taxable items.",
                        ),
                        'level': 'warning',
                    }
            wizard.l10n_in_warning = warning

    def _l10n_in_get_mixed_tax_orders(self, orders):
        """ Return the orders whose future invoice would mix GST-taxable and exempt / nil rated / non-GST
        lines for a GST-registered customer.

        :param orders: the sale.order records to invoice (real records, not NewIds).
        :return: a sale.order recordset, subset of orders.
        """
        self.ensure_one()
        if self.advance_payment_method == 'downpayment' and len(orders) > 1:
            return self.env['sale.order']
        b2b_treatments = self.env['account.move']._l10n_in_get_b2b_gst_treatments()
        b2b_partners = orders.partner_invoice_id.filtered(
            lambda partner: partner._l10n_in_get_gst_treatment() in b2b_treatments,
        )
        eligible_orders = orders.filtered(lambda order: (
                order.country_code == 'IN'
                and order.company_id.l10n_in_gst_registration_type == 'regular'
                and order.partner_invoice_id in b2b_partners
        ))

        if not eligible_orders:
            return self.env['sale.order']
        # Read what is used on all the lines at once: the lines to invoice are browsed again per order and
        # would otherwise be read order by order (always for the taxes, and for the products from
        # BIG_RECORDSET_SIZE lines, when the ORM only reads the requested field).
        order_lines = eligible_orders.order_line
        order_lines.fetch(['product_id', 'tax_ids'])
        if self.advance_payment_method == 'delivered':
            # Only read to skip combo parent lines: 'downpayment' mode does not use the product type.
            order_lines.product_id.fetch(['type'])

        kind_by_taxes = {}
        kinds_by_order = {}
        for order in eligible_orders:
            kinds = set()
            for taxes in self._l10n_in_get_invoice_tax_sets(order):
                # Classify each distinct set of taxes once for all the orders.
                if taxes not in kind_by_taxes:
                    kind_by_taxes[taxes] = taxes._l10n_in_classify_gst_supply()
                kinds.add(kind_by_taxes[taxes])
            kinds.discard(False)
            if kinds:
                kinds_by_order[order] = kinds

        if not {'taxable', 'exempt'} <= set().union(*kinds_by_order.values()):
            return self.env['sale.order']

        if self.advance_payment_method == 'delivered' and self.consolidated_billing and len(orders) > 1:
            orders_by_key = defaultdict(lambda: self.env['sale.order'])
            fiscal_positions = {}
            for order in kinds_by_order:
                orders_by_key[self._l10n_in_get_invoice_grouping_key(order, fiscal_positions)] |= order
            invoice_groups = orders_by_key.values()
        else:
            invoice_groups = list(kinds_by_order)

        mixed_orders = self.env['sale.order']
        for group_orders in invoice_groups:
            group_kinds = set().union(*(kinds_by_order[order] for order in group_orders))
            if {'taxable', 'exempt'} <= group_kinds:
                mixed_orders |= group_orders
        return mixed_orders

    def _l10n_in_get_invoice_grouping_key(self, order, fiscal_positions):
        """ Values of the base invoice grouping keys (sale.order._get_invoice_grouping_keys) that the invoice
        of this order would get from sale.order._prepare_invoice.

        :param order: a sale.order record.
        :param fiscal_positions: dict caching the fiscal position found for a (company, invoice address), so
            that the fiscal positions are searched at most once per customer and not once per order.
        :return: a tuple (company id, invoice address id, delivery address id, currency id, fiscal position id,
            incoterm id, incoterm location): orders with the same tuple are invoiced together.
        """
        fiscal_position = order.fiscal_position_id
        if not fiscal_position:
            cache_key = (order.company_id, order.partner_invoice_id)
            if cache_key not in fiscal_positions:
                fiscal_positions[cache_key] = fiscal_position.with_company(
                    order.company_id,
                )._get_fiscal_position(order.partner_invoice_id)
            fiscal_position = fiscal_positions[cache_key]
        return (
            order.company_id.id,
            order.partner_invoice_id.id,
            order.partner_shipping_id.id,
            order.currency_id.id,
            fiscal_position.id,
            order.incoterm.id,
            order.incoterm_location,
        )

    def _l10n_in_get_invoice_tax_sets(self, order):
        """ Return the distinct sets of taxes of the invoice lines this wizard would create for the order.
        Display lines and combo parent lines (they become sections on the invoice) are left out.
        """
        self.ensure_one()
        if self.advance_payment_method == 'downpayment':
            return self._l10n_in_get_down_payment_tax_sets(order)

        final = self.deduct_down_payments
        lines = order._get_invoiceable_lines(final=final)
        if order.has_overages and self.invoice_overages != order.invoice_overages:
            lines_to_add, lines_to_remove = self._l10n_in_get_overage_lines(order, final)
            lines = (lines | lines_to_add) - lines_to_remove
        return {
            line.tax_ids
            for line in lines
            if not line.display_type and line.product_id.type != 'combo'
        }

    def _l10n_in_get_overage_lines(self, order, final):
        """ Re-evaluate the quantity to invoice of the overage lines of the order with the wizard's
        invoice_overages value instead of the order's one.

        Mirrors the overage branch of sale.order.line._compute_qty_to_invoice and the inclusion rule of
        sale.order._get_invoiceable_lines: keep both in sync with them.

        :return: a tuple (lines to add, lines to remove) of sale.order.line recordsets.
        """
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get('Product Unit')
        lines_to_add = lines_to_remove = self.env['sale.order.line']
        for line in order.order_line:
            if (
                    line.state != 'sale'
                    or line.display_type
                    or line.product_id.type == 'combo'
                    or line.invoice_policy != 'order'
                    or not line.qty_overage
            ):
                continue
            invoiced_base = line.qty_delivered if self.invoice_overages else line.product_uom_qty
            qty_to_invoice = invoiced_base - line.qty_invoiced
            if not float_is_zero(qty_to_invoice, precision_digits=precision) and (qty_to_invoice > 0 or final):
                lines_to_add |= line
            else:
                lines_to_remove |= line
        return lines_to_add, lines_to_remove

    def _l10n_in_get_down_payment_tax_sets(self, order):
        """ Return the sets of taxes of the down payment lines this wizard would create for the order.

        Same computation as in _create_invoices: one down payment line per set of taxes with a non-zero
        amount, without the taxes that cannot be discounted. The share does not change the sets of taxes,
        so the down payment is computed for 100 %.
        """
        company = order.company_id
        AccountTax = self.env['account.tax'].with_company(company)
        base_lines = [
            line._prepare_base_line_for_taxes_computation(quantity=line.product_uom_qty or line.qty_delivered)
            for line in order.order_line.filtered(lambda line: not line.display_type)
        ]
        AccountTax._add_tax_details_in_base_lines(base_lines, company)
        AccountTax._round_base_lines_tax_details(base_lines, company)
        down_payment_lines = AccountTax._prepare_down_payment_lines(
            base_lines=base_lines,
            company=company,
            amount_type='percent',
            amount=100.0,
            computation_key='l10n_in_down_payment',
        )
        return {base_line['tax_ids'] for base_line in down_payment_lines}

    def _prepare_invoice_values(self, order, so_line, accounts):
        res = super()._prepare_invoice_values(order, so_line, accounts)
        if order.l10n_in_reseller_partner_id:
            res['l10n_in_reseller_partner_id'] = order.l10n_in_reseller_partner_id
        return res
