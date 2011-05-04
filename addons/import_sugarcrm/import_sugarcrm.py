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
from import_framework import *
import pprint
import base64
pp = pprint.PrettyPrinter(indent=4)

#print 'xml ids exist', sugar_obj.pool.get('ir.model.data').search(cr, uid, [('name', 'in', address_id )])  

OPENERP_FIEDS_MAPS = {'Leads': 'crm.lead',
                      'Opportunities': 'crm.lead',
                      'Contacts': 'res.partner.address',
                      'Accounts': 'res.partner',
                      'Resources': 'resource.resource',
                      'Users': 'res.users',
                      'Meetings': 'crm.meeting',
                      'Calls': 'crm.phonecall',
                      'Claims': 'crm.claim',
                      'Employee': 'hr.employee',
                      'Project': 'project.project',
                      'ProjectTask': 'project.task',
                      'Bugs': 'project.issue',
                      'Documents': 'ir.attachment',
                      
  }


TABLE_CONTACT = "contact"
TABLE_ACCOUNT = "account"
TABLE_USER = "user"
TABLE_EMPLOYEE = "employee"
TABLE_RESSOURCE = "resource"

def get_sugar_data(module_name, context=None):
    if not context:
        context = {}
    PortType,sessionid = sugar.login(context.get('username',''), context.get('password',''), context.get('url',''))
    return sugar.search(PortType,sessionid, module_name)

def get_all_states(sugar_obj, cr, uid, external_val, country_id, context=None):
    """Get states or create new state unless country_id is False"""
    state_code = external_val[0:3] #take the tree first char
    fields = ['country_id/id', 'name', 'code']
    data = [country_id, external_val, state_code]
    if country_id:
        return import_object(sugar_obj, cr, uid, fields, data, 'res.country.state', 'country_state', external_val, context=context) 
     
    return False


def get_all_countries(sugar_obj, cr, uid, sugar_country_val, context=None):
    """Get Country, if no country match do not create anything, to avoid duplicate country code"""
    xml_id = generate_xml_id(sugar_country_val, 'country')
    return mapped_id_if_exist(sugar_obj, cr, uid, 'res.country', [('name', 'ilike', sugar_country_val)], xml_id, context=context)

def import_partner_address(sugar_obj, cr, uid, context=None):
    if not context:
        context = {}
        
    map_partner_address = {
            'id': 'id_new',              
            'name': ['first_name', 'last_name'],
            'partner_id/id': 'partner_id/id',
            'phone': 'phone_work',
            'mobile': 'phone_mobile',
            'fax': 'phone_fax',
            'function': 'title',
            'street': 'primary_address_street',
            'zip': 'primary_address_postalcode',
            'city': 'primary_address_city',
            'country_id/id': 'country_id/id',
            'state_id/id': 'state_id/id',
            'email': 'email',
            'type': 'type'
            }
    
    address_obj = sugar_obj.pool.get('res.partner.address')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'Contacts')
    
    for val in sugar_data:
        val['id_new'] = generate_xml_id(val['id'], TABLE_CONTACT) 
        val['partner_id/id'] = xml_id_exist(sugar_obj, cr, uid, TABLE_ACCOUNT, val.get('account_id'))
        val['type'] = 'contact'
        val['email'] = val.get('email1') + ','+ val.get('email2')        
        if val.get('primary_address_country'):
            country_id = get_all_countries(sugar_obj, cr, uid, val.get('primary_address_country'), context)
            state = get_all_states(sugar_obj,cr, uid, val.get('primary_address_state'), country_id, context)
            val['country_id/id'] =  country_id
            val['state_id/id'] =  state        
        fields, datas = sugarcrm_fields_mapp(val, map_partner_address)
        print 'address'
        pp.pprint(val)
        address_obj.import_data(cr, uid, fields, [datas], mode='update', current_module=MODULE_NAME, noupdate=True, context=context)
    return True
    
#Validated
def import_users(sugar_obj, cr, uid, context=None):
    map_user = {
        'name': ['first_name', 'last_name'],
        'login': 'user_name',
        'context_lang' : 'context_lang',
        'password' : 'password',
        '.id' : '.id',
        'context_department_id/id': 'context_department_id/id',
    } 
    
    def get_users_department(sugar_obj, cr, uid, val, context=None):
        fields = ['name']
        data = [val]
        if not val:
            return False
        return import_object(sugar_obj, cr, uid, fields, data, 'hr.department', 'hr_department_user', val, context=context)
    
    if not context:
        context = {}
    
    user_obj = sugar_obj.pool.get('res.users')
    
    datas = get_sugar_data('Users', context)
    for val in datas:
        user_ids = user_obj.search(cr, uid, [('login', '=', val.get('user_name'))])
        if user_ids: 
            val['.id'] = str(user_ids[0])
            val['password'] = ''
        else:
            val['.id'] = ''
            val['password'] = 'sugarcrm' #default password for all user #TODO needed in documentation
            
        val['id_new'] = generate_xml_id(val['id'], TABLE_USER)
        val['context_department_id/id'] = get_users_department(sugar_obj, cr, uid, val.get('department'), context=context)
        val['context_lang'] = context.get('lang','en_US')
    import_module(sugar_obj, cr, uid, 'res.users', map_user, datas, TABLE_USER, context)
    return True

def get_lead_status(sugar_obj, cr, uid, sugar_val,context=None):
    if not context:
        context = {}
    fields = ['name', 'type']
    name = 'lead_' + sugar_val['status']
    data = [sugar_val['status'], 'lead']
    return import_object(sugar_obj, cr, uid, fields, data, 'crm.case.stage', 'crm_lead_stage', name, [('type', '=', 'lead'), ('name', 'ilike', sugar_val['status'])], context)

def get_lead_state(surgar_obj, cr, uid, sugar_val,context=None):
    if not context:
        context = {}
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


def import_partners(sugar_obj, cr, uid, context=None):
    map_partner = {
            'id': 'id_new',
            'name': 'name',
            'website': 'website',
            'user_id/id': 'user_id/id',
            'ref': 'sic_code',
            'comment': ['__prettyprint__', 'description', 'employees', 'ownership', 'annual_revenue', 'rating', 'industry', 'ticker_symbol'],
            'customer': 'customer',
            'supplier': 'supplier', 
    }
    
    def get_address_type(sugar_obj, cr, uid, val, type, context=None):
        if type == 'invoice':
            type_address = 'billing'
        else:
            type_address = 'shipping'     
    
        map_partner_address = {
            'name': 'name',
            'partner_id/id': 'account_id',
            'phone': 'phone_office',
            'mobile': 'phone_mobile',
            'fax': 'phone_fax',
            'type': 'type',
            'street': type_address + '_address_street',
            'zip': type_address +'_address_postalcode',
            'city': type_address +'_address_city',
             'country_id/id': 'country_id/id',
             'type': 'type',
            }
        
        
        if val.get(type_address +'_address_country'):
            country_id = get_all_countries(sugar_obj, cr, uid, val.get(type_address +'_address_country'), context)
            state = get_all_states(sugar_obj, cr, uid, val.get(type_address +'_address_state'), country_id, context)
            val['country_id/id'] =  country_id
            val['state_id/id'] =  state
        val['type'] = type
        val['id_new'] = val['id'] + '_address_' + type
        fields, datas = sugarcrm_fields_mapp(val, map_partner_address)
        return import_object(sugar_obj, cr, uid, fields, datas, 'res.partner.address', TABLE_CONTACT, val['id_new'], DO_NOT_FIND_DOMAIN, context=context)
    
    def get_address(sugar_obj, cr, uid, val, context=None):
        address_id=[]
        type_dict = {'billing_address_street' : 'invoice', 'shipping_address_street' : 'delivery'}
        for key, type_value in type_dict.items():
            if val.get(key):
                id = get_address_type(sugar_obj, cr, uid, val, type_value, context)
                address_id.append(id)
          
        return address_id
    
    if not context:
        context = {}
    partner_obj = sugar_obj.pool.get('res.partner')
    
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'Accounts')
    
    for val in sugar_data:
        add_id = get_address(sugar_obj, cr, uid, val, context)
        val['customer'] = '1'
        val['supplier'] = '0'
        val['user_id/id'] = xml_id_exist(sugar_obj, cr, uid, TABLE_USER, val['assigned_user_id'])
        val['id_new'] = generate_xml_id(val['id'], TABLE_ACCOUNT)
        print "values of partner"
        pp.pprint(val)
        if val['parent_id']:
            print 'parent_id', val['parent_id']
            val['parent_id_new'] = generate_xml_id(val['parent_id'], TABLE_ACCOUNT)
        
        fields, data = sugarcrm_fields_mapp(val, map_partner)
        fields, data = add_m2o_data(data, fields, 'address/id', add_id)
        
        partner_obj.import_data(cr, uid, fields, [data], mode='update', current_module=MODULE_NAME, noupdate=True, context=context)
    import_self_dependencies(partner_obj, cr, uid, 'parent_id', sugar_data, context)
    return True

def get_category(sugar_obj, cr, uid, model, name, context=None):
    if not context:
        context = {}
    fields = ['name', 'object_id']
    data = [name, model]
    return import_object(sugar_obj, cr, uid, fields, data, 'crm.case.categ', 'crm_categ', name, [('object_id.model','=',model), ('name', 'ilike', name)], context)

def get_alarm_id(sugar_obj, cr, uid, val, context=None):
    if not context:
        context = {}
    alarm_dict = {'60': '1 minute before',
                  '300': '5 minutes before',
                  '600': '10 minutes before',
                  '900': '15 minutes before',
                  '1800':'30 minutes before',
                  '3600': '1 hour before',
     }
    alarm_id = False
    alarm_obj = sugar_obj.pool.get('res.alarm')
    if alarm_dict.get(val):
        alarm_ids = alarm_obj.search(cr, uid, [('name', 'like', alarm_dict.get(val))])
        for alarm in alarm_obj.browse(cr, uid, alarm_ids, context):
            alarm_id = alarm.id
    return alarm_id 
    
def get_meeting_state(sugar_obj, cr, uid, val,context=None):
    if not context:
        context = {}
    state_dict = {'status': #field in the sugarcrm database
        { #Mapping of sugarcrm stage : openerp meeting stage
            'Planned' : 'draft',
            'Held':'open',
            'Not Held': 'draft',
        },}
    state = state_dict['status'].get(val, '')
    return state    

def get_task_state(sugar_obj, cr, uid, val, context=None):
    if not context:
        context = {}
    state_dict = {'status': #field in the sugarcrm database
        { #Mapping of sugarcrm stage : openerp meeting stage
            'Completed' : 'done',
            'Not Started':'draft',
            'In Progress': 'open',
            'Pending Input': 'draft',
            'deferred': 'cancel'
        },}
    state = state_dict['status'].get(val, '')
    return state    

def get_project_state(sugar_obj, cr, uid, val,context=None):
    if not context:
        context = {}
    state_dict = {'status': #field in the sugarcrm database
        { #Mapping of sugarcrm staus : openerp Projects state
            'Draft' : 'draft',
            'In Review': 'open',
            'Published': 'close',
        },}
    state = state_dict['status'].get(val, '')
    return state    

def get_project_task_state(sugar_obj, cr, uid, val,context=None):
    if not context:
        context = {}
    state_dict = {'status': #field in the sugarcrm database
        { #Mapping of sugarcrm status : openerp Porject Tasks state
             'Not Started': 'draft',
             'In Progress': 'open',
             'Completed': 'done',
            'Pending Input': 'pending',
            'Deferred': 'cancelled',
        },}
    state = state_dict['status'].get(val, '')
    return state    

def get_project_task_priority(sugar_obj, cr, uid, val,context=None):
    if not context:
        context = {}
    priority_dict = {'priority': #field in the sugarcrm database
        { #Mapping of sugarcrm status : openerp Porject Tasks state
            'High': '0',
            'Medium': '2',
            'Low': '3'
        },}
    priority = priority_dict['priority'].get(val, '')
    return priority    


