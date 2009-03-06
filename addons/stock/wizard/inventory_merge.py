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
<form string="Merge inventories">
    <separator colspan="4" string="Merge inventories" />
    <label string="Do you want to merge theses inventories ?"/>
</form>
"""


def do_merge(self, cr, uid, data, context):

    invent_obj = pooler.get_pool(cr.dbname).get('stock.inventory')
    invent_line_obj = pooler.get_pool(cr.dbname).get('stock.inventory.line')

    invent_lines = {}

    if len(data['ids']) < 2:
        raise wizard.except_wizard(_('Warning'),
            _('Please select at least two inventories.'))



    for inventory in invent_obj.browse(cr, uid, data['ids'], context=context):
        if inventory.state == "done":
            raise wizard.except_wizard(_('Warning'),
                _('Merging is only allowed on draft inventories.'))

        for line in inventory.inventory_line_id:
            key = (line.location_id.id, line.product_id.id, line.product_uom.id)
            if key in invent_lines:
                invent_lines[key] += line.product_qty
            else:
                invent_lines[key] = line.product_qty


    new_invent = invent_obj.create(cr, uid, {
        'name': 'Merged inventory'
        }, context=context)

    for key, quantity in invent_lines.items():
        invent_line_obj.create(cr, uid, {
            'inventory_id': new_invent,
            'location_id': key[0],
            'product_id': key[1],
            'product_uom': key[2],
            'product_qty': quantity,
            })

    return {}


class merge_inventory(wizard.interface):
    states = {
        'init' : {
            'actions' : [],
            'result' : {'type' : 'form',
                    'arch' : _form,
                    'fields' : {},
                    'state' : [('end', 'Cancel'),
                               ('merge', 'Yes') ]}
        },
        'merge' : {
            'actions' : [],
            'result' : {'type' : 'action',
                        'action': do_merge,
                        'state' : 'end'}
        },
    }
merge_inventory("inventory.merge")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

