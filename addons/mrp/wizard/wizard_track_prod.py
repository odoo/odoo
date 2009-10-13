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
import netsvc
import pooler

import time
from osv import osv
from tools.misc import UpdateableStr

arch = UpdateableStr()
fields = {}

def _get_moves(self, cr, uid, data, context):
    prod_obj = pooler.get_pool(cr.dbname).get('mrp.production')
    prod = prod_obj.browse(cr, uid, [data['id']])[0]
    res = {}
    fields.clear()
    if prod.state != 'done':
        arch.string = '''<?xml version="1.0"?><form string="Track lines"><label colspan="4" string="You can not split an unfinished production output" /></form>'''
        res['moves'] = []
    else:
        arch_lst = ['<?xml version="1.0"?>', '<form string="Track lines">', '<label colspan="4" string="The field on each line says if this lot should be tracked or not." />']
        for m in [line for line in prod.move_created_ids]:
            quantity = m.product_qty
            arch_lst.append('<field name="track%s" />\n<newline />' % m.id)
            fields['track%s' % m.id] = {'string' : m.product_id.name, 'type' : 'boolean', 'default' : lambda x,y,z: False}
            res.setdefault('moves', []).append(m.id)
        arch_lst.append('</form>')
        arch.string = '\n'.join(arch_lst)
    return res

def _track_lines(self, cr, uid, data, context):
    if not data['form']['moves']:
        return {}
    prodlot_obj = pooler.get_pool(cr.dbname).get('stock.production.lot')
    lot_obj = pooler.get_pool(cr.dbname).get('stock.lot')
    move_obj = pooler.get_pool(cr.dbname).get('stock.move')

    new_lot = lot_obj.create(cr, uid, {'name': 'PRODUCTION:%d' % data['id']})
    for idx, move in enumerate(move_obj.browse(cr, uid, data['form']['moves'])):
        if data['form']['track%s' % move.id]:
            for idx in range(move.product_qty):
                update_val = {'product_qty': 1, 'lot_id': new_lot}
                if idx:
                    current_move = move_obj.copy(cr, uid, move.id, {'state': move.state, 'production_id': move.production_id.id})
                else:
                    current_move = move.id
                new_prodlot = prodlot_obj.create(cr, uid, {'name': 'PRODUCTION:%d:LOT:%d' % (data['id'], idx+1)})
                update_val['prodlot_id'] = new_prodlot
                move_obj.write(cr, uid, [current_move], update_val)
    return {}

class wizard_track_move(wizard.interface):
    def _next(self, cr, uid, data, context):
        prod_obj = pooler.get_pool(cr.dbname).get('mrp.production')
        prod = prod_obj.browse(cr, uid, [data['id']])[0]
        if prod.state != 'done':
            return 'notrack'
        else:
            return 'track'
    states = {
        'init': {
            'actions': [],
            'result': {'type':'choice', 'next_state': _next}
        },
        'notrack':{
            'actions':[_get_moves],
            'result':{'type':'form', 'arch':arch, 'fields':fields, 'state':[('end', 'Cancel')]}
        },
        'track':{
            'actions':[_get_moves],
            'result': {'type':'form', 'arch':arch, 'fields':fields, 'state':[('end','Cancel'),('split','Track')]}
        },
        'split': {
            'actions': [_track_lines],
            'result': {'type':'state', 'state':'end'}
        }
    }

wizard_track_move('mrp.production.track')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

