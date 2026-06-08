# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class Website(models.Model):
    _inherit = "website"

    website_slide_google_app_key = fields.Char('Google Doc Key', groups='base.group_system')

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('Courses'), self.env['ir.http']._url_for('/slides'), 'website_slides'))
        return suggested_controllers

    def _search_get_details(self, search_type, order, options):
        result = super()._search_get_details(search_type, order, options)
        if search_type in ['slides', 'slide_channel', 'all']:
            result.append(self.env['slide.channel']._search_get_detail(self, order, options))
        if search_type == 'slides':
            result.append(self.env['slide.slide']._search_get_detail(self, order, options))
        return result

    @api.model
    def _get_settings_to_copy_onto_new_default_website(self):
        """ Provides a list of settings that should always be set on the default
        website. When the default website changes, a check is performed. If some
        of these settings are not already set on the new default website, they
        are copied from the previous default website."""
        return super()._get_settings_to_copy_onto_new_default_website() + ['website_slide_google_app_key']
