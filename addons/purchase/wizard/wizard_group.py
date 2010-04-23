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

import time

import wizard
import netsvc
import pooler
from osv.orm import browse_record, browse_null


merge_form = """<?xml version="1.0"?>
<form string="Merge orders">
    <separator string="Are you sure you want to merge these orders ?"/>
    <newline/>
    <label>Please note that:
      - orders will only be merged if:
        * their status is draft
        * they belong to the same partner
        * are going to the same location
        * have the same pricelist
      - lines will only be merged if:
        * they are exactly the same except for the quantity and unit</label>
</form>
"""

merge_fields = {
}

ack_form = """<?xml version="1.0"?>
<form string="Merge orders">
    <separator string="Orders merged"/>
</form>"""

ack_fields = {}


def _merge_orders(self, cr, uid, data, context):
    order_obj = pooler.get_pool(cr.dbname).get('purchase.order')

    def make_key(br, fields):
        list_key = []
        for field in fields:
            field_val = getattr(br, field)
            if field in ('product_id', 'move_dest_id', 'account_analytic_id'):
                if not field_val:
                    field_val = False
            if isinstance(field_val, browse_record):
                field_val = field_val.id
            elif isinstance(field_val, browse_null):
                field_val = False
            elif isinstance(field_val, list):
                field_val = ((6, 0, tuple([v.id for v in field_val])),)
            list_key.append((field, field_val))
        list_key.sort()
        return tuple(list_key)

    # compute what the new orders should contain
    new_orders = {}
    for porder in [order for order in order_obj.browse(cr, uid, data['ids']) if order.state == 'draft']:
        order_key = make_key(porder, ('partner_id', 'location_id', 'pricelist_id'))

        new_order = new_orders.setdefault(order_key, ({}, []))
        new_order[1].append(porder.id)
        order_infos = new_order[0]
        if not order_infos:
            order_infos.update({
                'origin': porder.origin,
                'date_order': time.strftime('%Y-%m-%d'),
                'partner_id': porder.partner_id.id,
                'partner_address_id': porder.partner_address_id.id,
                'dest_address_id': porder.dest_address_id.id,
                'warehouse_id': porder.warehouse_id.id,
                'location_id': porder.location_id.id,
                'pricelist_id': porder.pricelist_id.id,
                'state': 'draft',
                'order_line': {},
                'notes': '%s' % (porder.notes or '',),
                'fiscal_position': porder.fiscal_position and porder.fiscal_position.id or False,
            })
        else:
            #order_infos['name'] += ', %s' % porder.name
            if porder.notes:
                order_infos['notes'] = (order_infos['notes'] or '') + ('\n%s' % (porder.notes,))
            if porder.origin:
                order_infos['origin'] = (order_infos['origin'] or '') + ' ' + porder.origin

        for order_line in porder.order_line:
            line_key = make_key(order_line, ('name', 'date_planned', 'taxes_id', 'price_unit', 'notes', 'product_id', 'move_dest_id', 'account_analytic_id'))
            o_line = order_infos['order_line'].setdefault(line_key, {})
            if o_line:
                # merge the line with an existing line
                o_line['product_qty'] += order_line.product_qty * order_line.product_uom.factor / o_line['uom_factor']
            else:
                # append a new "standalone" line
                for field in ('product_qty', 'product_uom'):
                    field_val = getattr(order_line, field)
                    if isinstance(field_val, browse_record):
                        field_val = field_val.id
                    o_line[field] = field_val
                o_line['uom_factor'] = order_line.product_uom and order_line.product_uom.factor or 1.0

    wf_service = netsvc.LocalService("workflow")

    allorders = []
    for order_key, (order_data, old_ids) in new_orders.iteritems():
        # skip merges with only one order
        if len(old_ids) < 2:
            allorders += (old_ids or [])
            continue

        # cleanup order line data
        for key, value in order_data['order_line'].iteritems():
            del value['uom_factor']
            value.update(dict(key))
        order_data['order_line'] = [(0, 0, value) for value in order_data['order_line'].itervalues()]

        # create the new order
        neworder_id = order_obj.create(cr, uid, order_data)
        allorders.append(neworder_id)

        # make triggers pointing to the old orders point to the new order
        for old_id in old_ids:
            wf_service.trg_redirect(uid, 'purchase.order', old_id, neworder_id, cr)
            wf_service.trg_validate(uid, 'purchase.order', old_id, 'purchase_cancel', cr)

    return {
        'domain': "[('id','in', [" + ','.join(map(str, allorders)) + "])]",
        'name': 'Purchase Orders',
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'purchase.order',
        'view_id': False,
        'type': 'ir.actions.act_window'
    }


class merge_orders(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch': merge_form, 'fields' : merge_fields, 'state' : [('end', 'Cancel'), ('merge', 'Merge orders') ]}
        },
        'merge': {
            'actions': [],
            'result': {'type': 'action', 'action': _merge_orders, 'state': 'end'}
        },
    }

merge_orders("purchase.order.merge")

