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