def get_account(sugar_obj, cr, uid, val, context=None):
    if not context:
        context = {}
    partner_id = False    
    partner_address_id = False
    partner_phone = False
    partner_mobile = False
    model_obj = sugar_obj.pool.get('ir.model.data')
    address_obj = sugar_obj.pool.get('res.partner.address')
    crm_obj = sugar_obj.pool.get('crm.lead')
    project_obj = sugar_obj.pool.get('project.project')
    issue_obj = sugar_obj.pool.get('project.issue')
    if val.get('parent_type') == 'Accounts':
        model_ids = model_obj.search(cr, uid, [('name', '=', val.get('parent_id')), ('model', '=', 'res.partner')])
        if model_ids:
            model = model_obj.browse(cr, uid, model_ids)[0]
            partner_id = model.res_id
            address_ids = address_obj.search(cr, uid, [('partner_id', '=', partner_id)])
            if address_ids:
                address_id = address_obj.browse(cr, uid, address_ids[0])
                partner_address_id = address_id.id
                partner_phone = address_id.phone
                partner_mobile = address_id.mobile
            
    if val.get('parent_type') == 'Contacts':
        model_ids = model_obj.search(cr, uid, [('name', '=', val.get('parent_id')), ('model', '=', 'res.partner.address')])
        if model_ids:
            model = model_obj.browse(cr, uid, model_ids)[0]
            partner_address_id = model.res_id
            address_id = address_obj.browse(cr, uid, partner_address_id)
            partner_phone = address_id.phone
            partner_mobile = address_id.mobile
            partner_id = address_id and address_id.partner_id.id or False
            
    if val.get('parent_type') == 'Opportunities':
        model_ids = model_obj.search(cr, uid, [('name', '=', val.get('parent_id')), ('model', '=', 'crm.lead')])
        if model_ids:
            model = model_obj.browse(cr, uid, model_ids)[0]
            opportunity_id = model.res_id
            opportunity_id = crm_obj.browse(cr, uid, opportunity_id)
            partner_id = opportunity_id.partner_id.id
            partner_address_id =  opportunity_id.partner_address_id.id
            partner_phone = opportunity_id.partner_address_id.phone
            partner_mobile = opportunity_id.partner_address_id.mobile
            
    if val.get('parent_type') == 'Project':
        model_ids = model_obj.search(cr, uid, [('name', '=', val.get('parent_id')), ('model', '=', 'project.project')])
        if model_ids:
            model = model_obj.browse(cr, uid, model_ids)[0]
            proj_ids = model.res_id
            proj_id = project_obj.browse(cr, uid, proj_ids)
            partner_id = proj_id.partner_id.id
            partner_address_id =  proj_id.contact_id.id
            partner_phone = proj_id.contact_id.phone
            partner_mobile = proj_id.contact_id.mobile

    if val.get('parent_type') == 'Bugs':
        model_ids = model_obj.search(cr, uid, [('name', '=', val.get('parent_id')), ('model', '=', 'project.issue')])
        if model_ids:
            model = model_obj.browse(cr, uid, model_ids)[0]
            issue_ids = model.res_id
            issue_id = issue_obj.browse(cr, uid, issue_ids)
            partner_id = issue_id.partner_id.id
            partner_address_id =  issue_id.partner_address_id.id
            partner_phone = issue_id.partner_address_id.phone
            partner_mobile = issue_id.partner_address_id.mobile                        
    return partner_id, partner_address_id, partner_phone,partner_mobile     


def import_documents(sugar_obj, cr, uid, context=None):
    if not context:
        context = {}
    map_document = {'id' : 'id', 
             'name': 'filename',
           'description': 'description',
           'datas': 'datas',
           'datas_fname': 'datas_fname',
            } 
    attach_obj = sugar_obj.pool.get('ir.attachment')
    PortType,sessionid = sugar.login(context.get('username',''), context.get('password',''), context.get('url',''))
    sugar_data = sugar.search(PortType,sessionid, 'DocumentRevisions')
    for val in sugar_data:
        filepath = '/var/www/sugarcrm/cache/upload/'+ val.get('id')
        f = open(filepath, "r")
        datas = f.read()
        f.close()
        val['datas'] = base64.encodestring(datas)
        val['datas_fname'] = val.get('filename')
        fields, datas = sugarcrm_fields_mapp(val, map_document, context)
        attach_obj.import_data(cr, uid, fields, [datas], mode='update', current_module='sugarcrm_import', noupdate=True, context=context)
    return True

def import_tasks(sugar_obj, cr, uid, context=None):
    if not context:
        context = {}
    map_task = {'id' : 'id',
                'name': 'name',
                'date': ['__datetime__', 'date_start'],
                'date_deadline' : ['__datetime__', 'date_due'],
                'user_id/id': 'assigned_user_id',
                'categ_id/id': 'categ_id/id',
                'partner_id/.id': 'partner_id/.id',
                'partner_address_id/.id': 'partner_address_id/.id',
                'state': 'state'
    }
    meeting_obj = sugar_obj.pool.get('crm.meeting')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    categ_id = get_category(sugar_obj, cr, uid, 'crm.meeting', 'Tasks')
    sugar_data = sugar.search(PortType, sessionid, 'Tasks')
    for val in sugar_data:
        partner_xml_id = find_mapped_id(sugar_obj, cr, uid, 'res.partner.address', val.get('contact_id'), context)
        if not partner_xml_id:
            raise osv.except_osv(_('Warning !'), _('Reference Contact %s cannot be created, due to Lower Record Limit in SugarCRM Configuration.') % val.get('contact_name'))
        partner_id, partner_address_id, partner_phone, partner_mobile = get_account(sugar_obj, cr, uid, val, context)
        val['partner_id/.id'] = partner_id
        val['partner_address_id/.id'] = partner_address_id
        val['categ_id/id'] = categ_id
        val['state'] = get_task_state(sugar_obj, cr, uid, val.get('status'), context)
        fields, datas = sugarcrm_fields_mapp(val, map_task, context)
        meeting_obj.import_data(cr, uid, fields, [datas], mode='update', current_module='sugarcrm_import', noupdate=True, context=context)
    return True    
    
def get_attendee_id(sugar_obj, cr, uid, PortType, sessionid, module_name, module_id, context=None):
    if not context:
        context = {}
    model_obj = sugar_obj.pool.get('ir.model.data')
    att_obj = sugar_obj.pool.get('calendar.attendee')
    meeting_obj = sugar_obj.pool.get('crm.meeting')
    user_dict = sugar.user_get_attendee_list(PortType, sessionid, module_name, module_id)
    for user in user_dict: 
        user_model_ids = find_mapped_id(sugar_obj, cr, uid, 'res.users', user.get('id'), context)
        user_resource_id = model_obj.browse(cr, uid, user_model_ids)        
        if user_resource_id:
            user_id = user_resource_id[0].res_id 
            attend_ids = att_obj.search(cr, uid, [('user_id', '=', user_id)])
            if attend_ids:
                attendees = attend_ids[0]
            else:      
                attendees = att_obj.create(cr, uid, {'user_id': user_id, 'email': user.get('email1')})
            meeting_model_ids = find_mapped_id(sugar_obj, cr, uid, 'crm.meeting', module_id, context)
            meeting_xml_id = model_obj.browse(cr, uid, meeting_model_ids)
            if meeting_xml_id:
                meeting_obj.write(cr, uid, [meeting_xml_id[0].res_id], {'attendee_ids': [(4, attendees)]})       
    return True   
    
