# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
import time

def _action_open_window(self, cr, uid, data, context):
    cr.execute('select id,name from ir_ui_view where name=%s and type=%s', ('product.margin.tree', 'tree'))
    view_res = cr.fetchone()
    return {
        'name': 'Product Margins',
         'context':{'date_from':data['form']['from_date'],'date_to':data['form']['to_date'],'invoice_state' : data['form']['invoice_state']},
        'view_type': 'form',
        "view_mode": 'tree,form,graph',
        'res_model':'product.product',
        'type': 'ir.actions.act_window',
        'view_id': view_res,
    }


class product_margins(wizard.interface):
    form1 = '''<?xml version="1.0"?>
    <form string="View Stock of Products">
        <separator string="Select " colspan="4"/>
        <field name="from_date"/>
        <field name="to_date"/>
        <field name="invoice_state"/>
    </form>'''
    form1_fields = {
             'from_date': {
                'string': 'From',
                'type': 'date',
                'default': lambda *a:time.strftime('%Y-01-01'),

        },
             'to_date': {
                'string': 'To',
                'type': 'date',
                'default': lambda *a:time.strftime('%Y-12-31'),

        },
         'invoice_state': {
                'string': 'Invoice State',
                'type': 'selection',
                'selection': [('paid','Paid'),('open_paid','Open and Paid'),('draft_open_paid','Draft, Open and Paid'),],
                'required': True,
                'default': lambda *a:"open_paid",
        },
    }

    states = {
      'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':form1, 'fields':form1_fields, 'state': [('end', 'Cancel','gtk-cancel'),('open', 'Open Margins','gtk-ok')]}
        },
    'open': {
            'actions': [],
            'result': {'type': 'action', 'action': _action_open_window, 'state':'end'}
        }
    }
product_margins('product.margins')
