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
import tools
import os
from xml.dom import minidom
from tools.translate import _
from tools.safe_eval import safe_eval as eval

info_start_form = '''<?xml version="1.0"?>
<form string="Module Merging">
    <field name="modules_list" colspan="4"/>
</form>'''

info_start_fields = {
    'modules_list': {'string':'Modules', 'type':'many2many','relation':'ir.module.module','help':'Select Modules which you want to merge in single module'},
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
    <field name="module_file"/>
    <separator string="Information" colspan="4"/>
    <label string="If you think your module could interrest others people, we'd like you to publish it on OpenERP.com, in the 'Modules' section. You can do it through the website or using features of the 'base_module_publish' module." colspan="4" align="0.0"/>
    <label string="Thanks in advance for your contribution." colspan="4" align="0.0"/>
</form>'''

intro_save_fields = {
    'module_file': {'string': 'Module .zip File', 'type':'binary', 'readonly':True},
    'module_filename': {'string': 'Filename', 'type':'char', 'size': 64, 'readonly':True},
}
import zipfile
from zipfile import PyZipFile, ZIP_DEFLATED
import StringIO
import base64

class base_module_merge(wizard.interface):

    def _zip_writestr(self,file_name,data):
        info = zipfile.ZipInfo(file_name)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 2175008768
        self.archive.writestr(info,data)
        return True

    def _remove_prefix_ref(self,fromurl,path):
        infile=tools.file_open(os.path.join(fromurl,path))
        xml=infile.read()
        mydom = minidom.parseString(xml)
        for child in mydom.getElementsByTagName("field"):
            for attr in child.attributes.keys():
                if attr=='ref':
                    old=child.getAttribute(attr)
                    if len(old.split('.')) > 1:
                        if old.split('.')[0] in self.dependencies:
                            child.setAttribute(attr,old.split('.')[1])
        return mydom.toxml()

    def _parse_init(self,path,filename):
        res=[]
        path=os.path.join(path,filename)
        infile=open(path,'r')
        for i in infile:
            i=i.strip()
            if len(i)>0:
                if i[0]!="#":
                    res.append( i.strip().split('\n')[0])
        infile.close()
        return res

    def _zippy(self,archive, fromurl, path, src=True):
        if path!='':
            url = os.path.join(fromurl, path)
        else:
            url=fromurl
        if os.path.isdir(url):
            if path.split('/')[-1].startswith('.'):
                return False
            for fname in os.listdir(url):
                self._zippy(self.archive, fromurl, path and os.path.join(path, fname) or fname, src=src)
        else:
            if src:
                exclude = ['pyo', 'pyc']
            else:
                exclude = ['py','pyo','pyc']
            if (path.split('.')[-1] not in exclude):
                if os.path.basename(path)=='__init__.py':
                    datas=self._parse_init(fromurl,path)
                    if path in self.dict_init:
                        self.dict_init[path]+=datas
                    else:
                        self.dict_init[path]=datas
                    return True
                if os.path.basename(path)=='__terp__.py':
                    terp_file=os.path.join(fromurl,path)
                    terp_info=eval(tools.file_open(terp_file).read())
                    self.init_xml+=terp_info['init_xml']
                    self.demo_xml+=terp_info['demo_xml']
                    self.update_xml+=terp_info['update_xml']
                    return True
                try:
                    info = self.archive.getinfo(path)
                except KeyError:
                    if path.split('.')[-1] == 'xml':
                        xml_doc=self._remove_prefix_ref(fromurl,path)
                        xml_doc = xml_doc.encode("utf-8")
                        self._zip_writestr(path, xml_doc)
                    else:
                        file_data=tools.file_open(os.path.join(fromurl, path)).read()
                        self._zip_writestr(path, file_data)
                else:
                    path2=os.path.split(fromurl)[-1]
                    new_path=path2+'_'+os.path.split(path)[-1]
                    if len(os.path.split(path))>1:
                        new_path=os.path.join(os.path.split(path)[0],new_path)
                    if path.split('.')[-1] == 'xml':
                        xml_doc=self._remove_prefix_ref(fromurl,path)
                        xml_doc = xml_doc.encode("utf-8")
                        self._zip_writestr(new_path, xml_doc)
                        if len(os.path.split(path))>1:
                            terp_file=os.path.join(fromurl,'__terp__.py')
                            terp_info=eval(tools.file_open(terp_file).read())
                            if os.path.basename(path) in terp_info['init_xml']:
                                self.init_xml+=[os.path.basename(new_path)]
                            elif os.path.basename(path) in terp_info['demo_xml']:
                                self.demo_xml+=[os.path.basename(new_path)]
                            elif os.path.basename(path) in terp_info['update_xml']:
                                self.update_xml+=[os.path.basename(new_path)]
                    else:
                        file_data=tools.file_open(os.path.join(fromurl, path)).read()
                        self._zip_writestr(new_path, file_data)
                    if new_path.split('.')[-1] == 'py':
                        new_import='import '+os.path.basename(new_path).split('.')[0]
                        if os.path.dirname(path)=='':
                            dict_key='__init__.py'
                        else:
                            dict_key=os.path.join(os.path.dirname(path),'__init__.py')
                        if dict_key in self.dict_init:
                            self.dict_init[dict_key]+=[new_import]
                        else:
                            self.dict_init[dict_key]=[new_import]
        return True

    def rec_depend(self,cr, uid, ids, data, context=None, level=50):
        pool = pooler.get_pool(cr.dbname)
        dep_obj=pool.get('ir.module.module.dependency')
        if level<1:
            raise wizard.except_wizard(_('Error'), _('Recursion error in modules dependencies !'))
        for module in pool.get('ir.module.module').browse(cr, uid, ids):
            dep_ids = dep_obj.search(cr, uid, [('module_id', '=', module.id)])
            if dep_ids:
                ids2 = []
                for dep in dep_obj.browse(cr, uid, dep_ids):
                    dep_name=pool.get('ir.module.module').search(cr, uid, [('name','=',dep.name)])
                    ids2.append(dep_name[0])
                self.rec_depend(cr, uid, ids2, data, context, level-1)
            if module.name not in data['form']['dependencies']:
                data['form']['dependencies'].append(module.name)
        return True

    def _compute_dependencies(self, cr, uid, data, context):
        data['form']['dependencies']=[]
        self.rec_depend(cr,uid,data['form']['modules_list'][0][2],data,context)
        self.dependencies=data['form']['dependencies']
        pool = pooler.get_pool(cr.dbname)
        return {}

    def _create_module(self, cr, uid, data, context):
        self.dict_init={}
        self.init_xml=[]
        self.demo_xml=[]
        self.update_xml=[]
        self.archname = StringIO.StringIO('wb')
        self.archive = zipfile.ZipFile(self.archname, "w", ZIP_DEFLATED)
        for module in self.dependencies:
            ad = tools.config['addons_path']
            url = os.path.join(ad, module)
            if not os.path.isdir(url):
                url=url+'.zip'
            self._zippy(self.archive, url, '', src=True)
        dname = data['form']['directory_name']
        data['form']['depen']=[]

        data['form']['init_xml']=reduce(lambda l, x: x not in l and l.append(x) or l, self.init_xml, [])
        data['form']['demo_xml']=reduce(lambda l, x: x not in l and l.append(x) or l, self.demo_xml, [])
        data['form']['update_xml']=reduce(lambda l, x: x not in l and l.append(x) or l, self.update_xml, [])
        _terp = """{
            "name" : "%(name)s",
            "version" : "%(version)s",
            "author" : "%(author)s",
            "website" : "%(website)s",
            "category" : "%(category)s",
            "description":\"\"\"%(description)s\"\"\",
            "depends" : %(depen)s,
            "init_xml" : %(init_xml)s,
            "demo_xml" : %(demo_xml)s,
            "update_xml" : %(update_xml)s,
            "active": True,
            "installable": True
    } """ % data['form']
        for name,datastr in self.dict_init.items():
            self.dict_init[name]=reduce(lambda l, x: x not in l and l.append(x) or l, self.dict_init[name], [])
            init_data='\n'.join(self.dict_init[name])
            self._zip_writestr(name, init_data)
        self._zip_writestr('__terp__.py', _terp)
        self.archive.close()
        return {
            'module_file': base64.encodestring(self.archname.getvalue()),
            'module_filename': data['form']['directory_name']+'-'+data['form']['version']+'.zip'
        }

    states = {
        'init': {
            'actions': [],
            'result': {
                'type':'form',
                'arch':info_start_form,
                'fields': info_start_fields,
                'state':[
                    ('end', 'Cancel', 'gtk-cancel'),
                    ('info', 'Continue', 'gtk-ok'),
                ]
            }
        },
        'info': {
            'actions': [_compute_dependencies],
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
        }
    }
base_module_merge('base_module_merge.module_merge')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

