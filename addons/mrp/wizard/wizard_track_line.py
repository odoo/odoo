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
import netsvc
import pooler

import time
from osv import osv
from tools.translate import _

track_form = '''<?xml version="1.0"?>
<form string="Tracking a move">
 <field name="tracking_prefix"/>
 <newline/>
 <field name="quantity"/>
</form>
'''
fields = {
        'tracking_prefix': {
            'string': 'Tracking prefix',
            'type': 'char',
            'size': 64,
        },
        'quantity': {
            'string': 'Quantity per lot',
            'type': 'float',
            'default': 1,
        }
}

def _check_picking(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    move_obj = pool.get('stock.move').browse(cr, uid, data['id'])
    #Checking for the existence of production id too
    cr.execute('select production_id from mrp_production_move_ids where move_id=%s' % (data['id'],))
    res = cr.fetchone()
    res = res and res[0] or False
    
    if (not move_obj.picking_id) and (not res):
        raise wizard.except_wizard(_('Caution!'), _('Before splitting the production lots,make sure this move or its Production Order has a Picking attached !\nYou must save the move before performing this operation.'))
    return data['form']

def _track_lines(self, cr, uid, data, context):
    move_id = data['id']

    pool = pooler.get_pool(cr.dbname)
    prodlot_obj = pool.get('stock.production.lot')
    move_obj = pool.get('stock.move')
    production_obj = pool.get('mrp.production')
    ir_sequence_obj = pool.get('ir.sequence')

    sequence = ir_sequence_obj.get(cr, uid, 'stock.lot.serial')
    if not sequence:
        raise wizard.except_wizard(_('Error!'), _('No production sequence defined'))
    if data['form']['tracking_prefix']:
        sequence = data['form']['tracking_prefix']+'/'+(sequence or '')

    move = move_obj.browse(cr, uid, [move_id])[0]
    
    quantity=data['form']['quantity']
    if quantity <= 0 or move.product_qty == 0:
        return {}
    uos_qty = quantity/move.product_qty*move.product_uos_qty

    quantity_rest = move.product_qty%quantity
    uos_qty_rest = quantity_rest/move.product_qty*move.product_uos_qty

    update_val = {
        'product_qty': quantity,
        'product_uos_qty': uos_qty,
    }
    new_move = []
    production_ids = []
    for idx in range(int(move.product_qty//quantity)):
        if idx:
            current_move = move_obj.copy(cr, uid, move.id, {'state': move.state})
            new_move.append(current_move)
        else:
            current_move = move.id
        new_prodlot = prodlot_obj.create(cr, uid, {'name': sequence, 'ref': '%d'%idx}, {'product_id': move.product_id.id})
        update_val['prodlot_id'] = new_prodlot
        move_obj.write(cr, uid, [current_move], update_val)
        production_ids = production_obj.search(cr, uid, [('move_lines', 'in', [move.id])])

    if quantity_rest > 0:
        idx = int(move.product_qty//quantity)
        update_val['product_qty'] = quantity_rest
        update_val['product_uos_qty'] = uos_qty_rest
        if idx:
            current_move = move_obj.copy(cr, uid, move.id, {'state': move.state})
            new_move.append(current_move)
        else:
            current_move = move.id
        new_prodlot = prodlot_obj.create(cr, uid, {'name': sequence, 'ref': '%d'%idx}, {'product_id': move.product_id.id})
        update_val['prodlot_id'] = new_prodlot
        move_obj.write(cr, uid, [current_move], update_val)

    products = production_obj.read(cr, uid, production_ids, ['move_lines'])
    for p in products:
        for new in new_move:
            if new not in p['move_lines']:
                p['move_lines'].append(new)
        production_obj.write(cr, uid, [p['id']], {'move_lines': [(6, 0, p['move_lines'])]})

    return {}

class wizard_track_move(wizard.interface):
    states = {
        'init': {
            'actions': [_check_picking],
            'result': {'type': 'form', 'arch': track_form, 'fields': fields, 'state': [('end', 'Cancel', 'gtk-cancel'), ('track', 'Ok', 'gtk-ok')]},
            },
        'track': {
            'actions': [_track_lines],
            'result': {'type':'state', 'state':'end'}
        }
    }

wizard_track_move('mrp.stock.move.track')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