def import_meetings(sugar_obj, cr, uid, context=None):
    if not context:
        context = {}
    map_meeting = {'id' : 'id',
                    'name': 'name',
                    'date': ['__datetime__', 'date_start'],
                    'duration': ['duration_hours', 'duration_minutes'],
                    'location': 'location',
                    'alarm_id/.id': 'alarm_id/.id',
                    'user_id/id': 'assigned_user_id',
                    'partner_id/.id':'partner_id/.id',
                    'partner_address_id/.id':'partner_address_id/.id',
                    'state': 'state'
    }
    meeting_obj = sugar_obj.pool.get('crm.meeting')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'Meetings')
    for val in sugar_data:
        partner_id, partner_address_id, partner_phone, partner_mobile = get_account(sugar_obj, cr, uid, val, context)
        val['partner_id/.id'] = partner_id
        val['partner_address_id/.id'] = partner_address_id
        val['state'] = get_meeting_state(sugar_obj, cr, uid, val.get('status'),context)
        val['alarm_id/.id'] = get_alarm_id(sugar_obj, cr, uid, val.get('reminder_time'), context)
        fields, datas = sugarcrm_fields_mapp(val, map_meeting, context)
        meeting_obj.import_data(cr, uid, fields, [datas], mode='update', current_module='sugarcrm_import', noupdate=True, context=context)
        get_attendee_id(sugar_obj, cr, uid, PortType, sessionid, 'Meetings', val.get('id'), context)
    return True    

def get_calls_state(sugar_obj, cr, uid, val,context=None):
    if not context:
        context = {}
    state = False
    state_dict = {'status': #field in the sugarcrm database
        { #Mapping of sugarcrm stage : openerp calls stage
            'Planned' : 'open',
            'Held':'done',
            'Not Held': 'pending',
        },}
    state = state_dict['status'].get(val, '')
    return state   

def import_calls(sugar_obj, cr, uid, context=None):
    if not context:
        context = {}
    map_calls = {'id' : 'id',
                    'name': 'name',
                    'date': ['__datetime__', 'date_start'],
                    'duration': ['duration_hours', 'duration_minutes'],
                    'user_id/id': 'assigned_user_id',
                    'partner_id/.id': 'partner_id/.id',
                    'partner_address_id/.id': 'partner_address_id/.id',
                    'categ_id/id': 'categ_id/id',
                   'state': 'state',
                   'partner_phone': 'partner_phone',
                   'partner_mobile': 'partner_mobile',
                   'opportunity_id/id': 'opportunity_id/id',

    }
    phonecall_obj = sugar_obj.pool.get('crm.phonecall')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'Calls')
    for val in sugar_data:
        sugar_call_leads = sugar.relation_search(PortType, sessionid, 'Calls', module_id=val.get('id'), related_module='Leads', query=None, deleted=None)
        if sugar_call_leads:
            for call_opportunity in sugar_call_leads: 
                val['opportunity_id/id'] = call_opportunity 
        categ_id = get_category(sugar_obj, cr, uid, 'crm.phonecall', val.get('direction'))         
        val['categ_id/id'] = categ_id
        partner_id, partner_address_id, partner_phone, partner_mobile = get_account(sugar_obj, cr, uid, val, context)
        val['partner_id/.id'] = partner_id
        val['partner_address_id/.id'] = partner_address_id
        val['partner_phone'] = partner_phone
        val['partner_mobile'] = partner_mobile
        val['state'] =  get_calls_state(sugar_obj, cr, uid, val.get('status'), context)  
        fields, datas = sugarcrm_fields_mapp(val, map_calls, context)
        phonecall_obj.import_data(cr, uid, fields, [datas], mode='update', current_module=MODULE_NAME, noupdate=True, context=context)
    return True
   

def get_bug_priority(sugar_obj, cr, uid, val,context=None):
    if not context:
        context = {}
    priority_dict = {'priority': #field in the sugarcrm database
        { #Mapping of sugarcrm priority : openerp bugs priority
            'Urgent': '1',
            'High': '2',
            'Medium': '3',
            'Low': '4'
        },}
    priority = priority_dict['priority'].get(val, '')
    return priority  

def get_claim_priority(sugar_obj, cr, uid, val,context=None):
    if not context:
        context = {}
    priority_dict = {'priority': #field in the sugarcrm database
        { #Mapping of sugarcrm priority : openerp claims priority
            'High': '2',
            'Medium': '3',
            'Low': '4'
        },}
    priority = priority_dict['priority'].get(val, '')
    return priority   

def get_bug_state(sugar_obj, cr, uid, val,context=None):
    if not context:
        context = {}
    state_dict = {'status': #field in the sugarcrm database
        { #Mapping of sugarcrm status : openerp Bugs state
            'New' : 'draft',
            'Assigned':'open',
            'Closed': 'done',
            'Pending': 'pending',
            'Rejected': 'cancel',
        },}
    state = state_dict['status'].get(val, '')
    return state

def get_claim_state(sugar_obj, cr, uid, val,context=None):
    if not context:
        context = {}
    state_dict = {'status': #field in the sugarcrm database
        { #Mapping of sugarcrm status : openerp claim state
            'New' : 'draft',
            'Assigned':'open',
            'Closed': 'done',
            'Pending Input': 'pending',
            'Rejected': 'cancel',
            'Duplicate': 'draft',
        },}
    state = state_dict['status'].get(val, '')
    return state
    

def get_acc_contact_claim(sugar_obj, cr, uid, val, context=None):
    if not context:
        context = {}
    partner_id = False    
    partner_address_id = False
    partner_phone = False
    partner_email = False
    model_obj = sugar_obj.pool.get('ir.model.data')
    address_obj = sugar_obj.pool.get('res.partner.address')
    model_ids = model_obj.search(cr, uid, [('name', '=', val.get('account_id')), ('model', '=', 'res.partner')])
    if model_ids:
        model = model_obj.browse(cr, uid, model_ids)[0]
        partner_id = model.res_id
        address_ids = address_obj.search(cr, uid, [('partner_id', '=', partner_id)])
        if address_ids:
            address_id = address_obj.browse(cr, uid, address_ids[0])
            partner_address_id = address_id.id
            partner_phone = address_id.phone
            partner_email = address_id.email
    return partner_id, partner_address_id, partner_phone,partner_email

