# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
import os
from tempfile import TemporaryFile

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

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
                               help="If you enable this option, existing translations (including custom ones) "
                                    "will be overwritten and replaced by those in this file")

    def import_lang(self):
        this = self[0]
        this = this.with_context(overwrite=this.overwrite)
        with TemporaryFile('wb+') as buf:
            try:
                buf.write(base64.decodestring(this.data))

                # now we determine the file format
                buf.seek(0)
                fileformat = os.path.splitext(this.filename)[-1][1:].lower()

                tools.trans_load_data(this._cr, buf, fileformat, this.code,
                                      lang_name=this.name, context=this._context)
            except Exception as e:
                _logger.exception('File unsuccessfully imported, due to format mismatch.')
                raise UserError(
                    _('File %r not imported due to format mismatch or a malformed file.'
                      ' (Valid formats are .csv, .po, .pot)\n\nTechnical Details:\n%s') % \
                    (this.filename, tools.ustr(e))
                )
        return True
