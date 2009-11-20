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
    pool = pooler.get_pool(cr.dbname) 
    mod_obj = pool.get('ir.model.data') 
    result = mod_obj._get_id(cr, uid, 'product', 'product_search_form_view')
    id = mod_obj.read(cr, uid, result, ['res_id'])    
    cr.execute('select id,name from ir_ui_view where name=%s and type=%s', ('product.margin.graph', 'graph'))
    view_res3 = cr.fetchone()[0]
    cr.execute('select id,name from ir_ui_view where name=%s and type=%s', ('product.margin.form.inherit', 'form'))
    view_res2 = cr.fetchone()[0]
    cr.execute('select id,name from ir_ui_view where name=%s and type=%s', ('product.margin.tree', 'tree'))
    view_res = cr.fetchone()[0]
    return {
        'name': _('Product Margins'),
        'context':{'date_from':data['form']['from_date'],'date_to':data['form']['to_date'],'invoice_state' : data['form']['invoice_state']},
        'view_type': 'form',
        "view_mode": 'tree,form,graph',
        'res_model':'product.product',
        'type': 'ir.actions.act_window',
        'views': [(view_res,'tree'), (view_res2,'form'), (view_res3,'graph')],
        'view_id': False,
        'search_view_id': id['res_id'] 
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
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
