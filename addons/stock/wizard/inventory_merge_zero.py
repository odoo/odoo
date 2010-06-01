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
from tools.translate import _


_form = """<?xml version="1.0"?>
<form string="Set Stock to Zero">
    <separator colspan="4" string="Set Stocks to Zero" />
    <field name="location_id"/>
    <newline/>
    <label colspan="4" string="Do you want to set stocks to zero ?"/>
</form>
"""
_inventory_fields = {
    'location_id' : {
        'string':'Location',
        'type':'many2one',
        'relation':'stock.location',
        'required':True
        }
}


def do_merge(self, cr, uid, data, context):
    invent_obj = pooler.get_pool(cr.dbname).get('stock.inventory')
    invent_line_obj = pooler.get_pool(cr.dbname).get('stock.inventory.line')
    prod_obj =  pooler.get_pool(cr.dbname).get('product.product')

    if len(data['ids']) <> 1:
        raise wizard.except_wizard(_('Warning'),
                                   _('Please select one and only one inventory !'))

    loc = data['form']['location_id']

    cr.execute('select distinct location_id,product_id from stock_inventory_line where inventory_id=%s', (data['ids'][0],))
    inv = cr.fetchall()
    cr.execute('select distinct product_id from stock_move where (location_dest_id=%(location_id)s) or (location_id=%(location_id)s)', data['form'])
    stock = cr.fetchall()
    for s in stock:
        if (loc,s[0]) not in inv:
            p = prod_obj.browse(cr, uid, s[0])
            invent_line_obj.create(cr, uid, {
                'inventory_id': data['ids'][0],
                'location_id': loc,
                'product_id': s[0],
                'product_uom': p.uom_id.id,
                'product_qty': 0.0,
                })
    return {}


class merge_inventory(wizard.interface):
    states = {
        'init' : {
            'actions' : [],
            'result' : {'type' : 'form',
                    'arch' : _form,
                    'fields' : _inventory_fields,
                    'state' : [('end', 'Cancel'),
                               ('merge', 'Set to Zero') ]}
        },
        'merge' : {
            'actions' : [],
            'result' : {'type' : 'action',
                        'action': do_merge,
                        'state' : 'end'}
        },
    }
merge_inventory("inventory.merge.stock.zero")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

