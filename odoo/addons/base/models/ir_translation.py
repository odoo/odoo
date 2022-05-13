# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


# FP TODO 5: remove this file completely, and fix everywhere its is used
# TODO VSC don't forget to keep import/export

import hashlib
import itertools
import json
import logging
import operator
from collections import defaultdict
from difflib import get_close_matches

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.modules import get_module_path, get_module_resource

_logger = logging.getLogger(__name__)

TRANSLATION_TYPE = [
    ('model', 'Model Field'),
    ('model_terms', 'Structured Model Field'),
    ('code', 'Code'),
]


class IrTranslation(models.TransientModel):
    _name = "ir.translation"
    _description = 'Translation'
    # _log_access = False

    name = fields.Char(string='Translated field', required=True)
    res_id = fields.Integer(string='Record ID', index=True)
    lang = fields.Selection(selection='_get_languages', string='Language', validate=False)
    type = fields.Selection(TRANSLATION_TYPE, string='Type', index=True)
    src = fields.Text(string='Internal Source')  # stored in database, kept for backward compatibility
    value = fields.Text(string='Translation Value')
    module = fields.Char(index=True, help="Module this term belongs to")

    state = fields.Selection([('to_translate', 'To Translate'),
                              ('inprogress', 'Translation in Progress'),
                              ('translated', 'Translated')],
                             string="Status", default='to_translate',
                             help="Automatically set to let administators find new terms that might need to be translated")

    # aka gettext extracted-comments - we use them to flag openerp-web translation
    # cfr: http://www.gnu.org/savannah-checkouts/gnu/gettext/manual/html_node/PO-Files.html
    comments = fields.Text(string='Translation comments', index=True)

    @api.model
    def _get_languages(self):
        return self.env['res.lang'].get_installed()

    @api.model
    def _get_ids(self, name, tt, lang, ids):
        """ Return the translations of records.

        :param name: a string defined as "<model_name>,<field_name>"
        :param tt: the type of translation (should always be "model")
        :param lang: the language code
        :param ids: the ids of the given records
        """
        translations = dict.fromkeys(ids, False)
        if ids:
            self._cr.execute("""SELECT res_id, value FROM ir_translation
                                WHERE lang=%s AND type=%s AND name=%s AND res_id IN %s""",
                             (lang, tt, name, tuple(ids)))
            for res_id, value in self._cr.fetchall():
                translations[res_id] = value
        return translations

    @api.model
    def _get_source_query(self, name, types, lang, source, res_id):
        self.flush_model()
        if source:
            # Note: the extra test on md5(src) is a hint for postgres to use the
            # index ir_translation_src_md5
            query = """SELECT value FROM ir_translation
                       WHERE lang=%s AND type in %s AND src=%s AND md5(src)=md5(%s)"""
            source = tools.ustr(source)
            params = (lang or '', types, source, source)
            if res_id:
                query += " AND res_id in %s"
                params += (res_id,)
            if name:
                query += " AND name=%s"
                params += (tools.ustr(name),)
        else:
            query = """ SELECT value FROM ir_translation
                        WHERE lang=%s AND type in %s AND name=%s """
            params = (lang or '', types, tools.ustr(name))

        return (query, params)

    @tools.ormcache('name', 'types', 'lang', 'source', 'res_id')
    def __get_source(self, name, types, lang, source, res_id):
        # res_id is a tuple or None, otherwise ormcache cannot cache it!
        query, params = self._get_source_query(name, types, lang, source, res_id)
        self._cr.execute(query, params)
        res = self._cr.fetchone()
        trad = res and res[0] or u''
        if source and not trad:
            return tools.ustr(source)
        return trad

    @api.model
    def _get_source(self, name, types, lang, source=None, res_id=None):
        """ Return the translation for the given combination of ``name``,
        ``type``, ``language`` and ``source``. All values passed to this method
        should be unicode (not byte strings), especially ``source``.

        :param name: identification of the term to translate, such as field name (optional if source is passed)
        :param types: single string defining type of term to translate (see ``type`` field on ir.translation), or sequence of allowed types (strings)
        :param lang: language code of the desired translation
        :param source: optional source term to translate (should be unicode)
        :param res_id: optional resource id or a list of ids to translate (if used, ``source`` should be set)
        :rtype: unicode
        :return: the request translation, or an empty unicode string if no translation was
                 found and `source` was not passed
        """
        # FIXME: should assert that `source` is unicode and fix all callers to
        # always pass unicode so we can remove the string encoding/decoding.
        if not lang:
            return tools.ustr(source or '')
        if isinstance(types, str):
            types = (types,)
        if res_id:
            if isinstance(res_id, int):
                res_id = (res_id,)
            else:
                res_id = tuple(res_id)
        return self.__get_source(name, types, lang, source, res_id)

    @api.model
    @tools.ormcache_context('model_name', keys=('lang',))
    def get_field_string(self, model_name):
        """ Return the translation of fields strings in the context's language.
        Note that the result contains the available translations only.

        :param model_name: the name of a model
        :return: the model's fields' strings as a dictionary `{field_name: field_string}`
        """
        fields = self.env['ir.model.fields'].sudo().search([('model', '=', model_name)])
        return {field.name: field.field_description for field in fields}

    @api.model
    @tools.ormcache_context('model_name', keys=('lang',))
    def get_field_help(self, model_name):
        """ Return the translation of fields help in the context's language.
        Note that the result contains the available translations only.

        :param model_name: the name of a model
        :return: the model's fields' help as a dictionary `{field_name: field_help}`
        """
        fields = self.env['ir.model.fields'].sudo().search([('model', '=', model_name)])
        return {field.name: field.help for field in fields}

    @api.model
    @tools.ormcache_context('model_name', 'field_name', keys=('lang',))
    def get_field_selection(self, model_name, field_name):
        """ Return the translation of a field's selection in the context's language.
        Note that the result contains the available translations only.

        :param model_name: the name of the field's model
        :param field_name: the name of the field
        :return: the fields' selection as a list
        """
        field = self.env['ir.model.fields']._get(model_name, field_name)
        return [(sel.value, sel.name) for sel in field.selection_ids]

    def write(self, vals):
        # try not using this api
        if 'value' in vals:
            old_values = {translation: translation.value or translation.src for translation in self}
        super().write(vals)
        # sync all translations to real records
        if 'value' in vals:
            for translation in self:
                if not translation.value:
                    continue
                model_name, field_name = translation.name.split(',')
                # src is ignored
                record = self.env[model_name].with_context(lang=translation.lang).browse(translation.res_id)
                if translation.type == 'model_terms':
                    record.update_field_translations(field_name, {translation.lang: {old_values[translation]: translation.value}})
                else:
                    record[field_name] = translation.value

    def _update_translations(self, vals_list):
        """ Update translations of type 'model' or 'model_terms'.

            This method is used for update of translations where the given
            ``vals_list`` is trusted to be the right values
            No new translation will be created
        """
        self.flush_model()
        grouped_rows = {}
        for vals in vals_list:
            key = (vals['lang'], vals['type'], vals['name'])
            grouped_rows.setdefault(key, [vals['value'], vals['src'], vals['state'], []])
            grouped_rows[key][3].append(vals['res_id'])

        for where, values in grouped_rows.items():
            self._cr.execute(
                """ UPDATE ir_translation
                    SET value=%s,
                        src=%s,
                        state=%s
                    WHERE lang=%s AND type=%s AND name=%s AND res_id in %s
                """,
                (values[0], values[1], values[2], where[0], where[1], where[2], tuple(values[3]))
            )
        self.invalidate_model(['value', 'src', 'state'])

    def _load_module_terms(self, modules, langs, overwrite=False):
        """ Load PO files of the given modules for the given languages. """
        # load i18n files
        for module_name in modules:
            modpath = get_module_path(module_name)
            if not modpath:
                continue
            for lang in langs:
                lang_code = tools.get_iso_codes(lang)
                lang_overwrite = overwrite
                base_lang_code = None
                if '_' in lang_code:
                    base_lang_code = lang_code.split('_')[0]

                # Step 1: for sub-languages, load base language first (e.g. es_CL.po is loaded over es.po)
                if base_lang_code:
                    base_trans_file = get_module_resource(module_name, 'i18n', base_lang_code + '.po')
                    if base_trans_file:
                        _logger.info('module %s: loading base translation file %s for language %s', module_name, base_lang_code, lang)
                        tools.trans_load(self._cr, base_trans_file, lang, verbose=False, overwrite=lang_overwrite)
                        lang_overwrite = True  # make sure the requested translation will override the base terms later

                    # i18n_extra folder is for additional translations handle manually (eg: for l10n_be)
                    base_trans_extra_file = get_module_resource(module_name, 'i18n_extra', base_lang_code + '.po')
                    if base_trans_extra_file:
                        _logger.info('module %s: loading extra base translation file %s for language %s', module_name, base_lang_code, lang)
                        tools.trans_load(self._cr, base_trans_extra_file, lang, verbose=False, overwrite=lang_overwrite)
                        lang_overwrite = True  # make sure the requested translation will override the base terms later

                # Step 2: then load the main translation file, possibly overriding the terms coming from the base language
                trans_file = get_module_resource(module_name, 'i18n', lang_code + '.po')
                if trans_file:
                    _logger.info('module %s: loading translation file (%s) for language %s', module_name, lang_code, lang)
                    tools.trans_load(self._cr, trans_file, lang, verbose=False, overwrite=lang_overwrite)
                elif lang_code != 'en_US':
                    _logger.info('module %s: no translation for language %s', module_name, lang_code)

                trans_extra_file = get_module_resource(module_name, 'i18n_extra', lang_code + '.po')
                if trans_extra_file:
                    _logger.info('module %s: loading extra translation file (%s) for language %s', module_name, lang_code, lang)
                    tools.trans_load(self._cr, trans_extra_file, lang, verbose=False, overwrite=lang_overwrite)
        return True
