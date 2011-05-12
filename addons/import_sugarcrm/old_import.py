'''
Created on 9 mai 2011

@author: openerp
'''

#TODO old source code to be deleted once it's migrated


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



STATE_MAP = {
        
        TABLE_CALL : {   
            'Planned' : 'open',
            'Held':'done',
            'Not Held': 'pending',
        },
        TABLE_TASK :  {
            'Completed' : 'done',
            'Not Started':'draft',
            'In Progress': 'open',
            'Pending Input': 'draft',
            'deferred': 'cancel'
        },
        TABLE_PROJECT: {
            'Draft' : 'draft',
            'In Review': 'open',
            'Published': 'close',
        },
        TABLE_PROJECT_TASK: {
            'Not Started': 'draft',
            'In Progress': 'open',
            'Completed': 'done',
            'Pending Input': 'pending',
            'Deferred': 'cancelled',
        },
        TABLE_CASE : {
            'New' : 'draft',
            'Assigned':'open',
            'Closed': 'done',
            'Pending Input': 'pending',
            'Rejected': 'cancel',
            'Duplicate': 'draft',
        },
}







def get_related_objects(sugar_obj,cr,uid, id, TABLE_PARENT, TABLE_CHILD, context=None):
    if not context:
        context={}
    PortType,sessionid = sugar.login(context.get('username',''), context.get('password',''), context.get('url',''))
    sugar_links = sugar.relation_search(PortType, sessionid, TABLE_PARENT, module_id=id, related_module=TABLE_CHILD, query=None, deleted=None)
    res = []
    for link in sugar_links:
        xml_id = xml_id_exist(sugar_obj, cr, uid, TABLE_CHILD, link, context)
        res.append(xml_id)
    return res

def get_related_object(sugar_obj,cr,uid, id, TABLE_PARENT, TABLE_CHILD, context=None):
    res = get_related_objects(sugar_obj,cr,uid, id, TABLE_PARENT, TABLE_CHILD, context)
    return res and res[0] or ''

def get_contact_info_from_account(sugar_obj, cr, uid, account_id, context=None):
    partner_id = get_mapped_id(sugar_obj, cr, uid, TABLE_ACCOUNT, account_id, context)
    partner_address_id = False
    partner_phone = False
    partner_email = False
    
    if not partner_id:
        return partner_address_id, partner_phone,partner_email
    
    partner = sugar_obj.pool.get('res.partner').browse(cr, uid, [partner_id], context=context)[0]
    if partner.address and partner.address[0]:
        address = partner.address[0]
        partner_address_id = address.id
        partner_phone = address.phone
        partner_email = address.email
    
    return partner_address_id, partner_phone,partner_email







    

def get_project_task_state(sugar_obj, cr, uid, val,context=None):
    if not context:
        context = {}
    state_dict = {}
    state = state_dict['status'].get(val, '')
    return state    



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

def import_tasks(sugar_obj, cr, uid, context=None):
    map_task = {
                'name': 'name',
                'date': ['__datetime__', 'date_start'],
                'date_deadline' : ['__datetime__', 'date_due'],
                'user_id/id': 'user_id/id', 
                'categ_id/id': 'categ_id/id',
                'partner_id/id': 'partner_id/id',
                'partner_address_id/id': 'partner_address_id/id',
                'state': 'state'
    }
    
    
    
    sugar_data = get_sugar_data(TABLE_TASK, context)
    for val in sugar_data:
        val['user_id/id'] = xml_id_exist(sugar_obj, cr, uid, TABLE_USER, val['assigned_user_id'], context)
        val['partner_id/id'] = get_related_id(sugar_obj, cr, uid, val, TABLE_ACCOUNT, context)
        val['partner_address_id/id'] = get_related_id(sugar_obj, cr, uid, val, TABLE_CONTACT, context) or xml_id_exist(sugar_obj, cr, uid, TABLE_CONTACT, val['contact_id'], context)
        val['categ_id/id'] = get_category(sugar_obj, cr, uid, 'crm.meeting', 'Tasks')
        val['state'] =  STATE_MAP[TABLE_TASK].get(val['status'])
        val['date_start'] = val['date_start'] or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        val['date_due'] = val['date_due'] or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    import_module(sugar_obj, cr, uid, 'crm.meeting', map_task, sugar_data, TABLE_TASK, context=context)

