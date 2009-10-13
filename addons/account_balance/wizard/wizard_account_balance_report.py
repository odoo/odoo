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
    <notebook tabpos="up">
        <page string="Report Options">
            <separator string="Select Fiscal Year(s)(Maximum Three Years)" colspan="4"/>
            <label align="0.7" colspan="6" string="(If you do not select Fiscal year it will take all open fiscal years)"/>
            <field name="fiscalyear" colspan="5" nolabel="1"/>
            <field name="landscape" colspan="4"/>
            <field name="show_columns" colspan="4"/>
            <field name="format_perc" colspan="4"/>
            <field name="select_account" colspan="4"/>
            <field name="account_choice" colspan="4"/>
            <field name="compare_pattern" colspan="4"/>

        </page>

        <page string="Select Period">
            <field name="period_manner" colspan="4"/>
            <separator string="Select Period(s)" colspan="4"/>
            <field name="periods" colspan="4" nolabel="1"/>
        </page>
    </notebook>
</form>'''

dates_fields = {
    'fiscalyear': {'string': 'Fiscal year', 'type': 'many2many', 'relation': 'account.fiscalyear'},
    'select_account': {'string': 'Select Reference Account(for  % comparision)', 'type': 'many2one', 'relation': 'account.account','help': 'Keep empty for comparision to its parent'},
    'account_choice': {'string': 'Show Accounts', 'type': 'selection','selection':[('all','All accounts'),('bal_zero','With balance is not equal to 0'),('moves','With movements')]},
    'show_columns': {'string': 'Show Debit/Credit Information', 'type': 'boolean'},
    'landscape': {'string': 'Show Report in Landscape Form', 'type': 'boolean'},
    'format_perc': {'string': 'Show Comparision in %', 'type': 'boolean'},
    'compare_pattern':{'string':"Compare Selected Years In Terms Of",'type':'selection','selection':[('bal_cash','Cash'),('bal_perc','Percentage'),('none','Don'+ "'" +'t Compare')]},
    'period_manner':{'string':"Entries Selection Based on",'type':'selection','selection':[('actual','Financial Period'),('created','Creation Date')]},
    'periods': {'string': 'Periods', 'type': 'many2many', 'relation': 'account.period', 'help': 'All periods if empty'}
}

back_form='''<?xml version="1.0"?>
<form string="Notification">
<separator string="You might have done following mistakes. Please correct them and try again." colspan="4"/>
<separator string="1. You have selected more than 3 years in any case." colspan="4"/>
<separator string="2. You have not selected 'Percentage' option, but you have selected more than 2 years." colspan="4"/>
<label string="You can select maximum 3 years. Please check again." colspan="4"/>
<separator string="3. You have selected 'Percentage' option with more than 2 years, but you have not selected landscape format." colspan="4"/>
<label string="You have to select 'Landscape' option. Please Check it." colspan="4"/>
</form>'''

back_fields={
}

zero_form='''<?xml version="1.0"?>
<form string="Notification">
<separator string="You have to select at least 1 Fiscal Year. Try again." colspan="4"/>
<label string="You may have selected the compare options with more than 1 year with credit/debit columns and % option.This can lead contents to be printed out of the paper.Please try again."/>
</form>'''

zero_fields={
}

def _check(self, cr, uid, data, context):

        if (len(data['form']['fiscalyear'][0][2])==0) or (len(data['form']['fiscalyear'][0][2])>1 and (data['form']['compare_pattern']!='none') and (data['form']['format_perc']==1) and (data['form']['show_columns']==1) and (data['form']['landscape']!=1)):
            return 'zero_years'

        if ((len(data['form']['fiscalyear'][0][2])==3) and (data['form']['format_perc']!=1) and (data['form']['show_columns']!=1)):
            if data['form']['landscape']==1:
                return 'report_landscape'
            else:
                return 'report'


        if data['form']['format_perc']==1:
            if len(data['form']['fiscalyear'][0][2])<=2:
                if data['form']['landscape']==1:
                    return 'report_landscape'
                else:
                    return 'report'
            else:
                if len(data['form']['fiscalyear'][0][2])==3:
                    if data['form']['landscape']==1:
                        return 'report_landscape'
                    else:
                        return 'backtoinit'
                else:
                    return 'backtoinit'

        else:
            if len(data['form']['fiscalyear'][0][2])>2:
                if data['form']['landscape']==1:
                    return 'report_landscape'
                else:
                    return 'backtoinit'
            else:
                if data['form']['landscape']==1:
                    return 'report_landscape'
                else:
                    return 'report'




class wizard_report(wizard.interface):
    def _get_defaults(self, cr, uid, data, context={}):
        data['form']['context'] = context
        fiscalyear_obj = pooler.get_pool(cr.dbname).get('account.fiscalyear')
        data['form']['fiscalyear']=[fiscalyear_obj.find(cr, uid)]
#       p_ids=pooler.get_pool(cr.dbname).get('account.period').search(cr,uid,[('fiscalyear_id','=',fiscalyear_obj.find(cr, uid))])
#       data['form']['periods']=p_ids
        data['form']['compare_pattern']='none'
        data['form']['account_choice']='moves'
        data['form']['period_manner']='actual'
        return data['form']


    states = {
        'init': {
            'actions': [_get_defaults],
            'result': {'type':'form', 'arch':dates_form, 'fields':dates_fields, 'state':[('end','Cancel'),('checkyear','Print')]}
        },
        'backtoinit': {
            'actions': [],
            'result': {'type':'form','arch':back_form,'fields':back_fields,'state':[('end','Ok')]}
        },
        'zero_years': {
            'actions': [],
            'result': {'type':'form','arch':zero_form,'fields':zero_fields,'state':[('end','Ok')]}
        },
        'checkyear': {
            'actions': [],
            'result': {'type':'choice','next_state':_check}
        },
        'report_landscape': {
            'actions': [],
            'result': {'type':'print', 'report':'account.account.balance.landscape', 'state':'end'}
        },
        'report': {
            'actions': [],
            'result': {'type':'print', 'report':'account.balance.account.balance', 'state':'end'}
        }
    }
wizard_report('account.balance.account.balance.report')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

