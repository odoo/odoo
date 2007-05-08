##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: wizard_edi_import.py 1825 2005-12-13 11:04:20Z ede $
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
from edi_exchange import edi_exchange

import wizard
from osv import osv
import pooler

_import_form = '''<?xml version="1.0"?>
<form string="EDI file import">
	<separator string="Import the following files" colspan="4" />
	<field name="ediimportdir" colspan="4" />
	<field name="current" />
	<field name="error" />
</form>'''

_import_fields = { 	'ediimportdir' : {	'string' : 'EDI Import Dir', 
										'type' : 'char', 
										'size' : 100, 
										'default' : lambda *a: '/edi/reception', 
										'required' : True 
									},
					'current' : {		'string' : 'Current',
										'type' : 'boolean',
										'default' : lambda *a: True,
									},
					'error' : {			'string' : 'Error',
										'type' : 'boolean',
										'default' : lambda *a: False,
									},
				}

_import_done_form = '''<?xml version="1.0"?>
<form string="EDI file imported">
	<separator string="EDI file imported" colspan="4" />
</form>'''

_import_done_fields = {}

def _child_of_partner(cr, uid, child, parent):
	if child==parent:
		return True
	direct_parent_list=pooler.get_pool(cr.dbname).get('res.partner').read(cr, uid, [child], ['parent_id'])
	#print str(direct_parent_list)
	if len(direct_parent_list)!=1:
		return False
	if not direct_parent_list[0]['parent_id']:
		return False
	direct_parent=direct_parent_list[0]['parent_id'][0]
	if direct_parent and direct_parent!='':
		return _child_of_partner( cr, uid, direct_parent, parent)
	else:
		return False

def _prepare_import(self, cr, uid, data, context):
	files=[]
	for (type, dir) in [('current', 'encours'), ('error', 'erreur')]:
		if (data['form'][type]):
			edi_path = os.path.join(data['form']['ediimportdir'], dir)
			if not os.path.isdir(edi_path):
				os.makedirs(edi_path)
			for file in os.listdir(edi_path):
				#print file[:9]
				if file[:9]=="COMMANDE.":
					files.append((file, os.path.join(data['form']['ediimportdir'], dir, file)))
	for (filename, file) in files:
		#print "Importing %s" % filename
		FirstInt=True
		FirstOrd=True
		sr = {'sender':None, 'receiver':None}
		sale_orders = []
		log_id=pooler.get_pool(cr.dbname).get('edi.log').create(cr, uid, {})
		logline=pooler.get_pool(cr.dbname).get('edi.log.line')
		logline.create(cr, uid, {
			'log_id': log_id,
			'logdesc': "Checking %s" % filename,
		})
		try:
			status= edi_status()
			fh = open(file, "r")
			for line in fh:
				line_type, line_content = edi_exchange.parse_line(line)
				if line_type == "HINT":
					if not FirstInt:
						sale_orders.append(sale_order_o)
						FirstOrd=True
					sale_order_o = sale_order(cr, uid, sr)
				elif line_type == "HPTY":
					if not FirstOrd:
						FirstInt=False
				elif line_type == "DART":
					FirstOrd=False

				sale_order_o.parse_line(line_type, line_content, status)
				
			sale_orders.append(sale_order_o)

		finally:
			fh.close()

		for (order_id, order_timestamp, sender,  message) in status.messages:
			logline.create(cr, uid, {	'log_id': log_id,
										'logdesc': "\t%s" % message,
										'timestamp': order_timestamp,
										'order_num': order_id
										})
		logline.create(cr, uid, {	'log_id': log_id,
									'logdesc': "Messages:%s\tErrors:%s\tWarnings:%s" % (len(status.messages), status.error_count,  status.warning_count),
								})
		logline.create(cr, uid, {	'log_id': log_id,
									'logdesc': "Finished Checking %s" % filename,
								})

		if status.error_count==0:
			print "Integrating %s" % filename
			logline.create(cr, uid, {	'log_id': log_id,
										'logdesc': "Importing %s" % filename,
									})
			for order in sale_orders:
				order.store()
			logline.create(cr, uid, {	'log_id': log_id,
										'logdesc': "Import Finished",
									})
			if not os.path.isdir(os.path.join(data['form']['ediimportdir'],'archive')):
				os.mkdir(os.path.join(data['form']['ediimportdir'],'archive'))
			os.rename(file, os.path.join(data['form']['ediimportdir'],'archive', filename))
			logline.create(cr, uid, {	'log_id': log_id,
										'logdesc': "Moved %s to archive" % filename,
									})
		else:
			ids=pooler.get_pool(cr.dbname).get('res.users').search(cr,1, [('roles_id', 'ilike', 'EDI')])
			for id in ids:
				pooler.get_pool(cr.dbname).get('res.request').create(cr, uid, {	'act_to': id,
																	'name' : "Error while importing %s" % filename,
																	'ref_doc1' : "edi.log,%s" % log_id,
																	'state' : 'active',
																})
			try:
				os.rename(file, os.path.join(data['form']['ediimportdir'],'erreur', filename))
				logline.create(cr, uid, {	'log_id': log_id,
											'logdesc': "Moved %s to erreur" % filename,
										})
			except:
				logline.create(cr, uid, {	'log_id': log_id,
											'logdesc': "Couldn't move %s to erreur" % filename,
										})
		cr.commit()
	return {}

