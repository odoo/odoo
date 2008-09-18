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

import time
import wizard
import ir
import pooler
from osv.osv import except_osv
from osv import fields,osv
import netsvc

inventory_form = """<?xml version="1.0"?>
<form string="Fill Inventory">
    <separator colspan="4" string="Fill Inventory for specific location" />
    <field name="location_id"/>
    <newline/>
    <field name="recursive"/>
    <newline/>

</form>
"""

inventory_fields = {
    'location_id' : {
        'string':'Location',
        'type':'many2one',
        'relation':'stock.location',
        'required':True
    },
    'recursive' : {'string':'Include all childs for the location', 'type':'boolean'}
}



def _fill_inventory(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    inventory_line_obj = pooler.get_pool(cr.dbname).get('stock.inventory.line')
    location_obj = pooler.get_pool(cr.dbname).get('stock.location')
    res={}
    res_location={}
    if data['form']['recursive'] :
        location_ids = location_obj.search(cr, uid, [('location_id', 'child_of', [data['form']['location_id']])])
        for location in location_ids :
            res=location_obj._product_get(cr, uid, location)
            res_location[location]=res
    else:
        res=location_obj._product_get(cr, uid, data['form']['location_id'])
        res_location[data['form']['location_id']]=res

    product_ids=[]
    for location in res_location.keys():
        res=res_location[location]
        for product_id in res.keys():
            #product_ids.append(product_id)
            prod = pool.get('product.product').browse(cr, uid, [product_id])[0]
            uom = prod.uom_id.id
            amount=pool.get('stock.location')._product_get(cr, uid, location, [product_id], {'uom': uom})[product_id]

            if(amount):
                inventory_line={'inventory_id':data['id'],'location_id':location,'product_id':product_id,'product_uom':uom,'product_qty':amount}
                #inventory_line_obj.create(cr, uid, inventory_line)
                product_ids.append(inventory_line_obj.create(cr, uid, inventory_line))

    if(len(product_ids)==0):
        raise wizard.except_wizard('Message ! ','No product in this location.')
    return {}



class fill_inventory(wizard.interface):
    states = {
        'init' : {
            'actions' : [],
            'result' : {'type' : 'form',
                    'arch' : inventory_form,
                    'fields' : inventory_fields,
                    'state' : [('end', 'Cancel'),('fill_inventory', 'Fill Inventory') ]}
        },
        'fill_inventory' : {
            'actions' : [],
            'result' : {'type' : 'action', 'action': _fill_inventory, 'state' : 'end'}
        },
    }
fill_inventory("stock.fill_inventory")



