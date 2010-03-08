# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import time
import netsvc
from tools.misc import UpdateableStr, UpdateableDict
import pooler

import wizard
from osv import osv
import tools
from tools.translate import _

_moves_arch = UpdateableStr()
_moves_fields = UpdateableDict()

_moves_arch_end = '''<?xml version="1.0"?>
<form string="Picking result">
    <label string="Move(s) have been successfully Done !" colspan="4"/>    
</form>'''

def make_default(val):
    def fct(uid, data, state):
        return val
    return fct

def _to_xml(s):
    return (s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def _get_moves(self, cr, uid, data, context):
    move_obj = pooler.get_pool(cr.dbname).get('stock.move')
    move_lines = move_obj.browse(cr, uid, data['ids'], context)
    res = {}

    _moves_fields.clear()
    _moves_arch_lst = ['<?xml version="1.0"?>', '<form string="Partial Stock Moves">']

    for move in move_lines:
        quantity = move.product_qty
        if move.state != 'assigned':
            quantity = 0

        _moves_arch_lst.append('<field name="move%s" />' % (move.id,))
        _moves_fields['move%s' % move.id] = {
                'string': _to_xml(move.name),
                'type' : 'float', 'required' : True, 'default' : make_default(quantity)}

        if (move.picking_id.type == 'in') and (move.product_id.cost_method == 'average'):
            price = 0
            if hasattr(move, 'purchase_line_id') and move.purchase_line_id:
                price = move.purchase_line_id.price_unit

            currency = 0
            if hasattr(move.picking_id, 'purchase_id') and move.picking_id.purchase_id:
                currency = move.picking_id.purchase_id.pricelist_id.currency_id.id

            _moves_arch_lst.append('<group col="6"><field name="uom%s" nolabel="1"/>\
                    <field name="price%s"/>' % (move.id, move.id,))

            _moves_fields['price%s' % move.id] = {'string': 'Unit Price',
                    'type': 'float', 'required': True, 'default': make_default(price)}

            _moves_fields['uom%s' % move.id] = {'string': 'UOM', 'type': 'many2one',
                    'relation': 'product.uom', 'required': True,
                    'default': make_default(move.product_uom.id)}

            _moves_arch_lst.append('<field name="currency%d" nolabel="1"/></group>' % (move.id,))
            _moves_fields['currency%s' % m.id] = {'string': 'Currency',
                    'type': 'many2one', 'relation': 'res.currency',
                    'required': True, 'default': make_default(currency)}

        _moves_arch_lst.append('<newline/>')
        res.setdefault('moves', []).append(move.id)

    _moves_arch_lst.append('</form>')
    _moves_arch.string = '\n'.join(_moves_arch_lst)
    return res

def _do_split(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    move_obj = pool.get('stock.move')
    pick_obj = pool.get('stock.picking')
    product_obj = pool.get('product.product')
    currency_obj = pool.get('res.currency')
    users_obj = pool.get('res.users')
    uom_obj = pool.get('product.uom')
    move_lines = move_obj.browse(cr, uid, data['ids'])
    wf_service = netsvc.LocalService("workflow")
    complete, too_few, too_many = [], [], []
    for move in move_lines:        
        states = []
    
        if move.product_qty == data['form']['move%s' % move.id]:
            complete.append(move)
        elif move.product_qty > data['form']['move%s' % move.id]:
            too_few.append(move)
        else:
            too_many.append(move)        
        # Average price computation
        if (move.picking_id.type == 'in') and (move.product_id.cost_method == 'average'):
            product = move.product_id
            user = users_obj.browse(cr, uid, uid)
            qty = data['form']['move%s' % move.id]
            uom = data['form']['uom%s' % move.id]
            price = data['form']['price%s' % move.id]
            currency = data['form']['currency%s' % move.id]

            qty = uom_obj._compute_qty(cr, uid, uom, qty, product.uom_id.id)
            pricetype=pool.get('product.price.type').browse(cr,uid,user.company_id.property_valuation_price_type.id)
            
            if (qty > 0):
                new_price = currency_obj.compute(cr, uid, currency,
                        user.company_id.currency_id.id, price)
                new_price = uom_obj._compute_price(cr, uid, uom, new_price,
                        product.uom_id.id)
                if product.qty_available<=0:
                    new_std_price = new_price
                else:
                    # Get the standard price
                    amount_unit=product.price_get(pricetype.field, context)[product.id]
                    new_std_price = ((amount_unit * product.qty_available)\
                        + (new_price * qty))/(product.qty_available + qty)

                product_obj.write(cr, uid, [product.id],
                        {pricetype.field: new_std_price})
                move_obj.write(cr, uid, move.id, {'price_unit': new_price})        

    for move in too_few:        
        if data['form']['move%s' % move.id] != 0:
            new_move = move_obj.copy(cr, uid, move.id,
                {
                    'product_qty' : data['form']['move%s' % move.id],
                    'product_uos_qty':data['form']['move%s' % move.id],
                    'picking_id' : move.picking_id.id,
                    'state': 'assigned',
                    'move_dest_id': False,
                    'price_unit': move.price_unit,
                })
            complete.append(move_obj.browse(cr, uid, new_move))
        move_obj.write(cr, uid, move.id,
                {
                    'product_qty' : move.product_qty - data['form']['move%s' % move.id],
                    'product_uos_qty':move.product_qty - data['form']['move%s' % move.id],
                })
        
    
    for move in too_many:
        move_obj.write(cr, uid, move.id,
                {
                    'product_qty': data['form']['move%s' % move.id],
                    'product_uos_qty': data['form']['move%s' % move.id]
                })
        complete.append(move) 

    for move in complete:
        move_obj.action_done(cr, uid, [move.id])

        # TOCHECK : Done picking if all moves are done
        cr.execute('select move.id from stock_picking pick \
                    right join stock_move move on move.picking_id = pick.id and move.state = ''%s'' where pick.id = %s',
                    ('done', move.picking_id.id))
        res = cr.fetchall()        
        if len(res) == len(move.picking_id.move_lines):                       
            pick_obj.action_move(cr, uid, [move.picking_id.id])            
            wf_service.trg_validate(uid, 'stock.picking', move.picking_id.id, 'button_done', cr)

    return {}



class partial_move(wizard.interface):

    states = {
        'init': {
            'actions': [ _get_moves ],
            'result': {'type': 'form', 'arch': _moves_arch, 'fields': _moves_fields,
                'state' : (
                    ('end', 'Cancel', 'gtk-cancel'),
                    ('split', 'Partial', 'gtk-apply', True)
                )
            },
        },
        'split': {
            'actions': [ _do_split ],
            'result': {'type': 'state', 'state': 'end2'},
        },
        'end2': {
            'actions': [],
            'result': {'type': 'form', 'arch': _moves_arch_end,
                'fields': {},
                'state': (
                    ('end', 'Close'),
                )
            },
        },
    }

partial_move('stock.partial_move')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