def import_claims(sugar_obj, cr, uid, context=None):
    if not context:
        context = {}
    map_claim = {'id' : 'id',
                    'name': 'name',
                    'date': ['__datetime__', 'date_entered'],
                    'user_id/id': 'assigned_user_id',
                    'priority':'priority',
                    'partner_id/.id': 'partner_id/.id',
                    'partner_address_id/.id': 'partner_address_id/.id',
                    'partner_phone': 'partner_phone',
                    'partner_mobile': 'partner_email',                    
                    'description': 'description',
                    'state': 'state',
    }
    claim_obj = sugar_obj.pool.get('crm.claim')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'Cases')
    for val in sugar_data:
        partner_id, partner_address_id, partner_phone,partner_email = get_acc_contact_claim(sugar_obj, cr, uid, val, context)
        val['partner_id/.id'] = partner_id
        val['partner_address_id/.id'] = partner_address_id
        val['partner_phone'] = partner_phone
        val['email_from'] = partner_email
        val['priority'] = get_claim_priority(sugar_obj, cr, uid, val.get('priority'),context)
        val['state'] = get_claim_state(sugar_obj, cr, uid, val.get('status'),context)
        fields, datas = sugarcrm_fields_mapp(val, map_claim, context)
        claim_obj.import_data(cr, uid, fields, [datas], mode='update', current_module='sugarcrm_import', noupdate=True, context=context)
    return True    

def import_bug(sugar_obj, cr, uid, context=None):
    if not context:
        context = {}
    map_resource = {'id' : 'id',
                    'name': 'name',
                    'project_id/.id':'project_id/.id',
                    'categ_id/id': 'categ_id/id',
                    'priority':'priority',
                    'description': ['__prettyprint__','description', 'bug_number', 'fixed_in_release_name', 'source', 'fixed_in_release', 'work_log', 'found_in_release', 'release_name', 'resolution'],
                    'state': 'state',
    }
    issue_obj = sugar_obj.pool.get('project.issue')
    project_obj = sugar_obj.pool.get('project.project')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'Bugs')
    for val in sugar_data:
        project_ids = project_obj.search(cr, uid, [('name', 'like', 'sugarcrm_bugs')])
        if project_ids:
            project_id = project_ids[0]
        else:
            project_id = project_obj.create(cr, uid, {'name':'sugarcrm_bugs'})    
        val['project_id/.id'] = project_id
        val['categ_id/id'] = get_category(sugar_obj, cr, uid, 'project.issue', val.get('type'))
        val['priority'] = get_bug_priority(sugar_obj, cr, uid, val.get('priority'),context)
        val['state'] = get_bug_state(sugar_obj, cr, uid, val.get('status'),context)
        fields, datas = sugarcrm_fields_mapp(val, map_resource, context)
        issue_obj.import_data(cr, uid, fields, [datas], mode='update', current_module=MODULE_NAME, noupdate=True, context=context)
    return True    

def get_job_id(sugar_obj, cr, uid, val, context=None):
    if not context:
        context={}
    fields = ['name']
    data = [val]
    return import_object(sugar_obj, cr, uid, fields, data, 'hr.job', 'hr_job', val, context=context)

def get_campaign_id(sugar_obj, cr, uid, val, context=None):
    if not context:
        context={}
    fields = ['name']
    data = [val]
    return import_object(sugar_obj, cr, uid, fields, data, 'crm.case.resource.type', 'crm_campaign', val, context=context)
    
def get_attachment(sugar_obj, cr, uid, val, model, File, Filename, parent_type, context=None):
    if not context:
        context = {}
    attachment_obj = sugar_obj.pool.get('ir.attachment')
    model_obj = sugar_obj.pool.get('ir.model.data')
    mailgate_obj = sugar_obj.pool.get('mailgate.message')
    attach_ids = attachment_obj.search(cr, uid, [('res_id','=', val.get('res_id'), ('res_model', '=', val.get('model')))])
    if not attach_ids and Filename:
        if parent_type == 'Accounts':
            new_attachment_id = attachment_obj.create(cr, uid, {'name': Filename, 'datas_fname': Filename, 'datas': File, 'res_id': val.get('res_id', False),'res_model': val.get('model',False), 'partner_id': val.get('partner_id/.id')})
        else:    
            new_attachment_id = attachment_obj.create(cr, uid, {'name': Filename, 'datas_fname': Filename, 'datas': File, 'res_id': val.get('res_id', False),'res_model': val.get('model',False)})
        message_model_ids = find_mapped_id(sugar_obj, cr, uid, model, val.get('id'), context)
        message_xml_id = model_obj.browse(cr, uid, message_model_ids)
        if message_xml_id:
            if parent_type == 'Accounts':
                mailgate_obj.write(cr, uid, [message_xml_id[0].res_id], {'attachment_ids': [(4, new_attachment_id)], 'partner_id': val.get('partner_id/.id')})
            else:
                mailgate_obj.write(cr, uid, [message_xml_id[0].res_id], {'attachment_ids': [(4, new_attachment_id)]})                                              
    return True    
    
def import_history(sugar_obj, cr, uid, context=None):
    if not context:
        context = {}
    map_attachment = {'id' : 'id',
                      'name':'name',
                      'date': ['__datetime__', 'date_entered'],
                      'user_id/id': 'assigned_user_id',
                      'description': ['__prettyprint__','description', 'description_html'],
                      'res_id': 'res_id',
                      'model': 'model',
                      'partner_id/.id' : 'partner_id/.id',
    }
    mailgate_obj = sugar_obj.pool.get('mailgate.message')
    model_obj =  sugar_obj.pool.get('ir.model.data')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'Notes')
    for val in sugar_data:
        File, Filename = sugar.attachment_search(PortType, sessionid, 'Notes', val.get('id'))
        model_ids = model_obj.search(cr, uid, [('name', 'like', val.get('parent_id')),('model','=', OPENERP_FIEDS_MAPS[val.get('parent_type')])])
        if model_ids:
            model = model_obj.browse(cr, uid, model_ids)[0]
            if model.model == 'res.partner':
                val['partner_id/.id'] = model.res_id
            else:    
                val['res_id'] = model.res_id
                val['model'] = model.model
        fields, datas = sugarcrm_fields_mapp(val, map_attachment, context)   
        mailgate_obj.import_data(cr, uid, fields, [datas], mode='update', current_module='sugarcrm_import', noupdate=True, context=context)
        get_attachment(sugar_obj, cr, uid, val, 'mailgate.message', File, Filename, val.get('parent_type'), context)
    return True       

