# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_no_effect_on_threshold_lines(self):
        self.ensure_one()
        # Do not count shipping and free shipping
        free_delivery_product = self.env['coupon.program'].search([('reward_type', '=', 'free_shipping')]).mapped('discount_line_product_id')
        lines = self.order_line.filtered(lambda line: line.is_delivery or line.product_id in free_delivery_product)
        return lines + super(SaleOrder, self)._get_no_effect_on_threshold_lines()

    def _get_paid_order_lines(self):
        """ Returns the taxes included sale order total amount without the rewards amount"""
        free_reward_product = self.env['coupon.program'].search([('reward_type', '=', 'product')]).mapped('discount_line_product_id')
        return self.order_line.filtered(lambda x: not (x.is_reward_line or x.is_delivery) or x.product_id in free_reward_product)

    def _get_reward_line_values(self, program):
        if program.reward_type == 'free_shipping':
            return [self._get_reward_values_free_shipping(program)]
        else:
            return super(SaleOrder, self)._get_reward_line_values(program)

    def _get_reward_values_free_shipping(self, program):
        delivery_line = self.order_line.filtered(lambda x: x.is_delivery)
        taxes = self.fiscal_position_id.map_tax(delivery_line.product_id.taxes_id)
        return {
            'name': _("Discount: %s", program.name),
            'product_id': program.discount_line_product_id.id,
            'price_unit': delivery_line and - delivery_line.price_unit or 0.0,
            'product_uom_qty': 1.0,
            'product_uom': program.discount_line_product_id.uom_id.id,
            'order_id': self.id,
            'is_reward_line': True,
            'tax_id': [(4, tax.id, False) for tax in taxes],
        }

    def _get_cheapest_line(self):
        # Unit prices tax included
        return min(self.order_line.filtered(lambda x: not x.is_reward_line and not x.is_delivery and x.price_reduce > 0), key=lambda x: x['price_reduce'])

class SalesOrderLine(models.Model):
    _inherit = "sale.order.line"

    def unlink(self):
        # Due to delivery_set and delivery_unset methods that are called everywhere, don't unlink
        # reward lines if it's a free shipping
        self = self.exists()
        orders = self.mapped('order_id')
        applied_programs = orders.mapped('no_code_promo_program_ids') + \
                           orders.mapped('code_promo_program_id') + \
                           orders.mapped('applied_coupon_ids').mapped('program_id')
        free_shipping_products = applied_programs.filtered(
            lambda program: program.reward_type == 'free_shipping'
        ).mapped('discount_line_product_id')
        lines_to_unlink = self.filtered(lambda line: line.product_id not in free_shipping_products)
        # Unless these lines are the last ones
        res = super(SalesOrderLine, lines_to_unlink).unlink()
        only_free_shipping_line_orders = orders.filtered(lambda order: len(order.order_line.ids) == 1 and order.order_line.is_reward_line)
        super(SalesOrderLine, only_free_shipping_line_orders.mapped('order_line')).unlink()
        return res
