# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
import base64
import logging
from tempfile import TemporaryFile

from openerp import tools
from openerp.osv import osv, fields
from openerp.exceptions import UserError
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class base_language_import(osv.osv_memory):
    """ Language Import """

    _name = "base.language.import"
    _description = "Language Import"
    _columns = {
        'name': fields.char('Language Name', required=True),
        'code': fields.char('ISO Code', size=5, help="ISO Language and Country code, e.g. en_US", required=True),
        'data': fields.binary('File', required=True),
        'filename': fields.char('File Name', required=True),
        'overwrite': fields.boolean('Overwrite Existing Terms',
                                    help="If you enable this option, existing translations (including custom ones) "
                                         "will be overwritten and replaced by those in this file"),
    }

    def import_lang(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        this = self.browse(cr, uid, ids[0])
        if this.overwrite:
            context = dict(context, overwrite=True)
        fileobj = TemporaryFile('w+')
        try:
            fileobj.write(base64.decodestring(this.data))
    
            # now we determine the file format
            fileobj.seek(0)
            fileformat = os.path.splitext(this.filename)[-1][1:].lower()
    
            tools.trans_load_data(cr, fileobj, fileformat, this.code, lang_name=this.name, context=context)
        except Exception, e:
            _logger.exception('File unsuccessfully imported, due to format mismatch.')
            raise UserError(_('File not imported due to format mismatch or a malformed file. (Valid formats are .csv, .po, .pot)\n\nTechnical Details:\n%s') % tools.ustr(e))
        finally:
            fileobj.close()
        return True
