# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
from tempfile import TemporaryFile
from os.path import splitext

from odoo import fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools.translate import TranslationImporter

_logger = logging.getLogger(__name__)


class BaseLanguageImport(models.TransientModel):
    _name = "base_import.import.translation"
    _description = "Language Import"

    def _get_default_lang(self):
        return self.env["res.lang"]._lang_get(self.env.lang)

    lang_id = fields.Many2one('res.lang', default=_get_default_lang, required=True)
    data = fields.Binary('File', required=True, attachment=False)
    filename = fields.Char('File Name', required=True)

    def import_lang(self):
        self.ensure_one()
        try:
            with TemporaryFile('wb+') as buf:
                buf.write(base64.decodebytes(self.data))
                fileformat = splitext(self.filename)[-1][1:].lower()
                translation_importer = TranslationImporter(self.env.cr, user_id=self.env.user.id)
                translation_importer.load(buf, fileformat, self.lang_id.code)
                translation_importer.save(force_overwrite=True)
        except Exception as e:
            _logger.exception('File unsuccessfully imported, due to format mismatch.')
            raise UserError(
                _('File %r not imported due to format mismatch or a malformed file.'
                  ' (Valid formats are .csv, .po, .pot)\n\nTechnical Details:\n%s') % \
                (self.filename, tools.ustr(e))
            )
