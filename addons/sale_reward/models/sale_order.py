# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    reward_amount = fields.Float(compute='_compute_reward_total')

    @api.depends('order_line')
    def _compute_reward_total(self):
        for order in self:
            order.reward_amount = sum([line.price_subtotal for line in order._get_reward_lines()])

    def _get_no_effect_on_threshold_lines(self):
        self.ensure_one()
        lines = self.env['sale.order.line']
        return lines

    def _get_reward_lines(self):
        self.ensure_one()
        return self.order_line.filtered(lambda line: line.is_reward_line)

    def _get_paid_order_lines(self):
        """ Returns the sale order lines that must appear on invoice.
            Typically lines that are not reward lines.
            This method can also be overridden to return reward lines being free product lines. """
        return self.order_line.filtered(lambda x: not x._is_not_sellable_line())

    def _get_cheapest_line(self):
        # Unit prices tax included
        return min(self.order_line.filtered(lambda x: not x._is_not_sellable_line() and x.price_reduce > 0), key=lambda x: x['price_reduce'])

    def _get_invoice_status(self):
        # Handling of a specific situation: an order contains
        # a product invoiced on delivery and a promo line invoiced
        # on order. We would avoid having the invoice status 'to_invoice'
        # if the created invoice will only contain the promotion line
        super()._get_invoice_status()
        for order in self.filtered(lambda order: order.invoice_status == 'to invoice'):
            paid_lines = order._get_paid_order_lines()
            if not any(line.invoice_status == 'to invoice' for line in paid_lines):
                order.invoice_status = 'no'

    def _get_invoiceable_lines(self, final=False):
        """ Ensures we cannot invoice only reward lines.

        Since promotion lines are specified with service products,
        those lines are directly invoiceable when the order is confirmed
        which can result in invoices containing only promotion lines.

        To avoid those cases, we allow the invoicing of promotion lines
        if at least another 'basic' lines is also invoiceable.
        """
        invoiceable_lines = super()._get_invoiceable_lines(final)
        reward_lines = self._get_reward_lines()
        if invoiceable_lines <= reward_lines:
            return self.env['sale.order.line'].browse()
        return invoiceable_lines


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_reward_line = fields.Boolean('Is a program reward line')

    def _is_not_sellable_line(self):
        return self.is_reward_line or super()._is_not_sellable_line()

    def _compute_tax_id(self):
        reward_lines = self.filtered('is_reward_line')
        super(SaleOrderLine, self - reward_lines)._compute_tax_id()
        # Discount reward line is split per tax, the discount is set on the line but not on the product
        # as the product is the generic discount line.
        # In case of a free product, retrieving the tax on the line instead of the product won't affect the behavior.
        for line in reward_lines:
            line = line.with_company(line.company_id)
            fpos = line.order_id.fiscal_position_id or line.order_id.fiscal_position_id.get_fiscal_position(line.order_partner_id.id)
            # If company_id is set, always filter taxes by the company
            taxes = line.tax_id.filtered(lambda r: not line.company_id or r.company_id == line.company_id)
            line.tax_id = fpos.map_tax(taxes)

    def _get_display_price(self, product):
        # A product created from a promotion does not have a list_price.
        # The price_unit of a reward order line is computed by the promotion, so it can be used directly
        if self.is_reward_line:
            return self.price_unit
        return super()._get_display_price(product)
