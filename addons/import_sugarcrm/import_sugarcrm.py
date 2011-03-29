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
from operator import itemgetter
import sugar
import sugarcrm_fields_mapping
from tools.translate import _
import pprint
pp = pprint.PrettyPrinter(indent=4)

def create_mapping(obj, cr, uid, res_model, open_id, sugar_id, context):
    model_data = {
        'name':  sugar_id,
        'model': res_model,
        'module': 'sugarcrm_import',
        'res_id': open_id
    }
    model_obj = obj.pool.get('ir.model.data')
    model_obj.create(cr, uid, model_data, context=context)

def find_mapped_id(obj, cr, uid, res_model, sugar_id, context):
    model_obj = obj.pool.get('ir.model.data')
    return model_obj.search(cr, uid, [('model', '=', res_model), ('module', '=', 'sugarcrm_import'), ('name', '=', sugar_id)], context=context)

def get_all(sugar_obj, cr, uid, model, sugar_val, context=None):
       models = sugar_obj.pool.get(model)
       str = sugar_val[0:2]
       all_model_ids = models.search(cr, uid, [('name', '=', sugar_val)]) or models.search(cr, uid, [('code', '=', str.upper())]) 
       output = [(False, '')]
       output = sorted([(o.id, o.name)
                for o in models.browse(cr, uid, all_model_ids,
                                       context=context)],
               key=itemgetter(1))
       return output

def get_all_states(sugar_obj, cr, uid, sugar_val, context=None):
    return get_all(sugar_obj,
        cr, uid, 'res.country.state', sugar_val, context=context)

def get_all_countries(sugar_obj, cr, uid, sugar_val, context=None):
    return get_all(sugar_obj,
        cr, uid, 'res.country', sugar_val, context=context)

def import_partner_address(sugar_obj, cr, uid, context=None):
    if not context:
        context = {}
    res_country_obj = sugar_obj.pool.get('res.country')
    map_partner_address = {
             'id': 'id',              
             'name': ['first_name', 'last_name'],
            'phone': 'phone_work',
            'mobile': 'phone_mobile',
            'fax': 'phone_fax',
            'function': 'title',
            'street': 'primary_address_street',
            'zip': 'primary_address_postalcode',
            'city': 'primary_address_city',
            'country_id/.id': 'country_id/.id',
            'state_id/.id': 'state_id/id'
            }
    address_obj = sugar_obj.pool.get('res.partner.address')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'Contacts')
    for val in sugar_data:
        str = val.get('primary_address_country')[0:2]
        country = get_all_countries(sugar_obj, cr, uid, val.get('primary_address_country'), context)
        if country:
            country_id = country and country[0][0]
        else:
           country_id = res_country_obj.create(cr, uid, {'name': val.get('primary_address_country'), 'code': str})
        state = get_all_states(sugar_obj,cr, uid, val.get('primary_address_state'), context)
        val['country_id/.id'] =  country_id
        val['state_id/.id'] =  state and state[0][0] or False        
        fields, datas = sugarcrm_fields_mapping.sugarcrm_fields_mapp(val, map_partner_address)
        address_obj.import_data(cr, uid, fields, [datas], mode='update', current_module='sugarcrm_import', context=context)

def import_users(sugar_obj, cr, uid, context=None):
    if not context:
        context = {}
    map_user = {'id' : 'id', 
             'name': ['first_name', 'last_name'],
            'login': 'user_name',
            
            'context_lang' : 'context_lang',
            'password' : 'password',
            '.id' : '.id',
            'context_department_id': 'department'
            } 
    user_obj = sugar_obj.pool.get('res.users')
    department_obj = sugar_obj.pool.get('hr.department')
    PortType,sessionid = sugar.login(context.get('username',''), context.get('password',''), context.get('url',''))
    sugar_data = sugar.search(PortType,sessionid, 'Users')
    for val in sugar_data:
        user_ids = user_obj.search(cr, uid, [('login', '=', val.get('user_name'))])
        if user_ids: 
            val['.id'] = str(user_ids[0])
        else:
            val['password'] = 'sugarcrm' #default password for all user
