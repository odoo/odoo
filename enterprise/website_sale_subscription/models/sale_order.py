# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _cart_update_order_line(self, product_id, quantity, order_line, **kwargs):
        """ Update the SO's recurrence when adding or removing
            a subscription product"""

        # order_line_exist is used to check if SOL existed before
        # super() (in case of quantity <= 0, SOL is unlinked)
        order_line_exist = bool(order_line)
        order_line = super()._cart_update_order_line(product_id, quantity, order_line, **kwargs)

        def get_default_plan_id(p):
            if plan_id:= kwargs.get('plan_id'):
                return self.env['sale.subscription.plan'].browse(int(plan_id))
            pricing = self.env['sale.subscription.pricing'].sudo()._get_first_suitable_recurring_pricing(p, pricelist=self.pricelist_id)
            return pricing.plan_id

        # Take the product from order line (in case new variant created),
        # otherwise use the default product_id
        product_id = order_line.product_id.id or product_id
        product = self.env['product.product'].browse(product_id)
        if product.recurring_invoice:
            if order_line_exist and quantity <= 0:
                if not self.order_line.filtered(lambda sol: sol.product_id.recurring_invoice):
                    # Remove plan if there is no recurring line left
                    self.plan_id = False
            elif not order_line_exist and quantity >= 0:
                if not self.plan_id:
                    self.plan_id = get_default_plan_id(product)
                elif kwargs.get('plan_id') and self.plan_id != get_default_plan_id(product):
                    raise UserError(_("You cannot mix different subscription plans in the same order."))
        return order_line
