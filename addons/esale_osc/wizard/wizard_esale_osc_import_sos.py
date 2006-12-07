import ir
import time
import os
import netsvc
import xmlrpclib
import pooler
import wizard
from osv import osv

_import_form = '''<?xml version="1.0"?>
<form title="Categories import" />
'''

_import_fields = {}

_import_done_form = '''<?xml version="1.0"?>
<form title="Saleorders import">
<separator string="saleorders succesfully imported" colspan="4" />
</form>'''

_import_done_fields = {}

def _do_import(self, cr, uid, data, context):
	self.pool = pooler.get_pool(cr.dbname)
	website = self.pool.get('esale_osc.web').browse(cr, uid, data['id'])

	server = xmlrpclib.ServerProxy("%s/tinyerp-syncro.php" % website.url)

	cr.execute("select max(esale_osc_id) from sale_order where esale_osc_web=%s;" % str(website.id))
	max_web_id=cr.fetchone()[0]
	min_openorder=-1
	if max_web_id:
		saleorders = server.get_saleorders(max_web_id)
		min_openorder = server.get_min_open_orders(max_web_id)
	else:
		saleorders = server.get_saleorders(0)

	for saleorder in saleorders:
		print str(saleorder)
		value={	'esale_osc_web'	: website.id,
				'esale_osc_id'	: saleorder['id'],
				'shop_id'		: website.shop_id.id,
				'partner_id'	: website.partner_anonymous_id.id,
			}
		saleorder_pool=self.pool.get('sale.order')
		value.update(saleorder_pool.onchange_shop_id(cr, uid, [], value['shop_id'])['value'])
		value.update(saleorder_pool.onchange_partner_id(cr, uid, [], value['partner_id'])['value'])
		addresses_pool = self.pool.get('res.partner.address')
		for address in [('address','order'), ('billing', 'invoice'), ('delivery', 'shipping')]:
			criteria = [('partner_id', '=', website.partner_anonymous_id.id)]
			insert = {'partner_id': website.partner_anonymous_id.id}
			for criterium in [('city', 'city'), ('name', 'name'), ('zip','zip'), ('address', 'street') ]:
				criteria.append((criterium[1], 'like', saleorder[address[0]][criterium[0]]))
				insert[criterium[1]]=saleorder[address[0]][criterium[0]]
			address_ids=addresses_pool.search(cr, uid, criteria)
			if len(address_ids):
				id=address_ids[0]
			else:
				country_ids=self.pool.get('res.country').search(cr, uid, [('name', 'ilike', saleorder[address[0]]['country'])])
				if len(country_ids):
					country_id=country_ids[0]
				else:
					country_id=self.pool.get('res.country').create(cr, uid, {	'name'	: saleorder[address[0]]['country'],
																					'code'	: saleorder[address[0]]['country'][0:2].lower()})
				insert['country_id']=country_id
				if address[0]=='address':
					insert['email']=saleorder['address']['email']
				id=addresses_pool.create(cr, uid, insert)
				
			value.update({'partner_%s_id' % address[1]: id})
				
		order_id=saleorder_pool.create(cr, uid, value)
		for orderline in saleorder['lines']:
			ids=self.pool.get('esale_osc.product').search(cr, uid, [('esale_osc_id', '=', orderline['product_id']), ('web_id', '=', website.id)])
			if len(ids):
				osc_product_id=ids[0]
				osc_product=self.pool.get('esale_osc.product').browse(cr, uid, osc_product_id)
				linevalue={	'product_id'	: osc_product.product_id.id,
						'product_uom_qty'	: orderline['product_qty'],
						'order_id'		: order_id
				}
				linevalue.update(self.pool.get('sale.order.line').product_id_change(cr, uid, [], value['pricelist_id'], linevalue['product_id'], linevalue['product_uom_qty'])['value'])
				linevalue.update(self.pool.get('sale.order.line').default_get(cr, uid, ['sequence', 'invoiced', 'state', 'product_packaging']))
				del linevalue['weight']
				linevalue["product_uos"]= linevalue['product_uos'][0]
				tax_id=linevalue['tax_id'][0]
				del linevalue['tax_id']
				ids=self.pool.get('sale.order.line').create(cr, uid, linevalue)
				cr.execute('insert into sale_order_tax (order_line_id,tax_id) values (%d,%d)', (ids, tax_id))
	cr.commit()
	for saleorder in saleorders:
		server.process_order(saleorder['id'])

	###################### look for open orders in site that are 'done' in TinyERP ###################
	######################                and close them                           ###################
	if (min_openorder > -1):
		cr.execute("select esale_osc_id from sale_order where (esale_osc_id>=%d) and (state = 'done') and (esale_osc_web=%d);", (min_openorder,website.id))
		openorders=cr.fetchall()
		for openorder in openorders:
			server.close_open_orders(openorder[0])
	return {}

class wiz_esale_osc_import_sos(wizard.interface):

	states = {	'init'	: {	'actions'	: [_do_import],
							'result'	: {	'type'	: 'form',
											'arch'	: _import_done_form,
											'fields': _import_done_fields,
											'state'	: [('end', 'End')]
											}
							}
				}


wiz_esale_osc_import_sos('esale_osc.saleorders');
