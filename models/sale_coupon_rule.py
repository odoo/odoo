# -*- coding: utf-8 -*-

from odoo import models, fields


class SaleCouponRule(models.Model):
    _inherit = "sale.coupon.rule"

    # TODO Remove in master, useless now
    is_public_included = fields.Boolean(string="Include Public User",
        help="Is the public user included into the set of autorized customers", default=True, deprecated=True)
