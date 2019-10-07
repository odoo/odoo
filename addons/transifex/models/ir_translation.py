# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

try:
    from configparser import ConfigParser
except ImportError:
    # python2 import
    from ConfigParser import ConfigParser
from os.path import join as opj
import os
import werkzeug

from odoo import models, fields
from odoo.modules.module import ad_paths


class IrTranslation(models.Model):

    _inherit = 'ir.translation'

    transifex_url = fields.Char("Transifex URL", compute='_get_transifex_url')

    def _get_transifex_url(self):
        """ Construct transifex URL based on the module on configuration """
        # e.g. 'https://www.transifex.com/odoo/'
        base_url = self.env['ir.config_parameter'].sudo().get_param('transifex.project_url')

        tx_config_file = ConfigParser()
        tx_sections = []
        for addon_path in ad_paths:
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

        if not base_url or not tx_sections:
            self.update({'transifex_url': False})
        else:
            base_url = base_url.rstrip('/')

            # will probably be the same for all terms, avoid multiple searches
            translation_languages = list(set(self.mapped('lang')))
            languages = self.env['res.lang'].with_context(active_test=False).search(
                [('code', 'in', translation_languages)])

            language_codes = dict((l.code, l.iso_code) for l in languages)

            # .tx/config files contains the project reference
            # using ini files like '[odoo-master.website_sale]'
            translation_modules = set(self.mapped('module'))
            project_modules = {}
            for module in translation_modules:
                for section in tx_sections:
                    tx_project, tx_mod = section.split('.')
                    if tx_mod == module:
                        project_modules[module] = tx_project

            for translation in self:
                if not translation.module or not translation.source or translation.lang == 'en_US':
                    # custom or source term
                    translation.transifex_url = False
                    continue

                lang_code = language_codes.get(translation.lang)
                if not lang_code:
                    translation.transifex_url = False
                    continue

                project = project_modules.get(translation.module)
                if not project:
                    translation.transifex_url = False
                    continue

                # e.g. https://www.transifex.com/odoo/odoo-10/translate/#fr/sale/42?q=text'Sale+Order'
                translation.transifex_url = "%(url)s/%(project)s/translate/#%(lang)s/%(module)s/42?q=%(src)s" % {
                    'url': base_url,
                    'project': project,
                    'lang': lang_code,
                    'module': translation.module,
                    'src': "text:'" + werkzeug.url_quote_plus(
                               translation.source[:50].replace("\n", "").replace("'", "")
                           ) + "'",
                }
