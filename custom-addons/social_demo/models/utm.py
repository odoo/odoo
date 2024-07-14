# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from odoo import models


class DemoUtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    def _compute_clicks_count(self):
        """ Bypass the computation for our demo campaign. """
        demo_campaign = self.env.ref('social_demo.social_utm_campaign', raise_if_not_found=False) or self.env['utm.campaign']
        for campaign in self:
            if campaign == demo_campaign:
                campaign.click_count = random.randint(30000, 40000)

        super(DemoUtmCampaign, self - demo_campaign)._compute_clicks_count()
