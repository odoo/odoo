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
import urllib
import base64

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

def _product_id_to_joomla_id(cr,uid,pool,product,website):
	esale_joomla_id2 = pool.get('esale_joomla.product').search(cr, uid, [('web_id','=',website.id),('product_id','=',product.id)])
	esale_joomla_id = 0
	if esale_joomla_id2:
		esale_joomla_id = pool.get('esale_joomla.product').read(cr, uid, [esale_joomla_id2[0]],["esale_joomla_id"])[0]["esale_joomla_id"]
	return esale_joomla_id
	
def _do_export(self, cr, uid, data, context):
	pool = pooler.get_pool(cr.dbname)
	ids = pool.get('esale_joomla.web').search(cr, uid, [])
	prod_new = 0
	prod_update = 0
	for website in pool.get('esale_joomla.web').browse(cr, uid, ids):

		pricelist = website.shop_id.pricelist_id.id
		if not pricelist:
			raise wizard.except_wizard('UserError', 'You must define a pricelist in your shop !')
		server = xmlrpclib.ServerProxy("%s/tinyerp-synchro.php" % website.url)
		context['lang']=website.language_id.code
		categ_processed = []

		## delete book if necessary : 
		cr.execute("select jp.id, esale_joomla_id from esale_joomla_product jp inner join product_template pt  on pt.id = jp.product_id where pt.categ_id not in (select category_id from esale_joomla_category) ")
		esale_ids= []
		joomla_ids= []
		for res in cr.fetchall():
			esale_ids.append(res[0])
			joomla_ids.append(res[1])
		if joomla_ids : server.unpublish_product(joomla_ids)
		pool.get('esale_joomla.product').unlink(cr,uid,esale_ids)
			
		for categ in website.category_ids:
			if not categ.category_id: continue
			## for product already uploaded via another category we
			## just update the current category :
			if categ.category_id.id in categ_processed :
				prod_ids = pool.get('product.product').search(cr, uid, [('categ_id','in',cat_ids)])
				product_ids = []
				for product in pool.get('product.product').browse(cr, uid, prod_ids, context=context):
					product_ids.append( _product_id_to_joomla_id(cr,uid,pool,product,website))
				server.set_product_category(categ.esale_joomla_id ,product_ids)
				continue
				
			cat_ids = [categ.category_id.id]
			if categ.include_childs:
				def _add_child(cat_ids, categ):
					for child in categ.child_id:
						if child.id not in cat_ids:
							cat_ids.append(child.id)
							_add_child(cat_ids, child)
				_add_child(cat_ids, categ.category_id)
			categ_processed.extend(cat_ids)

			prod_ids = pool.get('product.product').search(cr, uid, [('categ_id','in',cat_ids)])
			for product in pool.get('product.product').browse(cr, uid, prod_ids, context=context):
				
				esale_joomla_id= _product_id_to_joomla_id(cr,uid,pool,product,website)

				price = pool.get('product.pricelist').price_get(cr, uid, [pricelist], product.id, 1, 'list')[pricelist]

				taxes_included=[]
				taxes_name=[]
				for taxe in product.taxes_id:
					for t in website.taxes_included_ids:
						if t.id == taxe.id:
							taxes_included.append(taxe)
				for c in pool.get('account.tax').compute(cr, uid, taxes_included, price, 1): # DELETED product = product 
					price+=c['amount']
					taxes_name.append(c['name'])

				tax_class_id = 1
				webproduct={
					'esale_joomla_id': esale_joomla_id,
					'quantity': pool.get('product.product')._product_virtual_available(cr, uid, [product.id], '', False, {'shop':website.shop_id.id})[product.id],
					'model': product.code or '',
					'price': price,
					'weight': float(0.0),
					'length': float(0.0),
					'width': float(0.0),
					'height': float(0.0),
					'tax_class_id': tax_class_id,
					'category_id': categ.esale_joomla_id,
				}


				attach_ids = pool.get('ir.attachment').search(cr, uid, [('res_model','=','product.product'), ('res_id', '=',product.id)])
				data = pool.get('ir.attachment').read(cr, uid, attach_ids)
				if len(data):
					webproduct['haspic'] = 1
					if not data[0]['link']:
						webproduct['picture'] = data[0]['datas']
					else:
						try:
							webproduct['picture'] = base64.encodestring(urllib.urlopen(data[0]['link']).read())
						except:
							webproduct['haspic'] = 0
					webproduct['fname'] = data[0]['datas_fname']
				else:
					webproduct['haspic'] =0
				
				webproduct['name'] = str(product.name or '')
				webproduct['description'] = str((product.description_sale or '') + (len(taxes_name) and ("\n(" + (', '.join(taxes_name)) + ')') or ''))
				webproduct['short_description'] = str(product.description_sale or '')

				osc_id=server.set_product(webproduct)

				if osc_id!=esale_joomla_id:
					if esale_joomla_id:
						pool.get('esale_joomla.product').write(cr, uid, [esale_joomla_id], {'esale_joomla_id': osc_id})
						prod_update += 1
					else:
						pool.get('esale_joomla.product').create(cr, uid, {'product_id': product.id, 'web_id': website.id, 'esale_joomla_id': osc_id, 'name': product.name })
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

