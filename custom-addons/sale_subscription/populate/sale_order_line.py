# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    _populate_dependencies = ['sale.order', 'product.product', 'product.pricing']

    def _populate(self, size):
        sol = super(SaleOrderLine, self)._populate(size)
        sale_orders = sol.order_id.filtered(lambda so: so.is_subscription and so.state == 'sale')
        # TODO upsell : add upselling when there are journal to create invoice
        # sale_orders._upsell(0.5)
        sale_orders._renew(0.5)
        return sol

    @classmethod
    def filter_confirmable_sale_orders(cls, sale_orders):
        # Remove so with no recurrence_id or a recurring order_line
        sale_orders = super(SaleOrderLine, cls).filter_confirmable_sale_orders(sale_orders)
        recurring_order = sale_orders.filtered(lambda o: o.recurrence_id and o.subscription_state)
        order_with_recurring = sale_orders.order_line.filtered(lambda l: l.product_id.recurring_invoice).order_id
        return sale_orders - (recurring_order - order_with_recurring)

    def _populate_factories(self):
        def generate_product_id(iterator, field_name, model_name):
            random = populate.Random('sub')
            sale_orders = self.env['sale.order'].browse(self.env.registry.populated_models['sale.order'])
            recurring_sale_order = set(sale_orders.filtered('recurrence_id').ids)

            product = self.env['product.product'].browse(self.env.registry.populated_models['product.product'])
            recurring_product = product.filtered('recurring_invoice')
            non_recurring_product = product - recurring_product
            recurring_product = recurring_product.ids
            non_recurring_product = non_recurring_product.ids

            for values in iterator:
                if values['order_id'] not in recurring_sale_order:
                    values['product_id'] = random.choice(non_recurring_product)
                elif random.random() > 0.8:
                    values['product_id'] = random.choice(recurring_product)
                else:
                    values['product_id'] = random.choice(non_recurring_product)
                yield values

        # Swap the product_id generator
        # TODO apply new generator on top of old instead
        return [
            f if f[0] != 'product_id' else ('product_id', generate_product_id) for f in super(SaleOrderLine, self)._populate_factories()
        ]
