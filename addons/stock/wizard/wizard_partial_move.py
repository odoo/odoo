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
    <label string="The picking has been successfully made !" colspan="4"/>
    <field name="back_order_notification" colspan="4" nolabel="1"/>
</form>'''
_moves_fields_end = {
    'back_order_notification': {'string':'Back Order' ,'type':'text', 'readonly':True}
                     }

def make_default(val):
    def fct(uid, data, state):
        return val
    return fct

def _to_xml(s):
    return (s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def _get_moves(self, cr, uid, data, context):
    move_obj = pooler.get_pool(cr.dbname).get('stock.move')
    move_lines = move_obj.browse(cr, uid, [data['id']], context)
    res = {}

    _moves_fields.clear()
    _moves_arch_lst = ['<?xml version="1.0"?>', '<form string="Partial Stock Moves">']

    for m in move_lines:
        quantity = m.product_qty
        if m.state<>'assigned':
            quantity = 0

        _moves_arch_lst.append('<field name="move%s" />' % (m.id,))
        _moves_fields['move%s' % m.id] = {
                'string': _to_xml(m.name),
                'type' : 'float', 'required' : True, 'default' : make_default(quantity)}

        if (m.picking_id.type == 'in') and (m.product_id.cost_method == 'average'):
            price=0
            if hasattr(m, 'purchase_line_id') and m.purchase_line_id:
                price=m.purchase_line_id.price_unit

            currency=0
            if hasattr(m.picking_id, 'purchase_id') and m.purchase_id:
                currency=m.purchase_id.pricelist_id.currency_id.id

            _moves_arch_lst.append('<group col="6"><field name="uom%s" nolabel="1"/>\
                    <field name="price%s"/>' % (m.id,m.id,))

            _moves_fields['price%s' % m.id] = {'string': 'Unit Price',
                    'type': 'float', 'required': True, 'default': make_default(price)}

            _moves_fields['uom%s' % m.id] = {'string': 'UOM', 'type': 'many2one',
                    'relation': 'product.uom', 'required': True,
                    'default': make_default(m.product_uom.id)}

            _moves_arch_lst.append('<field name="currency%d" nolabel="1"/></group>' % (m.id,))
            _moves_fields['currency%s' % m.id] = {'string': 'Currency',
                    'type': 'many2one', 'relation': 'res.currency',
                    'required': True, 'default': make_default(currency)}

        _moves_arch_lst.append('<newline/>')
        res.setdefault('moves', []).append(m.id)

    _moves_arch_lst.append('</form>')
    _moves_arch.string = '\n'.join(_moves_arch_lst)
    return res

def _do_split(self, cr, uid, data, context):
    move_obj = pooler.get_pool(cr.dbname).get('stock.move')
    pick_obj = pooler.get_pool(cr.dbname).get('stock.picking')
    move_lines = move_obj.browse(cr, uid, data['id'])
    pick = pick_obj.browse(cr, uid, [move_lines.picking_id.id])[0]
    pool = pooler.get_pool(cr.dbname)
    complete, too_few, too_many = False, False, False
    states = []
    
    if move_lines.product_qty == data['form']['move%s' % data['id']]:
        complete = move_lines
    elif move_lines.product_qty > data['form']['move%s' % data['id']]:
        too_few = move_lines
    else:
        too_many = move_lines
        
        # Average price computation
    if (move_lines.picking_id.type == 'in') and (move_lines.product_id.cost_method == 'average'):
        product_obj = pool.get('product.product')
        currency_obj = pool.get('res.currency')
        users_obj = pool.get('res.users')
        uom_obj = pool.get('product.uom')

        product = product_obj.browse(cr, uid, [move_lines.product_id.id])[0]
        user = users_obj.browse(cr, uid, [uid])[0]

        qty = data['form']['move%s' % move_lines.id]
        uom = data['form']['uom%s' % move_lines.id]
        price = data['form']['price%s' % move_lines.id]
        currency = data['form']['currency%s' % move_lines.id]

        qty = uom_obj._compute_qty(cr, uid, uom, qty, product.uom_id.id)

        if (qty > 0):
            new_price = currency_obj.compute(cr, uid, currency,
                    user.company_id.currency_id.id, price)
            new_price = uom_obj._compute_price(cr, uid, uom, new_price,
                    product.uom_id.id)
            if product.qty_available<=0:
                new_std_price = new_price
            else:
                new_std_price = ((product.standard_price * product.qty_available)\
                    + (new_price * qty))/(product.qty_available + qty)

            product_obj.write(cr, uid, [product.id],
                    {'standard_price': new_std_price})
            move_obj.write(cr, uid, [move_lines.id], {'price_unit': new_price})
    if complete:
        move_obj.write(cr, uid, [complete.id],{
                    'product_qty': data['form']['move%s' % complete.id],
                    'product_uos_qty': data['form']['move%s' % complete.id],
                    'state':'done' })
        for move in pick.move_lines:
            if move.state == 'done':
                states.append(True)
            else:
                states.append(False)
        if False not in states:
            pick_obj.write(cr, uid, complete.picking_id.id, {
                            'name': pool.get('ir.sequence').get(cr, uid, 'stock.picking'),
                            'state':'done' })
        return {'back_order':False}
    if too_few:
        pick_obj.write(cr, uid, too_few.picking_id.id, {
                        'name': pool.get('ir.sequence').get(cr, uid, 'stock.picking'),
                        'move_lines' : [],
                        'state':'assigned' })
        if data['form']['move%s' % too_few.id] <> 0:
            new_obj = move_obj.copy(cr, uid, too_few.id,
                {
                    'product_qty' : data['form']['move%s' % too_few.id],
                    'product_uos_qty':data['form']['move%s' % too_few.id],
                    'picking_id' : too_few.picking_id.id,
                    'move_dest_id': False,
                    'price_unit': too_few.price_unit,
                })
            move_obj.write(cr, uid, [new_obj],{'state':'done'})
        move_obj.write(cr, uid, [too_few.id],{
                    'product_qty' : move_lines.product_qty - data['form']['move%s' % too_few.id],
                    'product_uos_qty':move_lines.product_qty - data['form']['move%s' % too_few.id],
                    'state':'assigned' })
    if too_many:
        move_obj.write(cr, uid, [too_many.id],{
                    'product_qty': data['form']['move%s' % too_many.id],
                    'product_uos_qty': data['form']['move%s' % too_many.id],
                    'state':'assigned' })
    return {'back_order':False}

def _get_default(self, cr, uid, data, context):
    if data['form']['back_order']:
        data['form']['back_order_notification'] = _('Back Order %s Assigned to this Picking.') % (tools.ustr(data['form']['back_order']),)
    return data['form']

class partial_move(wizard.interface):

    states = {
        'init': {
            'actions': [ _get_moves ],
            'result': {'type': 'form', 'arch': _moves_arch, 'fields': _moves_fields,
                'state' : (
                    ('end', 'Cancel'),
                    ('split', 'Partial')
                )
            },
        },
        'split': {
            'actions': [ _do_split ],
            'result': {'type': 'state', 'state': 'end2'},
        },
        'end2': {
            'actions': [ _get_default ],
            'result': {'type': 'form', 'arch': _moves_arch_end,
                'fields': _moves_fields_end,
                'state': (
                    ('end', 'Close'),
                )
            },
        },
    }

partial_move('stock.partial_move')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

