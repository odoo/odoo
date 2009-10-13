# -*- coding: utf-8 -*-
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

_date_form = '''<?xml version="1.0"?>
<form string="Select a month">
    <separator string="Select a month" colspan="4"/>
    <field name="month"/>
    <field name="year"/>
</form>'''

_date_fields = {
    'month' : {
               'string' : 'Month',
               'type' : 'selection',
               'selection' : [(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'), (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')],
               'required':True,
               'default' : lambda * a: time.gmtime()[1]
               },
    'year' : {
              'string' : 'Year',
              'type' : 'integer',
              'required':True,
              'default' : lambda * a: time.gmtime()[0]
              },
}

class wiz_bymonth(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':_date_form, 'fields':_date_fields, 'state':[('print', 'Print Timesheet'), ('end', 'Cancel')]}
        },
        'print': {
            'actions': [],
            'result': {'type': 'print', 'report': 'hr.attendance.bymonth', 'state': 'end'}
        }
    }
wiz_bymonth('hr.attendance.print_month')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

