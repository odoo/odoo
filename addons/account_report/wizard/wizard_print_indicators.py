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
import pooler
from tools.translate import _

form = '''<?xml version="1.0"?>
<form string="Print Indicators">
    <label string="Select the criteria based on which Indicators will be printed."/>
    <newline/>
    <field name="select_base"/>
</form>'''

fields = {
    'select_base': {'string':'Choose Criteria', 'type':'selection','selection':[('year','Based On Fiscal Years'),('periods','Based on Fiscal Periods')],'required':True,},
}

next_form = '''<?xml version="1.0"?>
<form string="Print Indicators">
    <field name="base_selection"/>
</form>'''

next_fields = {
    'base_selection': {'string':'Select Criteria', 'type':'many2many','required':True,},
}

def _load(self, cr, uid, data, context):
    data['form']['select_base'] = 'year'
    return data['form']

def _load_base(self, cr, uid, data, context):
    next_fields['base_selection']['relation']='account.fiscalyear'
    if data['form']['select_base']=='periods':
        next_fields['base_selection']['relation']='account.period'
    return data['form']

def _check_len(self, cr, uid, data, context):
    if len(data['form']['base_selection'][0][2])>8:
        raise wizard.except_wizard(_('User Error!'),_("Please select maximum 8 records to fit the page-width."))
    return data['form']

class wizard_print_indicators(wizard.interface):
    states = {
        'init': {
            'actions': [_load],
            'result': {'type': 'form', 'arch':form, 'fields':fields, 'state':[('end','Cancel'),('next','Next')]}
        },
        'next': {
            'actions': [_load_base],
            'result': {'type':'form', 'arch':next_form, 'fields':next_fields, 'state':[('end','Cancel'),('print','Print')]}
        },
        'print': {
            'actions':[_check_len],
            'result' :{'type':'print','report':'print.indicators', 'state':'end'}
        }
    }
wizard_print_indicators('print.indicators')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
