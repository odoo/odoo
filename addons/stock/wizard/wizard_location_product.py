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
import pooler
import time

def _action_open_window(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname) 
    mod_obj = pool.get('ir.model.data') 
    result = mod_obj._get_id(cr, uid, 'product', 'product_search_form_view')
    id = mod_obj.read(cr, uid, result, ['res_id'])          
    return {
        'name': False,
        'view_type': 'form',
        "view_mode": 'tree,form',
        'res_model': 'product.product',
        'type': 'ir.actions.act_window',
        'context':{'location': data['ids'][0],'from_date':data['form']['from_date'],'to_date':data['form']['to_date']},
        'domain':[('type','<>','service')],
        'search_view_id': id['res_id'] 
    }


class product_by_location(wizard.interface):
    form1 = '''<?xml version="1.0"?>
    <form string="View Stock of Products">
        <separator string="Stock Location Analysis" colspan="4"/>
        <field name="from_date"/>
        <newline/>
        <field name="to_date"/>
        <newline/>
        <label string=""/>
        <label string="(Keep empty to open the current situation. Adjust HH:MM:SS to 00:00:00 to filter all resources of the day for the 'From' date and 23:59:59 for the 'To' date)" align="0.0" colspan="3"/>
    </form>'''
    form1_fields = {
             'from_date': {
                'string': 'From',
                'type': 'datetime',
        },
             'to_date': {
                'string': 'To',
                'type': 'datetime',
        },
    }

    states = {
      'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':form1, 'fields':form1_fields, 'state': [('end', 'Cancel','gtk-cancel'),('open', 'Open Products','gtk-ok')]}
        },
    'open': {
            'actions': [],
            'result': {'type': 'action', 'action': _action_open_window, 'state':'end'}
        }
    }
product_by_location('stock.location.products')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