def import_employees(sugar_obj, cr, uid, context=None):
    
    map_employee = {'id' : 'id_new',
                    'resource_id/id': 'resource_id/id', 
                    'name': ['first_name', 'last_name'],
                    'work_phone': 'phone_work',
                    'mobile_phone':  'phone_mobile',
                    'user_id/id': 'user_id/id', 
                    'address_home_id/id': 'address_home_id/id',
                    'notes': 'description',
                    'job_id/id': 'job_id/id'
    }
    
    def get_ressource(sugar_obj, cr, uid, val, context=None):
        map_resource = { 
            'name': ['first_name', 'last_name'],
        }        
        return import_object_mapping(sugar_obj, cr, uid, map_resource, val, 'resource.resource', TABLE_RESSOURCE, val['id'], DO_NOT_FIND_DOMAIN, context)
        
    def get_user_address(sugar_obj, cr, uid, val, context=None):
        map_user_address = {
            'name': ['first_name', 'last_name'],
            'city': 'address_city',
            'country_id/id': 'country_id/id',
            'state_id/id': 'state_id/id',
            'street': 'address_street',
            'zip': 'address_postalcode',
            'fax': 'fax',
        }
        
        if val.get('address_country'):
            country_id = get_all_countries(sugar_obj, cr, uid, val.get('address_country'), context)
            state_id = get_all_states(sugar_obj, cr, uid, val.get('address_state'), country_id, context)
            val['country_id/id'] =  country_id
            val['state_id/id'] =  state_id
            
        return import_object_mapping(sugar_obj, cr, uid, map_user_address, val, 'res.partner.address', TABLE_CONTACT, val['id'], DO_NOT_FIND_DOMAIN, context=context)
    
    sugar_data =  get_sugar_data('Employees', context)
    for val in sugar_data:
        val['address_home_id/id'] = get_user_address(sugar_obj, cr, uid, val, context)
        val['job_id/id'] = get_job_id(sugar_obj, cr, uid, val.get('title'), context)
        val['user_id/id'] = xml_id_exist(sugar_obj, cr, uid, TABLE_USER, val['id'])     
        val['resource_id/id'] = get_ressource(sugar_obj, cr, uid, val, context)
        #for cycle dependencies
        val['parent_id_new'] = val['reports_to_id'] and generate_xml_id(val['reports_to_id'], TABLE_EMPLOYEE) or ''

    import_module(sugar_obj, cr, uid, 'hr.employee', map_employee, sugar_data, TABLE_EMPLOYEE, context=context)
    return True

def import_emails(sugar_obj, cr, uid, context=None):
    if not context:
        context= {}
    map_emails = {
    'id': 'id',
    'name':'name',
    'date':['__datetime__', 'date_sent'],
    'email_from': 'from_addr_name',
    'email_to': 'reply_to_addr',
    'email_cc': 'cc_addrs_names',
    'email_bcc': 'bcc_addrs_names',
    'message_id': 'message_id',
    'user_id/id': 'assigned_user_id',
    'description': ['__prettyprint__', 'description', 'description_html'],
    'res_id': 'res_id',
    'model': 'model',
    'partner_id/.id': 'partner_id/.id'
    }
    mailgate_obj = sugar_obj.pool.get('mailgate.message')
    model_obj = sugar_obj.pool.get('ir.model.data')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'Emails')
    for val in sugar_data:
        model_ids = model_obj.search(cr, uid, [('name', 'like', val.get('parent_id')),('model','=', OPENERP_FIEDS_MAPS[val.get('parent_type')])])
        for model in model_obj.browse(cr, uid, model_ids):
            if model.model == 'res.partner':
                val['partner_id/.id'] = model.res_id
            else:    
                val['res_id'] = model.res_id
                val['model'] = model.model
        fields, datas = sugarcrm_fields_mapp(val, map_emails, context)
        mailgate_obj.import_data(cr, uid, fields, [datas], mode='update', current_module='sugarcrm_import', noupdate=True, context=context)
    return True    



    
def import_projects(sugar_obj, cr, uid, context=None):
  
    map_project = {'id': 'id',
        'name': 'name',
        'date_start': ['__datetime__', 'estimated_start_date'],
        'date': ['__datetime__', 'estimated_end_date'],
        'user_id/id': 'assigned_user_id',
        'partner_id/.id': 'partner_id/.id',
        'contact_id/.id': 'contact_id/.id', 
         'state': 'state'   
    }
    
    #TODO more simplier use xml id please !!!!    
    def get_project_account(sugar_obj,cr,uid, PortType, sessionid, val, context=None):
        if not context:
            context={}
        partner_id = False
        partner_invoice_id = False        
        model_obj = sugar_obj.pool.get('ir.model.data')
        partner_obj = sugar_obj.pool.get('res.partner')
        partner_address_obj = sugar_obj.pool.get('res.partner.address')
        sugar_project_account = sugar.relation_search(PortType, sessionid, 'Project', module_id=val.get('id'), related_module='Accounts', query=None, deleted=None)
        for account_id in sugar_project_account:
            model_ids = find_mapped_id(sugar_obj, cr, uid, 'res.partner', account_id, context)
            if model_ids:
                model_id = model_obj.browse(cr, uid, model_ids)[0].res_id
                partner_id = partner_obj.browse(cr, uid, model_id).id
                address_ids = partner_address_obj.search(cr, uid, [('partner_id', '=', partner_id),('type', '=', 'invoice')])
                partner_invoice_id = address_ids[0] 
        return partner_id, partner_invoice_id      
    
    if not context:
        context = {}
        
    
    project_obj = sugar_obj.pool.get('project.project')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'Project')
    for val in sugar_data:
        partner_id, partner_invoice_id = get_project_account(sugar_obj,cr,uid, PortType, sessionid, val, context) 
        val['partner_id/.id'] = partner_id
        val['contact_id/.id'] = partner_invoice_id 
        val['state'] = get_project_state(sugar_obj, cr, uid, val.get('status'),context)
        fields, datas = sugarcrm_fields_mapp(val, map_project, context)
        project_obj.import_data(cr, uid, fields, [datas], mode='update', current_module=MODULE_NAME, noupdate=True, context=context)
    return True 


def import_project_tasks(sugar_obj, cr, uid, context=None):
    if not context:
        context = {}
    map_project_task = {'id': 'id',
        'name': 'name',
        'date_start': ['__datetime__', 'date_start'],
        'date_end': ['__datetime__', 'date_finish'],
        'progress': 'progress',
        'project_id/name': 'project_name',
        'planned_hours': 'planned_hours',
        'total_hours': 'total_hours',        
        'priority': 'priority',
        'description': 'description',
        'user_id/id': 'assigned_user_id',
         'state': 'state'   
    }
    task_obj = sugar_obj.pool.get('project.task')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'ProjectTask')
    for val in sugar_data:
        val['state'] = get_project_task_state(sugar_obj, cr, uid, val.get('status'),context)
        val['priority'] = get_project_task_priority(sugar_obj, cr, uid, val.get('priority'),context)
        fields, datas = sugarcrm_fields_mapp(val, map_project_task, context)
        task_obj.import_data(cr, uid, fields, [datas], mode='update', current_module=MODULE_NAME, noupdate=True, context=context)
    return True 
    
