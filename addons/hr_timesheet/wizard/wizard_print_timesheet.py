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

