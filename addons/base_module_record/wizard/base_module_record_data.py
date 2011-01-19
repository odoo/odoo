# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

import wizard
import osv
import pooler
import time

info = '''<?xml version="1.0"?>
<form string="Module Recording">
    <label string="Thanks For using Module Recorder" colspan="4" align="0.0"/>
</form>'''

intro_start_form = '''<?xml version="1.0"?>
<form string="Objects Recording">
    <field name="check_date"/>
    <newline/>
    <field name="filter_cond"/>
    <separator string="Choose objects to record" colspan="4"/>
    <field name="objects" colspan="4" nolabel="1"/>
    <group><field name="info_yaml"/></group>
</form>'''

intro_start_fields = {
    'check_date':  {'string':"Record from Date",'type':'datetime','required':True, 'default': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S')},
    'objects':{'string': 'Objects', 'type': 'many2many', 'relation': 'ir.model', 'help': 'List of objects to be recorded'},
    'filter_cond':{'string':'Records only', 'type':'selection','selection':[('created','Created'),('modified','Modified'),('created_modified','Created & Modified')], 'required':True, 'default': lambda *args:'created'},
    'info_yaml': {'string':'YAML','type':'boolean'}
}

exp_form = '''<?xml version="1.0"?>
<form string="Objects Recording">
    <separator string="Result, paste this to your module's xml" colspan="4" />
    <field name="res_text" nolabel="1"  colspan="4"/>
</form>'''

exp_fields = {
    'res_text':  {'string':"Result",'type':'text', },
}

def _info_default(self, cr, uid, data, context):
     pool = pooler.get_pool(cr.dbname)
     mod = pool.get('ir.model')
     list=('ir.ui.view','ir.ui.menu','ir.model','ir.model.fields','ir.model.access',\
        'res.partner','res.partner.address','res.partner.category','workflow',\
        'workflow.activity','workflow.transition','ir.actions.server','ir.server.object.lines')
     data['form']['objects']=mod.search(cr,uid,[('model','in',list)])
     cr.execute('select max(create_date) from ir_model_data')
     c=(cr.fetchone())[0].split('.')[0]
     c = time.strptime(c,"%Y-%m-%d %H:%M:%S")
     sec=c.tm_sec + 1
     c=(c[0],c[1],c[2],c[3],c[4],sec,c[6],c[7],c[8])
     data['form']['check_date']=time.strftime("%Y-%m-%d %H:%M:%S",c)
     return data['form']

def _record_objects(self, cr, uid, data, context):
    check_date=data['form']['check_date']
    filter=data['form']['filter_cond']
    pool = pooler.get_pool(cr.dbname)
    user=(pool.get('res.users').browse(cr,uid,uid)).login
    mod = pool.get('ir.module.record')
    mod_obj = pool.get('ir.model')
    mod.recording_data = []

    for id in data['form']['objects'][0][2]:
        obj_name=(mod_obj.browse(cr,uid,id)).model
        obj_pool=pool.get(obj_name)
        if filter =='created':
            search_condition =[('create_date','>',check_date)]
        elif filter =='modified':
            search_condition =[('write_date','>',check_date)]
        elif filter =='created_modified':
            search_condition =['|',('create_date','>',check_date),('write_date','>',check_date)]
        if '_log_access' in dir(obj_pool):
              if not (obj_pool._log_access):
                  search_condition=[]
              if '_auto' in dir(obj_pool):
                  if not obj_pool._auto:
                      continue
        elif '_log_access' not in dir(obj_pool):
             search_condition = []
        search_ids=obj_pool.search(cr,uid,search_condition)
        for s_id in search_ids:
             args=(cr.dbname,uid,obj_name,'copy',s_id,{},context)
             mod.recording_data.append(('query',args, {}, s_id))
    return {'type': 'ir.actions.act_window_close'}

def _check(self, cr, uid, data, context):
     pool = pooler.get_pool(cr.dbname)
     mod = pool.get('ir.module.record')
     if len(mod.recording_data):
         if data['form']['info_yaml']:
             return 'save_yaml'
         else:
             return 'info'
     else:
         return 'end'
         
def _create_xml(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    mod = pool.get('ir.module.record')
    res_xml = mod.generate_xml(cr, uid)
    return { 'res_text': res_xml }

def _create_yaml(self,cr,uid,data,context):
    pool = pooler.get_pool(cr.dbname)
    mod = pool.get('ir.module.record')
    res_xml = mod.generate_yaml(cr, uid)
    return { 'res_text': res_xml }

class base_module_record_objects(wizard.interface):
    states = {
         'init': {
            'actions': [_info_default],
            'result': {
                'type':'form',
                'arch':intro_start_form,
                'fields': intro_start_fields,
                'state':[
                    ('end', 'Cancel', 'gtk-cancel'),
                    ('record', 'Record', 'gtk-ok'),
                ]
            }
        },
        'record': {
            'actions': [],
            'result': {'type':'action','action':_record_objects,'state':'check'}
                },
        'check': {
            'actions': [],
            'result': {'type':'choice','next_state':_check}
        },
         'info': {
            'actions': [ _create_xml ],
            'result': {
                'type':'form',
                'arch': exp_form,
                'fields':exp_fields,
                'state':[
                    ('end', 'End', 'gtk-cancel'),
                ]
            },
        },
        'save_yaml': {
            'actions': [ _create_yaml ],
            'result': {
                'type':'form',
                'arch': exp_form,
                'fields':exp_fields,
                'state':[
                    ('end', 'End', 'gtk-cancel'),
                ]
            },
        },
         'end': {
            'actions': [],
            'result': {'type':'form', 'arch':info, 'fields':{}, 'state':[('end','OK')]}
        },
    }
base_module_record_objects('base_module_record.module_record_data')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

