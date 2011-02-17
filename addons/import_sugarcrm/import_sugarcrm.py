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

class import_sugarcrm(osv.osv):
     """Import SugarCRM DATA"""

     _name = "import.sugarcrm"
     _description = __doc__
     _columns = {
        'mod_name':fields.selection([
            ('lead','Leads'),
            ('opportunity','Opportunities'),
            ('accounts','Accounts'),
            ('contact','Contacts'),
        ],'Module Name', help="Module Name is used to specify which Module data want to Import"),
         'username': fields.char('User Name', size=64),
         'password': fields.char('Password', size=24),
     }

     def _get_all(self, cr, uid, model, sugar_val, context=None):
           models = self.pool.get(model)
           all_model_ids = models.search(cr, uid, [('name', '=', sugar_val)])
           output = [(False, '')]
           output = sorted([(o.id, o.name)
                    for o in models.browse(cr, uid, all_model_ids,
                                           context=context)],
                   key=itemgetter(1))
           return output

     def _get_all_states(self, cr, uid, sugar_val, context=None):
        return self._get_all(
            cr, uid, 'res.country.state', sugar_val, context=context)

     def _get_all_countries(self, cr, uid, sugar_val, context=None):
        return self._get_all(
            cr, uid, 'res.country', sugar_val, context=context)

     def _create_lead(self, cr, uid, sugar_val, country, state, context=None):
           lead_pool = self.pool.get("crm.lead")
           
           stage_id = ''
           stage_pool = self.pool.get('crm.case.stage')
           if sugar_val.get('status','') == 'New':
               sugar_stage = 'New'
           elif sugar_val.get('status','') == 'Assigned':
               sugar_stage = 'Qualification'
           elif sugar_val.get('status','') == 'In Progress':
               sugar_stage = 'Proposition'
           elif sugar_val.get('status','') == 'Recycled':
               sugar_stage = 'Negotiation'
           elif sugar_val.get('status','') == 'Dead':
               sugar_stage = 'Lost'
           else:
               sugar_stage = ''
           stage_ids = stage_pool.search(cr, uid, [("type", '=', 'lead'), ('name', '=', sugar_stage)])

           for stage in stage_pool.browse(cr, uid, stage_ids):
               stage_id = stage.id     
                     
           vals = {'name': sugar_val.get('first_name','')+' '+ sugar_val.get('last_name',''),
                   'contact_name': sugar_val.get('first_name','')+' '+ sugar_val.get('last_name',''),
                   'user_id':sugar_val.get('created_by',''),
                   'description': sugar_val.get('description',''),
                   'partner_name': sugar_val.get('first_name','')+' '+ sugar_val.get('last_name',''),
                   'email_from': sugar_val.get('email1',''),
                   'stage_id': stage_id or '',
                   'phone': sugar_val.get('phone_work',''),
                   'mobile': sugar_val.get('phone_mobile',''),
                   'write_date':sugar_val.get('date_modified',''),
                   'function':sugar_val.get('title',''),
                   'street': sugar_val.get('primary_address_street',''),
                   'zip': sugar_val.get('primary_address_postalcode',''),
                   'city':sugar_val.get('primary_address_city',''),
                   'country_id': country and country[0][0] or False,
                   'state_id': state and state[0][0] or False
           }
           new_lead_id = lead_pool.create(cr, uid, vals)
           return new_lead_id

     def _create_opportunity(self, cr, uid, sugar_val, country, state, context=None):

           lead_pool = self.pool.get("crm.lead")
           stage_id = ''
           stage_pool = self.pool.get('crm.case.stage')
           if sugar_val.get('sales_stage','') == 'Need Analysis':
               sugar_stage = 'New'
           elif sugar_val.get('sales_stage','') == 'Closed Lost':
               sugar_stage = 'Lost'
           elif sugar_val.get('sales_stage','') == 'Closed Won':
               sugar_stage = 'Won'
           elif sugar_val.get('sales_stage','') == 'Value Proposition':
               sugar_stage = 'Proposition'
           elif sugar_val.get('sales_stage','') == 'Negotiation/Review':
               sugar_stage = 'Negotiation'
           else:
               sugar_stage = ''
           stage_ids = stage_pool.search(cr, uid, [("type", '=', 'opportunity'), ('name', '=', sugar_stage)])           
           for stage in stage_pool.browse(cr, uid, stage_ids):
               stage_id = stage.id
           vals = {'name': sugar_val.get('name',''),
               'probability': sugar_val.get('probability',''),
               'user_id': sugar_val.get('created_by', ''),
               'stage_id': stage_id or '',
               'type': 'opportunity',
               'user_id': sugar_val.get('created_by',''),
               'planned_revenue': sugar_val.get('amount_usdollar'),
               'write_date':sugar_val.get('date_modified',''),
           }
           new_opportunity_id = lead_pool.create(cr, uid, vals)
           return new_opportunity_id

     def _create_contact(self, cr, uid, sugar_val, country, state, context=None):
           addr_pool = self.pool.get("res.partner.address")
           partner_pool = self.pool.get("res.partner")

           vals =  {'name': sugar_val.get('first_name','')+' '+ sugar_val.get('last_name',''),
                            'partner_id': sugar_val.get('account_id'),
           }
           new_partner_id = partner_pool.create(cr, uid, vals)
           addr_vals = {'partner_id': new_partner_id,
                        'name': sugar_val.get('first_name','')+' '+ sugar_val.get('last_name',''),
                        'function':sugar_val.get('title',''),
                        'phone': sugar_val.get('phone_home'),
                        'mobile': sugar_val.get('phone_mobile'),
                        'fax': sugar_val.get('phone_fax'),
                        'street': sugar_val.get('primary_address_street',''),
                        'zip': sugar_val.get('primary_address_postalcode',''),
                        'city':sugar_val.get('primary_address_city',''),
                        'country_id': country and country[0][0] or False,
                        'state_id': state and state[0][0] or False,
                        'email': sugar_val.get('email1'),
           }
           addr_pool.create(cr, uid, addr_vals)
           return new_partner_id


     def import_data(self, cr, uid, ids,context=None):
       if not context:
        context={}
       for current in self.browse(cr, uid, ids):
        if current.mod_name == 'lead' or current.mod_name == 'opportunity':
          module_name = 'crm'

        elif current.mod_name == "accounts":
          module_name = 'account'
        else:
          module_name = 'base'

        ids = self.pool.get("ir.module.module").search(cr, uid, [("name", '=',
           module_name), ('state', '=', 'installed')])
        if not ids:
           raise osv.except_osv(_('Error !'), _('Please  Install %s Module') % (module_name))

        if current.mod_name == 'lead':
           sugar_name = "Leads"
        elif current.mod_name == 'opportunity':
           sugar_name="Opportunities"
        elif current.mod_name == 'accounts':
           sugar_name="Accounts"
        elif current.mod_name == 'contact':
           sugar_name="Contacts"
       PortType,sessionid = sugar.login(context.get('username',''), context.get('password',''))
       sugar_data = sugar.search(PortType,sessionid,sugar_name)
       if sugar_data:    
           for sugar_val in sugar_data:
                country = self._get_all_countries(cr, uid, sugar_val.get('primary_address_country'), context)
                state = self._get_all_states(cr, uid, sugar_val.get('primary_address_state'), context)
                if sugar_name == "Leads":
                    self._create_lead(cr, uid, sugar_val, country, state, context)
    
                elif sugar_name == "Opportunities":
                    self._create_opportunity(cr, uid, sugar_val, country, state,context)
    
                elif sugar_name == "Contacts":
                    self._create_contact(cr, uid, sugar_val, country, state, context)
                    
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





