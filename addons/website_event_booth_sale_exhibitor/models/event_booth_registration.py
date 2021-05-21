# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventBoothRegistration(models.Model):
    _inherit = 'event.booth.registration'

    sponsor_name = fields.Char(string='Sponsor Name')
    sponsor_email = fields.Char(string='Sponsor Email')
    sponsor_mobile = fields.Char(string='Sponsor Mobile')
    sponsor_phone = fields.Char(string='Sponsor Phone')
    sponsor_subtitle = fields.Char(string='Sponsor Slogan')
    sponsor_website_description = fields.Html(string='Sponsor Description')
    sponsor_image_512 = fields.Image(string='Sponsor Logo')

    def _get_fields_for_booth_confirmation(self):
        return super(EventBoothRegistration, self)._get_fields_for_booth_confirmation() + \
               ['sponsor_name', 'sponsor_email', 'sponsor_mobile', 'sponsor_phone', 'sponsor_subtitle',
                'sponsor_website_description', 'sponsor_image_512']
