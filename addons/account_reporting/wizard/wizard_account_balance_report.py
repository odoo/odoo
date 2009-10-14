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
import ir
import pooler
import time
import netsvc
from osv import fields, osv
import mx.DateTime
from mx.DateTime import RelativeDateTime

from tools import config


dates_form = '''<?xml version="1.0"?>
<form string="Customize Report">
    <field name="fiscalyear" colspan="4"/>
    <field name="periods" colspan="4"/>
</form>'''

#   <field name="report_type" colspan="4"/>


dates_fields = {
    'fiscalyear': {'string': 'Fiscal year', 'type': 'many2one', 'relation': 'account.fiscalyear', 'required': True},
    'periods': {'string': 'Periods', 'type': 'many2many', 'relation': 'account.period', 'help': 'All periods if empty'},
#   'report_type': {'string': 'Report Type','type': 'selection','selection': [('only_obj', 'Report Objects Only'),('with_account', 'Report Objects With Accounts'),('acc_with_child', 'Report Objects With Accounts and child of Accounts'),],'required': True},
}

back_form='''<?xml version="1.0"?>
<form string="Notification">
<separator string="You might have done following mistakes.Please correct them and try again." colspan="4"/>
<separator string="1. You have selected more than 3 years in any case." colspan="4"/>
<separator string="2. You have not selected 'Percentage' option,but you have selected more than 2 years." colspan="4"/>
<label string="You can select maximum 3 years.Please check again." colspan="4"/>
</form>'''

back_fields={
}

zero_form='''<?xml version="1.0"?>
<form string="Notification">
<label string="You have to select at least 1 Fiscal Year. Try again."/>
</form>'''

zero_fields={
}

periods_form='''<?xml version="1.0"?>
<form string="Set Periods">
<separator string="Select Period(s) (All periods if empty)" colspan="4"/>
            <field name="periods" colspan="4" nolabel="1"/>
</form>'''

periods_fields={
    'periods': {'string': 'Periods', 'type': 'many2many', 'relation': 'account.period', 'help': 'All periods if empty'}
}

class wizard_report(wizard.interface):
    def _get_defaults(self, cr, uid, data, context):
        fiscalyear_obj = pooler.get_pool(cr.dbname).get('account.fiscalyear')
        data['form']['fiscalyear'] = fiscalyear_obj.find(cr, uid)
        data['form']['report_type'] = 'only_obj'
        return data['form']

    states = {
        'init': {
            'actions': [_get_defaults],
            'result': {'type':'form', 'arch':dates_form, 'fields':dates_fields, 'state':[('end','Cancel'),('report','Print BalanceSheet')]}
        },
        'report': {
            'actions': [],
            'result': {'type':'print', 'report':'account.report.bs', 'state':'end'}
        }
    }
wizard_report('account.account.balancesheet.report')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