#TODO    
def get_attendee_id(sugar_obj, cr, uid, module_name, module_id, context=None):
    if not context:
        context = {}
    PortType,sessionid = sugar.login(context.get('username',''), context.get('password',''), context.get('url',''))
    model_obj = sugar_obj.pool.get('ir.model.data')
    att_obj = sugar_obj.pool.get('calendar.attendee')
    meeting_obj = sugar_obj.pool.get('crm.meeting')
    user_dict = sugar.user_get_attendee_list(PortType, sessionid, module_name, module_id)
    #TODO there is more then just user in attendee list
    #there is contact, partner, lead (but we don't import the link) and user
    for user in user_dict: 
        continue
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
    
def import_meetings(sugar_obj, cr, uid, context=None):
    map_meeting = 
    
    
    sugar_data = get_sugar_data(TABLE_MEETING, context)
    for val in sugar_data:
        val['alarm_id/id'] = get_alarm_id(sugar_obj, cr, uid, val.get('reminder_time'), context)
        get_attendee_id(sugar_obj, cr, uid, 'Meetings', val.get('id'), context) #TODO
    import_module(sugar_obj, cr, uid, 'crm.meeting', map_meeting, sugar_data, TABLE_MEETING, context=context)
        



        

def import_calls(sugar_obj, cr, uid, context=None):
    if not context:
        context = {}
    map_calls = {
            'name': 'name',
            'date': ['__datetime__', 'date_start'],
            'duration': ['duration_hours', 'duration_minutes'],
            'user_id/id': 'user_id/id',
            'partner_id/id': 'partner_id/id',
            'partner_address_id/id': 'partner_address_id/id',
            'categ_id/id': 'categ_id/id',
            'state': 'state',
            'opportunity_id/id': 'opportunity_id/id',
            'description': 'description',
    }
    sugar_data = get_sugar_data('Calls', context)
    for val in sugar_data:
        val['user_id/id'] = xml_id_exist(sugar_obj, cr, uid, TABLE_USER, val['assigned_user_id'], context)
        val['opportunity_id/id'] = get_related_id(sugar_obj, cr, uid, val, [TABLE_OPPORTUNITY, TABLE_LEAD], context)
        val['partner_id/id'] = get_related_id(sugar_obj, cr, uid, val, [TABLE_ACCOUNT], context)
        val['partner_address_id/id'] = get_related_id(sugar_obj, cr, uid, val, [TABLE_CONTACT], context)
        val['state'] =  STATE_MAP[TABLE_CALL].get(val['status'])
        val['categ_id/id'] = get_category(sugar_obj, cr, uid, 'crm.phonecall', val.get('direction'))   
    import_module(sugar_obj, cr, uid, 'crm.phonecall', map_calls, sugar_data, TABLE_CALL, context=context)
   

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


    


