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

import pooler
import wizard
from tools.translate import _

picking_form = """<?xml version="1.0"?>
<form string="Select an Open Sale Order">
    <field name="picking_id" domain="[('state','in',('assigned','confirmed')), ('type', '=', 'out')]" context="{'contact_display':'partner'}"/>
</form>
"""

picking_fields = {
    'picking_id': {'string': 'Sale Order', 'type': 'many2one', 'relation': 'stock.picking', 'required': True}
}


def _sale_complete(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    order = pool.get('pos.order').browse(cr, uid, data['id'], context)

    if order.state in ('paid', 'invoiced'):
        raise wizard.except_wizard(_('UserError'), _("You can't modify this order. It has already been paid"))

    pick = pool.get('stock.picking').browse(cr, uid, data['form']['picking_id'], context)

    pool.get('pos.order').write(cr, uid, data['id'], {
        'last_out_picking': data['form']['picking_id'],
        'partner_id': pick.address_id and pick.address_id.partner_id.id
    })

    order = pool.get('stock.picking').write(cr, uid, [data['form']['picking_id']], {
        'invoice_state': 'none',
        'pos_order': data['id']
    })

    for line in pick.move_lines:
        pool.get('pos.order.line').create(cr, uid, {
            'name': line.sale_line_id.name,
            'order_id': data['id'],
            'qty': line.product_qty,
            'product_id': line.product_id.id,
            'price_unit': line.sale_line_id.price_unit,
            'discount': line.sale_line_id.discount,
        })

    return {}


class pos_sale_get(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': picking_form,
                'fields': picking_fields,
                'state': (('end', 'Cancel'),
                          ('set', 'Confirm', 'gtk-ok', True)
                         )
            }
        },
        'set': {
            'actions': [_sale_complete],
            'result': {
                'type': 'state',
                'state': "end",
            }
        },
    }

pos_sale_get('pos.sale.get')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

