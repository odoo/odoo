# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, tools


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    won_loyalty_points = fields.Float(help='The amount of Loyalty points the customer won with this order', default=0.0)
    reached_loyalty_points = fields.Float(help='The number of points that will be available to spend after this order completion', compute='_compute_reached_loyalty_points')

    @api.depends('won_loyalty_points', 'state')
    def _compute_reached_loyalty_points(self):
        for order in self:
            order.reached_loyalty_points = order.partner_id.loyalty_points
            # Points are already received on balance if the order is paid
            if order.state not in ('sale', 'done'):
                order.reached_loyalty_points += max(0, order.won_loyalty_points)

    def write(self, vals):
        """Adjust partner's points on state transition:
        - gain points only when payment is received
        - restore points on cancel
        """
        new_state = vals.get('state')
        if new_state:
            for order in self.filtered(lambda order: order.partner_id):
                if order.state in ('draft', 'sent') and new_state in ('sale', 'done') \
                        and order.won_loyalty_points > 0:
                    order.partner_id.loyalty_points += order.won_loyalty_points
                if order.state in ('sale') and new_state == 'cancel' \
                        and order.won_loyalty_points > 0:
                    # Never remove more points than current balance.
                    order.partner_id.loyalty_points -= min(order.partner_id.loyalty_points, order.won_loyalty_points)
        return super(SaleOrder, self).write(vals)

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        values = super(SaleOrder, self)._cart_update(product_id, line_id, add_qty, set_qty, **kwargs)
        website = self.env['website'].get_current_website()
        if website.has_loyalty:
            self.recompute_loyalty_points(website.loyalty_id.id)
        return values

    def _get_won_points(self, loyalty):
        """The total of points won"""
        if self.website_id.is_public_user() or not loyalty:
            return 0
        total_points = 0
        for line in self.order_line:
            line_points = 0
            for rule in loyalty.rule_ids:
                rule_points = 0
                if rule.is_product_valid(line.product_id):
                    rule_points += rule.points_quantity * line.product_uom_qty
                    rule_points += rule.points_currency * line.price_total
                if rule_points > line_points:
                    line_points = rule_points

            total_points += line_points

        total_points += max(0, self.amount_total * loyalty.points)
        return max(0, tools.float_round(total_points, 0, rounding_method='HALF-UP'))

    def recompute_loyalty_points(self, loyalty_id):
        loyalty = self.env['loyalty.program'].browse(loyalty_id) if loyalty_id else None
        for order in self:
            if loyalty and self.partner_id.active:
                order.won_loyalty_points = order._get_won_points(loyalty)
            else:
                order.won_loyalty_points = 0

    def get_portal_loyalty_url(self):
        return self.get_portal_url().replace('orders', 'loyalty')