def import_claims(sugar_obj, cr, uid, context=None):
    map_claim = {
                    'name': 'name',
                    'date': ['__datetime__', 'date_entered'],
                    'user_id/id': 'user_id/id',
                    'priority':'priority',
                    'partner_id/id': 'partner_id/id',
                    'partner_address_id/.id': 'partner_address_id/.id',
                    'partner_phone': 'partner_phone',
                    'email_from': 'email_from',                    
                    'description': 'description',
                    'state': 'state',
    }
    
    def get_claim_priority(val):
        priority_dict = {            
                'High': '2',
                'Medium': '3',
                'Low': '4'
        }
        return priority_dict.get(val, '')
    
    sugar_data = get_sugar_data(TABLE_CASE, context)
    print sugar_data
    for val in sugar_data:
        val['user_id/id'] = xml_id_exist(sugar_obj, cr, uid, TABLE_USER, val['assigned_user_id'], context)
        val['partner_address_id/.id'], val['partner_phone'],val['email_from'] = get_contact_info_from_account(sugar_obj, cr, uid, val['account_id'], context)
        val['partner_id/id'] = xml_id_exist(sugar_obj, cr, uid, TABLE_ACCOUNT, val['account_id'], context=context)
        val['priority'] = get_claim_priority(val.get('priority'))
        val['state'] = STATE_MAP[TABLE_CASE].get( val.get('status'))
        print "cases"
        pp.pprint(val)
    import_module(sugar_obj, cr, uid, 'crm.claim', map_claim, sugar_data, TABLE_CASE, context=context)

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
#Validated

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
  
    map_project = {
        'name': 'name',
        'date_start': ['__datetime__', 'estimated_start_date'],
        'date': ['__datetime__', 'estimated_end_date'],
        'user_id/id': 'user_id/id',
        'partner_id/id': 'partner_id/id',
        'contact_id/id' : 'contact_id/id',
        'state': 'state'   
    }
    
    sugar_data = get_sugar_data(TABLE_PROJECT, context)
    for val in sugar_data:
        val['user_id/id'] = xml_id_exist(sugar_obj, cr, uid, TABLE_USER, val['assigned_user_id'], context)
        val['partner_id/id'] = get_related_object(sugar_obj,cr,uid, val['id'], TABLE_PROJECT, TABLE_ACCOUNT, context)
        val['contact_id/id'] = get_related_object(sugar_obj,cr,uid, val['id'], TABLE_PROJECT, TABLE_CONTACT, context)
        val['state'] = STATE_MAP[TABLE_PROJECT].get(val['status'])
    import_module(sugar_obj, cr, uid, 'project.project', map_project, sugar_data, TABLE_PROJECT, context)

def import_project_tasks(sugar_obj, cr, uid, context=None):
    map_project_task = {
        'name': 'name',
        'date_start': ['__datetime__', 'date_start'],
        'date_end': ['__datetime__', 'date_finish'],
        'progress': 'progress',
        'project_id/id': 'project_id/id',
        'planned_hours': 'planned_hours',
        'total_hours': 'total_hours',        
        'priority': 'priority',
        'description': 'description',
        'user_id/id': 'user_id/id',
        'state': 'state'   
    }
    
    def get_project_task_priority(val):
        priority_dict = {
                'High': '0',
                'Medium': '2',
                'Low': '3'
        }
        return priority_dict.get(val, '')
     
    sugar_data = get_sugar_data(TABLE_PROJECT_TASK, context)
    for val in sugar_data:
        val['project_id/id'] = xml_id_exist(sugar_obj, cr, uid, TABLE_PROJECT, val['project_id'], context)
        val['user_id/id'] = xml_id_exist(sugar_obj, cr, uid, TABLE_USER, val['assigned_user_id'], context)
        val['state'] = STATE_MAP[TABLE_PROJECT_TASK].get( val.get('status'))
        val['priority'] = get_project_task_priority(val.get('priority'))
    import_module(sugar_obj, cr, uid, 'project.task', map_project_task, sugar_data, TABLE_PROJECT_TASK, context)
    

MAP_FIELDS = {'Documents': 
                    {'dependencies' : ['Users'],
                     'process' : import_documents,
                    },
              'Tasks': 
                    {'dependencies' : ['Accounts', 'Contacts', 'Users'],
                     'process' : import_tasks,
                    },  
              'Calls': 
                    {'dependencies' : ['Accounts', 'Contacts', 'Users', 'Opportunities', 'Leads'],
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
          }
