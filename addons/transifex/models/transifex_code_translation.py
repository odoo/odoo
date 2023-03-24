# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2

from odoo import api, models, fields
from odoo.tools.translate import CodeTranslations


class TransifexCodeTranslation(models.Model):
    _name = "transifex.code.translation"
    _description = "Code Translation"
    _log_access = False

    source = fields.Text(string='Code')
    value = fields.Text(string='Translation Value')
    module = fields.Char(help="Module this term belongs to")
    lang = fields.Selection(selection='_get_languages', string='Language', validate=False)
    transifex_url = fields.Char("Transifex URL", compute='_compute_transifex_url',
                                help="Propose a modification in the official version of Odoo")

    def _get_languages(self):
        return self.env['res.lang'].get_installed()

    def _compute_transifex_url(self):
        self.transifex_url = False
        self.env['transifex.translation']._update_transifex_url(self)

    def _load_code_translations(self, module_names=None, langs=None):
        try:
            # the table lock promises translations for a (module, language) will only be created once
            self.env.cr.execute(f'LOCK TABLE {self._table} IN EXCLUSIVE MODE NOWAIT')

            if module_names is None:
                module_names = self.env['ir.module.module'].search([('state', '=', 'installed')]).mapped('name')
            if langs is None:
                langs = [lang for lang, _ in self._get_languages() if lang != 'en_US']
            self.env.cr.execute(f'SELECT DISTINCT module, lang FROM {self._table}')
            loaded_code_translations = set(self.env.cr.fetchall())
            create_value_list = [
                {
                    'source': src,
                    'value': value,
                    'module': module_name,
                    'lang': lang,
                }
                for module_name in module_names
                for lang in langs
                if (module_name, lang) not in loaded_code_translations
                for src, value in CodeTranslations._get_code_translations(module_name, lang, lambda x: True).items()
            ]
            self.sudo().create(create_value_list)

        except psycopg2.errors.LockNotAvailable:
            return False

        return True

    def _open_code_translations(self):
        self._load_code_translations()
        return {
            'name': 'Code Translations',
            'type': 'ir.actions.act_window',
            'res_model': 'transifex.code.translation',
            'view_mode': 'list',
        }

    @api.model
    def reload(self):
        self.env.cr.execute(f'DELETE FROM {self._table}')
        return self._load_code_translations()
