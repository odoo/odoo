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
from operator import itemgetter
from osv import fields, osv
import sugar
from tools.translate import _
import sugarcrm_fields_mapping

def import_users(self, cr, uid, context=None):
    if not context:
        context = {}
    map_user = {'Users': 
           {'name': ['first_name', 'last_name'], 
           'login': 'user_name',
           'new_password' : 'pwd_last_changed',
           } ,
       }
    user_obj = self.pool.get('res.users')
    ids = self.search(cr, uid, [])
    PortType,sessionid = sugar.login(context.get('username',''), context.get('password',''))
    sugar_data = sugar.search(PortType,sessionid, 'Users')
    for val in sugar_data:
        user_ids = user_obj.search(cr, uid, [('login', '=', val.get('user_name'))])
        if user_ids:
            return user_ids[0]
        fields, datas = sugarcrm_fields_mapping.sugarcrm_fields_mapp(val, 'Users', map_user)
        openerp_val = dict(zip(fields,datas))
        openerp_val['context_lang'] = context.get('lang','en_US')
        new_user_id = user_obj.create(cr, uid, openerp_val, context)
    return new_user_id    
        
def import_opportunities(self, cr, uid, context=None):
   if not context:
       context = {} 
   user_id =  import_users(self, cr, uid, context) 
   map_opportunity = {'Opportunities':  {'name': 'name',
          'probability': 'probability',
          'planned_revenue': 'amount_usdollar',
          'date_deadline':'date_closed'
          },
      }
   ids = self.search(cr, uid, [])
   lead_pool = self.pool.get('crm.lead')
   PortType,sessionid = sugar.login(context.get('username',''), context.get('password',''))
   sugar_data = sugar.search(PortType,sessionid, 'Opportunities')
   for val in sugar_data:
       fields, datas = sugarcrm_fields_mapping.sugarcrm_fields_mapp(val, 'Opportunities', map_opportunity)
       openerp_val = dict(zip(fields,datas))
       openerp_val['type'] = 'opportunity'
       openerp_val['user_id'] = user_id
       new_lead_id = lead_pool.create(cr, uid, openerp_val, context)
   return new_lead_id           
        
def resolve_dependencies(self, cr, uid, dict, dep, key, context=None):
     if not context:
         context = {}
     for dependency in dep:
       resolve_dependencies(self, cr, uid, dict, dict[dependency]['dependencies'], key, context)
       dict[dependency]['process'](self, cr, uid, context)
     dict[key]['process'](self, cr, uid, context)
     return True 

MAP_FIELDS = {'Opportunities':  #Object Mapping name
                     { 'dependencies' : ['Users'],  #Object to import before this table
                       'process' : import_opportunities,
                     },
                'Users' : {'dependencies' : [],
                          'process' : import_users,
                         }
          } 

class import_sugarcrm(osv.osv):
     """Import SugarCRM DATA"""

     _name = "import.sugarcrm"
     _description = __doc__
     _columns = {
        'lead': fields.boolean('Leads', help="If Leads is checked, SugarCRM Leads data imported in openerp crm-Lead form"),
        'opportunity': fields.boolean('Opportunities', help="If Leads is checked, SugarCRM Leads data imported in openerp crm-Opportunity form"),
         'username': fields.char('User Name', size=64),
         'password': fields.char('Password', size=24),
     }
     _defaults = {
        'lead': lambda *a: True,
        'opportunity': lambda *a: True,
     }        

     def import_all(self, cr, uid, ids, context=None):
           if not context:
               context = {}
           for key in MAP_FIELDS.keys():
                resolve_dependencies(self, cr, uid, MAP_FIELDS, MAP_FIELDS[key]['dependencies'], key, context=context)
           obj_model = self.pool.get('ir.model.data')
           model_data_ids = obj_model.search(cr,uid,[('model','=','ir.ui.view'),('name','=','import.message.form')])
           resource_id = obj_model.read(cr, uid, model_data_ids, fields=['res_id'])
           return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'import.message',
                'views': [(resource_id,'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
            }                 

import_sugarcrm()
