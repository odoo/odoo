# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    website_event_track_youtube_api_key = fields.Char(related='website_id.website_event_track_youtube_api_key', readonly=False)
