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
from osv import fields, osv
from tools.translate import _
from import_sugarcrm import sugar

class sugarcrm_login(osv.osv):
    """SugarCRM Login"""

    _name = "sugarcrm.login"
    _description = __doc__
    _columns = {
        'username': fields.char('User Name', size=64, required=True),
        'password': fields.char('Password', size=24,required=True),
         'url' : fields.char('SugarCRM Path', size=264, required=True, help="Path for SugarCRM connection should be 'http://localhost/sugarcrm/soap.php' Format."),
    }
    _defaults = {
       'username' : 'admin',
       'password' : 'admin',
       'url':  "http://localhost/sugarcrm/soap.php"
    }

    def open_import(self, cr, uid, ids, context=None):

        for current in self.browse(cr, uid, ids, context):
            PortType,sessionid = sugar.login(current.username, current.password, current.url)
            if sessionid == '-1':
                raise osv.except_osv(_('Error !'), _('Authentication error !\nBad Username or Password !'))

            obj_model = self.pool.get('ir.model.data')
            model_data_ids = obj_model.search(cr,uid,[('model','=','ir.ui.view'),('name','=','import.sugarcrm.form')])
            resource_id = obj_model.read(cr, uid, model_data_ids, fields=['res_id'])
            context.update({'rec_id': ids, 'username': current.username, 'password': current.password, 'url': current.url})
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'import.sugarcrm',
            'views': [(resource_id,'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }

sugarcrm_login()
