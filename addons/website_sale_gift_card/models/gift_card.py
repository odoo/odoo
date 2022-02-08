# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class GiftCard(models.Model):
    _name = "gift.card"
    _inherit = ['website.multi.mixin', 'gift.card']

    website_id = fields.Many2one('website', related='buy_line_id.order_id.website_id', store=True, readonly=False)

    def can_be_used(self):
        website = self.env['website'].get_current_website()
        return super(GiftCard, self).can_be_used() and self.website_id.id in [website.id, False]
