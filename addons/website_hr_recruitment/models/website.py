# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.addons import website


class Website(website.Website):

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('Jobs'), self.env['ir.http']._url_for('/jobs'), 'website_hr_recruitment'))
        return suggested_controllers

    def _search_get_details(self, search_type, order, options):
        result = super()._search_get_details(search_type, order, options)
        if search_type in ['jobs', 'all']:
            result.append(self.env['hr.job']._search_get_detail(self, order, options))
        return result
