# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
from tempfile import TemporaryFile
from os.path import splitext

from odoo import api, fields, models, tools, sql_db, _
from odoo.exceptions import UserError
from odoo.tools.translate import TranslationImporter

_logger = logging.getLogger(__name__)


class BaseLanguageImport(models.TransientModel):
    _name = "base.language.import"
    _description = "Language Import"

    name = fields.Char('Language Name', required=True)
    code = fields.Char('ISO Code', size=6, required=True,
                       help="ISO Language and Country code, e.g. en_US")
    data = fields.Binary('File', required=True, attachment=False)
    filename = fields.Char('File Name', required=True)
    overwrite = fields.Boolean('Overwrite Existing Terms',
                               default=True,
                               help="If you enable this option, existing translations (including custom ones) "
                                    "will be overwritten and replaced by those in this file")

    def import_lang(self):
        self.ensure_one()
        Lang = self.env["res.lang"]
        try:
            if not Lang._activate_lang(self.code):
                Lang._create_lang(self.code, lang_name=self.name)
            with TemporaryFile('wb+') as buf:
                buf.write(base64.decodebytes(self.data))
                fileformat = splitext(self.filename)[-1][1:].lower()
                translation_importer = TranslationImporter(self.env.cr)
                translation_importer.load(buf, fileformat, self.code)
                translation_importer.save(overwrite=self.overwrite)
        except Exception as e:
            _logger.exception('File unsuccessfully imported, due to format mismatch.')
            raise UserError(
                _('File %r not imported due to format mismatch or a malformed file.'
                  ' (Valid formats are .csv, .po, .pot)\n\nTechnical Details:\n%s') % \
                (self.filename, tools.ustr(e))
            )
