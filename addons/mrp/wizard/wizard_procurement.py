##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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
from schedulers import _procure_confirm
import threading

parameter_form = '''<?xml version="1.0"?>
<form string="Parameters" colspan="4">
	<separator string="Time (days)" colspan="4"/>
	<field name="po_lead"/>
	<field name="picking_lead"/>
	<field name="schedule_cycle"/>
	<field name="po_cycle"/>
	<field name="security_lead"/>
	<separator string="Control" colspan="4"/>
	<field name="user_id"/>
</form>'''

parameter_fields = {
	'schedule_cycle': {'string':'Scheduler Cycle', 'type':'float', 'required':True, 'default': lambda *a: 1.0},
	'po_cycle': {'string':'PO Cycle', 'type':'float', 'required':True, 'default': lambda *a: 1.0},
	'po_lead': {'string':'PO Lead Time', 'type':'float', 'required':True, 'default': lambda *a: 1.0},
	'security_lead': {'string':'Security Days', 'type':'float', 'required':True, 'default': lambda *a: 5.0},
	'picking_lead': {'string':'Picking Lead Time', 'type':'float', 'required':True, 'default': lambda *a: 1.0},
	'user_id': {'string':'Send Result To', 'type':'many2one', 'relation':'res.users', 'default': lambda uid,data,state: uid},
}

def _procure_calculation(self, cr, uid, data, context):
	#CHECKME: I wonder if it would be a good idea to pass the cursor...
	# in doubt, I didn't
	threaded_calculation = threading.Thread(target=_procure_confirm, args=(self, cr.dbname, uid, data, context))
	threaded_calculation.start()
	return {}

class procurement_compute(wizard.interface):
	states = {
		'init': {
			'actions': [],
			'result': {'type': 'form', 'arch':parameter_form, 'fields': parameter_fields, 'state':[('end','Cancel'),('compute','Compute Procurements') ]}
		},
		'compute': {
			'actions': [_procure_calculation],
			'result': {'type': 'state', 'state':'end'}
		},
	}
procurement_compute('mrp.procurement.compute')