#            cr.execute('SELECT * FROM users_signatures u LIMIT 0,1000')
        new_department_id = department_obj.create(cr, uid, {'name': val.get('department')})
        val['context_department_id'] = new_department_id     
        val['context_lang'] = context.get('lang','en_US')
        fields, datas = sugarcrm_fields_mapping.sugarcrm_fields_mapp(val, map_user)
        #All data has to be imported separatly because they don't have the same field
        user_obj.import_data(cr, uid, fields, [datas], mode='update', current_module='sugarcrm_import', context=context)

def get_lead_status(surgar_obj, cr, uid, sugar_val,context=None):
    if not context:
        context = {}
    stage_id = ''
    stage_dict = {'status': #field in the sugarcrm database
        { #Mapping of sugarcrm stage : openerp opportunity stage
            'New' : 'New',
            'Assigned':'Qualification',
            'In Progress': 'Proposition',
            'Recycled': 'Negotiation',
            'Dead': 'Lost'
        },}
    stage = stage_dict['status'].get(sugar_val['status'], '')
    stage_pool = surgar_obj.pool.get('crm.case.stage')
    stage_ids = stage_pool.search(cr, uid, [('type', '=', 'lead'), ('name', '=', stage)])
    for stage in stage_pool.browse(cr, uid, stage_ids, context):
        stage_id = stage.id
    return stage_id

def get_lead_state(surgar_obj, cr, uid, sugar_val,context=None):
    if not context:
        context = {}
    state = ''
    state_dict = {'status': #field in the sugarcrm database
        { #Mapping of sugarcrm stage : openerp opportunity stage
            'New' : 'draft',
            'Assigned':'open',
            'In Progress': 'open',
            'Recycled': 'cancel',
            'Dead': 'done'
        },}
    state = state_dict['status'].get(sugar_val['status'], '')
    return state

def get_opportunity_status(surgar_obj, cr, uid, sugar_val,context=None):
    if not context:
        context = {}
    stage_id = ''
    stage_dict = { 'sales_stage':
            {#Mapping of sugarcrm stage : openerp opportunity stage Mapping
               'Need Analysis': 'New',
               'Closed Lost': 'Lost',
               'Closed Won': 'Won',
               'Value Proposition': 'Proposition',
                'Negotiation/Review': 'Negotiation'
            },
    }
    stage = stage_dict['sales_stage'].get(sugar_val['sales_stage'], '')
    stage_pool = surgar_obj.pool.get('crm.case.stage')
    stage_ids = stage_pool.search(cr, uid, [('type', '=', 'opportunity'), ('name', '=', stage)])
    for stage in stage_pool.browse(cr, uid, stage_ids, context):
        stage_id = stage.id
    return stage_id

def get_user_address(sugar_obj, cr, uid, val, context=None):
    address_obj = sugar_obj.pool.get('res.partner.address')
    
    map_user_address = {
    'name': ['first_name', 'last_name'],
    'city': 'address_city',
    'country_id.id': 'address_country',
    'state_id.id': 'address_state',
    'street': 'address_street',
    'zip': 'address_postalcode',
    }
    address_ids = address_obj.search(cr, uid, [('name', '=',val.get('first_name') +''+ val.get('last_name'))])
    
    fields, datas = sugarcrm_fields_mapping.sugarcrm_fields_mapp(val, map_user_address)
    dict_val = dict(zip(fields,datas))
    
    if address_ids:
        address_obj.write(cr, uid, address_ids, dict_val)
    else:        
        new_address_id = address_obj.create(cr,uid, dict_val)
        return new_address_id
    