def import_leads(sugar_obj, cr, uid, context=None):

    map_lead = {
            'id' : 'id',
            'name': ['first_name', 'last_name'],
            'contact_name': ['first_name', 'last_name'],
            'description': ['__prettyprint__', 'description', 'refered_by', 'lead_source', 'lead_source_description', 'website', 'email2', 'status_description', 'lead_source_description', 'do_not_call'],
            'partner_name': 'account_name',
            'email_from': 'email1',
            'phone': 'phone_work',
            'mobile': 'phone_mobile',
            'title.id': 'title.id',
            'function':'title',
            'street': 'primary_address_street',
            'street2': 'alt_address_street',
            'zip': 'primary_address_postalcode',
            'city':'primary_address_city',
            'user_id/id' : 'assigned_user_id',
            'stage_id/id' : 'stage_id/id',
            'type' : 'type',
            'state': 'state',
            'fax': 'phone_fax',
            'referred': 'refered_by',
            'optout': 'optout',
            'type_id/id': 'type_id/id',
            'country_id.id': 'country_id.id',
            'state_id.id': 'state_id.id'
            }
    
    def get_contact_title(sugar_obj, cr, uid, salutation, domain, context=None):
        fields = ['shortcut', 'name', 'domain']
        data = [salutation, salutation, domain]
        return import_object(sugar_obj, cr, uid, fields, data, 'res.partner.title', 'contact_title', salutation, [('shortcut', '=', salutation)], context=context)
    
    if not context:
        context = {}  
    
    lead_obj = sugar_obj.pool.get('crm.lead')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'Leads')
    for val in sugar_data:
        if val.get('do_not_call') == '0':
            val['optout'] = '1'
        if val.get('opportunity_id'):
            continue
        if val.get('salutation'):
            title_id = get_contact_title(sugar_obj, cr, uid, val.get('salutation'), 'Contact', context)
            val['title/id'] = title_id
        val['type'] = 'lead'
        val['type_id/id'] = get_campaign_id(sugar_obj, cr, uid, val.get('lead_source'), context)
        stage_id = get_lead_status(sugar_obj, cr, uid, val, context)
        val['stage_id/id'] = stage_id
        val['state'] = get_lead_state(sugar_obj, cr, uid, val,context)
        if val.get('primary_address_country'):
            country_id = get_all_countries(sugar_obj, cr, uid, val.get('primary_address_country'), context)
            state = get_all_states(sugar_obj,cr, uid, val.get('primary_address_state'), country_id, context)
            val['country_id.id'] =  country_id
            val['state_id.id'] =  state            
        fields, datas = sugarcrm_fields_mapp(val, map_lead, context)
        lead_obj.import_data(cr, uid, fields, [datas], mode='update', current_module=MODULE_NAME, noupdate=True, context=context)
    return True



def import_opportunities(sugar_obj, cr, uid, context=None):
    map_opportunity = {'id' : 'id',
        'name': 'name',
        'probability': 'probability',
        'partner_id/name': 'account_name',
        'title_action': 'next_step',
        'partner_address_id/name': 'partner_address_id/name',
        'planned_revenue': 'amount',
        'date_deadline': ['__datetime__', 'date_closed'],
        'user_id/id' : 'assigned_user_id',
        'stage_id/id' : 'stage_id/id',
        'type' : 'type',
        'categ_id/id': 'categ_id/id',
        'email_from': 'email_from'
    }
    
    def get_opportunity_contact(sugar_obj,cr,uid, PortType, sessionid, val, partner_xml_id, context=None):
        partner_contact_name = False 
        partner_contact_email = False       
        model_obj = sugar_obj.pool.get('ir.model.data')
        partner_address_obj = sugar_obj.pool.get('res.partner.address')
        model_account_ids = model_obj.search(cr, uid, [('res_id', '=', partner_xml_id[0]), ('model', '=', 'res.partner'), ('module', '=', MODULE_NAME)])
        model_xml_id = model_obj.browse(cr, uid, model_account_ids)[0].name 
        sugar_account_contact = set(sugar.relation_search(PortType, sessionid, 'Accounts', module_id=model_xml_id, related_module='Contacts', query=None, deleted=None))
        sugar_opportunities_contact = set(sugar.relation_search(PortType, sessionid, 'Opportunities', module_id=val.get('id'), related_module='Contacts', query=None, deleted=None))
        sugar_contact = list(sugar_account_contact.intersection(sugar_opportunities_contact))
        if sugar_contact: 
            for contact in sugar_contact:
                model_ids = find_mapped_id(sugar_obj, cr, uid, 'res.partner.address', contact, context)
                if model_ids:
                    model_id = model_obj.browse(cr, uid, model_ids)[0].res_id
                    address_id = partner_address_obj.browse(cr, uid, model_id)
                    partner_address_obj.write(cr, uid, [address_id.id], {'partner_id': partner_xml_id[0]})
                    partner_contact_name = address_id.name
                    partner_contact_email = address_id.email
                else:
                    partner_contact_name = val.get('account_name')
        return partner_contact_name, partner_contact_email
    
    def get_opportunity_status(sugar_obj, cr, uid, sugar_val,context=None):
        fields = ['name', 'type']
        name = 'Opportunity_' + sugar_val['sales_stage']
        data = [sugar_val['sales_stage'], 'Opportunity']
        return import_object(sugar_obj, cr, uid, fields, data, 'crm.case.stage', 'crm_stage', name, [('type', '=', 'opportunity'), ('name', 'ilike', sugar_val['sales_stage'])], context)

    if not context:
        context = {}
    
    lead_obj = sugar_obj.pool.get('crm.lead')
    partner_obj = sugar_obj.pool.get('res.partner')
    PortType, sessionid = sugar.login(context.get('username', ''), context.get('password', ''), context.get('url',''))
    sugar_data = sugar.search(PortType, sessionid, 'Opportunities')
    for val in sugar_data:
        partner_xml_id = partner_obj.search(cr, uid, [('name', 'like', val.get('account_name'))])
        if not partner_xml_id:
            raise osv.except_osv(_('Warning !'), _('Reference Partner %s cannot be created, due to Lower Record Limit in SugarCRM Configuration.') % val.get('account_name'))
        partner_contact_name, partner_contact_email = get_opportunity_contact(sugar_obj,cr,uid, PortType, sessionid, val, partner_xml_id, context)
        val['partner_address_id/name'] = partner_contact_name
        val['email_from'] = partner_contact_email
        val['categ_id/id'] = get_category(sugar_obj, cr, uid, 'crm.lead', val.get('opportunity_type'))                    
        val['type'] = 'opportunity'
        val['stage_id/id'] = get_opportunity_status(sugar_obj, cr, uid, val, context)
        fields, datas = sugarcrm_fields_mapp(val, map_opportunity)
        lead_obj.import_data(cr, uid, fields, [datas], mode='update', current_module=MODULE_NAME, noupdate=True, context=context)
    return True


