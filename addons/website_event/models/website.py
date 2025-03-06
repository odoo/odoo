# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class Website(models.Model):
    _inherit = "website"

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('Events'), self.env['ir.http']._url_for('/event'), 'website_event'))
        return suggested_controllers

    def _search_get_details(self, search_type, order, options):
        result = super()._search_get_details(search_type, order, options)
        if search_type in ['events', 'all']:
            result.append(self.env['event.event']._search_get_detail(self, order, options))
        return result
