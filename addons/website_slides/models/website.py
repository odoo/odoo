# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.addons.http_routing.models.ir_http import url_for


class Website(models.Model):
    _inherit = "website"

    website_slide_google_app_key = fields.Char('Google Doc Key')

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('Courses'), url_for('/slides'), 'website_slides'))
        return suggested_controllers
