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

import wizard
import base64
import pooler


class cal_event_export_wizard(wizard.interface):
    form1 = '''<?xml version="1.0"?>
    <form string="Export ICS">
        <field name="name"/>
        <field name="file_path" colspan="4" width="300"/>
    </form>'''

    form1_fields = {
            'file_path': {
                'string': 'Save ICS file',
                'type': 'binary',
                'required': True,
                'filters': '*.ics'
                },
            'name': {
                    'string': 'File name',
                    'type': 'char',
                    'size': 34,
                    'required': True,
                    'help': 'Save in .ics format'},
            }

    def _process_export_ics(self, cr, uid, data, context):
        model = data.get('model')
        model_obj = pooler.get_pool(cr.dbname).get(model)
        calendar = model_obj.export_cal(cr, uid, data['ids'], context)
        return {'file_path': base64.encodestring(calendar), \
                            'name': 'OpenERP %s.ics' % (model_obj._description)}

    states = {
        'init': {
            'actions': [_process_export_ics],
            'result': {'type': 'form', 'arch':form1, 'fields':form1_fields, \
                       'state': [('end', '_Cancel', 'gtk-cancel')]}},
    }

cal_event_export_wizard('calendar.event.export')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
