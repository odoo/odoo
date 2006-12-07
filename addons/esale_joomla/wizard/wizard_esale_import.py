import netsvc
import ir
import time
import os
import netsvc
import xmlrpclib
import pooler

import wizard
from osv import osv

_import_done_fields = {
	'num': {'string':'New Sales Orders', 'readonly':True, 'type':'integer'}
}

_import_done_form = '''<?xml version="1.0"?>
<form string="Saleorders import">
	<separator string="eSale Orders imported" colspan="4" />
	<field name="num"/>
</form>'''

def _do_import(self, cr, uid, data, context):
	self.pool = pooler.get_pool(cr.dbname)
	ids = self.pool.get('esale_joomla.web').search(cr, uid, [])
	total = 0
	for website in self.pool.get('esale_joomla.web').browse(cr, uid, ids):
		server = xmlrpclib.ServerProxy("%s/tinyerp-synchro.php" % website.url)

		cr.execute("select max(web_ref) from esale_joomla_order where web_id=%d", (website.id,))
		max_web_id=cr.fetchone()[0]

		saleorders = server.get_saleorders(max_web_id or 0)
		for so in saleorders:
			total += 1
			pids = self.pool.get('esale_joomla.partner').search(cr, uid, [('esale_id','=',so['delivery']['esale_id'])])
			if pids:
				adr_ship = pids[0]
				self.pool.get('esale_joomla.partner').write(cr, uid, pids, so['delivery'] )
			else:
				adr_ship = self.pool.get('esale_joomla.partner').create(cr, uid, so['delivery'] )

			pids = self.pool.get('esale_joomla.partner').search(cr, uid, [('esale_id','=',so['billing']['esale_id'])])
			if pids:
				adr_bill = pids[0]
				self.pool.get('esale_joomla.partner').write(cr, uid, pids, so['billing'] )
			else:
				adr_bill = self.pool.get('esale_joomla.partner').create(cr, uid, so['billing'] )

			order_id=self.pool.get('esale_joomla.order').create(cr, uid, {
				'web_id': website.id,
				'web_ref': so['id'],
				'name': so['id'],
				'date_order': so['date'] or time.strftime('%Y-%m-%d'),
				'note': so['note'] or '',
				'epartner_shipping_id': adr_ship,
				'epartner_invoice_id': adr_bill,
			})

			for orderline in so['lines']:
				print orderline, website.id
				ids=self.pool.get('esale_joomla.product').search(cr, uid, [('esale_joomla_id', '=', orderline['product_id']), ('web_id', '=', website.id)])

				print 'Products', ids
				if len(ids):
					osc_product_id=ids[0]
					osc_product=self.pool.get('esale_joomla.product').browse(cr, uid, osc_product_id)
					a = {
						'product_id': osc_product.product_id.id,
						'product_qty': orderline['product_qty'],
						'name': osc_product.name,
						'order_id': order_id,
						'product_uom_id': osc_product.product_id.uom_id.id,
						'price_unit': orderline['price'],
					}
					print '-'*50
					print a
					self.pool.get('esale_joomla.order.line').create(cr, uid, {
						'product_id': osc_product.product_id.id,
						'product_qty': orderline['product_qty'],
						'name': osc_product.name,
						'order_id': order_id,
						'product_uom_id': osc_product.product_id.uom_id.id,
						'price_unit': orderline['price'],
					})
		cr.commit()
	return {'num':total}

class wiz_esale_joomla_import_sos(wizard.interface):
	states = {
		'init': {
			'actions': [_do_import],
			'result': {
				'type': 'form',
				'arch': _import_done_form,
				'fields': _import_done_fields,
				'state': [('end', 'End')]
			}
		}
	}
wiz_esale_joomla_import_sos('esale_joomla.saleorders');
