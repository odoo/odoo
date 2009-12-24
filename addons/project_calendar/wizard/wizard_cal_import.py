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

class project_cal_imp_wizard(wizard.interface):
    form1 = '''<?xml version="1.0"?>
    <form string="Import ICS">
        <separator string="Select ICS file"/>
        <field name="file_path" colspan="4" width="300" nolabel="1"/>
    </form>'''
    
    form1_fields = {
            'file_path': {
                'string': 'Select ICS file', 
                'type': 'binary', 
                'required': True, 
                'filters': '*.ics'
                }
            }
    display = '''<?xml version="1.0"?>
    <form string="Import Message">
        <field name="msg" colspan="4" width="300" nolabel="1"/>
    </form>'''
    
    display_fields = {
            'msg': {
                'string': '', 
                'type': 'text', 
                'readonly': True, 
                'default': 'Imported %s Tasks'
                }
            }

    def _process_imp_ics(self, cr, uid, data, context=None):
        task_obj = pooler.get_pool(cr.dbname).get('project.task')
        vals = task_obj.import_cal(cr, uid, data['ids'], data, context)
        global cnt
        cnt = 0
        if vals:
            cnt = vals['count']
        return {}
    
    def _result_set(self, cr, uid, data, context=None):
        return {'msg': 'Imported %s Task(s)' % cnt}
    
    states = {
        'init': {
            'actions': [], 
            'result': {'type': 'form', 'arch': form1, 'fields': form1_fields, \
                       'state': [('end', '_Cancel', 'gtk-cancel'), ('open', '_Import', 'gtk-ok')]}
        }, 
        'open': {
            'actions': [], 
            'result': {'type': 'action', 'action': _process_imp_ics, 'state': 'display'}
        },
       'display': {
            'actions': [_result_set], 
            'result': {'type': 'form', 'arch': display, 'fields': display_fields, \
                       'state': [('end', 'Ok', 'gtk-ok')]}
        }, 
    }
    
project_cal_imp_wizard('caldav.project.import')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: