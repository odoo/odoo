# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
from functools import cache

from odoo import api, fields, models, tools

from odoo.tools.translate import code_translations


class IrCodeTranslation(models.Model):
    _name = 'ir.code.translation'
    _description = 'Customized Code Translations'
    _log_access = False

    source = fields.Text(string='Code')
    value = fields.Text(string='Translation Value', required=True)
    module = fields.Char(help="Module this term belongs to")
    lang = fields.Selection(selection='_get_languages', string='Language', validate=False)
    type = fields.Selection([
        ('web', 'Web code translation'),
        ('python', 'Python code translation'),
    ], string='Translation Type')

    _sql_constraints = [('unique_source_lang_module_type', 'UNIQUE(source, lang, module, type)', '(source, lang, module, type) should be unique')]

    def _get_languages(self):
        return self.env['res.lang'].get_installed()

    def create(self, vals_list):
        res = super().create(vals_list)
        self.clear_caches()
        return res

    def write(self, vals):
        res = super().write(vals)
        self.clear_caches()
        return res

    def unlink(self):
        res = super().unlink()
        self.clear_caches()
        return res

    def get_web_translations(self, module_name, lang):
        customized_web_translations = self._get_translations(module_name, lang, 'web')
        native_web_translations = code_translations.get_web_translations(module_name, lang)
        return {
            "messages": [
                *itertools.chain(
                    (
                        {"id": src, "string": value}
                        for src, value in native_web_translations.items()
                        if src not in customized_web_translations
                    ),
                    (
                        {"id": src, "string": value}
                        for src, value in customized_web_translations.items()
                    )
                )
            ]
        }

    def get_python_translation(self, module_name, lang, source):
        customized_translations = self._get_translations(module_name, lang, 'python')
        if source in customized_translations:
            return customized_translations[source]
        return code_translations.get_python_translations(module_name, lang).get(source, source)

    @api.model
    @tools.ormcache('module_name', 'lang', 'type_')
    def _get_translations(self, module_name: str, lang: str, type_: str) -> dict:
        translations = self.sudo().search_fetch(
            domain=[('module', '=', module_name), ('lang', '=', lang), ('type', '=', type_)],
            field_names=['source', 'value'],
        )
        return {t.source: t.value for t in translations}

    def _cleanup(self):
        self.check_access_rights('unlink')
        self.check_access_rule('unlink')
        module_names = self.env['ir.module.module']._installed()
        langs = tuple(lang for lang, _ in self.env['res.lang'].get_installed())

        @cache
        def get_code_translations(module_name):
            return code_translations._get_code_translations(module_name, None, lambda r: True)

        self.flush_model()
        cr = self.env.cr
        cr.execute('DELETE FROM ir_code_translation WHERE module NOT IN %s OR lang NOT IN %s', (tuple(module_names), langs))
        cr.execute('SELECT id, source, value, module, lang, type FROM ir_code_translation')
        ids_to_remove = [
            id_
            for id_, source, value, module_name, lang, type_ in cr.fetchall()
            if source not in get_code_translations(module_name) or
               (type_ == 'python' and code_translations.get_python_translations(module_name, lang).get(source) == value) or
               (type_ == 'web' and code_translations.get_web_translations(module_name, lang).get(source) == value)

        ]

        if ids_to_remove:
            self.browse(ids_to_remove).unlink()

    def _open_ir_code_translations(self):
        return {
            'name': 'Customized Code Translations',
            'type': 'ir.actions.act_window',
            'res_model': 'ir.code.translation',
            'view_mode': 'list',
        }
