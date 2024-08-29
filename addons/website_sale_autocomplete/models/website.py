# -*- encoding: utf-8 -*-
from odoo.addons import website
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class Website(models.Model, website.Website):

    google_places_api_key = fields.Char(
        string='Google Places API Key',
        groups="base.group_system")

    def has_google_places_api_key(self):
        return bool(self.sudo().google_places_api_key)
