# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    loyalty_website_redeemed_reward_ids = fields.One2many('loyalty.website.redeemed.reward', "partner_id")
    can_afford_reward = fields.Boolean(compute='_compute_can_afford_reward')

    def _compute_can_afford_reward(self):
        website = self.env['website'].get_current_website()
        for partner in self:
            if website.has_loyalty and website.loyalty_id.website_reward_ids:
                cheapest_reward_cost = min(website.loyalty_id.website_reward_ids.mapped('point_cost'))
                partner.can_afford_reward = cheapest_reward_cost <= self.loyalty_points
            else:
                partner.can_afford_reward = False
