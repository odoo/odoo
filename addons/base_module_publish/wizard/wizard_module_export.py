# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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


import wizard
import pooler

import module_zip

init_form = '''<?xml version="1.0"?>
<form string="Export module">
    <separator string="Export module" colspan="4"/>
    <field name="include_src"/>
</form>'''

init_fields = {
        'include_src': {'string': 'Include sources', 'type': 'boolean',
            'default': lambda *a: True,},
}

finish_form = '''<?xml version="1.0"?>
<form string="Finish">
    <separator string="Module successfully exported !" colspan="4"/>
    <field name="module_file" filename='module_filename'/>
    <newline/>
    <field name="module_filename"/>
</form>'''

finish_fields = {
    'module_file': {'string': 'Module .zip file', 'type':'binary', 'readonly':True},
    'module_filename': {'string': 'Filename', 'type':'char', 'size': 64, 'readonly':True},
}

class move_module_wizard(wizard.interface):
    def createzip(self, cr, uid, data, context):
       return module_zip.createzip(cr, uid, data['id'], context, src=data['form']['include_src'])

    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch': init_form,
                'fields': init_fields, 'state': [('end', 'Cancel'), ('zip', 'Ok')]},
        },
        'zip': {
            'actions': [createzip],
            'result': {'type': 'form', 'arch': finish_form,
                'fields': finish_fields, 'state': [('end', 'Close')]},
        }
    }
move_module_wizard('base_module_publish.module_export')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

