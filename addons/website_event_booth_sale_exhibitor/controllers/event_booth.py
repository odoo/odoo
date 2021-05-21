# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_event.controllers.main import WebsiteEventController


class WebsiteEventBoothController(WebsiteEventController):

    def _prepare_booth_registration_values(self, event, kwargs):
        values = super(WebsiteEventBoothController, self)._prepare_booth_registration_values(event, kwargs)
        del values['partner_id']
        return values
