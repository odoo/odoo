# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


import hashlib
import json

from odoo import api, models, tools
from odoo.modules import get_resource_path
from odoo.tools.misc import file_open
from odoo.tools.translate import trans_load_code_webclient, trans_load_code_python


class IrTranslationCode(models.AbstractModel):
    _name = "ir.translation.code"
    _description = 'Translation for code'

    def _get_po_paths(self, mod, lang):
        lang_base = lang.split('_')[0]
        po_paths = [get_resource_path(mod, 'i18n', lang_base + '.po'),
                    get_resource_path(mod, 'i18n', lang + '.po'),
                    get_resource_path(mod, 'i18n_extra', lang_base + '.po'),
                    get_resource_path(mod, 'i18n_extra', lang + '.po')]
        return [path for path in po_paths if path]

    @api.model
    def __get_translations_for_code_python(self, mod, lang):
        po_paths = self._get_po_paths(mod, lang)
        python_translations = {}
        for po_path in po_paths:
            try:
                with file_open(po_path, mode='rb') as fileobj:
                    p = trans_load_code_python(fileobj, 'po', lang)
                python_translations.update(p)
            except IOError:
                pass
        return python_translations

    def get_translations_for_python(self, module, lang):
        return self.__get_translations_for_code_python(module, lang)

    @api.model
    def __get_translations_for_code_webclient(self, module, lang):
        po_paths = self._get_po_paths(module, lang)
        webclient_translations = {}
        for po_path in po_paths:
            if po_path:
                try:
                    with file_open(po_path, mode='rb') as fileobj:
                        w = trans_load_code_webclient(fileobj, 'po', lang)
                    webclient_translations.update(w)
                except IOError:
                    pass
        return webclient_translations

    @api.model
    def get_translations_for_webclient(self, modules, lang):
        if not modules:
            modules = [x['name'] for x in self.env['ir.module.module'].sudo().search_read(
                [('state', '=', 'installed')], ['name'])]
        if not lang:
            lang = self._context.get("lang")
        langs = self.env['res.lang']._lang_get(lang)
        lang_params = None
        if langs:
            lang_params = {
                "name": langs.name,
                "direction": langs.direction,
                "date_format": langs.date_format,
                "time_format": langs.time_format,
                "grouping": langs.grouping,
                "decimal_point": langs.decimal_point,
                "thousands_sep": langs.thousands_sep,
                "week_start": langs.week_start,
            }
            lang_params['week_start'] = int(lang_params['week_start'])
            lang_params['code'] = lang

        # Regional languages (ll_CC) must inherit/override their parent lang (ll), but this is
        # done server-side when the language is loaded, so we only need to load the user's lang.
        translations_per_module = {}
        for module in modules:
            webclient_translations = [{'id': src, 'string': value} for src, value in self.__get_translations_for_code_webclient(module, lang).items()]
            translations_per_module[module] = {'messages': webclient_translations}

        return translations_per_module, lang_params

    @api.model
    @tools.ormcache('frozenset(modules)', 'lang')
    def get_web_translations_hash(self, modules, lang):
        translations, lang_params = self.get_translations_for_webclient(modules, lang)
        translation_cache = {
            'lang_parameters': lang_params,
            'modules': translations,
            'lang': lang,
            'multi_lang': len(self.env['res.lang'].sudo().get_installed()) > 1,
        }
        return hashlib.sha1(json.dumps(translation_cache, sort_keys=True).encode()).hexdigest()
