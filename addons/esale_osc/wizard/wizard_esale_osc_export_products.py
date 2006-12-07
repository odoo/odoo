##############################################################################
#
# Copyright (c) 2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

import ir
import time
import os
import netsvc
import xmlrpclib
import netsvc
import pooler
import wizard
from osv import osv

_export_done_form = '''<?xml version="1.0"?>
<form string="Product Export">
	<separator string="Products exported" colspan="4" />
	<field name="prod_new"/>
	<newline/>
	<field name="prod_update"/>
</form>'''

_export_done_fields = {
	'prod_new': {'string':'New products', 'type':'float', 'readonly': True},
	'prod_update': {'string':'Updated products', 'type':'float', 'readonly': True},
}

def _do_export(self, cr, uid, data, context):
	self.pool = pooler.get_pool(cr.dbname)
	website=self.pool.get('esale_osc.web').browse(cr, uid, [data['id']])[0]
	pricelist = website.shop_id.pricelist_id.id
	print "%s/tinyerp-syncro.php" % website.url
	server = xmlrpclib.ServerProxy("%s/tinyerp-syncro.php" % website.url)

	prod_new = 0
	prod_update = 0
	for osc_product in website.product_ids:
		attachs = self.pool.get('ir.attachment').search(cr, uid, [('res_model','=','product.product'), ('res_id', '=',osc_product.product_id.id)])
		data = self.pool.get('ir.attachment').read(cr, uid, attachs)

		category_ids=self.pool.get('esale_osc.category').search(cr, uid, [('web_id','=', website.id), ('category_id', '=', osc_product.product_id.categid)])
		if len(category_ids)>0:
			category_id=category_ids[1]
		else:
			category_id=0

		print [pricelist], osc_product.id, 1, 'list'
		webproduct={
				'product_id'	: osc_product.esale_osc_id,
				'quantity'		: self.pool.get('product.product')._product_virtual_available(cr, uid, [osc_product.product_id.id], '', False, {'shop':website.shop_id.id})[osc_product.product_id.id],
				'model'		: osc_product.product_id.code,
				'price'		: 10, #self.pool.get('product.pricelist').price_get(cr, uid, [pricelist], osc_product.product_id.id, 1, 'list')[pricelist],
				'weight'		: float(osc_product.product_id.weight),
#				'tax_class_id'	: osc_product.esale_osc_tax_id,
				'tax_class_id'	: 1,
				'category_id'	: category_id,
		}
		if len(data):
			webproduct['haspic'] = 1
			webproduct['picture'] = data[0]['datas']
			webproduct['fname'] = data[0]['datas_fname']
		else:
			webproduct['haspic'] =0
			
		langs={}
		products_pool=self.pool.get('product.product')
		for lang in website.language_ids:
			if lang.language_id and lang.language_id.translatable:
				langs[str(lang.esale_osc_id)] = {
					'name': products_pool.read(cr, uid, [osc_product.product_id.id], ['name'], {'lang': lang.language_id.code})[0]['name'] or '',
					'description': products_pool.read(cr, uid, [osc_product.product_id.id], ['description_sale'], {'lang': lang.language_id.code})[0]['description_sale'] or ''
				}

		webproduct['langs'] = langs
		webproduct['name'] = str(osc_product.product_id.name)
		webproduct['description'] = str(osc_product.product_id.description_sale)

		osc_id=server.set_product(webproduct)

		if osc_id!=osc_product.esale_osc_id:
			self.pool.get('esale_osc.product').write(cr, uid, [osc_product.id], {'esale_osc_id': osc_id})
			cr.commit()
			prod_new += 1
		else:
			prod_update += 1

	return {'prod_new':prod_new, 'prod_update':prod_update}

class wiz_esale_osc_products(wizard.interface):

	states = {	'init'	: {	'actions'	: [_do_export],
							'result'	: {	'type'	: 'form',
										'arch'	: _export_done_form,
										'fields': _export_done_fields,
										'state'	: [('end', 'End')]
							}
					}
	}


wiz_esale_osc_products('esale_osc.products');
