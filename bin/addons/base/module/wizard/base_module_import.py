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


import pooler
import os
import tools

import zipfile
from StringIO import StringIO
import base64
from tools.translate import _
from osv import osv, fields

class base_module_import(osv.osv_memory):
    """ Import Module """

    _name = "base.module.import"
    _description = "Import Module"

    _columns = {
          'module_file': fields.binary('Module .ZIP file', required=True),
    }

    def importzip(self, cr, uid, ids, context):
        module_obj= self.pool.get('ir.module.module')
        active_ids = context and context.get('active_ids', False)
        data = self.browse(cr, uid, ids , context=context)[0]
        module_data = data.module_file

        val =base64.decodestring(module_data)
        fp = StringIO()
        fp.write(val)
        fdata = zipfile.ZipFile(fp, 'r')
        fname = fdata.namelist()[0]
        module_name = os.path.split(fname)[0]

        ad = tools.config['addons_path']

        fname = os.path.join(ad,module_name+'.zip')
        try:
            fp = file(fname, 'wb')
            fp.write(val)
            fp.close()
        except IOError, e:
            raise osv.except_osv(_('Error !'), _('Can not create the module file: %s !') % (fname,) )

        module_obj.update_list(cr, uid,{'module_name': module_name,})
        data_obj = self.pool.get('ir.model.data')
        id2 = data_obj._get_id(cr, uid, 'base', 'view_base_module_import_msg')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id

        module_name = module_obj.browse(cr, uid, ids, context=context)
        return {
            'domain': str([('name', '=', module_name)]),
            'name': 'Message',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'base.module.import.msg',
            'views': [(id2, 'form')],
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

base_module_import()

class base_module_import_msg(osv.osv_memory):
    """   message    """
    _name = "base.module.import.msg"
    _description = "Message"

    def action_module_open(self, cr, uid, ids, context):
        module_obj = self.pool.get('base.module.import')
        data = module_obj.browse(cr, uid, ids , context=context)[0]
        module_data = data.module_file

        val =base64.decodestring(module_data)
        fp = StringIO()
        fp.write(val)
        fdata = zipfile.ZipFile(fp, 'r')
        fname = fdata.namelist()[0]
        module_name = os.path.split(fname)[0]

        return {
            'domain': str([('name', '=', module_name)]),
            'name': 'Module List',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'ir.module.module',
            'type': 'ir.actions.act_window',
        }


base_module_import_msg()