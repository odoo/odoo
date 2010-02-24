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

from tools.translate import _
import base64
import pooler
import urllib
import wizard

class cal_event_subscribe_wizard(wizard.interface):
    form1 = '''<?xml version="1.0"?>
    <form string="Subscribe to Remote Calendar">
        <separator string="Provide path for Remote Calendar"/>
        <field name="url_path" colspan="4" width="300" nolabel="1" widget="url"/>
    </form>'''

    form1_fields = {
            'url_path': {
                'string': 'Provide path for remote calendar',
                'type': 'char',
                'required': True,
                'size': 124
                }
            }
    display = '''<?xml version="1.0"?>
    <form string="Message...">
        <field name="msg" colspan="4" width="300" nolabel="1"/>
    </form>'''

    display_fields = {
            'msg': {
                'string': '',
                'type': 'text',
                'readonly': True,
                }
            }

    def _process_imp_ics(self, cr, uid, data, context=None):
        global cnt
        cnt = 0
        try:
            f = urllib.urlopen(data['form']['url_path'])
            caldata = f.fp.read()
            f.close()
        except Exception, e:
            raise wizard.except_wizard(_('Error!'), _('Please provide Proper URL !'))
        model = data.get('model')
        model_obj = pooler.get_pool(cr.dbname).get(model)
        context.update({'url': data['form']['url_path'],
                                    'model': data.get('model')})
        vals = model_obj.import_cal(cr, uid, base64.encodestring(caldata), \
                                            data['id'], context)
        if vals:
            cnt = vals['count']
        return {}

    def _result_set(self, cr, uid, data, context=None):
        return {'msg': 'Import Sucessful.'}

    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch': form1, 'fields': form1_fields, \
                       'state': [('end', '_Cancel', 'gtk-cancel'), ('open', '_Subscribe', 'gtk-ok')]}
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

cal_event_subscribe_wizard('calendar.event.subscribe')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
