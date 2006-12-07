##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
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
from osv import osv
import pooler

arch = '''<?xml version="1.0"?>
<form string="Lots lines">
	<field name="lot_lines" widget="one2many_list" nolabel="1" colspan="4"/>
</form>'''

fields = {
	'lot_lines': {'string':'Lot Lines', 'type':'one2many', 'relation':'stock.picking.lot.line'},
}

def _get_value(self, cr, uid, data, context):
	cr.execute("select l.id,l.name,l.product_uom,l.product_qty,l.serial,l.tracking,l.reservation_id,l.product_id,r.state from stock_lot_line l left join stock_reservation r on (l.reservation_id=r.id) where r.state='assigned' and r.picking_id=%d", (data['id'],))
	records = cr.dictfetchall()
	ids_products = [x['product_id'] for x in records]
	prods = dict(pooler.get_pool(cr.dbname).get('product.product').name_get(cr, uid, ids_products))
	ids_new = []
	for record in records:
		ids_new.append( pooler.get_pool(cr.dbname).get('stock.picking.lot.line').create(cr, uid, {'name': prods.get(record['product_id'],'Unknown'),'product_id':record['product_id'],  'product_uom':record['product_uom'], 'product_qty':record['product_qty'],'serial':record['serial'],'tracking':record['tracking'],'reservation_id':record['reservation_id'],'picking_id':data['id'],'lot_line_id':record['id'],'state':record['state']}) )
	return {'lot_lines':ids_new}

def _split_line(self, cr, uid, data, context):
	service = netsvc.LocalService("object_proxy")
	quantity = service.execute(cr.dbname, uid, 'stock.lot.line', '_split', data['id'], data['form']['quantity'], data['form']['serial'], data['form']['tracking'])
	return {}

class stock_picking_make(wizard.interface):
	states = {
		'init': {
			'actions': [_get_value],
			'result': {'type':'form', 'arch':arch, 'fields':fields, 'state':[('end','Cancel'),('make','Make Parcel')]}
		},
		'make': {
#SUPERCHECKME: this doesn't do anything... doesn't seem normal to me...		
			'actions': [],
			'result': {'type':'state', 'state':'end'}
		}
	}

stock_picking_make('stock.picking.make')

