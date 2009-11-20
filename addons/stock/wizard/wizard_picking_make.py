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
import netsvc

ARCH = '''<?xml version="1.0"?>
<form string="Make packing">
    <field name="pickings" nolabel="1" colspan="4"
        width="600" height="300"/>
</form>'''

FIELDS = {
    'pickings': {
        'string': 'Packing',
        'type': 'one2many',
        'relation': 'stock.picking',
        'readonly': True,
    },
}

def _get_value(obj, cursor, user, data, context):
    pool = pooler.get_pool(cursor.dbname)
    picking_obj = pool.get('stock.picking')

    picking_ids = picking_obj.search(cursor, user, [
        ('id', 'in', data['ids']),
        ('state', '<>', 'done'),
        ('state', '<>', 'cancel')], context=context)
    return {'pickings': picking_ids}

def _make_packing(obj, cursor, user, data, context):
    wkf_service = netsvc.LocalService('workflow')
    pool = pooler.get_pool(cursor.dbname)
    picking_obj = pool.get('stock.picking')
    ids = [x[1] for x in data['form']['pickings']]

    picking_obj.force_assign(cursor, user, ids)
    picking_obj.action_move(cursor, user, ids)
    for picking_id in ids:
        wkf_service.trg_validate(user, 'stock.picking', picking_id,
                'button_done', cursor)
    return {}

class stock_picking_make(wizard.interface):
    states = {
        'init': {
            'actions': [_get_value],
            'result': {
                'type': 'form',
                'arch': ARCH,
                'fields': FIELDS,
                'state': [
                    ('end', 'Cancel', 'gtk-cancel'),
                    ('make', 'Ok', 'gtk-ok', True)
                ],
            },
        },
        'make': {
            'actions': [_make_packing],
            'result': {
                'type': 'state',
                'state':'end',
            },
        },
    }

stock_picking_make('stock.picking.make')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

