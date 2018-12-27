# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from ast import literal_eval


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _compute_website_theme_onboarding_done(self):
        """ The step is marked as done if one theme is installed. """
        # we need the same domain as the existing action
        action = self.env.ref('website_theme_install.theme_install_kanban_action').read()[0]
        domain = literal_eval(action['domain'])
        domain.append(('state', '=', 'installed'))
        installed_themes_count = self.env['ir.module.module'].sudo().search_count(domain)
        for record in self:
            record.website_theme_onboarding_done = (installed_themes_count > 0)

    website_theme_onboarding_done = fields.Boolean("Onboarding website theme step done",
                                                   compute='_compute_website_theme_onboarding_done')

    @api.model
    def action_open_website_theme_selector(self):
        action = self.env.ref('website_theme_install.theme_install_kanban_action').read()[0]
        action['target'] = 'new'
        return action
