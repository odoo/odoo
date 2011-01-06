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
import ir
import pooler
from osv.osv import except_osv
from osv import fields,osv
import netsvc
from tools.translate import _

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
    res = {}
    res_location = {}
    if data['form']['recursive'] :
        location_ids = location_obj.search(cr, uid, [('location_id', 'child_of', [data['form']['location_id']])])
        for location in location_ids :
            res = location_obj._product_get(cr, uid, location)
            res_location[location] = res
    else:
        context.update({'compute_child':False})
        res = location_obj._product_get(cr, uid, data['form']['location_id'],context=context)
        res_location[data['form']['location_id']] = res

    product_ids=[]
    for location in res_location.keys():
        res=res_location[location]
        for product_id in res.keys():
            #product_ids.append(product_id)
            prod = pool.get('product.product').browse(cr, uid, [product_id])[0]
            uom = prod.uom_id.id
            context.update({'uom': uom})
            amount=pool.get('stock.location')._product_get(cr, uid, location, [product_id], context=context)[product_id]

            if(amount):
                line_ids=inventory_line_obj.search(cr,uid,[('inventory_id','=',data['id']),('location_id','=',location),('product_id','=',product_id),('product_uom','=',uom),('product_qty','=',amount)])
                if not len(line_ids):
                    inventory_line={'inventory_id':data['id'],'location_id':location,'product_id':product_id,'product_uom':uom,'product_qty':amount}
                    inventory_line_obj.create(cr, uid, inventory_line)
                product_ids.append(product_id)

    if(len(product_ids)==0):
        raise wizard.except_wizard(_('Message !'), _('No product in this location.'))
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



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