def _do_import(self, cr, uid, data, context):
	pass

class wiz_edi_import(wizard.interface):
	states = {
		'init' : {
			'actions' : [],
			'result' : { 'type' : 'form', 'arch' : _import_form, 'fields' : _import_fields, 'state' : [('end', 'Cancel'),('check', 'Check EDI')]},
		},
		'check' : {
			'actions' : [ _prepare_import ],
#			'result' : { 'type' : 'print', 'report' : 'edi.import-results', 'state' : [('do_import', 'Import EDI'), ('end', 'End')] },
			'result' : { 'type' : 'form', 'arch' : _import_done_form, 'fields': _import_done_fields, 'state' : [('end','end')]},
		},
		'do_import' : {
			'actions' : [ _do_import ],
			'result' : { 'type' : 'form', 'arch' : _import_done_form, 'fields' : _import_done_fields, 'state' : [('end','end')]},
		},
	}

class sale_order:

	def __init__(self, cr, uid, sr):
		self.cr=cr
		self.uid=uid
		self.shop_id=pooler.get_pool(cr.dbname).get('sale.shop').search(cr, uid, [])[0]
		self.pricelist_id = None
		self.order_lines=[]
		self.partner_id=sr['sender']
		self.partner_order_id=0
		self.partner_invoice_id=0
		self.sr = sr
		self.timesatmp_edi=time.strftime('%Y%m%d%H%M')
		self.ordernum = '0'
		self.deliverdate=None
		self.note = ''

	def store(self):
		if not hasattr(self, 'partner_invoice_id'):
			self.partner_invoice_id = self.partner_id
		if not hasattr(self, 'partner_shipping_id'):
			self.partner_shipping_id = self.partner_invoice_id
		order_id = pooler.get_pool(cr.dbname).get('sale.order').create(self.cr, self.uid, {	'partner_id': self.partner_id,
																				'partner_order_id': self.partner_order_id,
																				'partner_invoice_id': self.partner_invoice_id,
																				'partner_shipping_id': self.partner_shipping_id,
																				'shop_id': self.shop_id,
																				'pricelist_id': self.pricelist_id,
																				'client_order_ref': self.ordernum,
																				'date_order': self.orderdate,
																				'note': self.note,
																			})
		for orderline in self.order_lines:
			orderline.store(order_id)

	def addline(self, line):
		self.orderlines.append(line)

	def parse_line(self, line_type, line_content, status):
		if hasattr(self, "_parse_%s" % line_type):
			myFct=getattr(self, "_parse_%s" % line_type)
			myFct(line_content, status)
		else:
			status.add_warning("ignoring line type: %s" % line_type, self.ordernum, self.timestamp_edi, self.sr['sender'])

	def _parse_HINT(self, line_content, status):
		self.timestamp_edi="%s%s" % (line_content["date"], line_content["time"])
		self.sr['sender'] = line_content['sender']
		
		partners=pooler.get_pool(cr.dbname).get('res.partner').search(self.cr, self.uid, [('ean13','=',line_content["receiver"]),])
		if len(partners) != 1:
			status.add_error("unknown receiver: %s" % line_content["receiver"], self.ordernum, self.timestamp_edi, self.sr['sender'])
		else:
			self.sr['receiver']=partners[0]
			thisadd=pooler.get_pool(cr.dbname).get('res.users').read(self.cr, self.uid, [self.uid], ['address_id'])[0]['address_id'][0]
			partner=pooler.get_pool(cr.dbname).get('res.partner.address').read(self.cr, self.uid, [thisadd], ['partner_id'])[0]['partner_id'][0]
			if not partner or partner!=self.sr['receiver']:
				status.add_error("This message is not for us (%s)" % line_content["receiver"], self.ordernum, self.timestamp_edi, self.sr['sender'])

	def _parse_HGEN(self, line_content, status):
		if line_content["order-num"]=='':
			status.add_error("No client order reference", self.ordernum, self.timestamp_edi, self.sr['sender'])
		self.ordernum=line_content["order-num"]
		self.orderdate=line_content["order-date"]
		if line_content["message-type"]!="ORDERS93A" and line_content["message-type"]!="ORDERS96A" and line_content["message-type"]!="GENCOD02303" and line_content["message-type"]!="GENCOD08604":
			status.add_error("Unknown message type %s" % line_content["message-type"], self.ordernum, self.timestamp_edi, self.sr['sender'])

	def _parse_HDEL(self, line_content, status):
		if (not self.deliverdate or self.deliverdate > line_content['deliv-date']) and line_content['deliv-q'] in ('137', '200'):
			self.deliverdate = line_content['deliv-date']
		if self.deliverdate < self.orderdate:
			status.add_error("%s (order date) is after %s (delivery date)" % (self.orderdate,self.deliverdate), self.ordernum, self.timestamp_edi, self.sr['sender'])

	def _parse_HPTY(self, line_content, status):
		partner_table = pooler.get_pool(cr.dbname).get('res.partner')
		
		partners = partner_table.search(self.cr, self.uid, [('ean13', '=', line_content['partner-code'])])
		if partners and len(partners) == 1:
			default_addresses = pooler.get_pool(cr.dbname).get('res.partner.address').search(self.cr, self.uid, [('partner_id', '=', partners[0]), ('type', 'ilike', 'default')])
			if not default_addresses:
				default_addresses = pooler.get_pool(cr.dbname).get('res.partner.address').search(self.cr, self.uid, [('partner_id', '=', partners[0]), ('type', 'ilike', '')])
			if not default_addresses:
				default_addresses = pooler.get_pool(cr.dbname).get('res.partner.address').search(self.cr, self.uid, [('partner_id', '=', partners[0])])
			self.hpty_dispatchers[line_content['partner-type']](self, partners[0], default_addresses, line_content, status)
		else:
			status.add_error("unknown %s: %s" % (line_content["partner-type"], line_content["partner-code"]), self.ordernum, self.timestamp_edi, self.sr['sender'])
	
	def _parse_HPTYBY(self, partner, default_addresses, line_content, status):
		partner_table = pooler.get_pool(cr.dbname).get('res.partner')

		self.sr['sender'] = partner
		self.partner_id = partner
		self.partner_order_id = default_addresses[0]
		self.pricelist_id = ir.ir_get(self.cr, self.uid, 'meta', 'product.pricelist', [('res.partner', self.partner_id)])[0][2]
		orders=pooler.get_pool(cr.dbname).get("sale.order").search(self.cr, self.uid, [('client_order_ref', 'ilike', self.ordernum), ('partner_order_id',"=",self.partner_order_id)])
		if orders and len(orders)>0:
			status.add_warning("This client order reference (%s) already exists for this client" % self.ordernum, self.ordernum, self.timestamp_edi, self.sr['sender'])
	
	def _parse_HPTYSU(self, partner, default_addresses, line_content, status):
		partner_table = pooler.get_pool(cr.dbname).get('res.partner')
		if not (partner_table._is_related_to(self.cr, self.uid, [partner], self.sr['receiver'])[0] or self.sr['receiver'] == partner):
			status.add_error("unknown %s: %s" % (line_content["partner-type"], line_content["partner-code"]), self.ordernum, self.timestamp_edi, self.sr['sender'])
	
	def _parse_HPTYDP(self, partner, default_addresses, line_content, status):
		shipping_addresses=pooler.get_pool(cr.dbname).get('res.partner.address').search(self.cr, self.uid, [('partner_id','=',partner), ('type', 'ilike', 'delivery')])
		if len(shipping_addresses) < 1:
			self.partner_shipping_id=default_addresses[0]
		else:
			self.partner_shipping_id=shipping_addresses[0]

		invoice_addresses=pooler.get_pool(cr.dbname).get('res.partner.address').search(self.cr, self.uid, [('partner_id','=',partner), ('type', 'ilike', 'invoice')])
		if len(invoice_addresses) < 1:
			self.partner_invoice_id=default_addresses[0]
		else:
			self.partner_invoice_id=invoice_addresses[0]
	
	def _parse_HPTYIV(self, partner, default_addresses, line_content, status):
		invoice_addresses=pooler.get_pool(cr.dbname).get('res.partner.address').search(self.cr, self.uid, [('partner_id','=',partner), ('type', 'ilike', 'invoice')])
		if len(invoice_addresses) < 1:
			self.partner_invoice_id=default_addresses[0]
		else:
			self.partner_invoice_id=invoice_addresses[0]
	
	hpty_dispatchers = { 'BY' : _parse_HPTYBY, 'SU' : _parse_HPTYSU, 'DP' : _parse_HPTYDP, 'IV' : _parse_HPTYIV }

	def _parse_HFTX(self, line_content, status):
		self.note+=line_content['text']+'\n'

	def _parse_DART(self, line_content, status):
		products=pooler.get_pool(cr.dbname).get('product.product').search(self.cr, self.uid, [('ean13','=',line_content["barcode"]),])
		#sale_order_line_o=sale_order_line(self.cr, self.uid, self.deliverdate, self.partner_invoice_id, status)
		sale_order_line_o=sale_order_line(self.cr, self.uid, self, self.deliverdate)
		if len(products) != 1:
			status.add_error("unknown product: %s" % line_content["barcode"], self.ordernum, self.timestamp_edi, self.sr['sender'])
			return
		else:
			sale_order_line_o.product=products[0]
		sale_order_line_o.product_ean=line_content["barcode"]
		if (line_content["unit21"]==''):
			status.add_warning("Using default Unit Of Measure", self.ordernum, self.timestamp_edi, self.sr['sender'])
		else:
			uoms=pooler.get_pool(cr.dbname).get('product.uom').search(self.cr, self.uid, [('name', 'ilike', line_content["unit21"]),])
			if len(uoms) != 1:
				status.add_error("unknown uom: %s" % line_content["unit21"], self.ordernum, self.timestamp_edi, self.sr['sender'])
				return
			else:
				sale_order_line_o.uom=uoms[0]
		sale_order_line_o.quantity=float(line_content["quantity21"])
		sale_order_line_o.uoc_quantity=float(line_content["quantity59"])
		sale_order_line_o.lineid=line_content["line-num"]
		sale_order_line_o.partner_address=None
		sale_order_line_o.price=line_content["price"]
		if sale_order_line_o.partner==0:
			partner=self.partner_id
		else:
			partner=sale_order_line_o.partner
		pricelist_id = ir.ir_get(self.cr, self.uid, 'meta', 'product.pricelist', [('res.partner', partner)])[0][2]
		sale_order_line_o.price = pooler.get_pool(cr.dbname).get('product.pricelist').price_get(self.cr, self.uid, [pricelist_id], sale_order_line_o.product, sale_order_line_o.quantity)[pricelist_id]
		sale_order_line_o.pricelist_id=pricelist_id
		if float(line_content["price"])!=sale_order_line_o.price:
			status.add_warning("Price from EDI (%s) different from what we have (%s) for product %s" % (str(float(line_content["price"])), sale_order_line_o.price, line_content["barcode"]), self.ordernum, self.timestamp_edi, self.sr['sender'])
		product_infos = pooler.get_pool(cr.dbname).get('product.product').read(self.cr, self.uid, [sale_order_line_o.product])[0]
		if line_content['price-unit']=="":
			status.add_warning("Blank Unit Of Price for product %s should be %s" % (line_content['barcode'], product_infos['uos_id'][1]), self.ordernum, self.timestamp_edi, self.sr['sender'])
			sale_order_line_o.price_unit= product_infos['uos_id'][0]
		elif product_infos['uos_id'][1] != line_content['price-unit']:
			status.add_error('Invalid Unit Of Price for product %s Should be "%s" instead of "%s"' % (line_content['barcode'], product_infos['uos_id'][1], line_content["price-unit"]), self.ordernum, self.timestamp_edi, self.sr['sender'])
		else:
			sale_order_line_o.price_unit= product_infos['uos_id'][0]
		sale_order_line_o.price_unit_customer=float(line_content['hint-price'])
		sale_order_line_o.check(status)
		self.order_lines.append(sale_order_line_o)

	def _parse_DDEL(self, line_content, status):
		sale_order_line_o = self.order_lines[len(self.order_lines)-1]
		sale_order_line_o.deliv_date = "%s%s" % (line_content["deliv-date"], line_content["deliv-time"])

	def _parse_DPTY(self, line_content, status):
		if len(self.order_lines)<1:
			status.add_error("no DART line parsed before this DPTY line", self.ordernum, self.timestamp_edi, self.sr['sender'])
		else:
			sale_order_line_o = self.order_lines[len(self.order_lines)-1]
			partners=pooler.get_pool(cr.dbname).get('res.partner').search(self.cr, self.uid, [('ean13','=',line_content["shop-barcode"]),])
			if len(partners) != 1:
				status.add_error("unknown address: %s" % line_content["shop-barcode"], self.ordernum, self.timestamp_edi, self.sr['sender'])
			elif not _child_of_partner(self.cr, self.uid, partners[0], self.sr['sender']):
				status.add_error("unknown address: %s" % line_content["shop-barcode"], self.ordernum, self.timestamp_edi, self.sr['sender'])
			else:
				sale_order_line_o.partner_address=partners[0]

	def _parse_DPID(self, line_content, status):
		if len(self.order_lines)<1:
			status.add_error("no DART line parsed before this DPTY line", self.ordernum, self.timestamp_edi, self.sr['sender'])
		else:
			sale_order_line_o = self.order_lines[len(self.order_lines)-1]
			sale_order_line_o.note+=line_content['ident-art']+'\n'

	def _parse_DFTX(self, line_content, status):
		if len(self.order_lines)<1:
			status.add_error("no DART line parsed before this DPTY line", self.ordernum, self.timestamp_edi, self.sr['sender'])
		else:
			sale_order_line_o = self.order_lines[len(self.order_lines)-1]
			sale_order_line_o.note+=line_content['text']+'\n'


