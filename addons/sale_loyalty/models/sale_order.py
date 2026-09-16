import itertools
import random
from collections import defaultdict
from functools import partial

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs.datetime import timezone
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_round, lazy, str2bool

_debug = DebugLog(__name__)


def _generate_random_reward_code():
    return str(random.getrandbits(32))


class SaleOrder(models.Model):
    _inherit = "sale.order"

    applied_coupon_ids = fields.Many2many(
        comodel_name="loyalty.card",
        string="Manually Applied Coupons",
        copy=False,
    )
    code_enabled_rule_ids = fields.Many2many(
        comodel_name="loyalty.rule",
        string="Manually Triggered Rules",
        copy=False,
    )
    coupon_point_ids = fields.One2many(
        comodel_name="sale.order.coupon.points",
        inverse_name="order_id",
        copy=False,
    )
    reward_amount = fields.Float(compute="_compute_reward_amount")

    gift_card_count = fields.Integer(compute="_compute_gift_card_count")
    loyalty_data = fields.Json(compute="_compute_loyalty_data")

    @api.depends("line_ids")
    def _compute_reward_amount(self):
        for order in self:
            reward_amount = 0
            for line in order.line_ids:
                if not line.reward_id:
                    continue
                if line.reward_id.reward_type != "product":
                    reward_amount += line.price_subtotal
                else:
                    reward_amount -= line.product_id.lst_price * line.product_uom_qty
            order.reward_amount = reward_amount

    def _compute_loyalty_data(self):
        self.loyalty_data = {}

        confirmed_so = self.filtered(
            lambda order: order.state == "done" and bool(order.id)
        )
        if not confirmed_so:
            return

        loyalty_history_data = (
            self.env["loyalty.history"]
            .sudo()
            ._read_group(
                domain=[
                    ("order_id", "in", confirmed_so.ids),
                    ("order_model", "=", self._name),
                ],
                groupby=["order_id"],
                aggregates=["issued:sum", "used:sum"],
            )
        )
        loyalty_history_data_per_order = {
            order_id: {
                "total_issued": issued,
                "total_cost": cost,
            }
            for order_id, issued, cost in loyalty_history_data
        }
        for order in confirmed_so:
            if order.id not in loyalty_history_data_per_order:
                continue
            coupons = order.coupon_point_ids.coupon_id
            coupon_point_name = (len(coupons) == 1 and coupons.point_name) or _(
                "Points"
            )
            order.loyalty_data = {
                "point_name": coupon_point_name,
                "issued": loyalty_history_data_per_order[order.id]["total_issued"],
                "cost": loyalty_history_data_per_order[order.id]["total_cost"],
            }

    def _compute_gift_card_count(self):
        gift_card_data = dict(
            self.env["loyalty.card"]._read_group(
                domain=[
                    ("order_id", "in", self.ids),
                    ("program_type", "=", "gift_card"),
                ],
                groupby=["order_id"],
                aggregates=["__count"],
            )
        )
        for order in self:
            order.gift_card_count = gift_card_data.get(order, 0)

    def _add_loyalty_history_lines(self):
        self.check_singleton()
        points_per_coupon = defaultdict(partial(defaultdict, int))
        for coupon_point in self.coupon_point_ids:
            points_per_coupon[coupon_point.coupon_id]["issued"] = coupon_point.points
        for line in self.line_ids:
            if not line.coupon_id:
                continue
            points_per_coupon[line.coupon_id]["cost"] += line.points_cost

        create_values = []
        base_values = {
            "order_id": self.id,
            "order_model": self._name,
            "description": _("Order %s", self.display_name),
        }
        for coupon, point_dict in points_per_coupon.items():
            cost = point_dict.get("cost", 0.0)
            issued = point_dict.get("issued", 0.0)
            create_values.append(
                {
                    **base_values,
                    "card_id": coupon.id,
                    "used": cost,
                    "issued": issued,
                }
            )

        self.env["loyalty.history"].create(create_values)

    def _get_no_effect_on_threshold_lines(self):
        self.check_singleton()
        return self.env["sale.order.line"]

    def copy(self, default=None):
        new_orders = super().copy(default)
        reward_lines = new_orders.line_ids.filtered("is_reward_line")
        if reward_lines:
            reward_lines.unlink()
        return new_orders

    def action_confirm(self):
        for order in self:
            all_coupons = (
                order.applied_coupon_ids
                | order.coupon_point_ids.coupon_id
                | order.line_ids.coupon_id
            )
            if any(
                order._get_real_points_for_coupon(coupon) < 0 for coupon in all_coupons
            ):
                _debug.logic(
                    "confirm_refused",
                    order=order,
                    reason="negative_coupon_points",
                    coupons=all_coupons,
                )
                raise ValidationError(
                    _(
                        "One or more rewards on the sale order is invalid. Please check them."
                    )
                )
            order._update_programs_and_rewards()
            order._add_loyalty_history_lines()
        has_claimable_rewards = len(self) == 1 and bool(self._get_claimable_rewards())

        reward_coupons = self.line_ids.coupon_id
        self.coupon_point_ids.filtered(
            lambda pe: (
                pe.coupon_id.program_id.applies_on == "current"
                and pe.coupon_id not in reward_coupons
            )
        ).coupon_id.sudo().unlink()
        for coupon, change in (
            self.filtered(lambda s: s.state != "done")._get_point_changes().items()
        ):
            _debug.lifecycle(
                "coupon_points_applied", coupon=coupon, change=change, orders=self
            )
            coupon.points += change
        res = super().action_confirm()
        if isinstance(res, bool) and has_claimable_rewards:
            _debug.logic("claimable_rewards_notice", orders=self)
            res = {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "info",
                    "title": _("Rewards Available"),
                    "message": _(
                        "There are available rewards not added to this order."
                    ),
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }
        self._send_reward_coupon_mail()
        return res

    def _action_cancel(self):
        previously_confirmed = self.filtered(lambda s: s.state == "done")
        res = super()._action_cancel()

        order_history_lines = self.env["loyalty.history"].search(
            [
                ("order_model", "=", self._name),
                ("order_id", "in", previously_confirmed.ids),
            ]
        )
        if order_history_lines:
            _debug.lifecycle(
                "loyalty_history_removed", orders=self, lines=order_history_lines
            )
            order_history_lines.sudo().unlink()

        for coupon, changes in (
            previously_confirmed.filtered(lambda s: s.state != "done")
            ._get_point_changes()
            .items()
        ):
            _debug.lifecycle(
                "coupon_points_reverted", coupon=coupon, change=changes, orders=self
            )
            coupon.points -= changes
        self.line_ids.filtered(lambda l: l.is_reward_line).unlink()
        self.coupon_point_ids.coupon_id.sudo().filtered(
            lambda c: (
                not c.program_id.is_nominative
                and c.order_id in self
                and not c.use_count
            )
        ).unlink()
        self.coupon_point_ids.unlink()
        return res

    def action_view_reward_wizard(self):
        self.check_singleton()
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
        return self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "sale_loyalty.sale_loyalty_reward_wizard_action"
        )

    def action_view_gift_cards(self):
        self.check_singleton()
        return {
            "name": _("Gift Cards"),
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": "loyalty.card",
            "domain": [("order_id", "=", self.id), ("program_type", "=", "gift_card")],
            "context": {"create": False},
        }

    def _send_reward_coupon_mail(self):
        coupons = self.env["loyalty.card"]
        for order in self:
            coupons |= order._get_reward_coupons()
        if coupons:
            coupons._send_creation_communication(force_send=True)

    def _get_applied_global_discount_lines(self):
        self.check_singleton()
        return self.line_ids.filtered(lambda l: l.reward_id.is_global_discount)

    def _get_applied_global_discount(self):
        return self._get_applied_global_discount_lines().reward_id

    def _get_reward_values_product(self, reward, coupon, product=None, **kwargs):
        self.check_singleton()
        assert reward.reward_type == "product"

        reward_products = reward.reward_product_ids
        product = product or reward_products[:1]
        if not product or product not in reward_products:
            _debug.logic("reward_product_rejected", order=self, reward=reward)
            raise UserError(_("Invalid product to claim."))
        taxes = self.fiscal_position_id.map_tax(
            product.taxes_id._filter_taxes_by_company(self.company_id)
        )
        points = self._get_real_points_for_coupon(coupon)
        claimable_count = (
            float_round(
                points / reward.required_points,
                precision_rounding=1,
                rounding_method="DOWN",
            )
            if not reward.clear_wallet
            else 1
        )
        cost = (
            points if reward.clear_wallet else claimable_count * reward.required_points
        )
        return [
            {
                "name": reward.description,
                "product_id": product.id,
                "discount": 100,
                "product_qty": reward.reward_product_qty * claimable_count,
                "reward_id": reward.id,
                "coupon_id": coupon.id,
                "points_cost": cost,
                "reward_identifier_code": _generate_random_reward_code(),
                "sequence": max(
                    self.line_ids.filtered(lambda x: not x.is_reward_line).mapped(
                        "sequence"
                    ),
                    default=10,
                )
                + 1,
                "tax_ids": [Command.clear()] + [Command.link(tax.id) for tax in taxes],
            }
        ]

    def _discountable_amount(self, rewards_to_ignore):
        self.check_singleton()

        discountable = 0

        for line in self.line_ids - self._get_no_effect_on_threshold_lines():
            if rewards_to_ignore and line.reward_id in rewards_to_ignore:
                continue
            if not line.product_qty or not line.price_unit:
                continue
            tax_data = line.tax_ids.compute_all(
                line.price_unit,
                quantity=line.product_qty,
                product=line.product_id,
                partner=line.partner_id,
            )
            taxes = line.tax_ids.filtered(lambda t: t.amount_type != "fixed")
            discountable += tax_data["total_excluded"] + sum(
                tax["amount"] for tax in tax_data["taxes"] if tax["id"] in taxes.ids
            )
        return discountable

    def _discountable_order(self, reward):
        self.check_singleton()
        reward.check_singleton()
        assert reward.discount_applicability == "order"

        lines = self.line_ids.filtered(lambda line: not line.display_type)
        if not reward.program_id.is_payment_program:
            lines -= self._get_no_effect_on_threshold_lines()
        else:
            top_up_products = reward.program_id.trigger_product_ids
            lines -= lines.filtered(lambda line: line.product_id in top_up_products)

        discountable = 0
        discountable_per_tax = defaultdict(float)

        AccountTax = self.env["account.tax"]
        base_lines = []
        for line in lines:
            base_line = line._prepare_base_line_for_taxes_computation()
            taxes = base_line["tax_ids"]
            discountable_taxes = base_line["tax_ids"].flatten_taxes_hierarchy()
            if not reward.program_id.is_payment_program:
                taxes = taxes.filtered(lambda t: t.amount_type != "fixed")
                discountable_taxes = discountable_taxes.filtered(
                    lambda t: t.amount_type != "fixed"
                )
            base_line["discount_taxes"] = taxes
            base_line["discountable_taxes"] = discountable_taxes
            base_lines.append(base_line)
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id)

        def grouping_function(base_line, tax_data):
            if not tax_data:
                return None
            return {
                "taxes": base_line["discount_taxes"],
                "skip": (
                    tax_data["tax"] not in base_line["discountable_taxes"]
                    or base_line["record"] not in lines
                ),
            }

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(
            base_lines, grouping_function
        )
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        )
        for grouping_key, values in values_per_grouping_key.items():
            if grouping_key and grouping_key["skip"]:
                continue

            taxes = grouping_key["taxes"] if grouping_key else self.env["account.tax"]
            discountable += (
                values["raw_base_amount_currency"] + values["raw_tax_amount_currency"]
            )
            discountable_per_tax[taxes] += values["raw_base_amount_currency"] + sum(
                tax_data["raw_tax_amount_currency"]
                for base_line, taxes_data in values["base_line_x_taxes_data"]
                for tax_data in taxes_data
                if tax_data["tax"].price_include
            )
        return discountable, discountable_per_tax

    def _cheapest_line(self, reward):
        self.check_singleton()
        cheapest_line = False
        cheapest_line_price_unit = False
        domain = reward._get_domain_discount_product()
        for line in self.line_ids - self._get_no_effect_on_threshold_lines():
            line_price_unit = self._get_order_line_price(line, "price_unit")
            if (
                line.reward_id
                or line.combo_item_id
                or not line.product_qty
                or not line_price_unit
                or not line.product_id.filtered_domain(domain)
            ):
                continue
            if not cheapest_line or cheapest_line_price_unit > line_price_unit:
                cheapest_line = line._get_lines_with_price()
                cheapest_line_price_unit = line_price_unit
        return cheapest_line

    def _discountable_cheapest(self, reward):
        self.check_singleton()
        assert reward.discount_applicability == "cheapest"

        cheapest_line = self._cheapest_line(reward)
        if not cheapest_line:
            return False, False

        discountable = 0
        discountable_per_tax = defaultdict(int)
        for line in cheapest_line:
            discountable += line.price_total / line.product_qty
            taxes = line.tax_ids.filtered(lambda t: t.amount_type != "fixed")
            discountable_per_tax[taxes] += line.price_unit * (
                1 - (line.discount or 0) / 100
            )

        return discountable, discountable_per_tax

    def _get_specific_discountable_lines(self, reward):
        self.check_singleton()
        assert reward.discount_applicability == "specific"

        discountable_lines = self.env["sale.order.line"]
        for line in self.line_ids - self._get_no_effect_on_threshold_lines():
            domain = reward._get_domain_discount_product()
            if (
                not line.reward_id
                and not line.combo_item_id
                and line.product_id.filtered_domain(domain)
            ):
                discountable_lines |= line._get_lines_with_price()
        return discountable_lines

    def _discountable_specific(self, reward):
        self.check_singleton()
        assert reward.discount_applicability == "specific"

        lines_to_discount = self._get_specific_discountable_lines(reward).filtered(
            lambda line: bool(line.product_qty and line.price_total)
        )
        discount_lines = defaultdict(lambda: self.env["sale.order.line"])
        order_lines = self.line_ids - self._get_no_effect_on_threshold_lines()
        remaining_amount_per_line = defaultdict(int)
        for line in order_lines:
            if not line.product_qty or not line.price_total:
                continue
            remaining_amount_per_line[line] = line.price_total
            if line.reward_id.reward_type == "discount":
                discount_lines[line.reward_identifier_code] |= line

        order_lines -= self.line_ids.filtered("reward_id")
        cheapest_line = False
        for lines in discount_lines.values():
            line_reward = lines.reward_id
            discounted_lines = order_lines
            if line_reward.discount_applicability == "cheapest":
                cheapest_line = cheapest_line or self._cheapest_line(line_reward)
                discounted_lines = cheapest_line
            elif line_reward.discount_applicability == "specific":
                discounted_lines = self._get_specific_discountable_lines(line_reward)
            if not discounted_lines:
                continue
            common_lines = discounted_lines & lines_to_discount
            if line_reward.discount_mode == "percent":
                for line in discounted_lines:
                    if line_reward.discount_applicability == "cheapest":
                        remaining_amount_per_line[line] *= (
                            1 - line_reward.discount / 100 / line.product_qty
                        )
                    else:
                        remaining_amount_per_line[line] *= (
                            1 - line_reward.discount / 100
                        )
            else:
                non_common_lines = discounted_lines - lines_to_discount
                discounted_amounts = defaultdict(
                    int,
                    {
                        sol.tax_ids.filtered(lambda t: t.amount_type != "fixed"): abs(
                            sol.price_total
                        )
                        for sol in lines
                    },
                )
                for line in itertools.chain(non_common_lines, common_lines):
                    if lines.reward_id.program_id.is_payment_program:
                        discounted_amount = discounted_amounts[
                            lines.tax_ids.filtered(lambda t: t.amount_type != "fixed")
                        ]
                    else:
                        discounted_amount = discounted_amounts[
                            line.tax_ids.filtered(lambda t: t.amount_type != "fixed")
                        ]
                    if discounted_amount == 0:
                        continue
                    remaining = remaining_amount_per_line[line]
                    consumed = min(remaining, discounted_amount)
                    if lines.reward_id.program_id.is_payment_program:
                        discounted_amounts[
                            lines.tax_ids.filtered(lambda t: t.amount_type != "fixed")
                        ] -= consumed
                    else:
                        discounted_amounts[
                            line.tax_ids.filtered(lambda t: t.amount_type != "fixed")
                        ] -= consumed
                    remaining_amount_per_line[line] -= consumed

        discountable = 0
        discountable_per_tax = defaultdict(int)
        for line in lines_to_discount:
            discountable += remaining_amount_per_line[line]
            line_discountable = (
                line.price_unit
                * line.product_qty
                * (1 - (line.discount or 0.0) / 100.0)
            )
            taxes = line.tax_ids.filtered(lambda t: t.amount_type != "fixed")
            discountable_per_tax[taxes] += line_discountable * (
                remaining_amount_per_line[line] / line.price_total
            )
        return discountable, discountable_per_tax

    def _get_reward_values_discount(self, reward, coupon, **kwargs):
        self.check_singleton()
        assert reward.reward_type == "discount"

        reward_applies_on = reward.discount_applicability
        reward_product = reward.discount_line_product_id
        reward_program = reward.program_id
        reward_currency = reward.currency_id
        sequence = (
            max(
                self.line_ids.filtered(lambda x: not x.is_reward_line).mapped(
                    "sequence"
                ),
                default=10,
            )
            + 1
        )
        base_reward_line_values = {
            "product_id": reward_product.id,
            "product_qty": 1.0,
            "tax_ids": [Command.clear()],
            "name": reward.description,
            "reward_id": reward.id,
            "coupon_id": coupon.id,
            "sequence": sequence,
            "reward_identifier_code": _generate_random_reward_code(),
        }

        discountable = 0
        discountable_per_tax = defaultdict(int)
        if reward_applies_on == "order":
            discountable, discountable_per_tax = self._discountable_order(reward)
        elif reward_applies_on == "specific":
            discountable, discountable_per_tax = self._discountable_specific(reward)
        elif reward_applies_on == "cheapest":
            discountable, discountable_per_tax = self._discountable_cheapest(reward)

        if not discountable:
            if not reward_program.is_payment_program and any(
                line.reward_id.program_id.is_payment_program for line in self.line_ids
            ):
                return [
                    {
                        **base_reward_line_values,
                        "name": _("TEMPORARY DISCOUNT LINE"),
                        "price_unit": 0,
                        "product_qty": 0,
                        "points_cost": 0,
                    }
                ]
            _debug.logic("discount_refused", order=self, reason="nothing_to_discount")
            raise UserError(_("There is nothing to discount"))

        max_discount = reward_currency._convert(
            reward.discount_max_amount,
            self.currency_id,
            self.company_id,
            fields.Date.today(),
        ) or float("inf")
        max_discount = min(self.amount_total, max_discount)
        if reward.discount_mode == "per_point":
            points = self._get_real_points_for_coupon(coupon)
            if not reward_program.is_payment_program:
                points = points // reward.required_points * reward.required_points
            max_discount = min(
                max_discount,
                reward_currency._convert(
                    reward.discount * points,
                    self.currency_id,
                    self.company_id,
                    fields.Date.today(),
                ),
            )
        elif reward.discount_mode == "per_order":
            max_discount = min(
                max_discount,
                reward_currency._convert(
                    reward.discount,
                    self.currency_id,
                    self.company_id,
                    fields.Date.today(),
                ),
            )
        elif reward.discount_mode == "percent":
            max_discount = min(max_discount, discountable * (reward.discount / 100))

        point_cost = (
            reward.required_points
            if not reward.clear_wallet
            else self._get_real_points_for_coupon(coupon)
        )
        if reward.discount_mode == "per_point" and not reward.clear_wallet:
            converted_discount = self.currency_id._convert(
                min(max_discount, discountable),
                reward_currency,
                self.company_id,
                fields.Date.today(),
            )
            point_cost = coupon.currency_id.round(converted_discount / reward.discount)

        if reward_program.is_payment_program:
            reward_line_values = {
                **base_reward_line_values,
                "price_unit": -min(max_discount, discountable),
                "points_cost": point_cost,
            }

            if reward_program.program_type == "gift_card":
                taxes_to_apply = reward_product.taxes_id._filter_taxes_by_company(
                    self.company_id
                )
                if taxes_to_apply:
                    mapped_taxes = self.fiscal_position_id.map_tax(taxes_to_apply)
                    price_incl_taxes = mapped_taxes.filtered("price_include")
                    tax_res = mapped_taxes.with_context(
                        force_price_include=True,
                        round=False,
                        round_base=False,
                    ).compute_all(
                        reward_line_values["price_unit"],
                        currency=self.currency_id,
                    )
                    new_price = tax_res["total_excluded"]
                    new_price += sum(
                        tax_data["amount"]
                        for tax_data in tax_res["taxes"]
                        if tax_data["id"] in price_incl_taxes.ids
                    )
                    reward_line_values.update(
                        {
                            "price_unit": new_price,
                            "tax_ids": [Command.set(mapped_taxes.ids)],
                        }
                    )
            return [reward_line_values]

        discount_factor = min(1, (max_discount / discountable)) if discountable else 1
        reward_dict = {}
        for tax, price in discountable_per_tax.items():
            if not price:
                continue
            mapped_taxes = self.fiscal_position_id.map_tax(tax)
            tax_desc = ""
            if len(discountable_per_tax) > 1 and any(t.name for t in mapped_taxes):
                tax_desc = _(
                    " - On products with the following taxes: %(taxes)s",
                    taxes=", ".join(mapped_taxes.mapped("name")),
                )
            reward_dict[tax] = {
                **base_reward_line_values,
                "name": _(
                    "Discount %(desc)s%(tax_str)s",
                    desc=reward.description,
                    tax_str=tax_desc,
                )
                if mapped_taxes
                else reward.description,
                "price_unit": -(price * discount_factor),
                "points_cost": 0,
                "tax_ids": [Command.clear()]
                + [Command.link(tax.id) for tax in mapped_taxes],
            }
        if reward_dict:
            reward_dict[next(iter(reward_dict))]["points_cost"] = point_cost
        return list(reward_dict.values())

    def _get_domain_program(self):
        self.check_singleton()
        today = self._get_confirmed_tx_create_date()
        return [
            ("active", "=", True),
            ("sale_ok", "=", True),
            *self.env["loyalty.program"]._check_company_domain(
                [self.company_id.id, self.company_id.parent_id.id]
            ),
            "|",
            ("pricelist_ids", "=", False),
            ("pricelist_ids", "in", [self.pricelist_id.id]),
            "|",
            ("date_from", "=", False),
            ("date_from", "<=", today),
            "|",
            ("date_to", "=", False),
            ("date_to", ">=", today),
        ]

    def _get_domain_trigger(self):
        self.check_singleton()
        today = self._get_confirmed_tx_create_date()
        return [
            ("active", "=", True),
            ("program_id.sale_ok", "=", True),
            *self.env["loyalty.program"]._check_company_domain(
                [self.company_id.id, self.company_id.parent_id.id]
            ),
            "|",
            ("program_id.pricelist_ids", "=", False),
            ("program_id.pricelist_ids", "in", [self.pricelist_id.id]),
            "|",
            ("program_id.date_from", "=", False),
            ("program_id.date_from", "<=", today),
            "|",
            ("program_id.date_to", "=", False),
            ("program_id.date_to", ">=", today),
        ]

    def _get_program_timezone(self):
        self.check_singleton()
        return self.company_id.partner_id.tz or self.env[
            "ir.config_parameter"
        ].sudo().get_param("loyalty.timezone", "UTC")

    def _get_confirmed_tx_create_date(self):
        self.check_singleton()
        order_tz = self._get_program_timezone()
        confirmed_txs_dates = (
            self.sudo()
            .transaction_ids.filtered(
                lambda tx: tx.state in ("done", "authorized"),
            )
            .mapped("create_date")
        )
        if confirmed_txs_dates:
            tx_date = min(confirmed_txs_dates)
            return tx_date.astimezone(timezone(order_tz)).date()
        return fields.Date.context_today(self.with_context(tz=order_tz))

    def _get_applicable_program_points(self, domain=None):
        self.check_singleton()
        if not domain:
            domain = [("trigger", "=", "auto")]
        domain = Domain.AND([self._get_domain_program(), domain])
        programs = self.env["loyalty.program"].search(domain)
        all_status = self._program_check_compute_points(programs)
        return {
            p: status["points"][0]
            for p, status in all_status.items()
            if "points" in status
        }

    def _get_points_programs(self):
        self.check_singleton()
        return self.coupon_point_ids.filtered("points").coupon_id.program_id

    def _get_reward_programs(self):
        self.check_singleton()
        return self.line_ids.reward_id.program_id

    def _get_reward_coupons(self):
        self.check_singleton()
        return self.coupon_point_ids.filtered("points").coupon_id.filtered(
            lambda c: c.program_id.applies_on == "future",
        )

    def _get_applied_programs(self):
        self.check_singleton()
        return self._get_points_programs() | self._get_reward_programs()

    def _recompute_prices(self):
        super()._recompute_prices()
        for order in self:
            if any(line.is_reward_line for line in order.line_ids):
                order._update_programs_and_rewards()

    def _get_point_changes(self):
        points_per_coupon = defaultdict(lambda: 0)
        for coupon_point in self.coupon_point_ids:
            points_per_coupon[coupon_point.coupon_id] += coupon_point.points
        for line in self.line_ids:
            if not line.reward_id or not line.coupon_id:
                continue
            points_per_coupon[line.coupon_id] -= line.points_cost
        return points_per_coupon

    def _get_real_points_for_coupon(self, coupon, post_confirm=False):
        self.check_singleton()
        points = coupon.points
        if self.state != "done":
            if coupon.program_id.applies_on != "future":
                points += self.coupon_point_ids.filtered(
                    lambda p: p.coupon_id == coupon
                ).points
            points -= sum(
                self.line_ids.filtered(lambda l: l.coupon_id == coupon).mapped(
                    "points_cost"
                )
            )
        if any(
            rule.reward_point_mode == "money" for rule in coupon.program_id.rule_ids
        ):
            points = coupon.currency_id.round(points)
        return points

    def _add_points_for_coupon(self, coupon_points):
        self.check_singleton()
        if self.state == "done":
            for coupon, points in coupon_points.items():
                coupon.sudo().points += points
        for pe in self.coupon_point_ids.sudo():
            if pe.coupon_id in coupon_points:
                pe.points = coupon_points.pop(pe.coupon_id)
        if coupon_points:
            self.sudo().with_context(tracking_disable=True).write(
                {
                    "coupon_point_ids": [
                        (
                            0,
                            0,
                            {
                                "coupon_id": coupon.id,
                                "points": points,
                            },
                        )
                        for coupon, points in coupon_points.items()
                    ]
                }
            )

    def _update_loyalty_history(self, coupon_id, points):
        self.check_singleton()
        order_coupon_history = self.env["loyalty.history"].search(
            [
                ("card_id", "=", coupon_id.id),
                ("order_model", "=", self._name),
                ("order_id", "=", self.id),
            ],
            limit=1,
        )
        if order_coupon_history:
            order_coupon_history.update(
                {
                    "used": order_coupon_history.used + points,
                }
            )
        else:
            issued = self.coupon_point_ids.filtered(
                lambda p: p.coupon_id == coupon_id
            ).points
            self.env["loyalty.history"].create(
                {
                    "card_id": coupon_id.id,
                    "order_model": self._name,
                    "order_id": self.id,
                    "description": _("Order %s", self.display_name),
                    "issued": issued,
                    "used": points,
                }
            )

    def _remove_program_from_points(self, programs):
        self.coupon_point_ids.filtered(
            lambda p: p.coupon_id.program_id in programs
        ).sudo().unlink()

    def _get_reward_line_values(self, reward, coupon, **kwargs):
        self.check_singleton()
        self = self.with_context(lang=self._get_lang())
        reward = reward.with_context(lang=self._get_lang())
        if reward.reward_type == "discount":
            return self._get_reward_values_discount(reward, coupon, **kwargs)
        elif reward.reward_type == "product":
            return self._get_reward_values_product(reward, coupon, **kwargs)
        return None

    def _write_vals_from_reward_vals(self, reward_vals, old_lines, delete=True):
        self.check_singleton()
        command_list = []
        for vals, line in zip(reward_vals, old_lines, strict=False):
            if vals["product_id"] == line.product_id.id:
                vals["name"] = line.name
            command_list.append((Command.UPDATE, line.id, vals))
        if len(reward_vals) > len(old_lines):
            command_list.extend(
                (Command.CREATE, 0, vals) for vals in reward_vals[len(old_lines) :]
            )
        elif len(reward_vals) < len(old_lines) and delete:
            command_list.extend(
                (Command.DELETE, line.id) for line in old_lines[len(reward_vals) :]
            )
        self.write({"line_ids": command_list})
        return self.env["sale.order.line"] if delete else old_lines[len(reward_vals) :]

    def _best_global_discount_already_applied(
        self, current_reward, new_reward, discountable=None
    ):
        self.check_singleton()
        current_reward.check_singleton()
        new_reward.check_singleton()

        if current_reward == new_reward:
            return True

        if discountable is None:
            discountable = self._discountable_amount(current_reward)

        discount_current_reward = self._get_discount_amount(
            current_reward, discountable
        )
        discount_new_reward = self._get_discount_amount(new_reward, discountable)

        discount_current_bigger_than_discountable = (
            self.currency_id.compare_amounts(
                amount1=discount_current_reward,
                amount2=discountable,
            )
            >= 0
        )
        discount_new_bigger_than_discountable = (
            self.currency_id.compare_amounts(
                amount1=discount_new_reward,
                amount2=discountable,
            )
            >= 0
        )
        compare_current_and_new_reward = self.currency_id.compare_amounts(
            amount1=discount_current_reward,
            amount2=discount_new_reward,
        )

        if (
            discount_current_bigger_than_discountable
            and discount_new_bigger_than_discountable
        ):
            return compare_current_and_new_reward <= 0

        return compare_current_and_new_reward >= 0

    def _get_discount_amount(self, reward, discountable):
        if reward.discount_mode == "per_order":
            return reward.currency_id._convert(
                from_amount=reward.discount,
                to_currency=self.currency_id,
                company=self.company_id,
                date=fields.Date.today(),
            )
        elif reward.discount_mode == "percent":
            return discountable * (reward.discount / 100)
        return None

    def _apply_program_reward(self, reward, coupon, **kwargs):
        self.check_singleton()
        old_reward_lines = kwargs.get("old_lines", self.env["sale.order.line"])
        if reward.is_global_discount:
            global_discount_reward_lines = self._get_applied_global_discount_lines()
            global_discount_reward = global_discount_reward_lines.reward_id
            if (
                global_discount_reward
                and global_discount_reward != reward
                and self._best_global_discount_already_applied(
                    global_discount_reward, reward
                )
            ):
                return {"error": _("A better global discount is already applied.")}
            elif global_discount_reward and global_discount_reward != reward:
                global_discount_reward_lines._reset_loyalty(True)
                old_reward_lines |= global_discount_reward_lines
        if (
            not reward.program_id.is_nominative
            and reward.program_id.applies_on == "future"
            and coupon in self.coupon_point_ids.coupon_id
        ):
            return {"error": _("The coupon can only be claimed on future orders.")}
        elif self._get_real_points_for_coupon(coupon) < reward.required_points:
            return {
                "error": _(
                    "The coupon does not have enough points for the selected reward."
                )
            }
        reward_vals = self._get_reward_line_values(reward, coupon, **kwargs)
        self._write_vals_from_reward_vals(reward_vals, old_reward_lines)
        return {}

    def _get_claimable_rewards(self, forced_coupons=None):
        self.check_singleton()
        result = defaultdict(lambda: self.env["loyalty.reward"])

        check_date = self._get_confirmed_tx_create_date()

        all_coupons = forced_coupons or (
            self.coupon_point_ids.coupon_id
            | self.line_ids.coupon_id
            | self.applied_coupon_ids
        )
        if not all_coupons:
            return result

        has_payment_reward = any(
            line.reward_id.program_id.is_payment_program for line in self.line_ids
        )
        global_discount_reward = self._get_applied_global_discount()
        active_products_domain = self.env[
            "loyalty.reward"
        ]._get_domain_active_products()

        discountable = lazy(lambda: self._discountable_amount(global_discount_reward))
        total_is_zero = lazy(lambda: self.currency_id.is_zero(discountable))

        for coupon in all_coupons:
            if coupon.program_id.applies_on == "future" and coupon.order_id == self:
                continue
            if coupon.expiration_date and coupon.expiration_date < check_date:
                continue
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
                is_discount = reward.reward_type == "discount"
                is_payment_program = reward.program_id.is_payment_program
                if (
                    is_discount
                    and total_is_zero
                    and (not has_payment_reward or is_payment_program)
                ):
                    continue
                if (
                    is_discount
                    and not is_payment_program
                    and reward in self.line_ids.reward_id
                ):
                    continue
                if reward.reward_type == "product" and not reward.filtered_domain(
                    active_products_domain
                ):
                    continue
                if points >= reward.required_points:
                    result[coupon] |= reward
        return result

    def _allow_nominative_programs(self):
        self.check_singleton()
        return True

    def _update_programs_and_rewards(self):
        self.check_singleton()

        if self._allow_nominative_programs():
            loyalty_card = self.env["loyalty.card"].search(
                [
                    ("id", "not in", self.applied_coupon_ids.ids),
                    ("partner_id", "=", self.partner_id.id),
                    ("points", ">", 0),
                    "|",
                    ("program_id.program_type", "=", "ewallet"),
                    "&",
                    ("program_id.program_type", "=", "loyalty"),
                    ("program_id.applies_on", "!=", "current"),
                ]
            )
            if loyalty_card:
                self.applied_coupon_ids += loyalty_card
        points_programs = self._get_points_programs()
        coupon_programs = self.applied_coupon_ids.program_id
        program_domain = self._get_domain_program()
        domain = Domain.AND(
            [
                program_domain,
                [
                    ("id", "not in", points_programs.ids),
                    ("trigger", "=", "auto"),
                    ("rule_ids.mode", "=", "auto"),
                ],
            ]
        )
        automatic_programs = (
            self.env["loyalty.program"]
            .search(domain)
            .filtered(lambda p: not p.limit_usage or p.total_order_count < p.max_usage)
        )

        all_programs_to_check = points_programs | coupon_programs | automatic_programs
        all_coupons = self.coupon_point_ids.coupon_id | self.applied_coupon_ids
        domain_matching_programs = all_programs_to_check.filtered_domain(program_domain)
        all_programs_status = {
            p: {"error": "error"}
            for p in all_programs_to_check - domain_matching_programs
        }
        all_programs_status.update(
            self._program_check_compute_points(domain_matching_programs)
        )
        lines_to_unlink = self.env["sale.order.line"]
        coupons_to_unlink = self.env["loyalty.card"]
        point_entries_to_unlink = self.env["sale.order.coupon.points"]
        if initial_coupons := self.applied_coupon_ids:
            check_date = self._get_confirmed_tx_create_date()
            self.applied_coupon_ids = initial_coupons.filtered(
                lambda c: not c.expiration_date or c.expiration_date >= check_date,
            )
            removed = initial_coupons - self.applied_coupon_ids
            lines_to_unlink |= self.line_ids.filtered(
                lambda sol: sol.coupon_id in removed
            )
        point_ids_per_program = defaultdict(
            lambda: self.env["sale.order.coupon.points"]
        )
        for pe in self.coupon_point_ids:
            if pe.coupon_id.partner_id.is_public and not self.partner_id.is_public:
                pe.coupon_id.partner_id = self.partner_id
            if pe.coupon_id.partner_id and pe.coupon_id.partner_id != self.partner_id:
                pe.points = 0
                point_entries_to_unlink |= pe
            else:
                point_ids_per_program[pe.coupon_id.program_id] |= pe

        for program in points_programs:
            status = all_programs_status[program]
            program_point_entries = point_ids_per_program[program]
            if "error" in status:
                coupons_from_order = program_point_entries.coupon_id.filtered(
                    lambda c: c.order_id == self
                )
                all_coupons -= coupons_from_order
                program_reward_lines = self.line_ids.filtered(
                    lambda l: l.coupon_id in coupons_from_order  # noqa: B023  (consumed by filtered() in the same iteration)
                )
                program_reward_lines._reset_loyalty(True)
                lines_to_unlink |= program_reward_lines
                if not program.is_nominative:
                    coupons_to_unlink |= coupons_from_order
                else:
                    point_entries_to_unlink |= program_point_entries
                    point_entries_to_unlink.points = 0
                self.code_enabled_rule_ids -= program.rule_ids
            else:
                all_point_changes = [p for p in status["points"] if p]
                if not all_point_changes and program.is_nominative:
                    all_point_changes = [0]
                for pe, points in zip(
                    program_point_entries.sudo(), all_point_changes, strict=False
                ):
                    pe.points = points
                if len(program_point_entries) < len(all_point_changes):
                    new_coupon_points = all_point_changes[len(program_point_entries) :]
                    partner_id = (
                        program.program_type == "next_order_coupons"
                        and self.partner_id.id
                    )
                    new_coupons = (
                        self.env["loyalty.card"]
                        .with_context(loyalty_no_mail=True, tracking_disable=True)
                        .create(
                            [
                                {
                                    "program_id": program.id,
                                    "partner_id": partner_id,
                                    "points": 0,
                                    "order_id": self.id,
                                }
                                for _ in new_coupon_points
                            ]
                        )
                    )
                    self._add_points_for_coupon(
                        dict(zip(new_coupons, new_coupon_points, strict=True))
                    )
                elif len(program_point_entries) > len(all_point_changes):
                    point_ids_to_unlink = program_point_entries[
                        len(all_point_changes) :
                    ]
                    all_coupons -= point_ids_to_unlink.coupon_id
                    coupons_to_unlink |= point_ids_to_unlink.coupon_id
                    point_ids_to_unlink.points = 0

        applied_coupon_per_program = defaultdict(lambda: self.env["loyalty.card"])
        for coupon in self.applied_coupon_ids:
            applied_coupon_per_program[coupon.program_id] |= coupon
        for program in coupon_programs:
            if program not in domain_matching_programs or (
                program.applies_on == "current"
                and "error" in all_programs_status[program]
            ):
                program_reward_lines = self.line_ids.filtered(
                    lambda l: l.coupon_id in applied_coupon_per_program[program]  # noqa: B023  (consumed by filtered() in the same iteration)
                )
                program_reward_lines._reset_loyalty(True)
                lines_to_unlink |= program_reward_lines
                self.applied_coupon_ids -= applied_coupon_per_program[program]
                all_coupons -= applied_coupon_per_program[program]

        reward_line_pool = self.line_ids.filtered(
            lambda l: l.reward_id and l.coupon_id
        )._reset_loyalty()
        seen_rewards = set()
        line_rewards = []
        payment_rewards = []
        for line in self.line_ids:
            if (
                line.reward_identifier_code in seen_rewards
                or not line.reward_id
                or not line.coupon_id
            ):
                continue
            seen_rewards.add(line.reward_identifier_code)
            if line.reward_id.program_id.is_payment_program:
                payment_rewards.append(
                    (
                        line.reward_id,
                        line.coupon_id,
                        line.reward_identifier_code,
                        line.product_id,
                    )
                )
            else:
                line_rewards.append(
                    (
                        line.reward_id,
                        line.coupon_id,
                        line.reward_identifier_code,
                        line.product_id,
                    )
                )

        for reward_key in itertools.chain(line_rewards, payment_rewards):
            coupon = reward_key[1]
            reward = reward_key[0]
            program = reward.program_id
            points = self._get_real_points_for_coupon(coupon)
            if (
                coupon not in all_coupons
                or points < reward.required_points
                or program not in domain_matching_programs
            ):
                continue
            try:
                values_list = self._get_reward_line_values(
                    reward, coupon, product=reward_key[3]
                )
            except UserError:
                values_list = []
            reward_line_pool = self._write_vals_from_reward_vals(
                values_list, reward_line_pool, delete=False
            )

        lines_to_unlink |= reward_line_pool

        for program in automatic_programs:
            program_status = all_programs_status[program]
            if "error" in program_status:
                continue
            self.__try_apply_program(program, False, program_status)

        order_line_update = [(Command.DELETE, line.id) for line in lines_to_unlink]
        if order_line_update:
            self.write({"line_ids": order_line_update})
        if coupons_to_unlink:
            coupons_to_unlink.sudo().unlink()
        if point_entries_to_unlink:
            point_entries_to_unlink.sudo().unlink()

    def _get_not_rewarded_order_lines(self):
        return self.line_ids.filtered(
            lambda line: line.product_id and not line.reward_id
        )

    def _get_order_line_price(self, order_line, price_type):
        return sum(order_line._get_lines_with_price().mapped(price_type))

    def _program_check_compute_points(self, programs):
        self.check_singleton()

        order_lines = self._get_not_rewarded_order_lines().filtered(
            lambda line: not line.combo_item_id
        )
        products = order_lines.product_id
        products_qties = dict.fromkeys(products, 0)
        for line in order_lines:
            product_qty = line.product_uom_qty
            products_qties[line.product_id] += product_qty
        products_per_rule = programs._get_valid_products(products)

        so_products_per_rule = programs._get_valid_products(self.line_ids.product_id)
        lines_per_rule = defaultdict(lambda: self.env["sale.order.line"])
        for line in self.line_ids - self._get_no_effect_on_threshold_lines():
            is_discount = line.reward_id.reward_type == "discount"
            reward_program = line.reward_id.program_id
            if (is_discount and reward_program.trigger == "auto") or line.combo_item_id:
                continue
            for program in programs:
                if is_discount and reward_program == program:
                    continue
                for rule in program.rule_ids:
                    if line.product_id in so_products_per_rule.get(rule, []):
                        lines_per_rule[rule] |= line._get_lines_with_price()

        result = {}
        for program in programs:
            code_matched = (
                not bool(program.rule_ids) and program.applies_on == "current"
            )
            minimum_amount_matched = code_matched
            product_qty_matched = code_matched
            points = 0
            rule_points = []
            program_result = result.setdefault(program, {})
            for rule in program.rule_ids:
                if (
                    program.program_type == "ewallet"
                    and not program.trigger_product_ids
                ):
                    break
                if rule.mode == "with_code" and rule not in self.code_enabled_rule_ids:
                    continue
                code_matched = True
                rule_amount = rule._get_minimum_amount(self.currency_id)
                untaxed_amount = sum(lines_per_rule[rule].mapped("price_subtotal"))
                tax_amount = sum(lines_per_rule[rule].mapped("price_tax"))
                if rule_amount > (
                    (
                        rule.minimum_amount_tax_mode == "incl"
                        and (untaxed_amount + tax_amount)
                    )
                    or untaxed_amount
                ):
                    continue
                minimum_amount_matched = True
                if not products_per_rule.get(rule):
                    continue
                rule_products = products_per_rule[rule]
                ordered_rule_products_qty = sum(
                    products_qties[product] for product in rule_products
                )
                if ordered_rule_products_qty < rule.minimum_qty or not rule_products:
                    continue
                product_qty_matched = True
                if not rule.reward_point_amount:
                    continue
                if (
                    program.applies_on == "future"
                    and rule.reward_point_split
                    and rule.reward_point_mode != "order"
                ):
                    if rule.reward_point_mode == "unit":
                        rule_points.extend(
                            rule.reward_point_amount
                            for _ in range(int(ordered_rule_products_qty))
                        )
                    elif rule.reward_point_mode == "money":
                        for line in self.line_ids:
                            if (
                                line.is_reward_line
                                or line.combo_item_id
                                or line.product_id not in rule_products
                                or line.product_qty <= 0
                            ):
                                continue
                            line_price_total = self._get_order_line_price(
                                line, "price_total"
                            )
                            points_per_unit = float_round(
                                (
                                    rule.reward_point_amount
                                    * line_price_total
                                    / line.product_qty
                                ),
                                precision_digits=2,
                                rounding_method="DOWN",
                            )
                            if not points_per_unit:
                                continue
                            rule_points.extend(
                                [points_per_unit] * int(line.product_qty)
                            )
                elif rule.reward_point_mode == "order":
                    points += rule.reward_point_amount
                elif rule.reward_point_mode == "money":
                    amount_paid = 0.0
                    rule_products = so_products_per_rule.get(rule, [])
                    for line in (
                        self.line_ids - self._get_no_effect_on_threshold_lines()
                    ):
                        if (
                            line.combo_item_id
                            or line.reward_id.program_id.program_type
                            in ["ewallet", "gift_card", program.program_type]
                        ):
                            continue
                        line_price_total = self._get_order_line_price(
                            line, "price_total"
                        )
                        amount_paid += (
                            line_price_total
                            if line.product_id in rule_products
                            else 0.0
                        )

                    points += float_round(
                        rule.reward_point_amount * amount_paid,
                        precision_digits=2,
                        rounding_method="DOWN",
                    )
                elif rule.reward_point_mode == "unit":
                    points += rule.reward_point_amount * ordered_rule_products_qty
            if not program.is_nominative:
                if not code_matched:
                    program_result["error"] = _(
                        "This program requires a code to be applied."
                    )
                elif not minimum_amount_matched:
                    program_result["error"] = _(
                        "A minimum of %(amount)s %(currency)s should be purchased to get the reward",
                        amount=min(program.rule_ids.mapped("minimum_amount")),
                        currency=program.currency_id.name,
                    )
                elif not product_qty_matched:
                    program_result["error"] = _(
                        "You don't have the required product quantities on your sales order."
                    )
            elif self.partner_id.is_public and not self._allow_nominative_programs():
                program_result["error"] = _(
                    "This program is not available for public users."
                )
            if "error" not in program_result:
                points_result = [points] + rule_points
                program_result["points"] = points_result
        return result

    def __try_apply_program(self, program, coupon, status):
        self.check_singleton()
        all_points = status["points"]
        points = all_points[0]
        coupons = coupon or self.env["loyalty.card"]
        if coupon:
            if program.is_nominative:
                self._add_points_for_coupon({coupon: points})
        elif not coupon:
            if program.is_nominative:
                coupon = self.env["loyalty.card"].search(
                    [
                        ("partner_id", "=", self.partner_id.id),
                        ("program_id", "=", program.id),
                    ],
                    limit=1,
                )
                if not points and not coupon:
                    _debug.logic(
                        "program_refused",
                        order=self,
                        program=program,
                        reason="no_card_and_no_points",
                    )
                    return {
                        "error": _(
                            "No card found for this loyalty program and no points will be given with this order."
                        )
                    }
                elif coupon:
                    self._add_points_for_coupon({coupon: points})
                coupons = coupon
            if not coupon:
                all_points = [p for p in all_points if p]
                partner = False
                if (
                    program.is_nominative
                    or program.program_type == "next_order_coupons"
                ):
                    partner = self.partner_id.id
                coupons = (
                    self.env["loyalty.card"]
                    .sudo()
                    .with_context(loyalty_no_mail=True, tracking_disable=True)
                    .create(
                        [
                            {
                                "program_id": program.id,
                                "partner_id": partner,
                                "points": 0,
                                "order_id": self.id,
                            }
                            for _ in all_points
                        ]
                    )
                )
                self._add_points_for_coupon(dict(zip(coupons, all_points, strict=True)))
                _debug.lifecycle(
                    "loyalty_cards_created",
                    order=self,
                    program=program,
                    coupons=coupons,
                )
        return {"coupon": coupons}

    def _try_apply_program(self, program, coupon=None):
        self.check_singleton()
        if not program.filtered_domain(self._get_domain_program()):
            _debug.logic(
                "program_refused", order=self, program=program, reason="domain_mismatch"
            )
            return {"error": _("The program is not available for this order.")}
        elif program in self._get_applied_programs():
            _debug.logic(
                "program_refused", order=self, program=program, reason="already_applied"
            )
            return {
                "error": _("This program is already applied to this order."),
                "already_applied": True,
            }
        elif program.reward_ids:
            global_rewards = program.reward_ids.filtered("is_global_discount")
            applied_global_reward = self._get_applied_global_discount()
            best_global_rewards = (
                max(
                    global_rewards,
                    key=lambda reward: self._get_discount_amount(
                        reward, self._discountable_amount(applied_global_reward)
                    ),
                )
                if len(global_rewards) > 1
                else global_rewards
            )
            if (
                best_global_rewards
                and applied_global_reward
                and self._best_global_discount_already_applied(
                    applied_global_reward, best_global_rewards
                )
            ):
                _debug.logic(
                    "program_refused",
                    order=self,
                    program=program,
                    reason="incompatible_global_discount",
                )
                return {
                    "error": _(
                        'This discount (%(discount)s) is not compatible with "%(other_discount)s". '
                        "Please remove it in order to apply this one.",
                        discount=best_global_rewards.description,
                        other_discount=applied_global_reward.description,
                    )
                }
        status = self._program_check_compute_points(program)[program]
        if "error" in status:
            _debug.logic(
                "program_refused", order=self, program=program, reason="points_check"
            )
            return status
        return self.__try_apply_program(program, coupon, status)

    def _try_apply_code(self, code):
        self.check_singleton()

        base_domain = self._get_domain_trigger()
        domain = Domain.AND(
            [base_domain, [("mode", "=", "with_code"), ("code", "=", code)]]
        )
        rule = self.env["loyalty.rule"].search(domain)
        program = rule.program_id
        coupon = False
        check_date = self._get_confirmed_tx_create_date()

        if (
            rule in self.code_enabled_rule_ids
            and program in self.line_ids.filtered("is_reward_line").reward_id.program_id
        ):
            _debug.logic("code_refused", order=self, reason="already_applied")
            return {"error": _("This promo code is already applied.")}

        if not program:
            coupon = self.env["loyalty.card"].search([("code", "=", code)])
            if (
                not coupon
                or not coupon.program_id.active
                or not coupon.program_id.reward_ids
                or not coupon.program_id.filtered_domain(self._get_domain_program())
            ):
                _debug.logic("code_refused", order=self, reason="unknown_code")
                return {
                    "error": _("This code is invalid (%s).", code),
                    "not_found": True,
                }
            if coupon.expiration_date and coupon.expiration_date < check_date:
                _debug.logic("code_refused", order=self, reason="coupon_expired")
                return {"error": _("This coupon is expired.")}
            elif coupon.points < min(
                coupon.program_id.reward_ids.mapped("required_points")
            ):
                _debug.logic("code_refused", order=self, reason="coupon_spent")
                return {"error": _("This coupon has already been used.")}
            program = coupon.program_id

        if not program or not program.active:
            _debug.logic("code_refused", order=self, reason="no_active_program")
            return {"error": _("This code is invalid (%s).", code), "not_found": True}
        elif program.program_type in ("loyalty", "ewallet"):
            _debug.logic(
                "code_refused",
                order=self,
                reason="program_type_not_code_applicable",
                program=program,
            )
            return {"error": _("This program cannot be applied with code.")}

        self.env.cr.execute(
            """
            SELECT id FROM loyalty_program WHERE id=%s FOR UPDATE NOWAIT
        """,
            (program.id,),
        )

        if program.limit_usage and program.total_order_count >= program.max_usage:
            _debug.logic(
                "code_refused", order=self, reason="usage_limit", program=program
            )
            return {"error": _("This code is expired (%s).", code)}

        if rule:
            self.code_enabled_rule_ids |= rule
        program_is_applied = program in self._get_points_programs()
        if coupon:
            self.applied_coupon_ids += coupon
        if program_is_applied:
            self._update_programs_and_rewards()
        elif program.applies_on != "future" or not coupon:
            apply_result = self._try_apply_program(program, coupon)
            if "error" in apply_result and (
                not program.is_nominative or (program.is_nominative and not coupon)
            ):
                if rule:
                    self.code_enabled_rule_ids -= rule
                if coupon and not apply_result.get("already_applied", False):
                    self.applied_coupon_ids -= coupon
                return apply_result
            coupon = apply_result.get("coupon", self.env["loyalty.card"])
        return self._get_claimable_rewards(forced_coupons=coupon)

    def _confirm_order(self):
        super()._confirm_order()
        if self.amount_total or not self.reward_amount:
            return
        auto_invoice = self.env["ir.config_parameter"].get_param(
            "sale.automatic_invoice"
        )
        if str2bool(auto_invoice):
            _debug.pipeline("fully_discounted_order_auto_invoiced", order=self)
            self._force_lines_to_invoice_policy_order()
            invoice = self._create_invoices(final=True)
            invoice.action_post()
