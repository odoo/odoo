# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# NOTE Use black to automatically format this code.

from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = "pos.config"

    use_coupon_programs = fields.Boolean(
        "Coupons & Promotions",
        help="Use coupon and promotion programs in this PoS configuration.",
    )
    coupon_program_ids = fields.Many2many(
        "coupon.program",
        string="Coupon Programs",
        compute="_filter_programs",
        inverse="_set_programs",
    )
    promo_program_ids = fields.Many2many(
        "coupon.program",
        string="Promotion Programs",
        compute="_filter_programs",
        inverse="_set_programs",
    )
    program_ids = fields.Many2many("coupon.program", string="Coupons and Promotions")

    @api.depends("program_ids")
    def _filter_programs(self):
        for config in self:
            config.coupon_program_ids = config.program_ids.filtered(
                lambda program: program.program_type == "coupon_program"
            )
            config.promo_program_ids = config.program_ids.filtered(
                lambda program: program.program_type == "promotion_program"
            )

    def _set_programs(self):
        for config in self:
            config.program_ids = config.coupon_program_ids | config.promo_program_ids

    def open_session_cb(self, check_coa=True):
        # Check validity of programs before opening a new session
        invalid_reward_products_msg = ""
        for program in self.program_ids:
            if (
                program.reward_product_id
                and not program.reward_product_id.available_in_pos
            ):
                reward_product = program.reward_product_id
                invalid_reward_products_msg += "\n\t"
                invalid_reward_products_msg += _(
                    "Program: %(name)s (%(type)s), Reward Product: `%(reward_product)s`",
                    name=program.name,
                    type=program.program_type,
                    reward_product=reward_product.name,
                )

        if invalid_reward_products_msg:
            intro = _(
                "To continue, make the following reward products to be available in Point of Sale."
            )
            raise UserError(f"{intro}\n{invalid_reward_products_msg}")

        return super(PosConfig, self).open_session_cb()

    def use_coupon_code(self, code, creation_date, partner_id, reserved_program_ids):
        coupon_to_check = self.env["coupon.coupon"].search(
            [("code", "=", code), ("program_id", "in", self.program_ids.ids)]
        )
        # If not unique, we only check the first coupon.
        coupon_to_check = coupon_to_check[:1]
        if not coupon_to_check:
            return {
                "successful": False,
                "payload": {
                    "error_message": _("This coupon is invalid (%s).") % (code)
                },
            }
        message = coupon_to_check._check_coupon_code(
            fields.Date.from_string(creation_date[:11]),
            partner_id,
            reserved_program_ids=reserved_program_ids,
        )
        error_message = message.get("error", False)
        if error_message:
            return {
                "successful": False,
                "payload": {"error_message": error_message},
            }

        coupon_to_check.write({"state": "used"})
        return {
            "successful": True,
            "payload": {
                "program_id": coupon_to_check.program_id.id,
                "coupon_id": coupon_to_check.id,
            },
        }
