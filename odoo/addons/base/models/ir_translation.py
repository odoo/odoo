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
