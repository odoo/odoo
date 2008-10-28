# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import wizard
import time

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

class wiz_attendance(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':_date_form, 'fields':_date_fields, 'state':[('print','Print Attendance Report'),('end','Cancel') ]}
        },
        'print': {
            'actions': [],
            'result': {'type': 'print', 'report': 'hr.timesheet.attendance.error', 'state':'end'}
        }
    }
wiz_attendance('hr.timesheet.attendance.report')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