class sale_order_line:

	def __init__(self, cr, uid, sale_order_o, deliv_date):
	#, partner_address, status):
		self.cr=cr
		self.uid=uid
		self.insertdict={}
		self.partner_address=None
		if deliv_date:
			self.deliv_date=deliv_date
		self.note=''
		self.product=0
		self.sale_order= sale_order_o
		self.price_unit=0
		if sale_order_o.partner_invoice_id!=0:
			self.partner=pooler.get_pool(cr.dbname).get('res.partner.address').read(self.cr, self.uid, [sale_order_o.partner_invoice_id], ['partner_id'])[0]['partner_id'][0]
		else:
			self.partner=0
		#self.status=status

	def check(self, status):
		self.cr.execute('select id from product_packaging where product_id=%d and qty=%f limit 1', (self.product, float(self.uoc_quantity)))
		packs = self.cr.fetchone()
		if packs is None or not len(packs):
			status.add_error('Invalid package for product %s (%s)' % (self.product_ean, float(self.uoc_quantity)), self.sale_order.ordernum, self.sale_order.timestamp_edi, self.sale_order.sr['sender'])
		else:
			self.pack_id=packs[0]
		
		#print "PriceList: %s, product: %s, quantity: %s " % (self.pricelist_id, self.product, self.quantity)
		try:
			dico=pooler.get_pool(cr.dbname).get('sale.order.line').product_id_change(self.cr, self.uid, [], self.pricelist_id, self.product, int(float(self.quantity)))
			self.insertdict.update({'product_uos_qty': dico['value']['product_uos_qty'], 'product_uos': dico['value']['product_uos'][0], 'price_unit': dico['value']['price_unit']})
		except:
			status.add_error('No price defined for product %s, line ommited !' % (self.product_ean,), self.sale_order.ordernum, self.sale_order.timestamp_edi, self.sale_order.sr['sender'])
		#print str(dico)
		# Checking the unit used for the price computation
