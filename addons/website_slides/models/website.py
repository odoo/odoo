# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Website(models.Model):
    _inherit = "website"

    website_slide_google_app_key = fields.Char('Google Doc Key')
