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

import netsvc
import wizard
import pooler
import os

import base64
import tempfile
import tarfile



choose_file_form = '''<?xml version="1.0"?>
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
            'description': self._handle_text(module.description or 'None'),
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
        dico = self.dico
        title = "Module %s (*%s*)" % (dico['shortdesc'], dico['name'])
        title_underline = "=" * len(title)
        dico['title'] = title
        dico['title_underline'] = title_underline
        sl = [
            "",
            "%(title)s",
            "%(title_underline)s",
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
        return '\n'.join(sl) % (dico)

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
        def write_field(field_def):
            field_name = field_def[0]
            field_dict = field_def[1]
            field_required = field_dict.get('required', '') and ', required'
            field_readonly = field_dict.get('readonly', '') and ', readonly'

            field_help_s = field_dict.get('help', '').strip()
            if field_help_s:
                field_help_s = "*%s*" % (field_help_s)
                field_help = '\n'.join(['    %s' % line.strip() for line in field_help_s.split('\n')])
            else:
                field_help = ''

            s = ""
            s += ":%s: " % (field_name)
            s += field_dict.get('string', 'Unknown')
            s += ", " + field_dict['type']
            s += field_required
            s += field_readonly
            s += "\n\n%s" % (field_help)
            return s

        sl = ["",
              "",
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
        module_ids = data['ids']

        module_index = []

        # create a temporary gzipped tarfile:
        tgz_tmp_filename = tempfile.mktemp('_rst_module_doc.tgz')
        try:
            tarf = tarfile.open(tgz_tmp_filename, 'w:gz')

            modules = module_model.browse(cr, uid, module_ids)
            for module in modules:
                index_dict = {
                    'name': module.name,
                    'shortdesc': module.shortdesc,
                }
                module_index.append(index_dict )

                objects = self._get_objects(cr, uid, module)
                rstdoc = RstDoc(module, objects)
                out = rstdoc.write()

                try:
                    tmp_file = tempfile.NamedTemporaryFile()
                    tmp_file.write(out.encode('utf8'))
                    tmp_file.file.flush() # write content to file
                    tarf.add(tmp_file.name, arcname=module.name + '.rst')
                finally:
                    tmp_file.close()

            # write index file:
            tmp_file = tempfile.NamedTemporaryFile()
            out = self._create_index(module_index)
            tmp_file.write(out.encode('utf8'))
            tmp_file.file.flush()
            tarf.add(tmp_file.name, arcname='index.rst')

        finally:
            tarf.close()

        try:
            os.unlink(tmp_file)
        except Exception, e:
            logger = netsvc.Logger()
            logger.notifyChannel("warning", netsvc.LOG_WARNING,
                "Temporary file %s could not be deleted. (%s)" % (tmp_file.name, e))

        f = open(tgz_tmp_filename, 'rb')
        out = f.read()
        f.close()

        return {
            'rst_file': base64.encodestring(out),
            'name': 'modules_technical_guide_rst.tgz'
        }

    def _create_index(self, module_index):
        sl = ["",
              ".. _module-technical-guide-link:",
              "",
              "Module Technical Guide: Introspection report on objects",
              "=======================================================",
              "",
              ".. toctree::",
              "    :maxdepth: 1",
              "",
              ]
        for mod in module_index:
            sl.append("    %s" % mod['name'])
        sl.append("")
        return '\n'.join(sl)

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
        ids2 = pool.get('ir.model.data').search(cr, uid, [('module', '=', module.name), ('model', '=', 'ir.model')])
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

##     def _object_doc(self, cr, uid, obj):
##         pool = pooler.get_pool(cr.dbname)
##         modobj = pool.get(obj)
##         return modobj.__doc__

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