#		product_infos = pooler.get_pool(cr.dbname).get('product.product').read(self.cr, self.uid, [self.product])[0]
#		if product_infos['uos_id'][1] != self.price_unit:
#			status.add_warning('Invalid unit for Sale price : Should be "%s"' % product_infos['uos_id'][1], self.sale_order.ordernum, self.sale_order.timestamp_edi, self.sale_order.sr['sender'])
		
		# Checking the price

#		if unit_price != self.price:
#			status.add_warning('Invalid price', self.sale_order.ordernum, self.sale_order.timestamp_edi, self.sale_order.sr['sender'])

	def store (self, order_id):
		insertdict.update( {	'order_id': order_id,
						'product_id': self.product,
						'product_uom_qty': self.quantity,
						'name': "%s%s" %(order_id, self.lineid),
						'address_allotment_id': self.partner_address,
						'notes': self.note,
						'product_packaging': self.pack_id,
#						'unit_price': self.price_unit,
						'price_unit': self.price,
						'price_unit_customer': self.price_unit_customer,
					})
		self.unit_price=self.price
		if hasattr(self, 'uom'):
			insertdict['product_uom'] = self.uom
		else:
			insertdict['product_uom'], desc = pooler.get_pool(cr.dbname).get('product.product').read(self.cr, self.uid, [self.product], ['uom_id'])[0]['uom_id']
		if hasattr(self, 'deliv_date'):
			insertdict['date_planned'] = self.deliv_date
		id=pooler.get_pool(cr.dbname).get('sale.order.line').create(self.cr, self.uid, insertdict)
		return id

class edi_status:
	def __init__(self):
		self.error_count=0
		self.warning_count=0
		self.messages=[]

	def add_error(self, message, order_id, timestamp_edi, sender):
		self.messages.append((order_id, timestamp_edi, sender, "ERROR:\t%s" % message))
		self.error_count+=1

	def add_warning(self, message, order_id, timestamp_edi, sender):
		self.messages.append((order_id, timestamp_edi, sender, "WARNING:\t%s" % message))
		self.warning_count+=1

wiz_edi_import('edi.import')


