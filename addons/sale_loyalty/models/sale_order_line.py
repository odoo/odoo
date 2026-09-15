from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_reward_line = fields.Boolean(
        string="Is a program reward line",
        compute="_compute_is_reward_line",
    )
    reward_id = fields.Many2one(
        comodel_name="loyalty.reward",
        readonly=True,
        ondelete="restrict",
    )
    coupon_id = fields.Many2one(
        comodel_name="loyalty.card",
        readonly=True,
        ondelete="restrict",
    )
    reward_identifier_code = fields.Char(
        help="Technical field used to link multiple reward lines from the same reward together."
    )
    points_cost = fields.Float(
        help="How much point this reward costs on the loyalty card."
    )

    def _compute_name(self):
        reward = self.filtered("reward_id")
        super(SaleOrderLine, self - reward)._compute_name()

    def _compute_price_and_discount(self):
        rewards = self.filtered("reward_id")
        return super(SaleOrderLine, self - rewards)._compute_price_and_discount()

    @api.depends("is_reward_line")
    def _compute_product_readonly(self):
        super()._compute_product_readonly()
        self.filtered("is_reward_line").product_readonly = False

    @api.depends("reward_id")
    def _compute_is_reward_line(self):
        for line in self:
            line.is_reward_line = bool(line.reward_id)

    def _compute_tax_ids(self):
        reward_lines = self.filtered("is_reward_line")
        super(SaleOrderLine, self - reward_lines)._compute_tax_ids()
        for line in reward_lines:
            line = line.with_company(line.company_id)
            fpos = (
                line.order_id.fiscal_position_id
                or line.order_id.fiscal_position_id._get_fiscal_position(
                    line.partner_id
                )
            )
            taxes = line.tax_ids.filtered_domain(
                self.env["account.tax"]._check_company_domain(line.company_id)
            )
            line.tax_ids = fpos.map_tax(taxes)
            _debug.logic(
                "reward_line_taxes", line=line, fiscal_position=fpos, taxes=line.tax_ids
            )

    def _get_price_display(self, pricelist_price=None, base_price=None):
        if self.is_reward_line and self.reward_id.reward_type != "product":
            _debug.logic("price_display", line=self, by="reward_line")
            return self.price_unit
        return super()._get_price_display(
            pricelist_price=pricelist_price, base_price=base_price
        )

    def _can_be_invoiced_alone(self):
        return super()._can_be_invoiced_alone() and not self.is_reward_line

    def _is_discount_line(self):
        return super()._is_discount_line() or self.reward_id.reward_type == "discount"

    def _reset_loyalty(self, complete=False):
        vals = {
            "points_cost": 0,
            "price_unit": 0,
            "price_unit_auto": 0,
        }
        if complete:
            vals.update(
                {
                    "coupon_id": False,
                    "reward_id": False,
                }
            )
        _debug.lifecycle("loyalty_reset", lines=self, complete=complete)
        self.write(vals)
        return self

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for line in res:
            if line.coupon_id and line.points_cost and line.state == "done":
                _debug.lifecycle(
                    "points_spent_on_create",
                    line=line,
                    coupon=line.coupon_id,
                    cost=line.points_cost,
                )
                line.coupon_id.points -= line.points_cost
                line.order_id._update_loyalty_history(line.coupon_id, line.points_cost)
        return res

    def write(self, vals):
        cost_in_vals = "points_cost" in vals
        if cost_in_vals:
            previous_vals = {line: (line.points_cost, line.coupon_id) for line in self}
        res = super().write(vals)
        if cost_in_vals:
            for line, (previous_cost, previous_coupon) in previous_vals.items():
                if line.state != "done":
                    continue
                if (
                    line.points_cost != previous_cost
                    or line.coupon_id != previous_coupon
                ):
                    _debug.lifecycle(
                        "points_moved_on_write",
                        line=line,
                        from_coupon=previous_coupon,
                        to_coupon=line.coupon_id,
                        previous_cost=previous_cost,
                        cost=line.points_cost,
                    )
                    previous_coupon.points += previous_cost
                    line.coupon_id.points -= line.points_cost
        return res

    def unlink(self):
        reward_coupon_set = {
            (l.reward_id, l.coupon_id, l.reward_identifier_code)
            for l in self
            if l.reward_id
        }
        related_lines = self.env["sale.order.line"]
        related_lines |= self.order_id.line_ids.filtered(
            lambda l: (
                (l.reward_id, l.coupon_id, l.reward_identifier_code)
                in reward_coupon_set
            )
        )
        coupons_to_unlink = self.env["loyalty.card"]
        for line in self:
            if line.coupon_id:
                if line.coupon_id in line.order_id.applied_coupon_ids:
                    line.order_id.applied_coupon_ids -= line.coupon_id
                elif (
                    line.coupon_id.order_id == line.order_id
                    and line.coupon_id.program_id.applies_on == "current"
                    and not any(
                        oLine.coupon_id == line.coupon_id and oLine not in related_lines
                        for oLine in line.order_id.line_ids
                    )
                ):
                    coupons_to_unlink |= line.coupon_id
                    line.order_id.code_enabled_rule_ids = (
                        line.order_id.code_enabled_rule_ids.filtered(
                            lambda r: r.program_id != line.coupon_id.program_id
                        )
                    )
        for line in related_lines:
            if line.state == "done":
                _debug.lifecycle(
                    "points_refunded_on_unlink",
                    line=line,
                    coupon=line.coupon_id,
                    cost=line.points_cost,
                )
                line.coupon_id.points += line.points_cost
        _debug.lifecycle(
            "reward_lines_unlinked",
            lines=self,
            related=related_lines,
            coupons_unlinked=coupons_to_unlink,
        )
        res = super(SaleOrderLine, self | related_lines).unlink()
        coupons_to_unlink.sudo().unlink()
        return res

    def _get_domain_lines_sellable(self):
        return super()._get_domain_lines_sellable() & Domain("reward_id", "=", False)

    def _can_be_edited_on_portal(self):
        return super()._can_be_edited_on_portal() and not self.is_reward_line
