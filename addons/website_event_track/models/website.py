# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    website_event_track_youtube_api_key = fields.Char('Youtube API Key',
        help="Used to query the Youtube API and display the viewers count on compatible Event Tracks.")
