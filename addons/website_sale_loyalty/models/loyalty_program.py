# -*- coding: utf-8 -*-
from odoo.addons import website, loyalty
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class LoyaltyProgram(models.Model, loyalty.LoyaltyProgram, website.WebsiteMultiMixin):

    ecommerce_ok = fields.Boolean("Available on Website", default=True)

    def action_program_share(self):
        self.ensure_one()
        return self.env['coupon.share'].create_share_action(program=self)
