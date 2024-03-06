# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

import itertools

import random

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools.float_utils import float_is_zero, float_round
from odoo.osv import expression

def _generate_random_reward_code():
    return str(random.getrandbits(32))

class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Contains how much points should be given to a coupon upon validating the order
    applied_coupon_ids = fields.Many2many('loyalty.card', string="Manually Applied Coupons", copy=False)
    code_enabled_rule_ids = fields.Many2many('loyalty.rule', string="Manually Triggered Rules", copy=False)
    coupon_point_ids = fields.One2many('sale.order.coupon.points', 'order_id', copy=False)
    reward_amount = fields.Float(compute='_compute_reward_total')

    @api.depends('order_line')
    def _compute_reward_total(self):
        for order in self:
            reward_amount = 0
            for line in order.order_line:
                if not line.reward_id:
                    continue
                if line.reward_id.reward_type != 'product':
                    reward_amount += line.price_subtotal
                else:
                    # Free product are 'regular' product lines with a price_unit of 0
                    reward_amount -= line.product_id.lst_price * line.product_uom_qty
            order.reward_amount = reward_amount

    def _get_no_effect_on_threshold_lines(self):
        """
        Returns the lines that have no effect on the minimum amount to reach
        """
        self.ensure_one()
        return self.env['sale.order.line']

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        order = super(SaleOrder, self).copy(default)
        reward_lines = order.order_line.filtered('is_reward_line')
        if reward_lines:
            reward_lines.unlink()
        return order

    def action_confirm(self):
        for order in self:
            all_coupons = order.applied_coupon_ids | order.coupon_point_ids.coupon_id | order.order_line.coupon_id
            if any(order._get_real_points_for_coupon(coupon) < 0 for coupon in all_coupons):
                raise ValidationError(_('One or more rewards on the sale order is invalid. Please check them.'))
            order._update_programs_and_rewards()

        # Remove any coupon from 'current' program that don't claim any reward.
        # This is to avoid ghost coupons that are lost forever.
        # Claiming a reward for that program will require either an automated check or a manual input again.
        reward_coupons = self.order_line.coupon_id
        self.coupon_point_ids.filtered(
            lambda pe: pe.coupon_id.program_id.applies_on == 'current' and pe.coupon_id not in reward_coupons
        ).coupon_id.sudo().unlink()
        # Add/remove the points to our coupons
        for coupon, change in self.filtered(lambda s: s.state != 'sale')._get_point_changes().items():
            coupon.points += change
        res = super().action_confirm()
        self._send_reward_coupon_mail()
        return res

    def _action_cancel(self):
        previously_confirmed = self.filtered(lambda s: s.state in ('sale', 'done'))
        res = super()._action_cancel()
        # Add/remove the points to our coupons
        for coupon, changes in previously_confirmed.filtered(lambda s: s.state not in ('sale', 'done'))._get_point_changes().items():
            coupon.points -= changes
        # Remove any rewards
        self.order_line.filtered(lambda l: l.is_reward_line).unlink()
        self.coupon_point_ids.coupon_id.sudo().filtered(
            lambda c: not c.program_id.is_nominative and c.order_id in self and not c.use_count)\
            .unlink()
        self.coupon_point_ids.unlink()
        return res

    def action_open_reward_wizard(self):
        self.ensure_one()
        self._update_programs_and_rewards()
        claimable_rewards = self._get_claimable_rewards()
        if len(claimable_rewards) == 1:
            coupon = next(iter(claimable_rewards))
            if len(claimable_rewards[coupon]) == 1:
                self._apply_program_reward(claimable_rewards[coupon], coupon)
                return True
        elif not claimable_rewards:
            return True
        return self.env['ir.actions.actions']._for_xml_id('sale_loyalty.sale_loyalty_reward_wizard_action')

    def _send_reward_coupon_mail(self):
        coupons = self.env['loyalty.card']
        for order in self:
            coupons |= order._get_reward_coupons()
        if coupons:
            coupons._send_creation_communication(force_send=True)

    def _get_applied_global_discount_lines(self):
        """
        Returns the first line of the currently applied global discount or False
        """
        self.ensure_one()
        return self.order_line.filtered(lambda l: l.reward_id.is_global_discount)

    def _get_applied_global_discount(self):
        """
        Returns the currently applied global discount reward or False
        """
        return self._get_applied_global_discount_lines().reward_id

    def _get_reward_values_product(self, reward, coupon, product=None, **kwargs):
        """
        Returns an array of dict containing the values required for the reward lines
        """
        self.ensure_one()
        assert reward.reward_type == 'product'

        reward_products = reward.reward_product_ids
        product = product or reward_products[:1]
        if not product or not product in reward_products:
            raise UserError(_('Invalid product to claim.'))
        taxes = self.fiscal_position_id.map_tax(product.taxes_id.filtered(lambda t: t.company_id == self.company_id))
        points = self._get_real_points_for_coupon(coupon)
        claimable_count = float_round(points / reward.required_points, precision_rounding=1, rounding_method='DOWN') if not reward.clear_wallet else 1
        cost = points if reward.clear_wallet else claimable_count * reward.required_points
        return [{
            'name': _("Free Product - %(product)s", product=product.with_context(display_default_code=False).display_name),
            'product_id': product.id,
            'discount': 100,
            'product_uom_qty': reward.reward_product_qty * claimable_count,
            'reward_id': reward.id,
            'coupon_id': coupon.id,
            'points_cost': cost,
            'reward_identifier_code': _generate_random_reward_code(),
            'product_uom': product.uom_id.id,
            'sequence': max(self.order_line.filtered(lambda x: not x.is_reward_line).mapped('sequence'), default=10) + 1,
            'tax_id': [(Command.CLEAR, 0, 0)] + [(Command.LINK, tax.id, False) for tax in taxes]
        }]

    def _discountable_order(self, reward):
        """
        Returns the discountable and discountable_per_tax for a discount that applies to the whole order
        """
        self.ensure_one()
        assert reward.discount_applicability == 'order'

        discountable = 0
        discountable_per_tax = defaultdict(int)
        lines = self.order_line if reward.program_id.is_payment_program else (self.order_line - self._get_no_effect_on_threshold_lines())
        for line in lines:
            # Ignore lines from this reward
            if not line.product_uom_qty or not line.price_unit:
                continue
            tax_data = line.tax_id.compute_all(
                line.price_unit,
                quantity=line.product_uom_qty,
                product=line.product_id,
                partner=line.order_partner_id,
            )
            # To compute the discountable amount we get the subtotal and add
            # non-fixed tax totals. This way fixed taxes will not be discounted
            taxes = line.tax_id.filtered(lambda t: t.amount_type != 'fixed')
            discountable += tax_data['total_excluded'] + sum(
                tax['amount'] for tax in tax_data['taxes'] if tax['id'] in taxes.ids
            )
            line_price = line.price_unit * line.product_uom_qty * (1 - (line.discount or 0.0) / 100)
            discountable_per_tax[taxes] += line_price - sum(
                tax['amount'] for tax in tax_data['taxes']
                if tax['price_include'] and tax['id'] not in taxes.ids
            )
        return discountable, discountable_per_tax

    def _cheapest_line(self):
        self.ensure_one()
        cheapest_line = False
        for line in (self.order_line - self._get_no_effect_on_threshold_lines()):
            if line.reward_id or not line.product_uom_qty or not line.price_unit:
                continue
            if not cheapest_line or cheapest_line.price_unit > line.price_unit:
                cheapest_line = line
        return cheapest_line

    def _discountable_cheapest(self, reward):
        """
        Returns the discountable and discountable_per_tax for a discount that applies to the cheapest line
        """
        self.ensure_one()
        assert reward.discount_applicability == 'cheapest'

        cheapest_line = self._cheapest_line()
        discountable = cheapest_line.price_unit * (1 - (cheapest_line.discount or 0) / 100)
        taxes = cheapest_line.tax_id.filtered(lambda t: t.amount_type != 'fixed')
        return discountable, {taxes: discountable}

    def _get_specific_discountable_lines(self, reward):
        """
        Returns all lines to which `reward` can apply
        """
        self.ensure_one()
        assert reward.discount_applicability == 'specific'

        discountable_lines = self.env['sale.order.line']
        for line in (self.order_line - self._get_no_effect_on_threshold_lines()):
            domain = reward._get_discount_product_domain()
            if not line.reward_id and line.product_id.filtered_domain(domain):
                discountable_lines |= line
        return discountable_lines

    def _discountable_specific(self, reward):
        """
        Special function to compute the discountable for 'specific' types of discount.
        The goal of this function is to make sure that applying a 5$ discount on an order with a
         5$ product and a 5% discount does not make the order go below 0.

        Returns the discountable and discountable_per_tax for a discount that only applies to specific products.
        """
        self.ensure_one()
        assert reward.discount_applicability == 'specific'

        lines_to_discount = self.env['sale.order.line']
        discount_lines = defaultdict(lambda: self.env['sale.order.line'])
        order_lines = self.order_line - self._get_no_effect_on_threshold_lines()
        remaining_amount_per_line = defaultdict(int)
        for line in order_lines:
            if not line.product_uom_qty or not line.price_total:
                continue
            remaining_amount_per_line[line] = line.price_total
            domain = reward._get_discount_product_domain()
            if not line.reward_id and line.product_id.filtered_domain(domain):
                lines_to_discount |= line
            elif line.reward_id.reward_type == 'discount':
                discount_lines[line.reward_identifier_code] |= line

        order_lines -= self.order_line.filtered("reward_id")
        cheapest_line = False
        for lines in discount_lines.values():
            line_reward = lines.reward_id
            discounted_lines = order_lines
            if line_reward.discount_applicability == 'cheapest':
                cheapest_line = cheapest_line or self._cheapest_line()
                discounted_lines = cheapest_line
            elif line_reward.discount_applicability == 'specific':
                discounted_lines = self._get_specific_discountable_lines(line_reward)
            if not discounted_lines:
                continue
            common_lines = discounted_lines & lines_to_discount
            if line_reward.discount_mode == 'percent':
                for line in discounted_lines:
                    if line_reward.discount_applicability == 'cheapest':
                        remaining_amount_per_line[line] *= (1 - line_reward.discount / 100 / line.product_uom_qty)
                    else:
                        remaining_amount_per_line[line] *= (1 - line_reward.discount / 100)
            else:
                non_common_lines = discounted_lines - lines_to_discount
                # Fixed prices are per tax
                discounted_amounts = {line.tax_id.filtered(lambda t: t.amount_type != 'fixed'): abs(line.price_total) for line in lines}
                for line in itertools.chain(non_common_lines, common_lines):
                    # For gift card and eWallet programs we have no tax but we can consume the amount completely
                    if lines.reward_id.program_id.is_payment_program:
                        discounted_amount = discounted_amounts[lines.tax_id.filtered(lambda t: t.amount_type != 'fixed')]
                    else:
                        discounted_amount = discounted_amounts[line.tax_id.filtered(lambda t: t.amount_type != 'fixed')]
                    if discounted_amount == 0:
                        continue
                    remaining = remaining_amount_per_line[line]
                    consumed = min(remaining, discounted_amount)
                    if lines.reward_id.program_id.is_payment_program:
                        discounted_amounts[lines.tax_id.filtered(lambda t: t.amount_type != 'fixed')] -= consumed
                    else:
                        discounted_amounts[line.tax_id.filtered(lambda t: t.amount_type != 'fixed')] -= consumed
                    remaining_amount_per_line[line] -= consumed

        discountable = 0
        discountable_per_tax = defaultdict(int)
        for line in lines_to_discount:
            discountable += remaining_amount_per_line[line]
            line_discountable = line.price_unit * line.product_uom_qty * (1 - (line.discount or 0.0) / 100.0)
            # line_discountable is the same as in a 'order' discount
            #  but first multiplied by a factor for the taxes to apply
            #  and then multiplied by another factor coming from the discountable
            taxes = line.tax_id.filtered(lambda t: t.amount_type != 'fixed')
            discountable_per_tax[taxes] += line_discountable *\
                (remaining_amount_per_line[line] / line.price_total)
        return discountable, discountable_per_tax

    def _get_reward_values_discount(self, reward, coupon, **kwargs):
        self.ensure_one()
        assert reward.reward_type == 'discount'

        # Figure out which lines are concerned by the discount
        # cheapest_line = self.env['sale.order.line']
        discountable = 0
        discountable_per_tax = defaultdict(int)
        reward_applies_on = reward.discount_applicability
        sequence = max(self.order_line.filtered(lambda x: not x.is_reward_line).mapped('sequence'), default=10) + 1
        if reward_applies_on == 'order':
            discountable, discountable_per_tax = self._discountable_order(reward)
        elif reward_applies_on == 'specific':
            discountable, discountable_per_tax = self._discountable_specific(reward)
        elif reward_applies_on == 'cheapest':
            discountable, discountable_per_tax = self._discountable_cheapest(reward)
        if not discountable:
            if not reward.program_id.is_payment_program and any(line.reward_id.program_id.is_payment_program for line in self.order_line):
                return [{
                    'name': _("TEMPORARY DISCOUNT LINE"),
                    'product_id': reward.discount_line_product_id.id,
                    'price_unit': 0,
                    'product_uom_qty': 0,
                    'product_uom': reward.discount_line_product_id.uom_id.id,
                    'reward_id': reward.id,
                    'coupon_id': coupon.id,
                    'points_cost': 0,
                    'reward_identifier_code': _generate_random_reward_code(),
                    'sequence': sequence,
                    'tax_id': [(Command.CLEAR, 0, 0)]
                }]
            raise UserError(_('There is nothing to discount'))
        max_discount = reward.currency_id._convert(reward.discount_max_amount, self.currency_id, self.company_id, fields.Date.today()) or float('inf')
        # discount should never surpass the order's current total amount
        max_discount = min(self.amount_total, max_discount)
        if reward.discount_mode == 'per_point':
            points = self._get_real_points_for_coupon(coupon)
            if not reward.program_id.is_payment_program:
                # Rewards cannot be partially offered to customers
                points = points // reward.required_points * reward.required_points
            max_discount = min(max_discount,
                reward.currency_id._convert(reward.discount * points,
                    self.currency_id, self.company_id, fields.Date.today()))
        elif reward.discount_mode == 'per_order':
            max_discount = min(max_discount,
                reward.currency_id._convert(reward.discount, self.currency_id, self.company_id, fields.Date.today()))
        elif reward.discount_mode == 'percent':
            max_discount = min(max_discount, discountable * (reward.discount / 100))
        # Discount per taxes
        reward_code = _generate_random_reward_code()
        point_cost = reward.required_points if not reward.clear_wallet else self._get_real_points_for_coupon(coupon)
        if reward.discount_mode == 'per_point' and not reward.clear_wallet:
            # Calculate the actual point cost if the cost is per point
            converted_discount = self.currency_id._convert(min(max_discount, discountable), reward.currency_id, self.company_id, fields.Date.today())
            point_cost = converted_discount / reward.discount
        # Gift cards and eWallets are considered gift cards and should not have any taxes
        if reward.program_id.is_payment_program:
            return [{
                'name': reward.description,
                'product_id': reward.discount_line_product_id.id,
                'price_unit': -min(max_discount, discountable),
                'product_uom_qty': 1.0,
                'product_uom': reward.discount_line_product_id.uom_id.id,
                'reward_id': reward.id,
                'coupon_id': coupon.id,
                'points_cost': point_cost,
                'reward_identifier_code': reward_code,
                'sequence': sequence,
                'tax_id': [(Command.CLEAR, 0, 0)],
            }]
        discount_factor = min(1, (max_discount / discountable)) if discountable else 1
        reward_dict = {}
        for tax, price in discountable_per_tax.items():
            if not price:
                continue
            mapped_taxes = self.fiscal_position_id.map_tax(tax)
            tax_desc = ''
            if any(t.name for t in mapped_taxes):
                tax_desc = _(
                    ' - On product with the following taxes: %(taxes)s',
                    taxes=", ".join(mapped_taxes.mapped('name')),
                )
            reward_dict[tax] = {
                'name': _(
                    'Discount: %(desc)s%(tax_str)s',
                    desc=reward.description,
                    tax_str=tax_desc,
                ),
                'product_id': reward.discount_line_product_id.id,
                'price_unit': -(price * discount_factor),
                'product_uom_qty': 1.0,
                'product_uom': reward.discount_line_product_id.uom_id.id,
                'reward_id': reward.id,
                'coupon_id': coupon.id,
                'points_cost': 0,
                'reward_identifier_code': reward_code,
                'sequence': sequence,
                'tax_id': [Command.clear()] + [Command.link(tax.id) for tax in mapped_taxes]
            }
        # We only assign the point cost to one line to avoid counting the cost multiple times
        if reward_dict:
            reward_dict[next(iter(reward_dict))]['points_cost'] = point_cost
        # Returning .values() directly does not return a subscribable list
        return list(reward_dict.values())

    def _get_program_domain(self):
        """
        Returns the base domain that all programs have to comply to.
        """
        self.ensure_one()
        return [('active', '=', True), ('sale_ok', '=', True),
                ('company_id', 'in', (self.company_id.id, False)),
                '|', ('date_to', '=', False), ('date_to', '>=', fields.Date.context_today(self))]

    def _get_trigger_domain(self):
        """
        Returns the base domain that all triggers have to comply to.
        """
        self.ensure_one()
        return [('active', '=', True), ('program_id.sale_ok', '=', True),
                ('company_id', 'in', (self.company_id.id, False)),
                '|', ('program_id.date_to', '=', False), ('program_id.date_to', '>=', fields.Date.context_today(self))]

    def _get_applicable_program_points(self, domain=None):
        """
        Returns a dict with the points per program for each (automatic) program that is applicable
        """
        self.ensure_one()
        if not domain:
            domain = [('trigger', '=', 'auto')]
        # Make sure domain always complies with the order's domain rules
        domain = expression.AND([self._get_program_domain(), domain])
        # No other way than to test all programs to the order
        programs = self.env['loyalty.program'].search(domain)
        all_status = self._program_check_compute_points(programs)
        program_points = {p: status['points'][0] for p, status in all_status.items() if 'points' in status}
        return program_points

    def _get_points_programs(self):
        """
        Returns all programs that give points on the current order.
        """
        self.ensure_one()
        return self.coupon_point_ids.coupon_id.program_id

    def _get_reward_programs(self):
        """
        Returns all programs that are being used for rewards.
        """
        self.ensure_one()
        return self.order_line.reward_id.program_id

    def _get_reward_coupons(self):
        """
        Returns all coupons that are a reward.
        """
        self.ensure_one()
        return self.coupon_point_ids.coupon_id.filtered(lambda c: c.program_id.applies_on == 'future')

    def _get_applied_programs(self):
        """
        Returns all applied programs on current order.

        Applied programs is the combination of both new points for your order and the programs linked to rewards.
        """
        self.ensure_one()
        return self._get_points_programs() | self._get_reward_programs()

    def _compute_invoice_status(self):
        # Handling of a specific situation: an order contains
        # a product invoiced on delivery and a promo line invoiced
        # on order. We would avoid having the invoice status 'to_invoice'
        # if the created invoice will only contain the promotion line
        super()._compute_invoice_status()
        for order in self:
            if order.invoice_status != 'to invoice':
                continue
            if not any(not line.is_reward_line and line.invoice_status == 'to invoice' for line in order.order_line):
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
        for line in invoiceable_lines:
            if not line.is_reward_line:
                return invoiceable_lines
        return self.env['sale.order.line']

    def _recompute_prices(self):
        """Recompute coupons/promotions after pricelist prices reset."""
        super()._recompute_prices()
        if any(line.is_reward_line for line in self.order_line):
            self._update_programs_and_rewards()

    def _get_point_changes(self):
        """
        Returns the changes in points per coupon as a dict.

        Used when validating/cancelling an order
        """
        points_per_coupon = defaultdict(lambda: 0)
        for coupon_point in self.coupon_point_ids:
            points_per_coupon[coupon_point.coupon_id] += coupon_point.points
        for line in self.order_line:
            if not line.reward_id or not line.coupon_id:
                continue
            points_per_coupon[line.coupon_id] -= line.points_cost
        return points_per_coupon

    def _get_real_points_for_coupon(self, coupon, post_confirm=False):
        """
        Returns the actual points usable for this coupon for this order. Set pos_confirm to True to include points for future orders.

        This is calculated by taking the points on the coupon, the points the order will give to the coupon (if applicable) and removing the points taken by already applied rewards.
        """
        self.ensure_one()
        points = coupon.points
        if coupon.program_id.applies_on != 'future' and self.state not in ('sale', 'done'):
            # Points that will be given by the order upon confirming the order
            points += self.coupon_point_ids.filtered(lambda p: p.coupon_id == coupon).points
        # Points already used by rewards
        points -= sum(self.order_line.filtered(lambda l: l.coupon_id == coupon).mapped('points_cost'))
        points = coupon.currency_id.round(points)
        return points

    def _add_points_for_coupon(self, coupon_points):
        """
        Updates (or creates) an entry in coupon_point_ids for the given coupons.
        """
        self.ensure_one()
        if self.state in ('sale', 'done'):
            for coupon, points in coupon_points.items():
                coupon.sudo().points += points
        for pe in self.coupon_point_ids.sudo():
            if pe.coupon_id in coupon_points:
                pe.points = coupon_points.pop(pe.coupon_id)
        if coupon_points:
            self.sudo().with_context(tracking_disable=True).write({
                'coupon_point_ids': [(0, 0, {
                    'coupon_id': coupon.id,
                    'points': points,
                }) for coupon, points in coupon_points.items()]
            })

    def _remove_program_from_points(self, programs):
        self.coupon_point_ids.filtered(lambda p: p.coupon_id.program_id in programs).sudo().unlink()

    def _get_reward_line_values(self, reward, coupon, **kwargs):
        self.ensure_one()
        self = self.with_context(lang=self._get_lang())
        reward = reward.with_context(lang=self._get_lang())
        if reward.reward_type == 'discount':
            return self._get_reward_values_discount(reward, coupon, **kwargs)
        elif reward.reward_type == 'product':
            return self._get_reward_values_product(reward, coupon, **kwargs)

    def _write_vals_from_reward_vals(self, reward_vals, old_lines, delete=True):
        """
        Update, create new reward line and delete old lines in one write on `order_line`

        Returns the untouched old lines.
        """
        self.ensure_one()
        command_list = []
        for vals, line in zip(reward_vals, old_lines):
            command_list.append((Command.UPDATE, line.id, vals))
        if len(reward_vals) > len(old_lines):
            command_list.extend((Command.CREATE, 0, vals) for vals in reward_vals[len(old_lines):])
        elif len(reward_vals) < len(old_lines) and delete:
            command_list.extend((Command.DELETE, line.id) for line in old_lines[len(reward_vals):])
        self.write({'order_line': command_list})
        return self.env['sale.order.line'] if delete else old_lines[len(reward_vals):]

    def _apply_program_reward(self, reward, coupon, **kwargs):
        """
        Applies the reward to the order provided the given coupon has enough points.
        This method does not check for program rules.

        This method also assumes the points added by the program triggers have already been computed.
        The temporary points are used if the program is applicable to the current order.

        Returns a dict containing the error message or empty if everything went correctly.
        NOTE: A call to `_update_programs_and_rewards` is expected to reorder the discounts.
        """
        self.ensure_one()
        # Use the old lines before creating new ones. These should already be in a 'reset' state.
        old_reward_lines = kwargs.get('old_lines', self.env['sale.order.line'])
        if reward.is_global_discount:
            global_discount_reward_lines = self._get_applied_global_discount_lines()
            global_discount_reward = global_discount_reward_lines.reward_id
            if global_discount_reward and global_discount_reward != reward and global_discount_reward.discount >= reward.discount:
                return {'error': _('A better global discount is already applied.')}
            elif global_discount_reward and global_discount_reward != reward:
                # Invalidate the old global discount as it may impact the new discount to apply
                global_discount_reward_lines._reset_loyalty(True)
                old_reward_lines |= global_discount_reward_lines
        if not reward.program_id.is_nominative and reward.program_id.applies_on == 'future' and coupon in self.coupon_point_ids.coupon_id:
            return {'error': _('The coupon can only be claimed on future orders.')}
        elif self._get_real_points_for_coupon(coupon) < reward.required_points:
            return {'error': _('The coupon does not have enough points for the selected reward.')}
        reward_vals = self._get_reward_line_values(reward, coupon, **kwargs)
        self._write_vals_from_reward_vals(reward_vals, old_reward_lines)
        return {}

    def _get_claimable_rewards(self, forced_coupons=None):
        """
        Fetch all rewards that are currently claimable from all concerned coupons,
         meaning coupons from applied programs and applied rewards or the coupons given as parameter.

        Returns a dict containing the all the claimable rewards grouped by coupon.
        Coupons that can not claim any reward are not contained in the result.
        """
        self.ensure_one()
        all_coupons = forced_coupons or (self.coupon_point_ids.coupon_id | self.order_line.coupon_id | self.applied_coupon_ids)
        has_payment_reward = any(line.reward_id.program_id.is_payment_program for line in self.order_line)
        total_is_zero = float_is_zero(self.amount_total, precision_digits=2)
        result = defaultdict(lambda: self.env['loyalty.reward'])
        global_discount_reward = self._get_applied_global_discount()
        for coupon in all_coupons:
            points = self._get_real_points_for_coupon(coupon)
            for reward in coupon.program_id.reward_ids:
                if reward.is_global_discount and global_discount_reward and global_discount_reward.discount >= reward.discount:
                    continue
                # Discounts are not allowed if the total is zero unless there is a payment reward, in which case we allow discounts.
                # If the total is 0 again without the payment reward it will be removed.
                if reward.reward_type == 'discount' and total_is_zero and (not has_payment_reward or reward.program_id.is_payment_program):
                    continue
                if points >= reward.required_points:
                    result[coupon] |= reward
        return result

    def _allow_nominative_programs(self):
        """
        Whether or not this order may use nominative programs.
        """
        self.ensure_one()
        return True

    def _update_programs_and_rewards(self):
        """
        Updates applied programs's given points with the current state of the order.
        Checks automatic programs for applicability.
        Updates applied rewards using the new points and the current state of the order (for example with % discounts).
        """
        self.ensure_one()

        # +===================================================+
        # |       STEP 1: Retrieve all applicable programs    |
        # +===================================================+

        # Automatically load in eWallet coupons
        if self._allow_nominative_programs():
            ewallet_coupons = self.env['loyalty.card'].search(
                [('id', 'not in', self.applied_coupon_ids.ids), ('partner_id', '=', self.partner_id.id),
                ('points', '>', 0), ('program_id.program_type', '=', 'ewallet')])
            if ewallet_coupons:
                self.applied_coupon_ids += ewallet_coupons
        # Programs that are applied to the order and count points
        points_programs = self._get_points_programs()
        # Coupon programs that require the program's rules to match but do not count for points
        coupon_programs = self.applied_coupon_ids.program_id
        # Programs that are automatic and not yet applied
        program_domain = self._get_program_domain()
        domain = expression.AND([program_domain, [('id', 'not in', points_programs.ids), ('trigger', '=', 'auto'), ('rule_ids.mode', '=', 'auto')]])
        automatic_programs = self.env['loyalty.program'].search(domain).filtered(lambda p:
            not p.limit_usage or p.total_order_count < p.max_usage)

        all_programs_to_check = points_programs | coupon_programs | automatic_programs
        all_coupons = self.coupon_point_ids.coupon_id | self.applied_coupon_ids
        # First basic check using the program_domain -> for example if a program gets archived mid quotation
        domain_matching_programs = all_programs_to_check.filtered_domain(program_domain)
        all_programs_status = {p: {'error': 'error'} for p in all_programs_to_check - domain_matching_programs}
        # Compute applicability and points given for all programs that passed the domain check
        # Note that points are computed with reward lines present
        all_programs_status.update(self._program_check_compute_points(domain_matching_programs))
        # Delay any unlink to the end of the function since they cause a full cache invalidation
        lines_to_unlink = self.env['sale.order.line']
        coupons_to_unlink = self.env['loyalty.card']
        point_entries_to_unlink = self.env['sale.order.coupon.points']
        # Remove any coupons that are expired
        self.applied_coupon_ids = self.applied_coupon_ids.filtered(lambda c:
            (not c.expiration_date or c.expiration_date >= fields.Date.today())
        )
        point_ids_per_program = defaultdict(lambda: self.env['sale.order.coupon.points'])
        for pe in self.coupon_point_ids:
            # Remove any point entry for a coupon that does not belong to the customer
            if pe.coupon_id.partner_id and pe.coupon_id.partner_id != self.partner_id:
                pe.points = 0
                point_entries_to_unlink |= pe
            else:
                point_ids_per_program[pe.coupon_id.program_id] |= pe

        # +==========================================+
        # |       STEP 2: Update applied programs    |
        # +==========================================+

        # Programs that were not applied via a coupon
        for program in points_programs:
            status = all_programs_status[program]
            program_point_entries = point_ids_per_program[program]
            if 'error' in status:
                # Program is not applicable anymore
                coupons_from_order = program_point_entries.coupon_id.filtered(lambda c: c.order_id == self)
                all_coupons -= coupons_from_order
                # Invalidate those lines so that they don't impact anything further down the line
                program_reward_lines = self.order_line.filtered(lambda l: l.coupon_id in coupons_from_order)
                program_reward_lines._reset_loyalty(True)
                lines_to_unlink |= program_reward_lines
                # Delete coupon created by this order for this program if it is not nominative
                if not program.is_nominative:
                    coupons_to_unlink |= coupons_from_order
                else:
                    # Only remove the coupon_point_id
                    point_entries_to_unlink |= program_point_entries
                    point_entries_to_unlink.points = 0
                # Remove the code activated rules
                self.code_enabled_rule_ids -= program.rule_ids
            else:
                # Program stays applicable, update our points
                all_point_changes = [p for p in status['points'] if p]
                if not all_point_changes and program.is_nominative:
                    all_point_changes = [0]
                for pe, points in zip(program_point_entries.sudo(), all_point_changes):
                    pe.points = points
                if len(program_point_entries) < len(all_point_changes):
                    new_coupon_points = all_point_changes[len(program_point_entries):]
                    # NOTE: Maybe we could batch the creation of coupons across multiple programs but this really only applies to gift cards
                    new_coupons = self.env['loyalty.card'].with_context(loyalty_no_mail=True, tracking_disable=True).create([{
                        'program_id': program.id,
                        'partner_id': False,
                        'points': 0,
                        'order_id': self.id,
                    } for _ in new_coupon_points])
                    self._add_points_for_coupon({coupon: x for coupon, x in zip(new_coupons, new_coupon_points)})
                elif len(program_point_entries) > len(all_point_changes):
                    point_ids_to_unlink = program_point_entries[len(all_point_changes):]
                    all_coupons -= point_ids_to_unlink.coupon_id
                    coupons_to_unlink |= point_ids_to_unlink.coupon_id
                    point_ids_to_unlink.points = 0

        # Programs applied using a coupon
        applied_coupon_per_program = defaultdict(lambda: self.env['loyalty.card'])
        for coupon in self.applied_coupon_ids:
            applied_coupon_per_program[coupon.program_id] |= coupon
        for program in coupon_programs:
            if program not in domain_matching_programs or\
                (program.applies_on == 'current' and 'error' in all_programs_status[program]):
                program_reward_lines = self.order_line.filtered(lambda l: l.coupon_id in applied_coupon_per_program[program])
                program_reward_lines._reset_loyalty(True)
                lines_to_unlink |= program_reward_lines
                self.applied_coupon_ids -= applied_coupon_per_program[program]
                all_coupons -= applied_coupon_per_program[program]

        # +==========================================+
        # |       STEP 3: Update reward lines        |
        # +==========================================+

        # We will reuse these lines as much as possible, this resets the order in a reward-less state
        reward_line_pool = self.order_line.filtered(lambda l: l.reward_id and l.coupon_id)._reset_loyalty()
        seen_rewards = set()
        line_rewards = []
        payment_rewards = [] # gift_card and ewallet are considered as payments and should always be applied last
        for line in self.order_line:
            if line.reward_identifier_code in seen_rewards or not line.reward_id or\
                not line.coupon_id:
                continue
            seen_rewards.add(line.reward_identifier_code)
            if line.reward_id.program_id.is_payment_program:
                payment_rewards.append((line.reward_id, line.coupon_id, line.reward_identifier_code, line.product_id))
            else:
                line_rewards.append((line.reward_id, line.coupon_id, line.reward_identifier_code, line.product_id))

        for reward_key in itertools.chain(line_rewards, payment_rewards):
            coupon = reward_key[1]
            reward = reward_key[0]
            program = reward.program_id
            points = self._get_real_points_for_coupon(coupon)
            if coupon not in all_coupons or points < reward.required_points or program not in domain_matching_programs:
                # Reward is not applicable anymore, the reward lines will simply be removed at the end of this function
                continue
            try:
                values_list = self._get_reward_line_values(reward, coupon, product=reward_key[3])
            except UserError:
                # It could happen that we have nothing to discount after changing the order.
                values_list = []
            reward_line_pool = self._write_vals_from_reward_vals(values_list, reward_line_pool, delete=False)

        lines_to_unlink |= reward_line_pool

        # +==========================================+
        # |       STEP 4: Apply new programs         |
        # +==========================================+

        for program in automatic_programs:
            program_status = all_programs_status[program]
            if 'error' in program_status:
                continue
            self.__try_apply_program(program, False, program_status)

        # +==========================================+
        # |       STEP 5: Cleanup                    |
        # +==========================================+

        order_line_update = [(Command.DELETE, line.id) for line in lines_to_unlink]
        if order_line_update:
            self.write({'order_line': order_line_update})
        if coupons_to_unlink:
            coupons_to_unlink.sudo().unlink()
        if point_entries_to_unlink:
            point_entries_to_unlink.sudo().unlink()

    def _get_not_rewarded_order_lines(self):
        return self.order_line.filtered(lambda line: line.product_id and not line.reward_id)

    def _program_check_compute_points(self, programs):
        """
        Checks the program validity from the order lines aswell as computing the number of points to add.

        Returns a dict containing the error message or the points that will be given with the keys 'points'.
        """
        self.ensure_one()

        # Prepare quantities
        order_lines = self._get_not_rewarded_order_lines()
        products = order_lines.product_id
        products_qties = dict.fromkeys(products, 0)
        for line in order_lines:
            products_qties[line.product_id] += line.product_uom_qty
        # Contains the products that can be applied per rule
        products_per_rule = programs._get_valid_products(products)

        # Prepare amounts
        no_effect_lines = self._get_no_effect_on_threshold_lines()
        base_untaxed_amount = self.amount_untaxed - sum(line.price_subtotal for line in no_effect_lines)
        base_tax_amount = self.amount_tax - sum(line.price_tax for line in no_effect_lines)
        amounts_per_program = {p: {'untaxed': base_untaxed_amount, 'tax': base_tax_amount} for p in programs}
        for line in self.order_line:
            if not line.reward_id or line.reward_id.reward_type != 'discount':
                continue
            for program in programs:
                # Do not consider the program's discount + automatic discount lines for the amount to check.
                if line.reward_id.program_id.trigger == 'auto' or line.reward_id.program_id == program:
                    amounts_per_program[program]['untaxed'] -= line.price_subtotal
                    amounts_per_program[program]['tax'] -= line.price_tax

        result = {}
        for program in programs:
            untaxed_amount = amounts_per_program[program]['untaxed']
            tax_amount = amounts_per_program[program]['tax']

            # Used for error messages
            # By default False, but True if no rules and applies_on current -> misconfigured coupons program
            code_matched = not bool(program.rule_ids) and program.applies_on == 'current' # Stays false if all triggers have code and none have been activated
            minimum_amount_matched = code_matched
            product_qty_matched = code_matched
            points = 0
            # Some rules may split their points per unit / money spent
            #  (i.e. gift cards 2x50$ must result in two 50$ codes)
            rule_points = []
            program_result = result.setdefault(program, dict())
            for rule in program.rule_ids:
                if rule.mode == 'with_code' and rule not in self.code_enabled_rule_ids:
                    continue
                code_matched = True
                rule_amount = rule._compute_amount(self.currency_id)
                if rule_amount > (rule.minimum_amount_tax_mode == 'incl' and (untaxed_amount + tax_amount) or untaxed_amount):
                    continue
                minimum_amount_matched = True
                if not products_per_rule.get(rule):
                    continue
                rule_products = products_per_rule[rule]
                ordered_rule_products_qty = sum(products_qties[product] for product in rule_products)
                if ordered_rule_products_qty < rule.minimum_qty or not rule_products:
                    continue
                product_qty_matched = True
                if not rule.reward_point_amount:
                    continue
                # Count all points separately if the order is for the future and the split option is enabled
                if program.applies_on == 'future' and rule.reward_point_split and rule.reward_point_mode != 'order':
                    if rule.reward_point_mode == 'unit':
                        rule_points.extend(rule.reward_point_amount for _ in range(int(ordered_rule_products_qty)))
                    elif rule.reward_point_mode == 'money':
                        for line in self.order_line:
                            if line.is_reward_line or line.product_id not in rule_products or line.product_uom_qty <= 0:
                                continue
                            points_per_unit = float_round(
                                (rule.reward_point_amount * line.price_total / line.product_uom_qty),
                                precision_digits=2, rounding_method='DOWN')
                            if not points_per_unit:
                                continue
                            rule_points.extend([points_per_unit] * int(line.product_uom_qty))
                else:
                    # All checks have been passed we can now compute the points to give
                    if rule.reward_point_mode == 'order':
                        points += rule.reward_point_amount
                    elif rule.reward_point_mode == 'money':
                        # Compute amount paid for rule
                        # NOTE: this does not account for discounts -> 1 point per $ * (100$ - 30%) will result in 100 points
                        amount_paid = sum(max(0, line.price_total) for line in order_lines if line.product_id in rule_products)
                        points += float_round(rule.reward_point_amount * amount_paid, precision_digits=2, rounding_method='DOWN')
                    elif rule.reward_point_mode == 'unit':
                        points += rule.reward_point_amount * ordered_rule_products_qty
            # NOTE: for programs that are nominative we always allow the program to be 'applied' on the order
            #  with 0 points so that `_get_claimable_rewards` returns the rewards associated with those programs
            if not program.is_nominative:
                if not code_matched:
                    program_result['error'] = _("This program requires a code to be applied.")
                elif not minimum_amount_matched:
                    program_result['error'] = _(
                        'A minimum of %(amount)s %(currency)s should be purchased to get the reward',
                        amount=min(program.rule_ids.mapped('minimum_amount')),
                        currency=program.currency_id.name,
                    )
                elif not product_qty_matched:
                    program_result['error'] = _("You don't have the required product quantities on your sales order.")
            elif not self._allow_nominative_programs():
                program_result['error'] = _("This program is not available for public users.")
            if 'error' not in program_result:
                points_result = [points] + rule_points
                program_result['points'] = points_result
        return result

    def __try_apply_program(self, program, coupon, status):
        self.ensure_one()
        all_points = status['points']
        points = all_points[0]
        coupons = coupon or self.env['loyalty.card']
        if coupon:
            if program.is_nominative:
                self._add_points_for_coupon({coupon: points})
        elif not coupon:
            # If the program only applies on the current order it does not make sense to fetch already existing coupons
            if program.is_nominative:
                coupon = self.env['loyalty.card'].search(
                    [('partner_id', '=', self.partner_id.id), ('program_id', '=', program.id)], limit=1)
                # Do not apply 'nominative' programs if no point is given and no coupon exists
                if not points and not coupon:
                    return {'error': _('No card found for this loyalty program and no points will be given with this order.')}
                elif coupon:
                    self._add_points_for_coupon({coupon: points})
                coupons = coupon
            if not coupon:
                all_points = [p for p in all_points if p]
                partner = False
                # Loyalty programs and ewallets are nominative
                if program.is_nominative:
                    partner = self.partner_id.id
                coupons = self.env['loyalty.card'].sudo().with_context(loyalty_no_mail=True, tracking_disable=True).create([{
                    'program_id': program.id,
                    'partner_id': partner,
                    'points': 0,
                    'order_id': self.id,
                } for _ in all_points])
                self._add_points_for_coupon({coupon: x for coupon, x in zip(coupons, all_points)})
        return {'coupon': coupons}

    def _try_apply_program(self, program, coupon=None):
        """
        Tries to apply a program using the coupon if provided.

        This function provides the full routine to apply a program, it will check for applicability
        aswell as creating the necessary coupons and co-models to give the points to the customer.

        This function does not apply any reward to the order, rewards have to be given manually.

        Returns a dict containing the error message or containing the associated coupon(s).
        """
        self.ensure_one()
        # Basic checks
        if not program.filtered_domain(self._get_program_domain()):
            return {'error': _('The program is not available for this order.')}
        elif program in self._get_applied_programs():
            return {'error': _('This program is already applied to this order.')}
        # Check for applicability from the program's triggers/rules.
        # This step should also compute the amount of points to give for that program on that order.
        status = self._program_check_compute_points(program)[program]
        if 'error' in status:
            return status
        return self.__try_apply_program(program, coupon, status)

    def _try_apply_code(self, code):
        """
        Tries to apply a promotional code to the sales order.
        It can be either from a coupon or a program rule.

        Returns a dict with the following possible keys:
         - 'not_found': Populated with True if the code did not yield any result.
         - 'error': Any error message that could occur.
         OR The result of `_get_claimable_rewards` with the found or newly created coupon, it will be empty if the coupon was consumed completely.
        """
        self.ensure_one()

        base_domain = self._get_trigger_domain()
        domain = expression.AND([base_domain, [('mode', '=', 'with_code'), ('code', '=', code)]])
        rule = self.env['loyalty.rule'].search(domain)
        program = rule.program_id
        coupon = False

        if rule in self.code_enabled_rule_ids:
            return {'error': _('This promo code is already applied.')}

        # No trigger was found from the code, try to find a coupon
        if not program:
            coupon = self.env['loyalty.card'].search([('code', '=', code)])
            if not coupon or\
                not coupon.program_id.active or\
                not coupon.program_id.reward_ids or\
                not coupon.program_id.filtered_domain(self._get_program_domain()):
                return {'error': _('This code is invalid (%s).', code), 'not_found': True}
            elif coupon.expiration_date and coupon.expiration_date < fields.Date.today():
                return {'error': _('This coupon is expired.')}
            elif coupon.points < min(coupon.program_id.reward_ids.mapped('required_points')):
                return {'error': _('This coupon has already been used.')}
            program = coupon.program_id

        if not program or not program.active:
            return {'error': _('This code is invalid (%s).', code), 'not_found': True}
        elif (program.limit_usage and program.total_order_count >= program.max_usage) or\
            (program.date_to and program.date_to < fields.Date.context_today(self)):
            return {'error': _('This code is expired (%s).', code)}

        # Rule will count the next time the points are updated
        if rule:
            self.code_enabled_rule_ids |= rule
        program_is_applied = program in self._get_points_programs()
        # Condition that need to apply program (if not applied yet):
        # current -> always
        # future -> if no coupon
        # nominative -> non blocking if card exists with points
        if coupon:
            self.applied_coupon_ids += coupon
        if program_is_applied:
            # Update the points for our programs, this will take the new trigger in account
            self._update_programs_and_rewards()
        elif program.applies_on != 'future' or not coupon:
            apply_result = self._try_apply_program(program, coupon)
            if 'error' in apply_result and (not program.is_nominative or (program.is_nominative and not coupon)):
                if rule:
                    self.code_enabled_rule_ids -= rule
                if coupon:
                    self.applied_coupon_ids -= coupon
                return apply_result
            coupon = apply_result.get('coupon', self.env['loyalty.card'])
        return self._get_claimable_rewards(forced_coupons=coupon)
