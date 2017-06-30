# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class WebsiteConfigSettings(models.TransientModel):
    _inherit = 'website.config.settings'

    channel_id = fields.Many2one('im_livechat.channel', string='Website Live Channel', related='website_id.channel_id')
