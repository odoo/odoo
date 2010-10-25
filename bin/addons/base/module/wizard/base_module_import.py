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
    _inherit = "ir.wizard.screen"
    _description = "Import Module"

    _columns = {
          'module_file': fields.binary('Module .ZIP file', required=True),
          'state':fields.selection([('init','init'),('done','done')], 'state', readonly=True),
          'module_name': fields.char('Module Name', size=128),
    }

    _defaults = {  
        'state': 'init',
    }

    def importzip(self, cr, uid, ids, context):
        (data,) = self.browse(cr, uid, ids , context=context)
        module_data = data.module_file

        val = base64.decodestring(module_data)
        fp = StringIO()
        fp.write(val)
        fdata = zipfile.ZipFile(fp, 'r')
        fname = fdata.namelist()[0]
        module_name = os.path.split(fname)[0]

        ad = tools.config['addons_path']

        fname = os.path.join(ad, module_name+'.zip')
        try:
            fp = file(fname, 'wb')
            fp.write(val)
            fp.close()
        except IOError:
            raise osv.except_osv(_('Error !'), _('Can not create the module file: %s !') % (fname,) )

        self.pool.get('ir.module.module').update_list(cr, uid, {'module_name': module_name,})
        self.write(cr, uid, ids, {'state':'done', 'module_name': module_name}, context)
        return False

    def action_module_open(self, cr, uid, ids, context):
        (data,) = self.browse(cr, uid, ids , context=context)
        return {
            'domain': str([('name', '=', data.module_name)]),
            'name': 'Modules',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'ir.module.module',
            'type': 'ir.actions.act_window',
        }

base_module_import()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: