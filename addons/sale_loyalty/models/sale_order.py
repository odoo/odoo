# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
import random
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.osv import expression
from odoo.tools import float_round, lazy, str2bool


def _generate_random_reward_code():
    return str(random.getrandbits(32))


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Contains how much points should be given to a coupon upon validating the order
    applied_coupon_ids = fields.Many2many(
        comodel_name='loyalty.card', string="Manually Applied Coupons", copy=False)
    code_enabled_rule_ids = fields.Many2many(
        comodel_name='loyalty.rule', string="Manually Triggered Rules", copy=False)
    coupon_point_ids = fields.One2many(
        comodel_name='sale.order.coupon.points', inverse_name='order_id', copy=False)
    reward_amount = fields.Float(compute='_compute_reward_total')

    loyalty_data = fields.Json(compute='_compute_loyalty_data')

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

    def _compute_loyalty_data(self):
        self.loyalty_data = {}

        confirmed_so = self.filtered(lambda order: order.state == 'sale' and bool(order.id))
        if not confirmed_so:
            return

        loyalty_history_data = self.env['loyalty.history'].sudo()._read_group(
            domain=[
                ('order_id', 'in', confirmed_so.ids),
            ],
            groupby=['order_id'],
            aggregates=['issued:sum', 'used:sum'],
        )
        loyalty_history_data_per_order = {
            order_id: {
                'total_issued': issued,
                'total_cost': cost,
            }
            for order_id, issued, cost in loyalty_history_data
        }
        for order in confirmed_so:
            if order.id not in loyalty_history_data_per_order:
                continue
            coupons = order.coupon_point_ids.coupon_id
            coupon_point_name = (len(coupons) == 1 and coupons.point_name) or _("Points")
            order.loyalty_data = {
                'point_name': coupon_point_name,
                'issued': loyalty_history_data_per_order[order.id]['total_issued'],
                'cost': loyalty_history_data_per_order[order.id]['total_cost'],
            }

    def _add_loyalty_history_lines(self):
        self.ensure_one()
        points_per_coupon = defaultdict(dict)
        for coupon_point in self.coupon_point_ids:
            points_per_coupon[coupon_point.coupon_id]['issued'] = coupon_point.points
        for line in self.order_line:
            if not line.coupon_id:
                continue
            points_per_coupon[line.coupon_id]['cost'] = line.points_cost

        create_values = []
        base_values = {
            'order_id': self.id,
            'order_model': self._name,
            'description': _("Order %s", self.display_name),
        }
        for coupon, point_dict in points_per_coupon.items():
            cost = point_dict.get('cost', 0.0)
            issued = point_dict.get('issued', 0.0)
            create_values.append({
                **base_values,
                'card_id': coupon.id,
                'used': cost,
                'issued': issued,
            })

        self.env['loyalty.history'].create(create_values)

    def _get_no_effect_on_threshold_lines(self):
        """Return the lines that have no effect on the minimum amount to reach."""
        self.ensure_one()
        return self.env['sale.order.line']

    def copy(self, default=None):
        new_orders = super().copy(default)
        reward_lines = new_orders.order_line.filtered('is_reward_line')
        if reward_lines:
            reward_lines.unlink()
        return new_orders

    def action_confirm(self):
        for order in self:
            all_coupons = order.applied_coupon_ids | order.coupon_point_ids.coupon_id | order.order_line.coupon_id
            if any(order._get_real_points_for_coupon(coupon) < 0 for coupon in all_coupons):
                raise ValidationError(_('One or more rewards on the sale order is invalid. Please check them.'))
            order._update_programs_and_rewards()
            order._add_loyalty_history_lines()

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
        previously_confirmed = self.filtered(lambda s: s.state == 'sale')
        res = super()._action_cancel()

        order_history_lines = self.env['loyalty.history'].search([
            ('order_model', '=', self._name),
            ('order_id', 'in', previously_confirmed.ids),
        ])
        if order_history_lines:
            order_history_lines.sudo().unlink()

        # Add/remove the points to our coupons
        for coupon, changes in previously_confirmed.filtered(
            lambda s: s.state != 'sale'
        )._get_point_changes().items():
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
            rewards = claimable_rewards[coupon]
            if len(rewards) == 1 and not rewards.multi_product:
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
        if not product or product not in reward_products:
            raise UserError(_('Invalid product to claim.'))
        taxes = self.fiscal_position_id.map_tax(product.taxes_id._filter_taxes_by_company(self.company_id))
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

    def _discountable_amount(self, rewards_to_ignore):
        """Compute the `discountable` amount for the current order, ignoring the provided rewards.

        :param rewards_to_ignore: the rewards to ignore from the total amount (if they were already
            applied on the order)
        :type reward: `loyalty.reward` recordset

        :return: The discountable amount
        :rtype: float
        """
        self.ensure_one()

        discountable = 0

        for line in self.order_line - self._get_no_effect_on_threshold_lines():
            if rewards_to_ignore and line.reward_id in rewards_to_ignore:
                # Ignore the existing reward line if it was already applied
                continue
            if not line.product_uom_qty or not line.price_unit:
                # Ignore lines whose amount will be 0 (bc of empty qty or 0 price)
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
        return discountable

    def _discountable_order(self, reward):
        """Compute the `discountable` amount (and amounts per tax group) for the current order.

        :param reward: if provided, the reward whose discountable amounts must be computed.
            It must be applicable at the order level.
        :type reward: `loyalty.reward` record, can be empty to compute the amounts regardless of the
            program configuration

        :return: A tuple with the first element being the total discountable amount of the order,
            and the second a dictionary mapping each non-fixed taxes group to its corresponding
            total untaxed amount of the eligible order lines.
        :rtype: tuple(float, dict(account.tax: float))
        """
        self.ensure_one()
        reward.ensure_one()
        assert reward.discount_applicability == 'order'

        if reward.program_id.is_payment_program:
            # Gift cards and eWallets are applied on the total order amount
            lines = self.order_line
        else:
            # Other types of programs are not expected to apply on delivery lines
            lines = self.order_line - self._get_no_effect_on_threshold_lines()

        discountable = 0
        discountable_per_tax = defaultdict(float)

        AccountTax = self.env['account.tax']
        order_lines = self.order_line.filtered(lambda x: not x.display_type)
        base_lines = []
        for line in order_lines:
            base_line = line._prepare_base_line_for_taxes_computation()
            taxes = base_line['tax_ids'].flatten_taxes_hierarchy()
            if not reward.program_id.is_payment_program:
                # To compute the discountable amount we get the subtotal and add
                # non-fixed tax totals. This way fixed taxes will not be discounted
                # This does not apply to Gift Cards and e-Wallet, where the total
                # order amount may be paid with the card balance
                taxes = taxes.filtered(lambda t: t.amount_type != 'fixed')
            base_line['discount_taxes'] = taxes
            base_lines.append(base_line)
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id)

        def grouping_function(base_line, tax_data):
            return {
                'taxes': base_line['discount_taxes'],
                'skip': (
                    tax_data['tax'] not in base_line['discount_taxes']
                    or base_line['record'] not in lines
                ),
            }

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        for grouping_key, values in values_per_grouping_key.items():
            if grouping_key and grouping_key['skip']:
                continue

            taxes = grouping_key['taxes'] if grouping_key else self.env['account.tax']
            discountable += values['raw_base_amount_currency'] + values['raw_tax_amount_currency']
            discountable_per_tax[taxes] += (
                values['raw_base_amount_currency']
                + sum(
                    tax_data['raw_tax_amount_currency']
                    for base_line, taxes_data in values['base_line_x_taxes_data']
                    for tax_data in taxes_data
                    if tax_data['tax'].price_include
                )
            )
        return discountable, discountable_per_tax

    def _cheapest_line(self):
        self.ensure_one()
        cheapest_line = False
        cheapest_line_price_unit = False
        for line in (self.order_line - self._get_no_effect_on_threshold_lines()):
            line_price_unit = self._get_order_line_price(line, 'price_unit')
            if (
                line.reward_id
                or line.combo_item_id
                or not line.product_uom_qty
                or not line_price_unit
            ):
                continue
            if not cheapest_line or cheapest_line_price_unit > line_price_unit:
                cheapest_line = self._get_order_lines_with_price(line)
                cheapest_line_price_unit = line_price_unit
        return cheapest_line

    def _discountable_cheapest(self, reward):
        """
        Returns the discountable and discountable_per_tax for a discount that applies to the cheapest line
        """
        self.ensure_one()
        assert reward.discount_applicability == 'cheapest'

        cheapest_line = self._cheapest_line()
        if not cheapest_line:
            return False, False

        discountable = 0
        discountable_per_tax = defaultdict(int)
        for line in cheapest_line:
            discountable += line.price_total
            taxes = line.tax_id.filtered(lambda t: t.amount_type != 'fixed')
            discountable_per_tax[taxes] += line.price_unit * (1 - (line.discount or 0) / 100)

        return discountable, discountable_per_tax

    def _get_specific_discountable_lines(self, reward):
        """
        Returns all lines to which `reward` can apply
        """
        self.ensure_one()
        assert reward.discount_applicability == 'specific'

        discountable_lines = self.env['sale.order.line']
        for line in (self.order_line - self._get_no_effect_on_threshold_lines()):
            domain = reward._get_discount_product_domain()
            if (
                not line.reward_id
                and not line.combo_item_id
                and line.product_id.filtered_domain(domain)
            ):
                discountable_lines |= self._get_order_lines_with_price(line)
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

        lines_to_discount = self._get_specific_discountable_lines(reward).filtered(
            lambda line: bool(line.product_uom_qty and line.price_total)
        )
        discount_lines = defaultdict(lambda: self.env['sale.order.line'])
        order_lines = self.order_line - self._get_no_effect_on_threshold_lines()
        remaining_amount_per_line = defaultdict(int)
        for line in order_lines:
            if not line.product_uom_qty or not line.price_total:
                continue
            remaining_amount_per_line[line] = line.price_total
            if line.reward_id.reward_type == 'discount':
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
                discounted_amounts = defaultdict(int, {
                    line.tax_id.filtered(lambda t: t.amount_type != 'fixed'): abs(line.price_total)
                    for line in lines
                })
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

        reward_applies_on = reward.discount_applicability
        reward_product = reward.discount_line_product_id
        reward_program = reward.program_id
        reward_currency = reward.currency_id
        sequence = max(
            self.order_line.filtered(lambda x: not x.is_reward_line).mapped('sequence'),
            default=10
        ) + 1
        base_reward_line_values = {
            'product_id': reward_product.id,
            'product_uom_qty': 1.0,
            'product_uom': reward_product.uom_id.id,
            'tax_id': [Command.clear()],
            'name': reward.description,
            'reward_id': reward.id,
            'coupon_id': coupon.id,
            'sequence': sequence,
            'reward_identifier_code': _generate_random_reward_code(),
        }

        discountable = 0
        discountable_per_tax = defaultdict(int)
        if reward_applies_on == 'order':
            discountable, discountable_per_tax = self._discountable_order(reward)
        elif reward_applies_on == 'specific':
            discountable, discountable_per_tax = self._discountable_specific(reward)
        elif reward_applies_on == 'cheapest':
            discountable, discountable_per_tax = self._discountable_cheapest(reward)

        if not discountable:
            if not reward_program.is_payment_program and any(line.reward_id.program_id.is_payment_program for line in self.order_line):
                return [{
                    **base_reward_line_values,
                    'name': _("TEMPORARY DISCOUNT LINE"),
                    'price_unit': 0,
                    'product_uom_qty': 0,
                    'points_cost': 0,
                }]
            raise UserError(_('There is nothing to discount'))

        max_discount = reward_currency._convert(reward.discount_max_amount, self.currency_id, self.company_id, fields.Date.today()) or float('inf')
        # discount should never surpass the order's current total amount
        max_discount = min(self.amount_total, max_discount)
        if reward.discount_mode == 'per_point':
            points = self._get_real_points_for_coupon(coupon)
            if not reward_program.is_payment_program:
                # Rewards cannot be partially offered to customers
                points = points // reward.required_points * reward.required_points
            max_discount = min(max_discount,
                reward_currency._convert(reward.discount * points,
                    self.currency_id, self.company_id, fields.Date.today()))
        elif reward.discount_mode == 'per_order':
            max_discount = min(max_discount,
                reward_currency._convert(reward.discount, self.currency_id, self.company_id, fields.Date.today()))
        elif reward.discount_mode == 'percent':
            max_discount = min(max_discount, discountable * (reward.discount / 100))

        # Discount per taxes
        point_cost = reward.required_points if not reward.clear_wallet else self._get_real_points_for_coupon(coupon)
        if reward.discount_mode == 'per_point' and not reward.clear_wallet:
            # Calculate the actual point cost if the cost is per point
            converted_discount = self.currency_id._convert(min(max_discount, discountable), reward_currency, self.company_id, fields.Date.today())
            point_cost = converted_discount / reward.discount

        if reward_program.is_payment_program:  # Gift card / eWallet
            reward_line_values = {
                **base_reward_line_values,
                'price_unit': -min(max_discount, discountable),
                'points_cost': point_cost,
            }

            if reward_program.program_type == 'gift_card':
                # For gift cards, the SOL should consider the discount product taxes
                taxes_to_apply = reward_product.taxes_id._filter_taxes_by_company(self.company_id)
                if taxes_to_apply:
                    mapped_taxes = self.fiscal_position_id.map_tax(taxes_to_apply)
                    price_incl_taxes = mapped_taxes.filtered('price_include')
                    tax_res = mapped_taxes.with_context(
                        force_price_include=True,
                        round=False,
                        round_base=False,
                    ).compute_all(
                        reward_line_values['price_unit'],
                        currency=self.currency_id,
                    )
                    new_price = tax_res['total_excluded']
                    new_price += sum(
                        tax_data['amount']
                        for tax_data in tax_res['taxes']
                        if tax_data['id'] in price_incl_taxes.ids
                    )
                    reward_line_values.update({
                        'price_unit': new_price,
                        'tax_id': [Command.set(mapped_taxes.ids)],
                    })
            return [reward_line_values]

        if reward_applies_on == 'order' and reward.discount_mode in ['per_point', 'per_order']:
            reward_line_values = {
                **base_reward_line_values,
                'price_unit': -min(max_discount, discountable),
                'points_cost': point_cost,
            }

            reward_taxes = reward.tax_ids._filter_taxes_by_company(self.company_id)
            if reward_taxes:
                mapped_taxes = self.fiscal_position_id.map_tax(reward_taxes)

                # Check for any order line where its taxes exactly match reward_taxes
                matching_lines = [
                    line for line in self.order_line
                    if not line.is_delivery and set(line.tax_id) == set(mapped_taxes)
                ]

                if not matching_lines:
                    raise ValidationError(_("No product is compatible with this promotion."))

                untaxed_amount = sum(line.price_subtotal for line in matching_lines)
                # Discount amount should not exceed total untaxed amount of the matching lines
                reward_line_values['price_unit'] = max(
                    -untaxed_amount,
                    reward_line_values['price_unit']
                )

                reward_line_values['tax_id'] = [Command.set(mapped_taxes.ids)]

            # Discount amount should not exceed the untaxed amount on the order
            if abs(reward_line_values['price_unit']) > self.amount_untaxed:
                reward_line_values['price_unit'] = -self.amount_untaxed

            return [reward_line_values]

        discount_factor = min(1, (max_discount / discountable)) if discountable else 1
        reward_dict = {}
        for tax, price in discountable_per_tax.items():
            if not price:
                continue
            mapped_taxes = self.fiscal_position_id.map_tax(tax)
            tax_desc = ''
            if len(discountable_per_tax) > 1 and any(t.name for t in mapped_taxes):
                tax_desc = _(
                    ' - On products with the following taxes: %(taxes)s',
                    taxes=", ".join(mapped_taxes.mapped('name')),
                )
            reward_dict[tax] = {
                **base_reward_line_values,
                'name': _(
                    'Discount %(desc)s%(tax_str)s',
                    desc=reward.description,
                    tax_str=tax_desc,
                ) if mapped_taxes else reward.description,
                'price_unit': -(price * discount_factor),
                'points_cost': 0,
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
        today = fields.Date.context_today(self)
        return [('active', '=', True), ('sale_ok', '=', True),
                *self.env['loyalty.program']._check_company_domain([self.company_id.id, self.company_id.parent_id.id]),
                '|', ('pricelist_ids', '=', False), ('pricelist_ids', 'in', [self.pricelist_id.id]),
                '|', ('date_from', '=', False), ('date_from', '<=', today),
                '|', ('date_to', '=', False), ('date_to', '>=', today)]

    def _get_trigger_domain(self):
        """
        Returns the base domain that all triggers have to comply to.
        """
        self.ensure_one()
        today = fields.Date.context_today(self)
        return [('active', '=', True), ('program_id.sale_ok', '=', True),
                *self.env['loyalty.program']._check_company_domain([self.company_id.id, self.company_id.parent_id.id]),
                '|', ('program_id.pricelist_ids', '=', False),
                     ('program_id.pricelist_ids', 'in', [self.pricelist_id.id]),
                '|', ('program_id.date_from', '=', False), ('program_id.date_from', '<=', today),
                '|', ('program_id.date_to', '=', False), ('program_id.date_to', '>=', today)]

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
        if self.state == 'sale':
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

    def _update_loyalty_history(self, coupon_id, points):
        self.ensure_one()
        order_coupon_history = self.env['loyalty.history'].search([
            ('card_id', '=', coupon_id.id),
            ('order_model', '=', self._name),
            ('order_id', '=', self.id),
        ], limit=1)
        order_coupon_history.update({
            'used': order_coupon_history.used + points,
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

    def _best_global_discount_already_applied(self, current_reward, new_reward, discountable=None):
        """Determine whether current_reward is better than new_reward.

        This function compares the discount amount of two rewards to determine whether the current
        one is better than another one.

        Notes
        -----

            If the discount amounts of both the current and the new rewards exceed the order total,
            the reward with the smaller discount amount is considered the best.
            This is to ensure that the most advantageous discount is applied for the customer,
            who will keep the most important voucher, having saved the same amount in the end.

        :param loyalty.reward current_reward: The reward currently applied on the sale order.
        :param loyalty.reward new_reward: The reward to compare with.
        :param float discountable: The total discountable amount of the sale order.
            If not provided, it will be calculated on the fly.
        :return: True if current_reward is considered better than new_reward.
        :rtype: bool
        """
        self.ensure_one()
        current_reward.ensure_one()
        new_reward.ensure_one()

        if current_reward == new_reward:
            return True

        if discountable is None:  # Only recompute if discountable is not given, not if its zero
            discountable = self._discountable_amount(current_reward)

        def compute_discount(reward, discountable):
            """Compute the discount amount for the given reward, w.r.t. the discountable amount.

            :param loyalty.reward reward: The reward for which to calculate the maximum discount.
            :param float discountable: The total discountable amount of the sale order.
            :return: The maximum discount amount.
            :rtype: float
            """
            if reward.discount_mode == 'per_order':
                return reward.currency_id._convert(
                    from_amount=reward.discount,
                    to_currency=self.currency_id,
                    company=self.company_id,
                    date=fields.Date.today(),
                )
            elif reward.discount_mode == 'percent':
                return discountable * (reward.discount / 100)

        discount_current_reward = compute_discount(current_reward, discountable)
        discount_new_reward = compute_discount(new_reward, discountable)

        discount_current_bigger_than_discountable = self.currency_id.compare_amounts(
            amount1=discount_current_reward,
            amount2=discountable,
        ) >= 0
        discount_new_bigger_than_discountable = self.currency_id.compare_amounts(
            amount1=discount_new_reward,
            amount2=discountable,
        ) >= 0
        compare_current_and_new_reward = self.currency_id.compare_amounts(
            amount1=discount_current_reward,
            amount2=discount_new_reward,
        )

        if discount_current_bigger_than_discountable and discount_new_bigger_than_discountable:
            # If both discounts are greater than the discountable amount, the lower discount
            # is better as it reduces the discount amount 'spent' by the customer.
            return compare_current_and_new_reward <= 0

        # Return True only if the discount of the new reward is greater than the current reward
        # discount.
        return compare_current_and_new_reward >= 0

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
            if (
                global_discount_reward
                and global_discount_reward != reward
                and self._best_global_discount_already_applied(global_discount_reward, reward)
            ):
                return {'error': _("A better global discount is already applied.")}
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
        global_discount_reward = self._get_applied_global_discount()
        active_products_domain = self.env['loyalty.reward']._get_active_products_domain()
        discountable = lazy(lambda: self._discountable_amount(global_discount_reward))

        total_is_zero = self.currency_id.is_zero(discountable)
        result = defaultdict(lambda: self.env['loyalty.reward'])
        for coupon in all_coupons:
            points = self._get_real_points_for_coupon(coupon)
            for reward in coupon.program_id.reward_ids:
                if (
                    reward.is_global_discount
                    and global_discount_reward
                    and self._best_global_discount_already_applied(
                        global_discount_reward, reward, discountable
                    )
                ):
                    continue
                # Discounts are not allowed if the total is zero unless there is a payment reward, in which case we allow discounts.
                # If the total is 0 again without the payment reward it will be removed.
                is_discount = reward.reward_type == 'discount'
                is_payment_program = reward.program_id.is_payment_program
                if is_discount and total_is_zero and (not has_payment_reward or is_payment_program):
                    continue
                # Skip discount that has already been applied if not part of a payment program
                if is_discount and not is_payment_program and reward in self.order_line.reward_id:
                    continue
                if reward.reward_type == 'product' and not reward.filtered_domain(
                    active_products_domain
                ):
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

    def _get_order_line_price(self, order_line, price_type):
        return sum(self._get_order_lines_with_price(order_line).mapped(price_type))

    @staticmethod
    def _get_order_lines_with_price(order_line):
        return order_line.linked_line_ids if order_line.product_type == 'combo' else order_line

    def _program_check_compute_points(self, programs):
        """
        Checks the program validity from the order lines aswell as computing the number of points to add.

        Returns a dict containing the error message or the points that will be given with the keys 'points'.
        """
        self.ensure_one()

        # Prepare quantities
        order_lines = self._get_not_rewarded_order_lines().filtered(
            lambda line: not line.combo_item_id
        )
        products = order_lines.product_id
        products_qties = dict.fromkeys(products, 0)
        for line in order_lines:
            products_qties[line.product_id] += line.product_uom_qty
        # Contains the products that can be applied per rule
        products_per_rule = programs._get_valid_products(products)

        # Prepare amounts
        so_products_per_rule = programs._get_valid_products(self.order_line.product_id)
        lines_per_rule = defaultdict(lambda: self.env['sale.order.line'])
        # Skip lines that have no effect on the minimum amount to reach.
        for line in self.order_line - self._get_no_effect_on_threshold_lines():
            is_discount = line.reward_id.reward_type == 'discount'
            reward_program = line.reward_id.program_id
            # Skip lines for automatic discounts, as well as combo item lines.
            if (is_discount and reward_program.trigger == 'auto') or line.combo_item_id:
                continue
            for program in programs:
                # Skip lines for the current program's discounts.
                if is_discount and reward_program == program:
                    continue
                for rule in program.rule_ids:
                    # Skip lines to which the rule doesn't apply.
                    if line.product_id in so_products_per_rule.get(rule, []):
                        lines_per_rule[rule] |= self._get_order_lines_with_price(line)

        result = {}
        for program in programs:
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
                # prevent bottomless ewallet spending
                if program.program_type == 'ewallet' and not program.trigger_product_ids:
                    break
                if rule.mode == 'with_code' and rule not in self.code_enabled_rule_ids:
                    continue
                code_matched = True
                rule_amount = rule._compute_amount(self.currency_id)
                untaxed_amount = sum(lines_per_rule[rule].mapped('price_subtotal'))
                tax_amount = sum(lines_per_rule[rule].mapped('price_tax'))
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
                            if (
                                line.is_reward_line
                                or line.combo_item_id
                                or line.product_id not in rule_products
                                or line.product_uom_qty <= 0
                            ):
                                continue
                            line_price_total = self._get_order_line_price(line, 'price_total')
                            points_per_unit = float_round(
                                (rule.reward_point_amount * line_price_total / line.product_uom_qty),
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
                        # NOTE: this accounts for discounts -> 1 point per $ * (100$ - 30%) will
                        # result in 70 points
                        amount_paid = 0.0
                        rule_products = so_products_per_rule.get(rule, [])
                        for line in self.order_line - self._get_no_effect_on_threshold_lines():
                            if line.combo_item_id or line.reward_id.program_id.program_type in [
                                'ewallet', 'gift_card', program.program_type
                            ]:
                                continue
                            line_price_total = self._get_order_line_price(line, 'price_total')
                            amount_paid += (
                                line_price_total if line.product_id in rule_products
                                else 0.0
                            )

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
            elif self.partner_id.is_public and not self._allow_nominative_programs():
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
                if program.is_nominative or program.program_type == 'next_order_coupons':
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
            return {'error': _('This program is already applied to this order.'), 'already_applied': True}
        elif program.reward_ids:
            global_reward = program.reward_ids.filtered('is_global_discount')
            applied_global_reward = self._get_applied_global_discount()
            if (
                global_reward
                and applied_global_reward
                and self._best_global_discount_already_applied(applied_global_reward, global_reward)
            ):
                return {'error': _(
                    'This discount (%(discount)s) is not compatible with "%(other_discount)s". '
                    'Please remove it in order to apply this one.',
                    discount=global_reward.description,
                    other_discount=applied_global_reward.program_id.reward_ids.description,
                )}
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
        elif (program.limit_usage and program.total_order_count >= program.max_usage):
            return {'error': _('This code is expired (%s).', code)}
        elif program.program_type in ('loyalty', 'ewallet'):
            return {'error': _("This program cannot be applied with code.")}

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
                if coupon and not apply_result.get('already_applied', False):
                    self.applied_coupon_ids -= coupon
                return apply_result
            coupon = apply_result.get('coupon', self.env['loyalty.card'])
        return self._get_claimable_rewards(forced_coupons=coupon)

    def _validate_order(self):
        """
        Override of sale to create invoice for zero amount order. If the order total is zero and
        automatic invoicing is enabled, it creates and posts an invoice.

        :return: None
        """
        super()._validate_order()
        if self.amount_total or not self.reward_amount:
            return
        auto_invoice = self.env['ir.config_parameter'].get_param('sale.automatic_invoice')
        if str2bool(auto_invoice):
            # create an invoice for order with zero total amount and automatic invoice enabled
            self._force_lines_to_invoice_policy_order()
            invoice = self._create_invoices(final=True)
            invoice.action_post()
