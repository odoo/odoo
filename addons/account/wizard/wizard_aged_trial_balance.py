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
import datetime
import pooler

from mx.DateTime import *
from tools.translate import _

_aged_trial_form = """<?xml version="1.0"?>
<form string="Aged Trial Balance">
    <field name="company_id"/>
    <newline/>
    <field name="date1"/>
    <field name="period_length"/>
    <newline/>    
    <field name="result_selection"/>
    <newline/>
    <field name="direction_selection"/>
</form>"""

_aged_trial_fields = {
    'company_id': {'string': 'Company', 'type': 'many2one', 'relation': 'res.company', 'required': True},
    'period_length': {'string': 'Period length (days)', 'type': 'integer', 'required': True, 'default': lambda *a:30},
    'date1': {'string':'Start of period', 'type':'date', 'required':True, 'default': lambda *a: time.strftime('%Y-%m-%d')},
    'result_selection':{
        'string':"Filter on Partners",
        'type':'selection',
        'selection':[('customer','Receivable'),('supplier','Payable'),('all','Receivable and Payable')],
        'required':True,
        'default': lambda *a: 'all',
    },
    'direction_selection':{
        'string':"Analysis Direction",
        'type':'selection',
        'selection':[('past','Past'),('future','Future')],
        'required':True,
        'default': lambda *a: 'past',
    },
}

def _calc_dates(self, cr, uid, data, context):
    res = {}
    period_length = data['form']['period_length']
    if period_length<=0:
        raise wizard.except_wizard(_('UserError'), _('You must enter a period length that cannot be 0 or below !'))
    start = datetime.date.fromtimestamp(time.mktime(time.strptime(data['form']['date1'],"%Y-%m-%d")))
    start = DateTime(int(start.year),int(start.month),int(start.day))
    if data['form']['direction_selection'] == 'past':
        for i in range(5)[::-1]:
            stop = start - RelativeDateTime(days=period_length)
            res[str(i)] = {
                'name' : str((5-(i+1))*period_length) + '-' + str((5-i)*period_length),
                
                'stop': start.strftime('%Y-%m-%d'),
                'start' : stop.strftime('%Y-%m-%d'),
                }
            start = stop - RelativeDateTime(days=1)
    else:
        for i in range(5):
            stop = start + RelativeDateTime(days=period_length)
            res[str(5-(i+1))] = {
                'name' : str((i)*period_length)+'-'+str((i+1)*period_length),
                'start': start.strftime('%Y-%m-%d'),
                'stop' : stop.strftime('%Y-%m-%d'),
                }
            start = stop + RelativeDateTime(days=1)
    return res

class wizard_report(wizard.interface):
    def _get_defaults(self, cr, uid, data, context):
        fiscalyear_obj = pooler.get_pool(cr.dbname).get('account.fiscalyear')
        data['form']['fiscalyear'] = fiscalyear_obj.find(cr, uid)
        user = pooler.get_pool(cr.dbname).get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            company_id = user.company_id.id
        else:
            company_id = pooler.get_pool(cr.dbname).get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]
        data['form']['company_id'] = company_id
        return data['form']
    states = {
        'init': {
            'actions': [_get_defaults],
            'result': {'type':'form', 'arch':_aged_trial_form, 'fields':_aged_trial_fields, 'state':[('end','Cancel'),('print','Print Aged Trial Balance')]},
        },
        'print': {
            'actions': [_calc_dates],
            'result': {'type':'print', 'report':'account.aged_trial_balance', 'state':'end'},
        },
    }
wizard_report('account.aged.trial.balance')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
