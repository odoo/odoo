# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# NOTE Use black to automatically format this code.

from collections import defaultdict

from odoo import api, fields, models, _


class PosOrder(models.Model):
    _inherit = "pos.order"

    applied_program_ids = fields.Many2many(
        "coupon.program",
        string="Applied Programs",
        help="Technical field. This is set when the order is validated. "
        "We normally get this value thru the `program_id` of the reward lines.",
    )
    used_coupon_ids = fields.One2many(
        "coupon.coupon", "pos_order_id", string="Consumed Coupons"
    )
    generated_coupon_ids = fields.One2many(
        "coupon.coupon", "source_pos_order_id", string="Generated Coupons"
    )

    def validate_coupon_programs(
        self, program_ids_to_generate_coupons, unused_coupon_ids
    ):
        """This is called after create_from_ui is called. We set here fields
        that are used to link programs and coupons to the order.

        We also return the generated coupons that can be used in the frontend
        to print the generated codes in the receipt.
        """
        self.ensure_one()

        program_ids_to_generate_coupons = program_ids_to_generate_coupons or []
        unused_coupon_ids = unused_coupon_ids or []

        self.env["coupon.coupon"].browse(unused_coupon_ids).write({"state": "new"})
        self.sudo().write(
            {
                "applied_program_ids": [(4, i) for i in self.lines.program_id.ids],
                "used_coupon_ids": [(4, i) for i in self.lines.coupon_id.ids],
                "generated_coupon_ids": [
                    (4, i)
                    for i in (
                        self.env["coupon.program"]
                        .browse(program_ids_to_generate_coupons)
                        .sudo()._generate_coupons(self.partner_id.id)
                    ).ids
                ],
            }
        )
        return [
            {
                "code": coupon.code,
                "expiration_date": coupon.expiration_date,
                "program_name": coupon.program_id.name,
            }
            for coupon in self.generated_coupon_ids
        ]

    def _get_fields_for_order_line(self):
        fields = super(PosOrder, self)._get_fields_for_order_line()
        fields.extend({
            'is_program_reward',
            'coupon_id',
            'program_id',
        })
        return fields

class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    is_program_reward = fields.Boolean(
        "Is reward line",
        help="Flag indicating that this order line is a result of coupon/promo program.",
    )
    program_id = fields.Many2one(
        "coupon.program",
        string="Program",
        help="Promotion/Coupon Program where this reward line is based.",
    )
    coupon_id = fields.Many2one(
        "coupon.coupon", string="Coupon", help="Coupon that generated this reward.",
    )
