# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
# $Id$
#
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
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
        'string': 'Packings',
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

