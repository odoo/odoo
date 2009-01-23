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
import os
import tools

import zipfile
from StringIO import StringIO
import base64

choose_file_form ='''<?xml version="1.0"?>
<form string="Create Technical Guide in rst format">
    <separator string="Technical Guide in rst format" colspan="4"/>
    <label string="Please choose a file where the Technical Guide will be written." colspan="4"/>
    <field name="rst_file" />
    <field name="name" invisible="1"/>
</form>
'''

choose_file_fields = {
    'rst_file': {'string': 'file', 'type': 'binary', 'required': True, 'readonly': True},
    'name': {'string': 'filename', 'type': 'char', 'required': True, 'readonly': True},
}


class RstDoc(object):
    def __init__(self, module, objects):
        self.dico = {
            'name': module.name,
            'shortdesc': module.shortdesc,
            'latest_version': module.latest_version,
            'website': module.website,
            'description': self._handle_text(module.description),
            'report_list': self._handle_list_items(module.reports_by_module),
            'menu_list': self._handle_list_items(module.menus_by_module),
            'view_list': self._handle_list_items(module.views_by_module),
            'depends': module.dependencies_id,
        }
        self.objects = objects

    def _handle_list_items(self, list_item_as_string):
        return [item.replace('*', '\*') for item in list_item_as_string.split('\n')]

    def _handle_text(self, txt):
        lst = ['  %s' % line for line in txt.split('\n')]
        return '\n'.join(lst)

    def _write_header(self):
        sl = [
            "",
            "Introspection report on objects",
            "===============================",
            "",
            ":Module: %(name)s",
            ":Name: %(shortdesc)s",
            ":Version: %(latest_version)s",
            ":Directory: %(name)s",
            ":Web: %(website)s",
            "",
            "Description",
            "-----------",
            "",
            "::",
            "  ",
            "  %(description)s",
            ""]
        return '\n'.join(sl) % (self.dico)

    def _write_reports(self):
        sl = ["",
              "Reports",
              "-------"]
        for report in self.dico['report_list']:
            if report:
                sl.append("")
                sl.append(" * %s" % report)
        sl.append("")
        return '\n'.join(sl)

    def _write_menus(self):
        sl = ["",
              "Menus",
              "-------"]
        for menu in self.dico['menu_list']:
            if menu:
                sl.append("")
                sl.append(" * %s" % menu)

        sl.append("")
        return '\n'.join(sl)

    def _write_views(self):
        sl = ["",
              "Views",
              "-----"]
        for view in self.dico['view_list']:
            if view:
                sl.append("")
                sl.append(" * %s" % view)
        sl.append("")
        return '\n'.join(sl)

    def _write_depends(self):
        sl = ["",
              "Dependencies",
              "------------"]
        for dependency in self.dico['depends']:
            sl.append("")
            sl.append(" * %s - %s" % (dependency.name, dependency.state))
        return '\n'.join(sl)

    def _write_objects(self):
        # {'fields': [('name', {'translate': True, 'required': True, 'type': 'char', 'string': 'Name', 'size': 64})], 'object': browse_record(ir.model, 87)}
        def write_field(field_def):
            field_name = field[0]
            field_dict = field[1]
            field_required = field_dict.get('required', '') and ', required'
            field_readonly = field_dict.get('readonly', '') and ', readonly'
            s = ""
            s += ":%s: " % (field_name)
            s += field_dict.get('string', 'Unknown')
            s += ", " + field_dict['type']
            s += field_required
            s += field_readonly
            s += " " + field_dict.get('help', '')
            return s

        sl = ["",
              "Objects",
              "-------"]
        for obj in self.objects:
            title = obj['object'].name
            sl.append("")
            sl.append(title)
            sl.append('#' * len(title))
            sl.append("")

            for field in obj['fields']:
                sl.append("")
                sl.append(write_field(field))
                sl.append("")

        return '\n'.join(sl)

    def write(self):
        s = ''
        s += self._write_header()
        s += self._write_reports()
        s += self._write_menus()
        s += self._write_views()
        s += self._write_depends()
        s += self._write_objects()

        return s


class wizard_tech_guide_rst(wizard.interface):

    def _generate(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        module_model = pool.get('ir.module.module')
        module = module_model.browse(cr, uid, data['id'])

        objects = self._get_objects(cr, uid, module)
        rstdoc = RstDoc(module, objects)
        out = rstdoc.write()

        return {
            'rst_file': base64.encodestring(out),
            'name': '%s_technical_guide.rst' % module.name.replace('.', '_')
        }

##     def _object_doc(self, cr, uid, obj):
##         pool = pooler.get_pool(cr.dbname)
##         modobj = pool.get(obj)
##         return modobj.__doc__

    def _get_objects(self, cr, uid, module):
        res = []
        objects = self._object_find(cr, uid, module)
        for obj in objects:
            dico = {
                'object': obj,
                'fields': self._fields_find(cr, uid, obj.model)
            }
            res.append(dico)
        return res

    def _object_find(self, cr, uid, module):
        pool = pooler.get_pool(cr.dbname)
        ids2 = pool.get('ir.model.data').search(cr, uid, [('module','=',module.name), ('model','=','ir.model')])
        ids = []
        for mod in pool.get('ir.model.data').browse(cr, uid, ids2):
            ids.append(mod.res_id)
        modobj = pool.get('ir.model')
        return modobj.browse(cr, uid, ids)

    def _fields_find(self, cr, uid, obj):
        pool = pooler.get_pool(cr.dbname)
        modobj = pool.get(obj)
        res = modobj.fields_get(cr, uid).items()
        return res

    states = {
        'init': {
            'actions': [_generate],
            'result': {
                'type': 'form',
                'arch': choose_file_form,
                'fields': choose_file_fields,
                'state': [
                    ('end', 'Close', 'gtk-close'),
                ]
            }
        },
    }

wizard_tech_guide_rst('tech.guide.rst')

