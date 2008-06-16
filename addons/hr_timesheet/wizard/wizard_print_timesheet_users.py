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
import datetime

form='''<?xml version="1.0"?>
<form string="Choose Users">
	<field name="month"/>
	<field name="year"/>
	<field name="user_ids" colspan="3"/>
</form>'''

fields = {
	'month': dict(string=u'Month', type='selection', required=True, selection=[(x, datetime.date(2000, x, 1).strftime('%B')) for x in range(1, 13)]), 
	'year': dict(string=u'Year', type='integer', required=True),
	'user_ids': dict(string=u'Users', type='many2many', relation='res.users', required=True),
}

def _get_value(self, cr, uid, data, context):
	today=datetime.date.today()
	return dict(month=today.month, year=today.year)

class wizard_report(wizard.interface):
	states={
		'init':{
			'actions':[_get_value],
			'result':{'type':'form', 'arch':form, 'fields':fields, 'state':[('end','Cancel','gtk-cancel'),('report','Print','gtk-print')]}
		},
		'report':{
			'actions':[],
			'result':{'type':'print', 'report':'hr.analytical.timesheet_users', 'state':'end'}
		}
	}
wizard_report('hr.analytical.timesheet_users')
