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
import time

_date_form = '''<?xml version="1.0"?>
<form string="Select a time span">
    <separator string="Select a starting and a end date" colspan="4"/>
    <field name="init_date"/>
    <newline/>
    <field name="end_date"/>
</form>'''

_date_fields = {
    'init_date': {'string':'Starting Date', 'type':'date', 'default':lambda *a: time.strftime('%Y-%m-%d'), 'required':True},
    'end_date': {'string':'Ending Date', 'type':'date', 'default':lambda *a: time.strftime('%Y-%m-%d'), 'required':True}
}

class wiz_byweek(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':_date_form, 'fields':_date_fields, 'state':[('print','Print Timesheet'),('end','Cancel') ]}
        },
        'print': {
            'actions': [],
            'result': {'type': 'print', 'report': 'hr.attendance.allweeks', 'state':'end'}
        }
    }
wiz_byweek('hr.attendance.print_week')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

