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
import time
from tools.translate import _

def _action_open_window(self, cr, uid, data, context): 
    domain = []
    from_date = data['form']['from_date']
    to_date = data['form']['to_date']
    if from_date and to_date:
        domain = [('date','>=',from_date),('date','<=',to_date)]
    elif from_date:
        domain = [('date','>=',from_date)]
    elif to_date:
        domain = [('date','<=',to_date)]
    return {
        'name': _('Analytic Entries'),
        'view_type': 'form',
        "view_mode": 'tree,form',
        'res_model': 'account.analytic.line',
        'type': 'ir.actions.act_window',
        'domain': domain}


class account_analytic_line(wizard.interface):
    form1 = '''<?xml version="1.0"?>
    <form string="View Account Analytic Lines">
        <separator string="Account Analytic Lines Analysis" colspan="4"/>
        <field name="from_date"/>
        <newline/>
        <field name="to_date"/>
        <newline/>
        <label string=""/>
        <label string="(Keep empty to open the current situation)" align="0.0" colspan="3"/>
    </form>'''
    form1_fields = {
             'from_date': {
                'string': 'From',
                'type': 'date',
        },
             'to_date': {
                'string': 'To',
                'type': 'date',
        },
    }

    states = {
      'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':form1, 'fields':form1_fields, 'state': [('end', 'Cancel','gtk-cancel'),('open', 'Open Entries','gtk-ok')]}
        },
    'open': {
            'actions': [],
            'result': {'type': 'action', 'action': _action_open_window, 'state':'end'}
        }
    }
account_analytic_line('account.analytic.line')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
