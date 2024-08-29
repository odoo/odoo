# -*- coding: utf-8 -*-
from odoo.addons import loyalty
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class LoyaltyCard(models.Model, loyalty.LoyaltyCard):

    def action_coupon_share(self):
        self.ensure_one()
        return self.env['coupon.share'].create_share_action(coupon=self)
