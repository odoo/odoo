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
<form string="Initial import">
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
	ids = self.pool.get('esale_joomla.web').search(cr, uid, [])
	for website in self.pool.get('esale_joomla.web').browse(cr, uid, ids):
		pricelist = website.shop_id.pricelist_id.id
		if not pricelist:
			raise wizard.except_wizard('UserError', 'You must define a pricelist in your shop !')
		server = xmlrpclib.ServerProxy("%s/tinyerp-synchro.php" % website.url)
		print 'SERVER', "%s/tinyerp-synchro.php" % website.url

		prod_new = 0
		prod_update = 0

		for categ in website.category_ids:
			if not categ.category_id:
				print 'Skipping Category', categ.name, categ.id
				continue
			cat_ids = [categ.category_id.id]
			if categ.include_childs:
				pass
			#
			# Use cat_ids and compute for childs
			#
			prod_ids = self.pool.get('product.product').search(cr, uid, [('categ_id','=',categ.category_id.id)])
			for product in self.pool.get('product.product').browse(cr, uid, prod_ids):

				category_id=categ.id

				esale_joomla_id2 = self.pool.get('esale_joomla.product').search(cr, uid, [('web_id','=',website.id),('product_id','=',product.id)])
				esale_joomla_id = 0
				if esale_joomla_id2:
					esale_joomla_id = self.pool.get('esale_joomla.product').browse(cr, uid, esale_joomla_id2[0]).esale_joomla_id

				tax_class_id = 1
				print [pricelist], product.id, 1, 'list'
				webproduct={
					'esale_joomla_id'	: esale_joomla_id or 0,
					'quantity'		: self.pool.get('product.product')._product_virtual_available(cr, uid, [product.id], '', False, {'shop':website.shop_id.id})[product.id],
					'model'			: product.code or '',
					'price'			: 10.0, #self.pool.get('product.pricelist').price_get(cr, uid, [pricelist], product.id, 1, 'list')[pricelist],
					'weight'		: float(product.weight),
					'tax_class_id'	: tax_class_id,
					'category_id'	: category_id,
				}

				attach_ids = self.pool.get('ir.attachment').search(cr, uid, [('res_model','=','product.product'), ('res_id', '=',product.id)])
				data = self.pool.get('ir.attachment').read(cr, uid, attach_ids)
				if len(data):
					webproduct['haspic'] = 1
					webproduct['picture'] = data[0]['datas']
					webproduct['fname'] = data[0]['datas_fname']
				else:
					webproduct['haspic'] =0
				
				langs={}
				products_pool=pooler.get_pool(cr.dbname).get('product.product')
				for lang in website.language_ids:
					if lang.language_id and lang.language_id.translatable:
						langs[str(lang.esale_joomla_id)] = {
							'name': products_pool.read(cr, uid, [osc_product.product_id.id], ['name'], {'lang': lang.language_id.code})[0]['name'] or '',
							'description': products_pool.read(cr, uid, [osc_product.product_id.id], ['description_sale'], {'lang': lang.language_id.code})[0]['description_sale'] or ''
						}

				webproduct['langs'] = langs
				webproduct['name'] = str(product.name or '')
				webproduct['description'] = str(product.description_sale or '')

				print webproduct

				osc_id=server.set_product(webproduct)

				print osc_id
				if osc_id!=webproduct['esale_joomla_id']:
					if esale_joomla_id2:
						self.pool.get('esale_joomla.product').write(cr, uid, [esale_joomla_id2[0]], {'esale_joomla_id': osc_id})
						print 'Changing', webproduct['esale_joomla_id'], 'to', osc_id
						prod_update += 1
					else:
						self.pool.get('esale_joomla.product').create(cr, uid, {
							'product_id': product.id,
							'web_id': website.id,
							'esale_joomla_id': osc_id,
							'name': product.name
						})
						prod_new += 1
				else:
					prod_update += 1
	return {'prod_new':prod_new, 'prod_update':prod_update}

class wiz_esale_joomla_products(wizard.interface):
	states = {
		'init': {
			'actions': [_do_export],
			'result': {'type': 'form', 'arch': _export_done_form, 'fields': _export_done_fields, 'state': [('end', 'End')] }
		}
	}
wiz_esale_joomla_products('esale_joomla.products');