def get_address_type(sugar_obj, cr, uid, val, map_partner_address, type, context=None):
        address_obj = sugar_obj.pool.get('res.partner.address')
        res_country_obj = sugar_obj.pool.get('res.country')
        new_address_id = False
        if type == 'invoice':
            type_address = 'billing'
        else:
            type_address = 'shipping'     
    
        map_partner_address.update({
            'street': type_address + '_address_street',
            'zip': type_address +'_address_postalcode',
            'city': type_address +'_address_city',
             'country_id': 'country_id',
             'type': 'type',
            })
        val['type'] = type
        str = val.get(type_address +'_address_country')[0:2]
        country = get_all_countries(sugar_obj, cr, uid, val.get(type_address +'_address_country'), context)
        state = get_all_states(sugar_obj, cr, uid, val.get(type_address +'_address_state'), context)
        val['country_id'] =  country and country[0][0] or res_country_obj.create(cr, uid, {'name': val.get(type_address +'_address_country'), 'code': str}),
        val['state_id'] =  state and state[0][0] or  False,
        fields, datas = sugarcrm_fields_mapping.sugarcrm_fields_mapp(val, map_partner_address)
        #Convert To list into Dictionary(Key, val). value pair.
        dict_val = dict(zip(fields,datas))
        new_address_id = address_obj.create(cr,uid, dict_val)
        return new_address_id
    
def get_address(sugar_obj, cr, uid, val, context=None):
    map_partner_address={}
    address_id=[]
    fields=[]
    datas=[]
    address_obj = sugar_obj.pool.get('res.partner.address')
    address_ids = address_obj.search(cr, uid, [('name', '=',val.get('name')), ('type', 'in', ('invoice', 'delivery')), ('street', '=', val.get('billing_address_street'))])
    if address_ids:
        return address_ids 
    else:
        map_partner_address = {
            'id': 'id',                    
            'name': 'name',
            'partner_id/id': 'account_id',
            'phone': 'phone_office',
            'mobile': 'phone_mobile',
            'fax': 'phone_fax',
            'type': 'type',
            }
        if val.get('billing_address_street'):
            address_id.append(get_address_type(sugar_obj, cr, uid, val, map_partner_address, 'invoice', context))
            
        if val.get('shipping_address_street'):
            address_id.append(get_address_type(sugar_obj, cr, uid, val, map_partner_address, 'delivery', context))
        return address_id

def import_partners(sugar_obj, cr, uid, context=None):
    if not context:
        context = {}
    map_partner = {
                'id': 'id',
                'name': 'name',
                'website': 'website',
                'user_id/id': 'assigned_user_id',
                'ref': 'sic_code',
                'comment': ['description', 'employees', 'ownership', 'annual_revenue', 'rating', 'industry', 'ticker_symbol'],
                'customer': 'customer',
                'supplier': 'supplier', 
                }
        
    partner_obj = sugar_obj.pool.get('res.partner')
    address_obj = sugar_obj.pool.get('res.partner.address')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'Accounts')
    
    for val in sugar_data:
        add_id = get_address(sugar_obj, cr, uid, val, context)
        if val.get('account_type') in  ('Customer', 'Prospect', 'Other'):
            val['customer'] = '1'
        else:
            val['supplier'] = '1'
        fields, datas = sugarcrm_fields_mapping.sugarcrm_fields_mapp(val, map_partner)
        partner_obj.import_data(cr, uid, fields, [datas], mode='update', current_module='sugarcrm_import', context=context)
        for address in  address_obj.browse(cr,uid,add_id):
            data_id = partner_obj.search(cr,uid,[('name','like',address.name),('website','like',val.get('website'))])
            if data_id:
                address_obj.write(cr,uid,address.id,{'partner_id':data_id[0]})                
    return True


def import_resources(sugar_obj, cr, uid, context=None):
    if not context:
        context = {}
    map_resource = {'id' : 'user_hash',
                    'name': ['first_name', 'last_name'],
    }
    resource_obj = sugar_obj.pool.get('resource.resource')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'Employees')
    for val in sugar_data:
        fields, datas = sugarcrm_fields_mapping.sugarcrm_fields_mapp(val, map_resource)
        resource_obj.import_data(cr, uid, fields, [datas], mode='update', current_module='sugarcrm_import', context=context)


