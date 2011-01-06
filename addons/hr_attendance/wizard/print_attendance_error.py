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
import time
import pooler
from tools.translate import _

_date_form = '''<?xml version="1.0"?>
<form string="Select a time span">
    <separator string="Analysis Information" colspan="4"/>
    <field name="init_date"/>
    <field name="end_date"/>
    <field name="max_delay"/>
    <label string="Bellow this delay, the error is considered to be voluntary" colspan="2"/>
</form>'''

_date_fields = {
    'init_date': {'string':'Starting Date', 'type':'date', 'default':lambda *a: time.strftime('%Y-%m-%d'), 'required':True},
    'end_date': {'string':'Ending Date', 'type':'date', 'default':lambda *a: time.strftime('%Y-%m-%d'), 'required':True},
    'max_delay': {'string':'Max. Delay (Min)', 'type':'integer', 'default':lambda *a: 120, 'required':True},
}

def _check_data(self, cr, uid, data, *args):
    date_from = data['form']['init_date']
    date_to = data['form']['end_date']
    cr.execute("SELECT id FROM hr_attendance "\
               "WHERE employee_id IN %s "\
               "AND to_char(name,'YYYY-mm-dd')<=%s "\
               "and to_char(name,'YYYY-mm-dd')>=%s "\
               "and action in (%s, %s) order by name",
               (tuple(data['ids']), date_to, date_from, 'sign_in', 'sign_out'))
    attendance_ids = [x[0] for x in cr.fetchall()]
    if not attendance_ids:
        raise wizard.except_wizard(_('No Data Available'), _('No records found for your selection!'))    
    
    attendance_records = pooler.get_pool(cr.dbname).get('hr.attendance').browse(cr,uid,attendance_ids)
    emp_ids = []
    for rec in attendance_records:
        if rec.employee_id.id not in emp_ids:
            emp_ids.append(rec.employee_id.id)
    
    data['form']['emp_ids'] = emp_ids
    
    return data['form']


class wiz_attendance(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':_date_form, 'fields':_date_fields, 'state':[('print','Print Attendance Report'),('end','Cancel') ]}
        },
        'print': {
            'actions': [_check_data],
            'result': {'type': 'print', 'report': 'hr.attendance.error', 'state':'end'}
        }
    }
wiz_attendance('hr.attendance.report')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

