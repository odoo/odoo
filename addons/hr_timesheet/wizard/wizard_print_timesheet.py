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

import datetime

import wizard
import netsvc

dates_form = '''<?xml version="1.0"?>
<form string="Choose your month">
    <field name="month" />
    <field name="year" />
    <field name="user_id" colspan="3" />
</form>'''


dates_form_ro = '''<?xml version="1.0"?>
<form string="Choose your month">
    <field name="month" />
    <field name="year" />
    <field name="user_id" colspan="3" readonly="1"/>
</form>'''

dates_fields = {
    'month': dict(string=u'Month', type='selection', required=True, selection=[(x, datetime.date(2000, x, 1).strftime('%B')) for x in range(1, 13)]),
    'year': dict(string=u'Year', type=u'integer', required=True),
    'user_id' : dict(string=u'User', type='many2one', relation='res.users', required=True),
}

def _get_value(self, cr, uid, data, context):
    today = datetime.date.today()
    return dict(month=today.month, year=today.year, user_id=uid)

class wizard_report(wizard.interface):
    states = {
        'init': {
            'actions': [_get_value], 
            'result': {'type':'form', 'arch':dates_form, 'fields':dates_fields, 'state':[ ('end','Cancel','gtk-cancel'),('report','Print','gtk-print')]}
        },
        'report': {
            'actions': [],
            'result': {'type':'print', 'report':'hr.analytical.timesheet', 'state':'end'}
        }
    }
wizard_report('hr.analytical.timesheet')

class wizard_report_my(wizard.interface):
    states = {
        'init': {
            'actions': [_get_value], 
            'result': {'type':'form', 'arch':dates_form_ro, 'fields':dates_fields, 'state':[ ('end','Cancel','gtk-cancel'),('report','Print','gtk-print')]}
        },
        'report': {
            'actions': [],
            'result': {'type':'print', 'report':'hr.analytical.timesheet', 'state':'end'}
        }
    }
wizard_report_my('hr.analytical.timesheet.my')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