def import_employees(sugar_obj, cr, uid, context=None):
    if not context:
        context = {}
    map_employee = {'id' : 'user_hash',
                    'name': ['first_name', 'last_name'],
                    'work_phone': 'phone_work',
                    'mobile_phone':  'phone_mobile',
                    'user_id/name': ['first_name', 'last_name'], 
                    'resource_id/.id': 'resource_id/.id', 
                    'address_home_id/.id': 'address_home_id/.id',
                    'notes': 'description',
                    #TODO: Creation of Employee create problem.
                 #   'coach_id/id': 'reports_to_id',
                    'job_id/.id': 'job_id/.id'
    }
    employee_obj = sugar_obj.pool.get('hr.employee')
    job_obj = sugar_obj.pool.get('hr.job')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'Employees')
    for val in sugar_data:
        address_id = get_user_address(sugar_obj, cr, uid, val, context)
        val['address_home_id/.id'] = address_id
        model_ids = find_mapped_id(sugar_obj, cr, uid, 'resource.resource', val.get('user_hash')+ '_resource_resource', context)
        resource_id = sugar_obj.pool.get('ir.model.data').browse(cr, uid, model_ids)
        if resource_id:
            val['resource_id/.id'] = resource_id[0].res_id
        new_job_id = job_obj.create(cr, uid, {'name': val.get('title')})
        val['job_id/.id'] = new_job_id
        fields, datas = sugarcrm_fields_mapping.sugarcrm_fields_mapp(val, map_employee)
        employee_obj.import_data(cr, uid, fields, [datas], mode='update', current_module='sugarcrm_import', context=context)

    
def import_leads(sugar_obj, cr, uid, context=None):
    if not context:
        context = {}
    map_lead = {
            'id' : 'id',
            'name': ['first_name', 'last_name'],
            'contact_name': ['first_name', 'last_name'],
            'description': 'description',
            'partner_name': 'account_name',
            'email_from': 'email1',
            'phone': 'phone_work',
            'mobile': 'phone_mobile',
            'function':'title',
            'street': 'primary_address_street',
            'zip': 'primary_address_postalcode',
            'city':'primary_address_city',
            'user_id/id' : 'assigned_user_id',
            'stage_id.id' : 'stage_id.id',
            'type' : 'type',
            'state': 'state',
            }
        
    lead_obj = sugar_obj.pool.get('crm.lead')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'Leads')
    for val in sugar_data:
        val['type'] = 'lead'
        stage_id = get_lead_status(sugar_obj, cr, uid, val, context)
        val['stage_id.id'] = stage_id
        val['state'] = get_lead_state(sugar_obj, cr, uid, val,context)
        fields, datas = sugarcrm_fields_mapping.sugarcrm_fields_mapp(val, map_lead)
        lead_obj.import_data(cr, uid, fields, [datas], mode='update', current_module='sugarcrm_import', context=context)

def import_opportunities(sugar_obj, cr, uid, context=None):
    if not context:
        context = {}
    map_opportunity = {'id' : 'id',
        'name': 'name',
        'probability': 'probability',
        'partner_id/name': 'account_name',
        'title_action': 'next_step',
        'partner_address_id/name': 'account_name',
        'planned_revenue': 'amount_usdollar',
        'date_deadline':'date_closed',
        'user_id/id' : 'assigned_user_id',
        'stage_id.id' : 'stage_id.id',
        'type' : 'type',
    }
    lead_obj = sugar_obj.pool.get('crm.lead')
    partner_obj = sugar_obj.pool.get('res.partner')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'Opportunities')
    for val in sugar_data:
        partner_xml_id = partner_obj.search(cr, uid, [('name', 'like', val.get('account_name'))])
        if not partner_xml_id:
            raise osv.except_osv(_('Warning !'), _('Partner %s not Found') % val.get('account_name'))        
        val['type'] = 'opportunity'
        stage_id = get_opportunity_status(sugar_obj, cr, uid, val, context)
        val['stage_id.id'] = stage_id
        fields, datas = sugarcrm_fields_mapping.sugarcrm_fields_mapp(val, map_opportunity)
        lead_obj.import_data(cr, uid, fields, [datas], mode='update', current_module='sugarcrm_import', context=context)

