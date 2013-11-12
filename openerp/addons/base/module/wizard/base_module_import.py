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

import base64
import os
from StringIO import StringIO
import zipfile

from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _

ADDONS_PATH = tools.config['addons_path'].split(",")[-1]

class base_module_import(osv.osv_memory):
    """ Import Module """

    _name = "base.module.import"
    _description = "Import Module"
    _columns = {
          'module_file': fields.binary('Module .ZIP file', required=True),
          'state':fields.selection([('init','init'),('done','done')],
                                   'Status', readonly=True),
          'module_name': fields.char('Module Name', size=128),
    }

    _defaults = {  
        'state': 'init',
    }

    def importzip(self, cr, uid, ids, context):
        #TODO: drop this model and the corresponding view/action in trunk
        raise NotImplementedError('This feature is not available')

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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
