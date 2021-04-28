# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, tools


REWARD_SALE_ORDER_LINE_SEQUENCE = 200


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    won_loyalty_points = fields.Float(help='The amount of Loyalty points the customer won with this order', default=0.0)
    spent_loyalty_points = fields.Float(help='The amount of Loyalty points the customer spent with this order', default=0.0)
    available_loyalty_points = fields.Float(help='The number of points still available to spend within this order', compute='_compute_available_loyalty_points')
    reached_loyalty_points = fields.Float(help='The number of points that will be available to spend after this order completion', compute='_compute_reached_loyalty_points')

    @api.depends('won_loyalty_points', 'spent_loyalty_points', 'state')
    def _compute_reached_loyalty_points(self):
        for order in self:
            order.reached_loyalty_points = order.partner_id.loyalty_points
            # Points are already spent from balance when the order is sent
            if order.state not in ('sent', 'sale', 'done'):
                order.reached_loyalty_points -= order.spent_loyalty_points
            # Points are already received on balance if the order is paid
            if order.state not in ('sale', 'done'):
                order.reached_loyalty_points += order.won_loyalty_points

    @api.depends('spent_loyalty_points')
    def _compute_available_loyalty_points(self):
        for order in self:
            order.available_loyalty_points = order.partner_id.loyalty_points - order.spent_loyalty_points

    def write(self, vals):
        """Adjust partner's points on state transition:
        - spend points as soon as the order is sent (for delayed payment method)
        - gain points only when payment is received
        - restore points on cancel
        """
        new_state = vals.get('state')
        if new_state:
            for order in self.filtered(lambda order: order.partner_id):
                if order.state == 'draft' and new_state in ('sent', 'sale', 'done') \
                        and order.spent_loyalty_points > 0:
                    order.partner_id.loyalty_points -= order.spent_loyalty_points
                if order.state in ('draft', 'sent') and new_state in ('sale', 'done') \
                        and order.won_loyalty_points > 0:
                    order.partner_id.loyalty_points += order.won_loyalty_points
                if order.state in ('sent', 'sale') and new_state == 'cancel' \
                        and order.spent_loyalty_points > 0:
                    order.partner_id.loyalty_points += order.spent_loyalty_points
                if order.state in ('sale') and new_state == 'cancel' \
                        and order.won_loyalty_points > 0:
                    order.partner_id.loyalty_points -= order.won_loyalty_points
        return super(SaleOrder, self).write(vals)

    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        if not line_id:
            kwargs['extra_domain'] = [('loyalty_reward_id', '=', False)]
        return super()._cart_find_product_line(product_id, line_id, **kwargs)

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        values = super(SaleOrder, self)._cart_update(product_id, line_id, add_qty, set_qty, **kwargs)
        self._cart_adjust_rewards()
        website = self.env['website'].get_current_website()
        if website.has_loyalty:
            self.recompute_loyalty_points(website.loyalty_id.id)
        return values

    def _cart_adjust_rewards(self):
        # 1. make sure no reward has a price yet to correctly compute discounts
        for line in self.order_line:
            if line.loyalty_reward_id:
                line.price_unit = 0
        # 2. determine value of each discount:
        # - 2.1. take into account non-global percentage discounts
        # - 2.2. take into account fixed price discounts (cannot be higher than what remains)
        # - 2.3. take into account percentage discounts cumulatively (% of what remains)

        def discount_precedence(line):
            if line.loyalty_reward_id.discount_type == 'percentage':
                return 3 if line.loyalty_reward_id.discount_apply_on == 'on_order' else 1
            else:
                return 2

        discount_lines = self.order_line.filtered(lambda l: l.loyalty_reward_id and l.loyalty_reward_id.reward_type == 'discount')
        for line in discount_lines.sorted(discount_precedence):
            reward = self.env['loyalty.reward'].browse(int(line.loyalty_reward_id))
            line.product_uom_qty = 1
            line.price_unit = -self._get_cart_loyalty_discount(reward)

    def _get_cart_loyalty_discount(self, reward):
        order_total = sum(self.order_line.filtered(lambda x: not x._is_not_sellable_line() or x.loyalty_reward_id).mapped('price_subtotal'))
        discount = 0
        if reward.discount_type == 'percentage':
            if reward.discount_apply_on == 'on_order':
                discount += self.currency_id.round(order_total * (reward.discount_percentage / 100))
            elif reward.discount_apply_on == 'specific_products':
                for prod in reward.discount_specific_product_ids:
                    for line in self.order_line:
                        if line.product_id.id == prod.id:
                            discount += line.currency_id.round(line.price_total * (reward.discount_percentage / 100))
            elif reward.discount_apply_on == 'cheapest_product':
                price = 0
                for line in self.order_line:
                    if price == 0 or price > line.price_unit and not line.loyalty_reward_id:
                        discount = line.currency_id.round(line.price_total * (reward.discount_percentage / 100))
                        price = line.price_unit
            if reward.discount_max_amount != 0 and discount > reward.discount_max_amount:
                discount = reward.discount_max_amount
        else:
            discount = min(order_total, reward.discount_fixed_amount)
        return discount

    def _cart_update_reward(self, reward_id=None, add_qty=1):
        if not reward_id:
            return
        if not self.partner_id:
            return
        if self.state != 'draft':
            return
        reward = self.env['loyalty.reward'].browse(int(reward_id))
        order_line = self.env['sale.order.line'].sudo().search([('order_id', '=', self.id), ('loyalty_reward_id', '=', reward_id)])
        if order_line:
            order_line.ensure_one()
            if reward.reward_type == 'gift':
                order_line.product_uom_qty += add_qty
        elif reward.reward_type == 'gift':
            # Take the default taxes on the reward product, mapped with the fiscal position
            taxes = reward.gift_product_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
            if self.fiscal_position_id:
                taxes = self.fiscal_position_id.map_tax(taxes)
            order_line = self.env['sale.order.line'].create({
                'product_id': reward.gift_product_id.id,
                'loyalty_reward_id': reward.id,
                'product_uom_qty': add_qty,
                'product_uom': reward.gift_product_id.uom_id.id,
                'order_id': self.id,
                'price_unit': 0,
                'tax_id': [fields.Command.link(tax.id) for tax in taxes],
                'sequence': REWARD_SALE_ORDER_LINE_SEQUENCE,
            })
        elif reward.reward_type == 'discount':
            product = reward.discount_product_id
            if not product:
                return
            taxes = product.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
            if self.fiscal_position_id:
                taxes = self.fiscal_position_id.map_tax(taxes)
            discount = self._get_cart_loyalty_discount(reward)
            order_line = self.env['sale.order.line'].create({
                'product_id': product.id,
                'loyalty_reward_id': reward.id,
                'product_uom_qty': 1,
                'product_uom': product.uom_id.id,
                'order_id': self.id,
                'price_unit': -discount,
                'tax_id': [fields.Command.link(tax.id) for tax in taxes],
                'sequence': REWARD_SALE_ORDER_LINE_SEQUENCE,
            })
        self._cart_adjust_rewards()
        website = self.env['website'].get_current_website()
        self.recompute_loyalty_points(website.loyalty_id.id)

    def _get_won_points(self, loyalty):
        """The total of points won, excluding the points spent on rewards"""
        if self.website_id.is_public_user() or not loyalty:
            return 0
        total_points = 0
        for line in self.order_line.filtered(lambda line: not line.loyalty_reward_id):
            line_points = 0
            for rule in loyalty.rule_ids:
                rule_points = 0
                if rule.is_product_valid(line.product_id):
                    rule_points += rule.points_quantity * line.product_uom_qty
                    rule_points += rule.points_currency * line.price_total
                if rule_points > line_points:
                    line_points = rule_points

            total_points += line_points

        total_points += self.amount_total * loyalty.points
        return max(0, tools.float_round(total_points, 0, rounding_method='HALF-UP'))

    def _get_spent_points(self):
        """The total number of points spent on rewards"""
        if not self.partner_id:
            return 0
        points = 0
        for line in self.order_line.filtered(lambda line: line.loyalty_reward_id):
            line_points = line.product_uom_qty * line.loyalty_reward_id.point_cost
            points += tools.float_round(line_points, 0, rounding_method='HALF-UP')
        return max(0, points)

    def recompute_loyalty_points(self, loyalty_id):
        loyalty = self.env['loyalty.program'].browse(loyalty_id) if loyalty_id else None
        for order in self:
            if loyalty and self.partner_id.active:
                won_points = order._get_won_points(loyalty)
                if order.won_loyalty_points != won_points:
                    order.won_loyalty_points = won_points
                spent_points = order._get_spent_points()
                if order.spent_loyalty_points != spent_points:
                    order.spent_loyalty_points = spent_points
            else:
                if order.won_loyalty_points != 0:
                    order.won_loyalty_points = 0
                if order.spent_loyalty_points != 0:
                    order.spent_loyalty_points = 0

    def get_portal_loyalty_url(self):
        return self.get_portal_url().replace('orders', 'loyalty')

    def update_prices(self):
        """Recompute rewards after pricelist prices reset."""
        super().update_prices()
        if any(line.loyalty_reward_id for line in self.order_line):
            self._cart_adjust_rewards()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    loyalty_reward_id = fields.Many2one('loyalty.reward', string='Loyalty Reward', help='The loyalty reward of this line')

    def _is_not_sellable_line(self):
        return self.loyalty_reward_id.reward_type == 'discount' or super()._is_not_sellable_line()
