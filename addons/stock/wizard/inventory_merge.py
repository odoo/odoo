# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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
        raise wizard.except_wizard("Warning",
            _("Please select at least two inventories."))



    for inventory in invent_obj.browse(cr, uid, data['ids'], context=context):
        if inventory.state == "done":
            raise wizard.except_wizard("Warning",
                _("Merging is only allowed on draft inventories."))

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