MAP_FIELDS = {'Opportunities':  #Object Mapping name
                    {'dependencies' : ['Users', 'Accounts'],  #Object to import before this table
                     'process' : import_opportunities,
                     },
              'Leads':
                    {'dependencies' : ['Users', 'Accounts', 'Contacts'],  #Object to import before this table
                     'process' : import_leads,
                    },
              'Contacts':
                    {'dependencies' : ['Users'],  #Object to import before this table
                     'process' : import_partner_address,
                    },
              'Accounts':
                    {'dependencies' : ['Users'],  #Object to import before this table
                     'process' : import_partners,
                    },
                          
              'Users': 
                    {'dependencies' : [],
                     'process' : import_users,
                    },
              'Employees': 
                    {'dependencies' : ['Resources'],
                     'process' : import_employees,
                    },    
              'Resources': 
                    {'dependencies' : ['Users'],
                     'process' : import_resources,
                    },                                      
          }

class import_sugarcrm(osv.osv):
    """Import SugarCRM DATA"""
    
    _name = "import.sugarcrm"
    _description = __doc__
    _columns = {
        'lead': fields.boolean('Leads', help="If Leads is checked, SugarCRM Leads data imported in openerp crm-Lead form"),
        'opportunity': fields.boolean('Opportunities', help="If Leads is checked, SugarCRM Leads data imported in openerp crm-Opportunity form"),
        'user': fields.boolean('User', help="If Users is checked, SugarCRM Users data imported in openerp crm-Opportunity form"),
        'contact': fields.boolean('Contacts', help="If Contacts is checked, SugarCRM Contacts data imported in openerp partner address form"),
        'account': fields.boolean('Accounts', help="If Accounts is checked, SugarCRM  Accounts data imported in openerp partner form"),
        'employee': fields.boolean('Employee', help="If Employees is checked, SugarCRM Employees data imported in openerp partner employee form"),
        'username': fields.char('User Name', size=64),
        'password': fields.char('Password', size=24),
    }
    _defaults = {
       'lead': True,
       'opportunity': True,
       'user' : True,
       'contact' : True,
       'account' : True,
        'employee' : True,        
    }
    
    def get_key(self, cr, uid, ids, context=None):
        """Select Key as For which Module data we want import data."""
        if not context:
            context = {}
        key_list = []
        for current in self.browse(cr, uid, ids, context):
            if current.lead:
                key_list.append('Leads')
            if current.opportunity:
                key_list.append('Opportunities')
            if current.user:
                key_list.append('Users')
            if current.contact:
                key_list.append('Contacts')
            if current.account:
                key_list.append('Accounts') 
            if current.employee:
                key_list.append('Employees')       
        return key_list

    def import_all(self, cr, uid, ids, context=None):
        """Import all sugarcrm data into openerp module"""
        if not context:
            context = {}
        keys = self.get_key(cr, uid, ids, context)
        imported = set() #to invoid importing 2 times the sames modules
        for key in keys:
            if not key in imported:
                self.resolve_dependencies(cr, uid, MAP_FIELDS, MAP_FIELDS[key]['dependencies'], imported, context=context)
                MAP_FIELDS[key]['process'](self, cr, uid, context)
                imported.add(key)

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

    def resolve_dependencies(self, cr, uid, dict, dep, imported, context=None):
        for dependency in dep:
            if not dependency in imported:
                self.resolve_dependencies(cr, uid, dict, dict[dependency]['dependencies'], imported, context=context)
                dict[dependency]['process'](self, cr, uid, context)
                imported.add(dependency)


import_sugarcrm()
