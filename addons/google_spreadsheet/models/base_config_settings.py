# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class BaseConfigSettings(models.TransientModel):
    _inherit = "base.config.settings"

    google_drive_uri_copy = fields.Char(related='google_drive_uri', string='URI', help="The URL to generate the authorization code from Google")
