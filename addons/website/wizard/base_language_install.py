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
        if self.website_ids and self.lang_ids:
            self.website_ids.language_ids |= self.lang_ids
        params = self._context.get('params', {})
        if 'url_return' in params:
            url = params['url_return'].replace('[lang]', self.first_lang_id.code)
            return self.env['website'].get_client_action(url)
        return action
