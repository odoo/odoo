# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class LoyaltyGenerateWizard(models.TransientModel):
    _inherit = 'loyalty.generate.wizard'

    website_id = fields.Many2one('website', 'Website')

    def _get_coupon_values(self, partner):
        res = super()._get_coupon_values(partner)
        if self.website_id:
            res.update(website_id=self.website_id.id)
        return res
