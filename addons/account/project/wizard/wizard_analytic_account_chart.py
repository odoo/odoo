# -*- encoding: utf-8 -*-
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
import pooler

class wizard_analytic_account_chart(wizard.interface):
    _account_chart_arch = '''<?xml version="1.0"?>
    <form string="Analytic Account Charts">
        <separator string="Select the Period for Analysis" colspan="4"/>
        <field name="from_date"/>
        <newline/>
        <field name="to_date"/>
        <newline/>
        <label string="(Keep empty to open the current situation)" align="0.0" colspan="3"/>
    </form>'''

    _account_chart_fields = {
             'from_date': {
                'string': 'From',
                'type': 'date',
        },
             'to_date': {
                'string': 'To',
                'type': 'date',
        },
    }


    def _analytic_account_chart_open_window(self, cr, uid, data, context):
        mod_obj = pooler.get_pool(cr.dbname).get('ir.model.data')
        act_obj = pooler.get_pool(cr.dbname).get('ir.actions.act_window')

        result = mod_obj._get_id(cr, uid, 'account', 'action_account_analytic_account_tree2')
        id = mod_obj.read(cr, uid, [result], ['res_id'])[0]['res_id']
        result = act_obj.read(cr, uid, [id], context=context)[0]

        result_context = {}
        if data['form']['from_date']:
            result_context.update({'from_date' : data['form']['from_date']})
        if data['form']['to_date']:
            result_context.update({'to_date' : data['form']['to_date']})    
            
        result['context'] = str(result_context)
        return result

    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':_account_chart_arch, 'fields':_account_chart_fields, 'state': [('end', 'Cancel'), ('open', 'Open Charts')]}
        },
        'open': {
            'actions': [],
            'result': {'type': 'action', 'action':_analytic_account_chart_open_window, 'state':'end'}
        }
    }
wizard_analytic_account_chart('account.analytic.account.chart')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

