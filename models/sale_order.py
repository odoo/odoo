# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_order_lines_untaxed_amount(self):
        """ Returns the untaxed sale order total amount without the rewards and shipping amount"""
        return sum([x.price_subtotal for x in self.order_line.filtered(lambda x: not (x.is_reward_line or x.is_delivery))])

    def _get_reward_line_values(self, program):
        if program.reward_type == 'free_shipping':
            return self._get_reward_values_free_shipping(program)
        else:
            return super(SaleOrder, self)._get_reward_line_values(program)

    def _get_reward_values_free_shipping(self, program):
        delivery_line = self.order_line.filtered(lambda x: x.is_delivery)
        taxes = delivery_line.product_id.taxes_id
        if self.fiscal_position_id:
            taxes = self.fiscal_position_id.map_tax(taxes)
        return {
            'name': "Discount: %s" % (program.name),
            'product_id': program.discount_line_product_id.id,
            'price_unit': - delivery_line.price_unit,
            'product_uom_qty': 1.0,
            'product_uom': program.discount_line_product_id.uom_id.id,
            'order_id': self.id,
            'is_reward_line': True,
            'tax_id': [(4, tax.id, False) for tax in taxes],
        }

    def _get_lines_unit_prices(self):
        return [x.price_unit for x in self.order_line.filtered(lambda x: not x.is_delivery and not x.program_id)]
