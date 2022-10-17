# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from configparser import ConfigParser
from os.path import join as opj
import os
import werkzeug.urls

import odoo
from odoo import models

class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def get_field_translations(self, field_name, langs=None):
        """ :return dict translations: [{lang: lang, source: val_en, value: val_lang, transifexUrl: transifex_url)] """
        translations, context = super().get_field_translations(field_name, langs=langs)
        self._get_transifex_url(translations)
        return translations, context

    def _get_transifex_url(self, translations):
        """ Construct transifex URL based on the module on configuration """
        self.ensure_one()
        # .tx/config files contains the project reference
        # using ini files like '[odoo-master.website_sale]'
        external_id = self.get_external_id().get(self.id)
        if not external_id:
            return
        module = external_id.split('.')[0]
        if not module:
            return

        # e.g. 'https://www.transifex.com/odoo/'
        base_url = self.env['ir.config_parameter'].sudo().get_param('transifex.project_url')

        tx_config_file = ConfigParser()
        tx_sections = []
        for addon_path in odoo.addons.__path__:
            tx_path = opj(addon_path, '.tx', 'config')
            if os.path.isfile(tx_path):
                tx_config_file.read(tx_path)
                # first section is [main], after [odoo-11.sale]
                tx_sections.extend(tx_config_file.sections()[1:])

            # parent directory ad .tx/config is root directory in odoo/odoo
            tx_path = opj(addon_path, os.pardir, '.tx', 'config')
            if os.path.isfile(tx_path):
                tx_config_file.read(tx_path)
                tx_sections.extend(tx_config_file.sections()[1:])

        if not (base_url and tx_sections):
            return

        base_url = base_url.rstrip('/')

        project = None
        for section in tx_sections:
            tx_project, tx_mod = section.split('.')
            if tx_mod == module:
                project = tx_project
                break
        if not project:
            return

        langs = [translation['lang'] for translation in translations]
        res_langs = self.env['res.lang'].search([('code', 'in', langs)])
        lang_to_iso = dict((l.code, l.iso_code) for l in res_langs)

        for translation in translations:
            if not translation['source'] or translation['lang'] == 'en_US':
                continue

            lang_iso = lang_to_iso.get(translation['lang'])
            if not lang_iso:
                continue

            # e.g. https://www.transifex.com/odoo/odoo-10/translate/#fr/sale/42?q=text:'Sale+Order'
            source = werkzeug.urls.url_quote_plus(translation['source'][:50].replace("\n", "").replace("'", "\\'"))
            source = f"'{source}'" if "+" in source else source
            translation['transifexUrl'] = "%(url)s/%(project)s/translate/#%(lang)s/%(module)s/42?q=%(source)s" % {
                'url': base_url,
                'project': project,
                'lang': lang_iso,
                'module': module,
                'source': f"text%3A{source}",
            }
