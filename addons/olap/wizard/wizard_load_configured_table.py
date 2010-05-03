##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
import time

import wizard
import pooler
import netsvc

class wizard_load_configured_table(wizard.interface):
    def _get_table_data(self, cr, uid, data, context={}):
        pool_obj = pooler.get_pool(cr.dbname)
        
#        vals={}
#        vals['configure']=True
#        vals['state']='dbconfigure'
#        pooler.get_pool(cr.dbname).get('olap.schema').write(cr,uid,data['id'],vals)
        
        wf_service = netsvc.LocalService('workflow')
        wf_service.trg_validate(uid, 'olap.schema', data['id'], 'dbconfigure', cr)
        
        lines=pool_obj.get('olap.schema').read(cr, uid, data['id'],context={})
        fact_ids=pool_obj.get('olap.database.tables').search(cr, uid, ([('fact_database_id','=',lines['database_id'][0])]),context={})
        model_data_ids = pool_obj.get('ir.model.data').search(cr,uid,[('model','=','ir.ui.view'),('name','=','view_olap_database_tables_form')],context={})
        resource_id = pool_obj.get('ir.model.data').read(cr,uid,model_data_ids,fields=['res_id'])[0]['res_id']
        
        return {
            'domain': "[('id','in', ["+','.join(map(str,fact_ids))+"])]",
            'name': 'Database Tables',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'olap.database.tables',
            'views': [(False,'tree'),(resource_id,'form')],
            'type': 'ir.actions.act_window'
        }
        
    states = {
        'init' : {
            'actions' : [],
            'result' : {'type' : 'action' ,'action':_get_table_data,'state':'end'}
        }
      }

wizard_load_configured_table('olap.load.configuration.table')
