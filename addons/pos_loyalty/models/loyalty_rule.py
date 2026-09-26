# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import float_round


class LoyaltyRule(models.Model):
    _name = 'loyalty.rule'
    _inherit = ['loyalty.rule', 'pos.load.mixin']

    any_product = fields.Boolean(
        compute="_compute_valid_product_ids", help="Technical field, whether all products match")
    valid_product_ids = fields.Many2many(
        'product.product', string="Valid Products", compute='_compute_valid_product_ids',
        help="these are the products that are valid for this rule.")

    promo_barcode = fields.Char("Barcode", compute='_compute_promo_barcode', store=True, readonly=False,
        help="A technical field used as an alternative to the promo code. "
        "This is automatically generated when the promo code is changed.")

    @api.model
    def _load_pos_data_domain(self, data):
        return [('program_id', 'in', data['pos.config']._get_program_ids().ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['program_id', 'valid_product_ids', 'currency_id', 'reward_point_amount', 'reward_point_mode',
                'minimum_qty', 'minimum_amount', 'minimum_amount_tax_mode', 'mode', 'code', 'any_product',
                'promo_barcode']

    @api.depends('product_ids', 'product_category_id', 'product_tag_id', 'product_domain')  # TODO later: product tags
    def _compute_valid_product_ids(self):
        for key, rules in self.grouped(lambda rule: (
            tuple(rule.product_ids.ids),
            rule.product_category_id.id,
            rule.product_tag_id.id,
            '' if rule.product_domain in ('[]', "[['sale_ok', '=', True]]") else rule.product_domain,
        )).items():
            if any(key):
                domain = Domain.AND([[('available_in_pos', '=', True)], rules[:1]._get_valid_product_domain()])
                rules.valid_product_ids = self.env['product.product'].search(domain, order="id")
                rules.any_product = False
            else:
                rules.valid_product_ids = self.env['product.product']
                rules.any_product = True

    @api.depends('code')
    def _compute_promo_barcode(self):
        for rule in self:
            rule.promo_barcode = self.env['loyalty.card']._generate_code()

    def _in_domain(self, line):
        """
        Whether the line's product falls within this rule's product domain.
        mirror of *static/src/app/models/loyalty_rule.js* LoyaltyRule._inDomain
        """
        self.ensure_one()
        return self.any_product or line.product_id in self.valid_product_ids

    def _counts_for_points(self, line):
        """
        Whether a line participates in this rule's point computations at all.
        mirror of *static/src/app/models/loyalty_rule.js* LoyaltyRule._countsForPoints
        """
        self.ensure_one()
        return not line.combo_parent_id and not line._is_tip_line()

    def _qualifying_lines(self, order, lines=None):
        """
        Lines that match this rule's product domain (the goods it applies to).
        mirror of *static/src/app/models/loyalty_rule.js* LoyaltyRule._qualifyingLines
        """
        self.ensure_one()
        order_lines = order.lines if lines is None else lines
        return order_lines.filtered(
            lambda l: not l.is_reward_line and self._counts_for_points(l) and self._in_domain(l)
        )

    def _is_fulfilled(self, order, lines=None):
        """
        Whether the order satisfies this rule's conditions (code activated, eligible
        products, minimum quantity and amount) independent of whether the rule earns
        points.
        mirror of *static/src/app/models/loyalty_rule.js* LoyaltyRule.isFulfilled
        """
        self.ensure_one()
        if self.mode == 'with_code' and self.code not in (order.applied_codes or []):
            return False
        qualifying = self._qualifying_lines(order, lines)
        if not qualifying:
            return False
        total_qty = sum(qualifying.mapped('qty'))
        if total_qty < self.minimum_qty:
            return False
        if self.minimum_amount_tax_mode == 'incl':
            amount = sum(qualifying.mapped('price_subtotal_incl'))
        else:
            amount = sum(qualifying.mapped('price_subtotal'))
        if order.is_refund:
            amount = -amount
        return amount >= self.minimum_amount

    def _get_pos_order_points(self, order, lines=None):
        """
        Points this rule generates for `order` over `lines` (defaults to all its lines).
        mirror of *static/src/app/models/loyalty_rule.js* LoyaltyRule.getPoints
        """
        self.ensure_one()
        if not self.reward_point_amount or not self._is_fulfilled(order, lines):
            return 0

        order_lines = order.lines if lines is None else lines
        if self.reward_point_mode == 'order':
            return self.reward_point_amount
        elif self.reward_point_mode == 'money':
            def is_excluded_reward(line):
                return line.is_reward_line and (
                    line.reward_id.program_id == self.program_id
                    or line.reward_id.program_id.program_type in ('ewallet', 'gift_card')
                )

            money_lines = order_lines.filtered(
                lambda l: self._counts_for_points(l) and self._in_domain(l) and not is_excluded_reward(l)
            )
            money_amount = sum(money_lines.mapped('price_subtotal_incl'))
            # Only refunds to cards should reach this
            if order.is_refund:
                money_amount = -money_amount
            return float_round(
                self.reward_point_amount * money_amount,
                precision_rounding=0.01,
                rounding_method='DOWN',
            )
        elif self.reward_point_mode == 'unit':
            return self.reward_point_amount * sum(self._qualifying_lines(order, lines).mapped('qty'))
        return 0
