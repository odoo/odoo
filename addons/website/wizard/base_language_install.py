# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class BaseLanguageInstall(models.TransientModel):

    _inherit = "base.language.install"

    website_ids = fields.Many2many('website', string='Websites to translate')

    @api.model
    def default_get(self, fields):
        defaults = super(BaseLanguageInstall, self).default_get(fields)
        website_id = self._context.get('params', {}).get('website_id')
        if website_id:
            if 'website_ids' not in defaults:
                defaults['website_ids'] = []
            defaults['website_ids'].append(website_id)
        return defaults

    def lang_install(self):
        action = super(BaseLanguageInstall, self).lang_install()
        lang = self.env['res.lang']._lang_get(self.lang)
        if self.website_ids and lang:
            self.website_ids.write({'language_ids': [(4, lang.id)]})
        params = self._context.get('params', {})
        if 'url_return' in params:
            return {
                'url': params['url_return'].replace('[lang]', self.lang),
                'type': 'ir.actions.act_url',
                'target': 'self'
            }
        return action
