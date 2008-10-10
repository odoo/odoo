# -*- encoding: utf-8 -*-
##############################################################################
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
import pooler
import locale
import time

report_type =  '''<?xml version="1.0"?>
<form string="Select Report Type">
</form>'''

dates_form = '''<?xml version="1.0"?>
<form string="Select period ">
    <field name="date_from" colspan="4"/>
    <field name="date_to" colspan="4"/>
    <field name="sortbydate" colspan="4"/>
    <field name="display_account" colspan="4"/>
    <field name="landscape" colspan="4"/>
    <field name="soldeinit"/>
    <field name="amount_currency" colspan="4"/>
</form>'''

dates_fields = {
    'date_from': {'string':"Start date",'type':'date','required':True ,'default': lambda *a: time.strftime('%Y-01-01')},
    'date_to': {'string':"End date",'type':'date','required':True, 'default': lambda *a: time.strftime('%Y-%m-%d')},
    'sortbydate':{'string':"Sort by",'type':'selection','selection':[('sort_date','Date'),('sort_mvt','Mouvement')]},
    'display_account':{'string':"Display accounts ",'type':'selection','selection':[('bal_mouvement','With movements'),('bal_all','All'),('bal_solde','With balance is not equal to 0')]},
    'landscape':{'string':"Print in Landscape Mode",'type':'boolean'},
    'soldeinit':{'string':"Inclure les soldes initiaux",'type':'boolean'},
    'amount_currency':{'string':"with amount in currency",'type':'boolean'}

}

account_form = '''<?xml version="1.0"?>
<form string="Select parent account">
    <field name="Account_list" colspan="4"/>
</form>'''

account_fields = {
    'Account_list': {'string':'Account', 'type':'many2one', 'relation':'account.account', 'required':True ,'domain':[('parent_id','=',False)]},
}




period_form = '''<?xml version="1.0"?>
<form string="Select period ">
    <field name="fiscalyear" colspan="4"/>
    <field name="periods" colspan="4"/>
    <field name="sortbydate" colspan="4"/>
    <field name="display_account" colspan="4"/>
    <field name="landscape" colspan="4"/>
    <field name="soldeinit"/>
    <field name="amount_currency" colspan="4"/>
</form>'''

period_fields = {
    'fiscalyear': {'string': 'Fiscal year', 'type': 'many2one', 'relation': 'account.fiscalyear',
        'help': 'Keep empty for all open fiscal year'},
    'periods': {'string': 'Periods', 'type': 'many2many', 'relation': 'account.period', 'help': 'All periods if empty'},
    'sortbydate':{'string':"Sort by:",'type':'selection','selection':[('sort_date','Date'),('sort_mvt','Mouvement')]},
    'display_account':{'string':"Display accounts ",'type':'selection','selection':[('bal_mouvement','With movements'),('bal_all','All'),('bal_solde','With balance is not equal to 0')]},
    'landscape':{'string':"Print in Landscape Mode",'type':'boolean'},
    'soldeinit':{'string':"Inclure les soldes initiaux",'type':'boolean'},
    'amount_currency':{'string':"with amount in currency",'type':'boolean'}
}
def _check_path(self, cr, uid, data, context):
    if data['model'] == 'account.account':
        return 'checktype'
    else:
        return 'account_selection'

def _check(self, cr, uid, data, context):
    if data['form']['landscape']==True:
        return 'report_landscape'
    else:
        return 'report'

def _check_date(self, cr, uid, data, context):
    sql = """
        SELECT f.id, f.date_start, f.date_stop FROM account_fiscalyear f  Where '%s' between f.date_start and f.date_stop """%(data['form']['date_from'])
    cr.execute(sql)
    res = cr.dictfetchall()
    if res:
        if (data['form']['date_to'] > res[0]['date_stop'] or data['form']['date_to'] < res[0]['date_start']):
                raise  wizard.except_wizard('UserError','Date to must be set between ' + res[0]['date_start'] + " and " + res[0]['date_stop'])
        else:
            return 'checkreport'

    else:
        raise wizard.except_wizard('UserError','Date not in a defined fiscal year')


class wizard_report(wizard.interface):
    def _get_defaults(self, cr, uid, data, context):
        fiscalyear_obj = pooler.get_pool(cr.dbname).get('account.fiscalyear')
        data['form']['fiscalyear'] = fiscalyear_obj.find(cr, uid)
        data['form']['sortbydate'] = 'sort_date'
        data['form']['display_account']='bal_all'
        data['form']['landscape']=True
        data['form']['amount_currency'] = True
        return data['form']
    def _get_defaults_fordate(self, cr, uid, data, context):
        data['form']['sortbydate'] = 'sort_date'
        data['form']['display_account']='bal_all'
        data['form']['landscape']=True
        data['form']['amount_currency'] = True
        return data['form']


    states = {
        'init': {
            'actions': [],
            'result': {'type':'choice','next_state':_check_path}
        },
        'account_selection': {
            'actions': [],
            'result': {'type':'form', 'arch':account_form,'fields':account_fields, 'state':[('end','Cancel'),('checktype','Print')]}
        },
        'checktype': {
            'actions': [],
            'result': {'type':'form', 'arch':report_type,'fields':{}, 'state':[('with_period','Use with Period'),('with_date','Use with Date')]}
        },
        'with_period': {
            'actions': [_get_defaults],
            'result': {'type':'form', 'arch':period_form, 'fields':period_fields, 'state':[('end','Cancel'),('checkreport','Print')]}
        },
        'with_date': {
            'actions': [_get_defaults_fordate],
            'result': {'type':'form', 'arch':dates_form, 'fields':dates_fields, 'state':[('end','Cancel'),('checkdate','Print')]}
        },
        'checkdate': {
            'actions': [],
            'result': {'type':'choice','next_state':_check_date}
        },
        'checkreport': {
            'actions': [],
            'result': {'type':'choice','next_state':_check}
        },
        'report_landscape': {
            'actions': [],
            'result': {'type':'print', 'report':'account.general.ledger_landscape', 'state':'end'}
        },
        'report': {
            'actions': [],
            'result': {'type':'print', 'report':'account.general.ledger', 'state':'end'}
        }
    }
wizard_report('account.general.ledger.report')
