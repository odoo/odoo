# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: account.py 1005 2005-07-25 08:41:42Z nicoe $
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
import time
import pooler

form='''<?xml version="1.0"?>
<form string="Report Options">
    <field name="date_from" colspan="2" />
    <field name="holiday_type" colspan="2" />
    <field name="depts" colspan="4" />

</form>'''

zero_form='''<?xml version="1.0"?>
<form string="Notification">
<label string="You have to select at least 1 Department. Try again." colspan="4"/>
</form>'''

zero_fields={
}

class wizard_report(wizard.interface):
    def _check(self, cr, uid, data, context):
        data['form']['date_from']=time.strftime('%Y-%m-%d')
        data['form']['holiday_type']='Validated'

        return data['form']

    def _checkdepts(self, cr, uid, data, context):

        if len(data['form']['depts'][0][2])==0:
            return 'notify'
        else:
            return 'report'

    fields={
        'date_from':{
                'string':'From',
                'type':'date',
                'required':True,
        },
        'depts': {
                'string': 'Department(s)', 
                'type': 'many2many', 
                'relation': 'hr.department'
        },
        'holiday_type':{
                'string':"Select Holiday Type",
                'required':True,
                'type':'selection',
                'selection':[('Validated','Validated'),('Confirmed','Confirmed'),('both','Both Validated and Confirmed')]
        },
    }

    states={
        'init':{
            'actions':[_check],
            'result':{'type':'form', 'arch':form, 'fields':fields, 'state':[('end', 'Cancel'), ('checkdept', 'Print')]}
        },
        'checkdept': {
            'actions': [],
            'result': {'type':'choice','next_state':_checkdepts}
        },
        'notify': {
            'actions': [],
            'result': {'type':'form','arch':zero_form,'fields':zero_fields,'state':[('end','Ok')]}
        },
        'report':{
            'actions':[],
            'result':{'type':'print', 'report':'holidays.summary', 'state':'end'}
        }
    }
wizard_report('hr.holidays.summary')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

