##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: makesale.py 1183 2005-08-23 07:43:32Z pinky $
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

from mx.DateTime import now

import wizard
import netsvc
import ir
import pooler

sale_form = """<?xml version="1.0"?>
<form string="Make an order">
	<separator string="Create a sale order from this opportunity"/>
	<field name="name" required="True" />
	<label string="(empty for default value)" colspan="2"/>
	<field name="shop_id" required="True" />
	<field name="partner_id" required="True" />
	<field name="state" required="True" />
	<field name="picking_policy" required="True" />
</form>"""

sale_fields = {
	'name' : {'string' : 'Order name', 'type': 'char'},
	'shop_id' : {'string' : 'Shop', 'type' : 'many2one', 'relation' : 'sale.shop'},
	'state' : {'string' : "Order's state", 'type' : 'selection', 'selection' : [('draft', 'Draft Order'), ('confirm', 'Confirm Order')]},
	'partner_id' : {'string' : 'Partner', 'type' : 'many2one', 'relation' : 'res.partner', 'readonly':True},
	'picking_policy': {'string': 'Picking policy', 'type': 'selection', 'selection' : [('direct','Direct Delivery'),('one','All at once')]},
}

ack_form = """<?xml version="1.0"?>
<form string="Make an order">
	<separator string="The sale order is now created" />
</form>"""

ack_fields = {}

class make_sale(wizard.interface):
	def _selectPartner(self, cr, uid, data, context):
		service = netsvc.LocalService("object_proxy")
		case = service.execute(cr.dbname, uid, data['model'], 'read', data['ids'], ['partner_id'])
		return {'partner_id': case[0]['partner_id']}

	def _makeOrder(self, cr, uid, data, context):
		case = pooler.get_pool(cr.dbname).get('crm.case')
		sale = pooler.get_pool(cr.dbname).get('sale.order')
		partner_addr = pooler.get_pool(cr.dbname).get('res.partner').address_get(cr, uid, [data['form']['partner_id']], ['invoice', 'delivery'])
		pricelist = ir.ir_get(cr, uid,
			[('meta','res.partner'), ('name','product.pricelist')],
			[('id',str(data['form']['partner_id'])), ('uid',str(uid))])[0][2]
		ddata = {
			'origin': 'BO: %s' % str(data['ids'][0]),
			'picking_policy': data['form']['picking_policy'],
			'shop_id': data['form']['shop_id'],
			'state': data['form']['state'],
			'partner_id': data['form']['partner_id'],
			'pricelist_id': pricelist,
			'partner_invoice_id': partner_addr['invoice'],
			'partner_shipping_id': partner_addr['delivery'],
			'order_policy': 'manual',
			'date_order': now(),
		}
		if data['form']['name']:
			ddata['name'] = data['form']['name']
		nid = sale.create(cr, uid, ddata)
		case.write(cr, uid, data['ids'], {'ref': 'sale.order,%s' % nid})
		return {}

	states = {
		'init' : {
			'actions' : [_selectPartner],
			'result' : {'type' : 'form', 'arch' : sale_form, 'fields' : sale_fields, 'state' : [('end', 'Cancel'),('order', 'Make an order')]}
		},
		'order' : {
			'actions' : [_makeOrder],
			'result' : {'type' : 'form', 'arch' : ack_form, 'fields' : ack_fields, 'state' : [('end', 'Ok')]}
		}
	}
make_sale('crm.case.make_order')
