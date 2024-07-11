# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_reward_line = fields.Boolean(
        string="Is a program reward line", compute='_compute_is_reward_line')
    reward_id = fields.Many2one(
        comodel_name='loyalty.reward', ondelete='restrict', readonly=True)
    coupon_id = fields.Many2one(
        comodel_name='loyalty.card', ondelete='restrict', readonly=True)
    reward_identifier_code = fields.Char(
        help="Technical field used to link multiple reward lines from the same reward together.")
    points_cost = fields.Float(help="How much point this reward costs on the loyalty card.")

    def _compute_name(self):
        # Avoid computing the name for reward lines
        reward = self.filtered('reward_id')
        super(SaleOrderLine, self - reward)._compute_name()

    @api.depends('reward_id')
    def _compute_is_reward_line(self):
        for line in self:
            line.is_reward_line = bool(line.reward_id)

    def _compute_tax_id(self):
        reward_lines = self.filtered('is_reward_line')
        super(SaleOrderLine, self - reward_lines)._compute_tax_id()
        # Discount reward line is split per tax, the discount is set on the line but not on the product
        # as the product is the generic discount line.
        # In case of a free product, retrieving the tax on the line instead of the product won't affect the behavior.
        for line in reward_lines:
            line = line.with_company(line.company_id)
            fpos = line.order_id.fiscal_position_id or line.order_id.fiscal_position_id._get_fiscal_position(line.order_partner_id)
            # If company_id is set, always filter taxes by the company
            taxes = line.tax_id.filtered(lambda r: not line.company_id or r.company_id == line.company_id)
            line.tax_id = fpos.map_tax(taxes)

    def _get_display_price(self):
        # A product created from a promotion does not have a list_price.
        # The price_unit of a reward order line is computed by the promotion, so it can be used directly
        if self.is_reward_line and self.reward_id.reward_type != 'product':
            return self.price_unit
        return super()._get_display_price()

    def _can_be_invoiced_alone(self):
        return super()._can_be_invoiced_alone() and not self.is_reward_line

    def _is_not_sellable_line(self):
        return self.is_reward_line or super()._is_not_sellable_line()

    def _reset_loyalty(self, complete=False):
        """
        Reset the line(s) to a state which does not impact reward computation.
        If complete is set to True we also remove the coupon and reward from the line(s).
            This option should be used when the line will be unlinked.

        Returns self
        """
        vals = {
            'points_cost': 0,
            'price_unit': 0,
        }
        if complete:
            vals.update({
                'coupon_id': False,
                'reward_id': False,
            })
        self.write(vals)
        return self

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        # Update our coupon points if the order is in a confirmed state
        for line in res:
            if line.coupon_id and line.points_cost and line.state == 'sale':
                line.coupon_id.points -= line.points_cost
        return res

    def write(self, vals):
        cost_in_vals = 'points_cost' in vals
        if cost_in_vals:
            previous_cost = {l: l.points_cost for l in self}
        res = super().write(vals)
        if cost_in_vals:
            # Update our coupon points if the order is in a confirmed state
            for line in self:
                if previous_cost[line] != line.points_cost and line.state == 'sale':
                    line.coupon_id.points += (previous_cost[line] - line.points_cost)
        return res

    def unlink(self):
        # Remove related reward lines
        reward_coupon_set = {(l.reward_id, l.coupon_id, l.reward_identifier_code) for l in self if l.reward_id}
        related_lines = self.env['sale.order.line']
        related_lines |= self.order_id.order_line.filtered(lambda l: (l.reward_id, l.coupon_id, l.reward_identifier_code) in reward_coupon_set)
        # Remove the line's coupon from order if it is the last line using that coupon
        coupons_to_unlink = self.env['loyalty.card']
        for line in self:
            if line.coupon_id:
                # 2 cases:
                #  case 1: coupon has been applied directly
                #  case 2: coupon was created from a program
                if line.coupon_id in line.order_id.applied_coupon_ids:
                    line.order_id.applied_coupon_ids -= line.coupon_id
                elif line.coupon_id.order_id == line.order_id and line.coupon_id.program_id.applies_on == 'current' and\
                    not any(oLine.coupon_id == line.coupon_id and oLine not in related_lines for oLine in line.order_id.order_line):
                    # ondelete='restrict' would prevent deletion of the coupon unlink after unlinking lines
                    coupons_to_unlink |= line.coupon_id
                    line.order_id.code_enabled_rule_ids = line.order_id.code_enabled_rule_ids.filtered(lambda r: r.program_id != line.coupon_id.program_id)
        # Give back the points if the order is confirmed, points are given back if the order is cancelled but in this case we need to do it directly
        for line in related_lines:
            if line.state == 'sale':
                line.coupon_id.points += line.points_cost
        res = super(SaleOrderLine, self | related_lines).unlink()
        coupons_to_unlink.sudo().unlink()
        return res
