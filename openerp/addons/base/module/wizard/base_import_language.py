# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import tools
import base64
from tempfile import TemporaryFile
from osv import osv, fields

class base_language_import(osv.osv_memory):
    """ Language Import """

    _name = "base.language.import"
    _description = "Language Import"
    _inherit = "ir.wizard.screen"

    _columns = {
        'name': fields.char('Language Name',size=64 , required=True),
        'code': fields.char('Code (eg:en__US)',size=5 , required=True),
        'data': fields.binary('File', required=True),
        'overwrite': fields.boolean('Overwrite Existing Terms',
                                    help="If you enable this option, existing translations (including custom ones) "
                                         "will be overwritten and replaced by those in this file"),
    }

    def import_lang(self, cr, uid, ids, context=None):
        """
            Import Language
            @param cr: the current row, from the database cursor.
            @param uid: the current user’s ID for security checks.
            @param ids: the ID or list of IDs
            @param context: A standard dictionary
        """
        if context is None:
            context = {}
        import_data = self.browse(cr, uid, ids)[0]
        if import_data.overwrite:
            context.update(overwrite=True)
        fileobj = TemporaryFile('w+')
        fileobj.write(base64.decodestring(import_data.data))

        # now we determine the file format
        fileobj.seek(0)
        first_line = fileobj.readline().strip().replace('"', '').replace(' ', '')
        fileformat = first_line.endswith("type,name,res_id,src,value") and 'csv' or 'po'
        fileobj.seek(0)

        tools.trans_load_data(cr, fileobj, fileformat, import_data.code, lang_name=import_data.name, context=context)
        tools.trans_update_res_ids(cr)
        fileobj.close()
        return {}

base_language_import()