MAP_FIELDS = {'Opportunities':  #Object Mapping name
                    {'dependencies' : ['Users', 'Accounts', 'Contacts', 'Leads'],  #Object to import before this table
                     'process' : import_opportunities,
                     },
              'Leads':
                    {'dependencies' : ['Users', 'Accounts', 'Contacts'],  #Object to import before this table
                     'process' : import_leads,
                    },
              'Contacts':
                    {'dependencies' : ['Users','Accounts'],  #Object to import before this table
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
              'Documents': 
                    {'dependencies' : ['Users'],
                     'process' : import_documents,
                    },
              'Meetings': 
                    {'dependencies' : ['Accounts', 'Contacts', 'Users', 'Projects', 'Opportunities', 'Tasks'],
                     'process' : import_meetings,
                    },        
              'Tasks': 
                    {'dependencies' : ['Accounts', 'Contacts', 'Users'],
                     'process' : import_tasks,
                    },  
              'Calls': 
                    {'dependencies' : ['Accounts', 'Contacts', 'Users', 'Opportunities'],
                     'process' : import_calls,
                    },  
              'Projects': 
                    {'dependencies' : ['Users', 'Accounts', 'Contacts'],
                     'process' : import_projects,
                    },                        
              'Project Tasks': 
                    {'dependencies' : ['Users', 'Projects'],
                     'process' : import_project_tasks,
                    },
              'Bugs': 
                    {'dependencies' : ['Users', 'Projects', 'Project Tasks'],
                     'process' : import_bug,
                    },                         
              'Claims': 
                    {'dependencies' : ['Users', 'Accounts', 'Contacts', 'Leads'],
                     'process' : import_claims,
                    },                         
              'Emails': 
                    {'dependencies' : ['Users', 'Projects', 'Project Tasks', 'Accounts', 'Contacts', 'Leads', 'Opportunities', 'Meetings', 'Calls'],
                     'process' : import_emails,
                    },    
              
              'Notes': 
                    {'dependencies' : ['Users', 'Projects', 'Project Tasks', 'Accounts', 'Contacts', 'Leads', 'Opportunities', 'Meetings', 'Calls'],
                     'process' : import_history,
                    },  
              'Employees': 
                    {'dependencies' : ['Users'],
                     'process' : import_employees,
                    },                                                                     
          }

class import_sugarcrm(osv.osv):
    """Import SugarCRM DATA"""
    
    _name = "import.sugarcrm"
    _description = __doc__
    _columns = {
        'opportunity': fields.boolean('Leads and Opportunities', help="If Opportunities are checked, SugarCRM opportunities data imported in OpenERP crm-Opportunity form"),
        'user': fields.boolean('Users', help="If Users  are checked, SugarCRM Users data imported in OpenERP Users form"),
        'contact': fields.boolean('Contacts', help="If Contacts are checked, SugarCRM Contacts data imported in OpenERP partner address form"),
        'account': fields.boolean('Accounts', help="If Accounts are checked, SugarCRM  Accounts data imported in OpenERP partners form"),
        'employee': fields.boolean('Employee', help="If Employees is checked, SugarCRM Employees data imported in OpenERP employees form"),
        'meeting': fields.boolean('Meetings', help="If Meetings is checked, SugarCRM Meetings data imported in OpenERP meetings form"),
        'call': fields.boolean('Calls', help="If Calls is checked, SugarCRM Calls data imported in OpenERP phonecalls form"),
        'claim': fields.boolean('Claims', help="If Claims is checked, SugarCRM Claims data imported in OpenERP Claims form"),
        'email': fields.boolean('Emails', help="If Emails is checked, SugarCRM Emails data imported in OpenERP Emails form"),
        'project': fields.boolean('Projects', help="If Projects is checked, SugarCRM Projects data imported in OpenERP Projects form"),
        'project_task': fields.boolean('Project Tasks', help="If Project Tasks is checked, SugarCRM Project Tasks data imported in OpenERP Project Tasks form"),
        'task': fields.boolean('Tasks', help="If Tasks is checked, SugarCRM Tasks data imported in OpenERP Meetings form"),
        'bug': fields.boolean('Bugs', help="If Bugs is checked, SugarCRM Bugs data imported in OpenERP Project Issues form"),
        'attachment': fields.boolean('Attachments', help="If Attachments is checked, SugarCRM Notes data imported in OpenERP's Related module's History with attachment"),
        'document': fields.boolean('Documents', help="If Documents is checked, SugarCRM Documents data imported in OpenERP Document Form"),
        'username': fields.char('User Name', size=64),
        'password': fields.char('Password', size=24),
    }
    _defaults = {#to be set to true, but easier for debugging
       'opportunity': False,
       'user' : False,
       'contact' : False,
       'account' : False,
        'employee' : False,
        'meeting' : False,
        'task' : False,
        'call' : False,
        'claim' : False,    
        'email' : False, 
        'project' : False,   
        'project_task': False,     
        'bug': False,
        'document': False
    }
    
    def get_key(self, cr, uid, ids, context=None):
        """Select Key as For which Module data we want import data."""
        if not context:
            context = {}
        key_list = []
        for current in self.browse(cr, uid, ids, context):
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
            if current.meeting:
                key_list.append('Meetings')
            if current.task:
                key_list.append('Tasks')
            if current.call:
                key_list.append('Calls')
            if current.claim:
                key_list.append('Claims')                
            if current.email:
                key_list.append('Emails') 
            if current.project:
                key_list.append('Projects')
            if current.project_task:
                key_list.append('Project Tasks')
            if current.bug:
                key_list.append('Bugs')
            if current.attachment:
                key_list.append('Notes')     
            if current.document:
                key_list.append('Documents')                                                  
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
        return True        

import_sugarcrm()
