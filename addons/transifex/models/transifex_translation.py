# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.urls
from configparser import ConfigParser
from os import pardir
from os.path import isfile, join as opj

import odoo
from odoo import models, tools


class TransifexTranslation(models.AbstractModel):
    _name = 'transifex.translation'
    _description = "Transifex Translation"

    @tools.ormcache()
    def _get_transifex_projects(self):
        """ get the transifex project name for each module

        .tx/config files contains the project reference
        first section is [main], after '[odoo-16.sale]'

        :rtype: dict
        :return: {module_name: tx_project_name}
        """
        tx_config_file = ConfigParser()
        projects = {}
        for addon_path in odoo.addons.__path__:
            for tx_path in (
                    opj(addon_path, '.tx', 'config'),
                    opj(addon_path, pardir, '.tx', 'config'),
            ):
                if isfile(tx_path):
                    tx_config_file.read(tx_path)
                    for sec in tx_config_file.sections()[1:]:
                        if len(sec.split(":")) != 6:
                            # old format ['main', 'odoo-16.base', ...]
                            tx_project, tx_mod = sec.split(".")
                        else:
                            # tx_config_file.sections(): ['main', 'o:odoo:p:odoo-16:r:base', ...]
                            _, _, _, tx_project, _, tx_mod = sec.split(':')
                        projects[tx_mod] = tx_project
        return projects

    def _update_transifex_url(self, translations):
        """ Update translations' Transifex URL

        :param translations: the translations to update, may be a recordset or a list of dicts.
            The elements of `translations` must have the fields/keys 'source', 'module', 'lang',
            and the field/key 'transifex_url' is updated on them.
        """

        # e.g. 'https://www.transifex.com/odoo/'
        base_url = self.env['ir.config_parameter'].sudo().get_param('transifex.project_url')
        if not base_url:
            return
        base_url = base_url.rstrip('/')

        res_langs = self.env['res.lang'].search([])
        lang_to_iso = {l.code: l.iso_code for l in res_langs}
        if not lang_to_iso:
            return

        projects = self._get_transifex_projects()
        if not projects:
            return

        for translation in translations:
            if not translation['source'] or translation['lang'] == 'en_US':
                continue

            lang_iso = lang_to_iso.get(translation['lang'])
            if not lang_iso:
                continue

            project = projects.get(translation['module'])
            if not project:
                continue

            # e.g. https://www.transifex.com/odoo/odoo-16/translate/#fr_FR/sale/42?q=text:'Sale+Order'
            # 42 is an arbitrary number to satisfy the transifex URL format
            source = werkzeug.urls.url_quote_plus(translation['source'][:50].replace("\n", "").replace("'", "\\'"))
            source = f"'{source}'" if "+" in source else source
            translation['transifex_url'] = f"{base_url}/{project}/translate/#{lang_iso}/{translation['module']}/42?q=text%3A{source}"
