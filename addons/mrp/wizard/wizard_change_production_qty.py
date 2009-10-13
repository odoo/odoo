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

import time
import wizard
import ir
import pooler
from osv.osv import except_osv
from osv import fields,osv
import netsvc
from tools.translate import _


form1 = '''<?xml version="1.0"?>
<form string="Change Product Qty">
    <field name="product_qty"/>
</form>'''

form1_fields={
                'product_qty': {'string': 'Product Qty', 'type':'float', 'required':True},
              }

def _get_qty(self,cr,uid, data, state):
    prod_obj = pooler.get_pool(cr.dbname).get('mrp.production')
    prod = prod_obj.browse(cr, uid,data['ids'])[0]
    form1_fields['product_qty']['default']=prod.product_qty
    return {}
def _get_states(self, cr, uid, data, context):
    prod_obj = pooler.get_pool(cr.dbname).get('mrp.production')
    prod = prod_obj.browse(cr, uid,data['ids'])[0]
    if prod.state in  ('cancel', 'done'):
        raise wizard.except_wizard(_('Warning !'), _('The production is in "%s" state. You can not change the production quantity anymore') % (prod.state).upper() )
        return 'end'
    if prod.state in  ('draft'):
        #raise wizard.except_wizard('Warning !', 'The production is in "%s" state. You can change the production quantity directly...!!!' % (prod.state).upper() )
        return 'end'
    else:
        return 'confirm'

def _change_prod_qty(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    prod_obj = pool.get('mrp.production')
    prod = prod_obj.browse(cr, uid,data['ids'])[0]
    prod_obj.write(cr, uid,prod.id, {'product_qty' : data['form']['product_qty']})
    prod_obj.action_compute(cr, uid, [prod.id])

    move_lines_obj = pool.get('stock.move')
    for move in prod.move_lines:
        bom_point = prod.bom_id
        bom_id = prod.bom_id.id
        if not bom_point:
            bom_id = pool.get('mrp.bom')._bom_find(cr, uid, prod.product_id.id, prod.product_uom.id)
            if not bom_id:
                raise osv.except_osv(_('Error'), _("Couldn't find bill of material for product"))
            self.write(cr, uid, [prod.id], {'bom_id': bom_id})
            bom_point = pool.get('mrp.bom').browse(cr, uid, [bom_id])[0]

        if not bom_id:
            raise osv.except_osv(_('Error'), _("Couldn't find bill of material for product"))

        factor = prod.product_qty * prod.product_uom.factor / bom_point.product_uom.factor
        res = pool.get('mrp.bom')._bom_explode(cr, uid, bom_point, factor / bom_point.product_qty, [])
        for r in res[0]:
            if r['product_id']== move.product_id.id:
                move_lines_obj.write(cr, uid,move.id, {'product_qty' :  r['product_qty']})

    product_lines_obj = pool.get('mrp.production.product.line')

    for m in prod.move_created_ids:
        move_lines_obj.write(cr, uid,m.id, {'product_qty' : data['form']['product_qty']})

    return {}

class change_production_qty(wizard.interface):
    states = {
        'init' : {
            'actions' : [],
            'result' : {'type' : 'choice', 'next_state' : _get_states}
        },

        'confirm' : {
            'actions' : [_get_qty],
            'result': {'type': 'form', 'arch':form1, 'fields':form1_fields, 'state':[('end','Cancel'),('validate','Validate')]}
        },

        'validate': {
            'actions': [],
            'result': {'type':'action', 'action':_change_prod_qty, 'state':'end'}
        },

        'end' : {
            'actions' : [],
            'result': {'type': 'state', 'state': 'end'},
        },
    }

change_production_qty('change_production_qty')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
