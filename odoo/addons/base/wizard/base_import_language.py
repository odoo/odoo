# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
import os
from tempfile import TemporaryFile
from psycopg2 import ProgrammingError
from contextlib import closing

from odoo import api, fields, models, tools, sql_db, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BaseLanguageImport(models.TransientModel):
    _name = "base.language.import"
    _description = "Language Import"

    name = fields.Char('Language Name', required=True)
    code = fields.Char('ISO Code', size=6, required=True,
                       help="ISO Language and Country code, e.g. en_US")
    data = fields.Binary('File', required=True)
    filename = fields.Char('File Name', required=True)
    overwrite = fields.Boolean('Overwrite Existing Terms',
                               help="If you enable this option, existing translations (including custom ones) "
                                    "will be overwritten and replaced by those in this file")

    @api.multi
    def import_lang(self):
        this = self[0]
        this = this.with_context(overwrite=this.overwrite)

        self.env['res.lang'].load_lang(lang=self.code, lang_name=self.name)

        with TemporaryFile('wb+') as buf:
            try:
                buf.write(base64.decodestring(this.data))

                # now we determine the file format
                buf.seek(0)
                fileformat = os.path.splitext(this.filename)[-1][1:].lower()

                tools.trans_load_data(this._cr, buf, fileformat, this.code,
                                      lang_name=this.name, context=this._context)
            except ProgrammingError as e:
                _logger.exception('File unsuccessfully imported, due to a malformed file.')

                with closing(sql_db.db_connect(self._cr.dbname).cursor()) as cr:
                    raise UserError(_('File not imported due to a malformed file.\n\n' +
                                      'This issue can be caused by duplicates entries who are referring to the same field. ' +
                                      'Please check the content of the file you are trying to import.\n\n' +
                                      'Technical Details:\n%s') % tools.ustr(e))
            except Exception as e:
                _logger.exception('File unsuccessfully imported, due to format mismatch or a malformed file.')
                raise UserError(_('File not imported due to format mismatch or a malformed file. (Valid formats are .csv, .po, .pot)\n\n' +
                                  'Technical Details:\n%s') % tools.ustr(e))
        return True
