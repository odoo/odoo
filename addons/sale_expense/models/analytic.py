# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    def _get_invoice_price(self, order):
        if self.product_id.invoice_policy == 'delivery' and self.product_id.expense_policy == 'sales_price':
            return self.product_id.with_context(
                partner=order.partner_id.id,
                date_order=order.date_order,
                pricelist=order.pricelist_id.id,
                uom=self.product_uom_id.id
            ).price
        else:
            if self.unit_amount == 0.0:
                return 0.0
            price_unit = abs(self.amount / self.unit_amount)
            if self.currency_id and self.currency_id != order.currency_id:
                price_unit = self.currency_id.compute(price_unit, order.currency_id)
            return price_unit

    def _get_sale_order_line_vals(self):
        order = self.env['sale.order'].search([('project_id', '=', self.account_id.id)], limit=1)
        if not order:
            return False
        if order.state != 'sale':
            raise UserError(_('The Sale Order %s linked to the Analytic Account must be validated before registering expenses.') % order.name)

        last_so_line = self.env['sale.order.line'].search([('order_id', '=', order.id)], order='sequence desc', limit=1)
        last_sequence = last_so_line.sequence + 1 if last_so_line else 100

        fpos = order.fiscal_position_id or order.partner_id.property_account_position_id
        taxes = fpos.map_tax(self.product_id.taxes_id)
        price = self._get_invoice_price(order)

        return {
            'order_id': order.id,
            'name': self.name,
            'sequence': last_sequence,
            'price_unit': price,
            'tax_id': [x.id for x in taxes],
            'discount': 0.0,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': 0.0,
            'qty_delivered': self.unit_amount,
        }

    def _process_expense_sale_order_line(self):
        for line in self:
            # If Product is expansible or its invoice policy is "Ordered Quantity"
            # AND current analytic_account_line does NOT have Sale Order Line
            # then search SO line based on account_id and product_id.
            if not line.so_line and line.account_id and line.product_id and (line.product_id.can_be_expensed or line.product_id.invoice_policy == 'order'):
                so_lines = self.env['sale.order.line'].search([
                    ('order_id.project_id', '=', line.account_id.id),
                    ('state', '=', 'sale'),
                    ('product_id', '=', line.product_id.id)])
                # Use the existing SO line only if the unit prices are the same, otherwise we create
                # a new line
                for so_line in so_lines:
                    # If product is can_be_expensed AND its invoice_policy is On Delivered Quantity AND unit prices are same
                    # then WRITE sale order line.
                    if not so_line.product_id.can_be_expensed \
                        or (so_line.product_id.can_be_expensed and so_line.product_id.invoice_policy == 'delivery' \
                            and so_line.price_unit == line._get_invoice_price(so_line.order_id)):
                        line.so_line = so_line
                        break

            # If product is can_be_expensed AND its invoice_policy is "On Delivered Quantity"
            # AND current analytic_account_line does NOT have Sale Order Line
            # then CREATE sale order line.
            if not line.so_line and line.account_id and line.product_id \
                    and line.product_id.can_be_expensed and line.product_id.invoice_policy == 'delivery':
                order_line_vals = line._get_sale_order_line_vals()
                if order_line_vals:
                    line.so_line = self.env['sale.order.line'].create(order_line_vals)
                    line.so_line._compute_tax_id()

            # _compute_analytic_qty filter on analytic lines linked to an expense and set qty_delivered of SO line.
            line.so_line._compute_analytic_qty()

    @api.multi
    def write(self, values):
        lines = super(AccountAnalyticLine, self).write(values)
        self._process_expense_sale_order_line()
        return lines

    @api.model
    def create(self, values):
        line = super(AccountAnalyticLine, self).create(values)
        line._process_expense_sale_order_line()
        return line
