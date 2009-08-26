# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import wizard
import osv
import pooler

info = '''<?xml version="1.0"?>
<form string="Module Recording">
    <label string="Thanks For using Module Recorder" colspan="4" align="0.0"/>
</form>'''

info_start_form = '''<?xml version="1.0"?>
<form string="Module Recording">
    <separator string="Recording Information" colspan="4"/>
    <field name="info_status"/>
    <field name="info_text" colspan="4" nolabel="1"/>
</form>'''

info_start_fields = {
    'info_text': {'string':'Information', 'type':'text', 'readonly':True},
    'info_status': {'string':'Status','type':'selection', 'selection':[('no','Not Recording'),('record','Recording')], 'readonly':True}
}



intro_start_form = '''<?xml version="1.0"?>
<form string="Module Recording">
    <separator string="Module Information" colspan="4"/>
    <field name="name"/>
    <field name="directory_name"/>
    <field name="version"/>
    <field name="author"/>
    <field name="website" colspan="4"/>
    <field name="category" colspan="4"/>
    <field name="data_kind"/>
    <newline/>
    <field name="description" colspan="4"/>
</form>'''

intro_start_fields = {
    'name': {'string':'Module Name', 'type':'char', 'size':64, 'required':True},
    'directory_name': {'string':'Directory Name', 'type':'char', 'size':32, 'required':True},
    'version': {'string':'Version', 'type':'char', 'size':16, 'required':True},
    'author': {'string':'Author', 'type':'char', 'size':64, 'default': lambda *args: 'Tiny', 'required':True},
    'category': {'string':'Category', 'type':'char', 'size':64, 'default': lambda *args: 'Vertical Modules/Parametrization', 'required':True},
    'website': {'string':'Documentation URL', 'type':'char', 'size':64, 'default': lambda *args: 'http://www.openerp.com', 'required':True},
    'description': {'string':'Full Description', 'type':'text', 'required':True},
    'data_kind': {'string':'Type of Data', 'type':'selection', 'selection':[('demo','Demo Data'),('update','Normal Data')], 'required':True, 'default': lambda *args:'update'},
}

intro_save_form = '''<?xml version="1.0"?>
<form string="Module Recording">
    <separator string="Module successfully created !" colspan="4"/>
    <field name="module_filename"/>
    <newline/>
    <field name="module_file" filename="module_filename"/>
    <separator string="Information" colspan="4"/>
    <label string="If you think your module could interrest others people, we'd like you to publish it on OpenERP.com, in the 'Modules' section. You can do it through the website or using features of the 'base_module_publish' module." colspan="4" align="0.0"/>
    <label string="Thanks in advance for your contribution." colspan="4" align="0.0"/>
</form>'''

intro_save_fields = {
    'module_file': {'string': 'Module .zip File', 'type':'binary', 'readonly':True},
    'module_filename': {'string': 'Filename', 'type':'char', 'size': 64, 'readonly':True},
}

import zipfile
import StringIO
import base64

def _info_default(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    mod = pool.get('ir.module.record')
    result = {}
    info = "Details of "+str(len(mod.recording_data))+" Operation(s):\n\n"

    for line in mod.recording_data:
        result.setdefault(line[0],{})
        result[line[0]].setdefault(line[1][3], {})
        result[line[0]][line[1][3]].setdefault(line[1][4], 0)
        result[line[0]][line[1][3]][line[1][4]]+=1
    for key1,val1 in result.items():
        info+=key1+"\n"
        for key2,val2 in val1.items():
            info+="\t"+key2+"\n"
            for key3,val3 in val2.items():
                info+="\t\t"+key3+" : "+str(val3)+"\n"
    return {'info_text': info, 'info_status':mod.recording and 'record' or 'no'}

def _create_module(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    mod = pool.get('ir.module.record')
    res_xml = mod.generate_xml(cr, uid)

    s=StringIO.StringIO()
    zip = zipfile.ZipFile(s, 'w')
    dname = data['form']['directory_name']
    data['form']['update_name'] = ''
    data['form']['demo_name'] = ''
    if data['form']['data_kind'] =='demo':
        data['form']['demo_name'] = '"%(directory_name)s_data.xml"' % data['form']
    else:
        data['form']['update_name'] = '"%(directory_name)s_data.xml"' % data['form']
    data['form']['depends'] = ','.join(map(lambda x: '"'+x+'"',mod.depends.keys()))
    _terp = """{
        "name" : "%(name)s",
        "version" : "%(version)s",
        "author" : "%(author)s",
        "website" : "%(website)s",
        "category" : "%(category)s",
        "description": \"\"\"%(description)s\"\"\",
        "depends" : [%(depends)s],
        "init_xml" : [ ],
        "demo_xml" : [ %(demo_name)s],
        "update_xml" : [%(update_name)s],
        "installable": True
} """ % data['form']
    filewrite = {
        '__init__.py':'#\n# Generated by the Open ERP module recorder !\n#\n',
        '__terp__.py':_terp,
        dname+'_data.xml': res_xml
    }
    for name,datastr in filewrite.items():
        info = zipfile.ZipInfo(dname+'/'+name)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 2175008768
        if not datastr:
            datastr = ''
        zip.writestr(info, datastr)
    zip.close()
    return {
        'module_file': base64.encodestring(s.getvalue()),
        'module_filename': data['form']['directory_name']+'-'+data['form']['version']+'.zip'
    }
def _check(self, cr, uid, data, context):
     pool = pooler.get_pool(cr.dbname)
     mod = pool.get('ir.module.record')
     if len(mod.recording_data):
         return 'info'
     else:
         return 'end'

class base_module_publish(wizard.interface):
    states = {
        'init': {
            'actions': [_info_default],
            'result': {
                'type':'form',
                'arch':info_start_form,
                'fields': info_start_fields,
                'state':[
                    ('end', 'Cancel', 'gtk-cancel'),
                    ('check', 'Continue', 'gtk-ok'),
                ]
            }
        },
        'check': {
            'actions': [],
            'result': {'type':'choice','next_state':_check}
        },
        'info': {
            'actions': [],
            'result': {
                'type':'form',
                'arch':intro_start_form,
                'fields': intro_start_fields,
                'state':[
                    ('end', 'Cancel', 'gtk-cancel'),
                    ('save', 'Continue', 'gtk-ok'),
                ]
            }
        },
        'save': {
            'actions': [_create_module],
            'result': {
                'type':'form',
                'arch':intro_save_form,
                'fields': intro_save_fields,
                'state':[
                    ('end', 'Close', 'gtk-ok'),
                ]
            }
        },
        'end': {
            'actions': [],
            'result': {'type':'form', 'arch':info, 'fields':{}, 'state':[('end','OK')]}
        },
    }
base_module_publish('base_module_record.module_save')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

