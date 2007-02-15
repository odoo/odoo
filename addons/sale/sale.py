##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: sale.py 1005 2005-07-25 08:41:42Z nicoe $
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
import netsvc
from osv import fields, osv
import ir
from mx import DateTime
from tools import config

class sale_shop(osv.osv):
	_name = "sale.shop"
	_description = "Sale Shop"
	_columns = {
		'name': fields.char('Shop name',size=64, required=True),
		'payment_default_id': fields.many2one('account.payment.term','Default Payment Term',required=True),
		'payment_account_id': fields.many2many('account.account','sale_shop_account','shop_id','account_id','Payment accounts'),
		'warehouse_id': fields.many2one('stock.warehouse','Warehouse'),
		'pricelist_id': fields.many2one('product.pricelist', 'Pricelist'),
		'project_id': fields.many2one('account.analytic.account', 'Analytic Account'),
	}
sale_shop()

def _incoterm_get(self, cr, uid, context={}):
	cr.execute('select code, code||\', \'||name from stock_incoterms where active')
	return cr.fetchall()

class sale_order(osv.osv):
	_name = "sale.order"
	_description = "Sale Order"
	def copy(self, cr, uid, id, default=None,context={}):
		if not default:
			default = {}
		default.update({
			'state':'draft',
			'shipped':False,
			'invoiced':False,
			'invoice_ids':[],
			'picking_ids':[],
			'name': self.pool.get('ir.sequence').get(cr, uid, 'sale.order'),
		})
		return super(sale_order, self).copy(cr, uid, id, default, context)

	def _amount_untaxed(self, cr, uid, ids, field_name, arg, context):
		id_set = ",".join(map(str, ids))
		cr.execute("SELECT s.id,COALESCE(SUM(l.price_unit*l.product_uos_qty*(100-l.discount))/100.0,0) AS amount FROM sale_order s LEFT OUTER JOIN sale_order_line l ON (s.id=l.order_id) WHERE s.id IN ("+id_set+") GROUP BY s.id ")
		res = dict(cr.fetchall())
		cur_obj=self.pool.get('res.currency')
		for id in res.keys():
			order=self.browse(cr, uid, [id])[0]
			cur=order.pricelist_id.currency_id
			res[id]=cur_obj.round(cr, uid, cur, res[id])
		return res

	def _amount_tax(self, cr, uid, ids, field_name, arg, context):
		res = {}
		cur_obj=self.pool.get('res.currency')
		for order in self.browse(cr, uid, ids):
			val = 0.0
			cur=order.pricelist_id.currency_id
			for line in order.order_line:
				for c in self.pool.get('account.tax').compute(cr, uid, line.tax_id, line.price_unit * (1-(line.discount or 0.0)/100.0), line.product_uos_qty, order.partner_invoice_id.id, line.product_id, order.partner_id):
					val+= cur_obj.round(cr, uid, cur, c['amount'])
			res[order.id]=cur_obj.round(cr, uid, cur, val)
		return res

	def _amount_total(self, cr, uid, ids, field_name, arg, context):
		res = {}
		untax = self._amount_untaxed(cr, uid, ids, field_name, arg, context) 
		tax = self._amount_tax(cr, uid, ids, field_name, arg, context)
		cur_obj=self.pool.get('res.currency')
		for id in ids:
			order=self.browse(cr, uid, [id])[0]
			cur=order.pricelist_id.currency_id
			res[id] = cur_obj.round(cr, uid, cur, untax.get(id, 0.0) + tax.get(id, 0.0))
		return res

	_columns = {
		'name': fields.char('Order Description', size=64, required=True, select=True),
		'shop_id':fields.many2one('sale.shop', 'Shop', required=True, readonly=True, states={'draft':[('readonly',False)]}),
		'origin': fields.char('Origin', size=64),
		'client_order_ref': fields.char('Partner Ref.',size=64),

		'state': fields.selection([
			('draft','Quotation'),
			('waiting_date','Waiting Schedule'),
			('manual','Manual in progress'),
			('progress','In progress'),
			('shipping_except','Shipping Exception'),
			('invoice_except','Invoice Exception'),
			('done','Done'),
			('cancel','Cancel')
		], 'Order State', readonly=True, help="Gives the state of the quotation or sale order. The exception state are automatically setted when a cancel operation occurs in the invoice validation (Invoice Exception) or in picking list process (Shipping Exception). The 'Waiting Schedule' state is set when the invoice is confirmed but waiting the 'Date Order' the schedule.", select=True),
		'date_order':fields.date('Date Ordered', required=True, readonly=True, states={'draft':[('readonly',False)]}),

		'user_id':fields.many2one('res.users', 'Salesman', states={'draft':[('readonly',False)]}, relate=True, select=True),
		'partner_id':fields.many2one('res.partner', 'Partner', readonly=True, states={'draft':[('readonly',False)]}, change_default=True, relate=True, select=True),
		'partner_invoice_id':fields.many2one('res.partner.address', 'Invoice Address', readonly=True, required=True, states={'draft':[('readonly',False)]}),
		'partner_order_id':fields.many2one('res.partner.address', 'Ordering Contact', readonly=True, required=True, states={'draft':[('readonly',False)]}, help="The name and address of the contact that requested the order or quotation."),
		'partner_shipping_id':fields.many2one('res.partner.address', 'Shipping Address', readonly=True, required=True, states={'draft':[('readonly',False)]}),

		'incoterm': fields.selection(_incoterm_get, 'Incoterm',size=3),
		'picking_policy': fields.selection([('direct','Direct Delivery'),('one','All at once')], 'Picking Policy', required=True ),
		'order_policy': fields.selection([
			('prepaid','Invoice before delivery'),
			('manual','Shipping & Manual Invoice'),
			('postpaid','Automatic Invoice after delivery'),
			('picking','Invoice from the pickings'),
		], 'Shipping Policy', required=True, readonly=True, states={'draft':[('readonly',False)]}, help="The Shipping Policy is used to synchronise invoive and delivery operations. The 'Pay before delivery' choice will first generate the invoice and then generate the picking order after the payment of this invoice. The 'Shipping & Manual Invoice' will create the picking order directly and wait the user to manually click on the 'Invoice Button' to generate the draft invoice. The 'Invoice after delivery' choice will generate the draft invoice after the picking list have been finnished"),
		'pricelist_id':fields.many2one('product.pricelist', 'Pricelist', required=True, readonly=True, states={'draft':[('readonly',False)]}),
		'project_id':fields.many2one('account.analytic.account', 'Profit/Cost Center', readonly=True, states={'draft':[('readonly', False)]}),

		'order_line': fields.one2many('sale.order.line', 'order_id', 'Order Lines', readonly=True, states={'draft':[('readonly',False)]}),
		'payment_line': fields.one2many('sale.order.payment', 'order_id', 'Order Payments', readonly=True, states={'draft':[('readonly',False)]}),

		'invoice_ids': fields.many2many('account.invoice', 'sale_order_invoice_rel', 'order_id', 'invoice_id', 'Invoice', help="This is the list of invoices that have been generated for this sale order. The same sale order may have been invoiced in several times (by line for example)."),
		'picking_ids': fields.one2many('stock.picking', 'sale_id', 'Picking List', readonly=True, help="This is the list of picking list that have been generated for this invoice"),

		'shipped':fields.boolean('Picked', readonly=True),
		'invoiced':fields.boolean('Paid', readonly=True),

		'note': fields.text('Notes'),

		'amount_untaxed': fields.function(_amount_untaxed, method=True, string='Untaxed Amount'),
		'amount_tax': fields.function(_amount_tax, method=True, string='Taxes'),
		'amount_total': fields.function(_amount_total, method=True, string='Total'),
		'invoice_quantity': fields.selection([('order','Ordered Quantities'),('procurement','Shipped Quantities')], 'Invoice on', help="The sale order will automatically create the invoice proposition (draft invoice). Ordered and delivered quantities may not be the same. You have to choose if you invoice based on ordered or shipped quantities. If the product is a service, shipped quantities means hours spent on the associated tasks."),
	}
	_defaults = {
		'picking_policy': lambda *a: 'direct',
		'date_order': lambda *a: time.strftime('%Y-%m-%d'),
		'order_policy': lambda *a: 'manual',
		'state': lambda *a: 'draft',
		'user_id': lambda obj, cr, uid, context: uid,
		'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'sale.order'),
		'invoice_quantity': lambda *a: 'order'
	}
	_order = 'name desc'

	# Form filling
	def onchange_shop_id(self, cr, uid, ids, shop_id):
		v={}
		if shop_id:
			shop=self.pool.get('sale.shop').browse(cr,uid,shop_id)
			v['project_id']=shop.project_id.id
			# Que faire si le client a une pricelist a lui ?
			if shop.pricelist_id.id:
				v['pricelist_id']=shop.pricelist_id.id
			#v['payment_default_id']=shop.payment_default_id.id
		return {'value':v}

	def action_cancel_draft(self, cr, uid, ids, *args):
		if not len(ids):
			return False
		cr.execute('select id from sale_order_line where order_id in ('+','.join(map(str, ids))+')', ('draft',))
		line_ids = map(lambda x: x[0], cr.fetchall())
		self.write(cr, uid, ids, {'state':'draft', 'invoice_ids':[], 'shipped':0, 'invoiced':0})
		self.pool.get('sale.order.line').write(cr, uid, line_ids, {'invoiced':False, 'state':'draft', 'invoice_lines':[(6,0,[])]})
		wf_service = netsvc.LocalService("workflow")
		for inv_id in ids:
			wf_service.trg_create(uid, 'sale.order', inv_id, cr)
		return True

	def onchange_partner_id(self, cr, uid, ids, part):
		if not part:
			return {'value':{'partner_invoice_id': False, 'partner_shipping_id':False, 'partner_order_id':False}}
		addr = self.pool.get('res.partner').address_get(cr, uid, [part], ['delivery','invoice','contact'])
		pricelist = self.pool.get('res.partner').browse(cr, uid, part).property_product_pricelist[0]
		return {'value':{'partner_invoice_id': addr['invoice'], 'partner_order_id':addr['contact'], 'partner_shipping_id':addr['delivery'], 'pricelist_id': pricelist}}

	def button_dummy(self, cr, uid, ids, context={}):
		return True

#FIXME: the method should return the list of invoices created (invoice_ids) 
# and not the id of the last invoice created (res). The problem is that we 
# cannot change it directly since the method is called by the sale order
# workflow and I suppose it expects a single id...
	def _inv_get(self, cr, uid, order, context={}):
		return {}

	def action_invoice_create(self, cr, uid, ids, grouped=False, states=['confirmed','done']):
		res = False
		invoices = {}
		invoice_ids = []

		def make_invoice(order, lines):
			a = order.partner_id.property_account_receivable[0]
			if order.partner_id and order.partner_id.property_payment_term:
				pay_term = order.partner_id.property_payment_term[0]
			else:
				pay_term = False
			for preinv in order.invoice_ids:
				if preinv.state in ('open','paid','proforma'):
					for preline in preinv.invoice_line:
						inv_line_id = self.pool.get('account.invoice.line').copy(cr, uid, preline.id, {'invoice_id':False, 'price_unit':-preline.price_unit})
						lines.append(inv_line_id)
			inv = {
				'name': order.name,
				'origin': order.name,
				'type': 'out_invoice',
				'reference': "P%dSO%d"%(order.partner_id.id,order.id),
				'account_id': a,
				'partner_id': order.partner_id.id,
				'address_invoice_id': order.partner_invoice_id.id,
				'address_contact_id': order.partner_invoice_id.id,
				'project_id': order.project_id.id,
				'invoice_line': [(6,0,lines)],
				'currency_id' : order.pricelist_id.currency_id.id,
				'comment': order.note,
				'payment_term': pay_term,
			}
			inv.update(self._inv_get(cr, uid, order))
			inv_obj = self.pool.get('account.invoice')
			inv_id = inv_obj.create(cr, uid, inv)
			inv_obj.button_compute(cr, uid, [inv_id])
			return inv_id

		for o in self.browse(cr,uid,ids):
			lines = []
			for line in o.order_line:
				if (line.state in states) and not line.invoiced:
					lines.append(line.id)
			created_lines = self.pool.get('sale.order.line').invoice_line_create(cr, uid, lines)
			if created_lines:
				invoices.setdefault(o.partner_id.id, []).append((o, created_lines))

		for val in invoices.values():
			if grouped:
				res = make_invoice(val[0][0], reduce(lambda x,y: x + y, [l for o,l in val], []))
				for o,l in val:
					self.write(cr, uid, [o.id], {'state' : 'progress'})
					cr.execute('insert into sale_order_invoice_rel (order_id,invoice_id) values (%d,%d)', (o.id, res))
			else:
				for order, il in val:
					res = make_invoice(order, il)
					invoice_ids.append(res)
					self.write(cr, uid, [order.id], {'state' : 'progress'})
					cr.execute('insert into sale_order_invoice_rel (order_id,invoice_id) values (%d,%d)', (o.id, res))
		return res

	def action_invoice_cancel(self, cr, uid, ids, context={}):
		for sale in self.browse(cr, uid, ids):
			for line in sale.order_line:
				invoiced=False
				for iline in line.invoice_lines:
					if iline.invoice_id and iline.invoice_id.state == 'cancel':
						continue
					else:
						invoiced=True
				self.pool.get('sale.order.line').write(cr, uid, [line.id], {'invoiced': invoiced})
		self.write(cr, uid, ids, {'state':'invoice_except', 'invoice_id':False})
		return True


	def action_cancel(self, cr, uid, ids, context={}):
		ok = True
		for sale in self.browse(cr, uid, ids):
			for pick in sale.picking_ids:
				if pick.state not in ('draft','cancel'):
					raise osv.except_osv(
						'Could not cancel sale order !',
						'You must first cancel all pickings attached to this sale order.')
			for r in self.read(cr,uid,ids,['picking_ids']):
				for pick in r['picking_ids']:
					wf_service = netsvc.LocalService("workflow")
					wf_service.trg_validate(uid, 'stock.picking', pick, 'button_cancel', cr)
			for inv in sale.invoice_ids:
				if inv.state not in ('draft','cancel'):
					raise osv.except_osv(
						'Could not cancel this sale order !',
						'You must first cancel all invoices attached to this sale order.')
			for r in self.read(cr,uid,ids,['invoice_ids']):
				for inv in r['invoice_ids']:
					wf_service = netsvc.LocalService("workflow")
					wf_service.trg_validate(uid, 'account.invoice', inv, 'invoice_cancel', cr)
		self.write(cr,uid,ids,{'state':'cancel'})
		return True

	def action_wait(self, cr, uid, ids, *args):
		for r in self.read(cr,uid,ids,['order_policy','invoice_ids','name','amount_untaxed','partner_id','user_id','order_line']):
			if self.pool.get('res.partner.event.type').check(cr, uid, 'sale_open'):
				self.pool.get('res.partner.event').create(cr, uid, {'name':'Sale Order: '+r['name'], 'partner_id':r['partner_id'][0], 'date':time.strftime('%Y-%m-%d %H:%M:%S'), 'user_id':(r['user_id'] and r['user_id'][0]) or uid, 'partner_type':'customer', 'probability': 1.0, 'planned_revenue':r['amount_untaxed']})
			if (r['order_policy']=='manual') and (not r['invoice_ids']):
				self.write(cr,uid,[r['id']],{'state':'manual'})
			else:
				self.write(cr,uid,[r['id']],{'state':'progress'})
			self.pool.get('sale.order.line').button_confirm(cr, uid, r['order_line'])

	def procurement_lines_get(self, cr, uid, ids, *args):
		res = []
		for order in self.browse(cr, uid, ids, context={}):
			for line in order.order_line:
				if line.procurement_id:
					res.append(line.procurement_id.id)
		return res

	# if mode == 'finished':
	#   returns True if all lines are done, False otherwise
	# if mode == 'canceled':
	#	returns True if there is at least one canceled line, False otherwise
	def test_state(self, cr, uid, ids, mode, *args):
		assert mode in ('finished', 'canceled'), "invalid mode for test_state"
		finished = True
		canceled = False
		write_done_ids = []
		write_cancel_ids = []
		for order in self.browse(cr, uid, ids, context={}):
			for line in order.order_line:
				if line.procurement_id and line.procurement_id.state != 'done':
					finished = False
				if line.procurement_id and line.procurement_id.state == 'cancel':
					canceled = True
				# if a line is finished (ie its procuremnt is done or it has not procuremernt and it
				# is not already marked as done, mark it as being so...
				if ((not line.procurement_id) or line.procurement_id.state == 'done') and line.state != 'done':
					write_done_ids.append(line.id)
				# ... same for canceled lines
				if line.procurement_id and line.procurement_id.state == 'cancel' and line.state != 'cancel':
					write_cancel_ids.append(line.id)
		if write_done_ids:
			self.pool.get('sale.order.line').write(cr, uid, write_done_ids, {'state': 'done'})
		if write_cancel_ids:
			self.pool.get('sale.order.line').write(cr, uid, write_cancel_ids, {'state': 'cancel'})

		if mode=='finished':
			return finished
		elif mode=='canceled':
			return canceled

	def action_ship_create(self, cr, uid, ids, *args):
		picking_id=False
		for order in self.browse(cr, uid, ids, context={}):
			output_id = order.shop_id.warehouse_id.lot_output_id.id
			picking_id = False
			for line in order.order_line:
				proc_id=False
				date_planned = (DateTime.now() + DateTime.RelativeDateTime(days=line.delay or 0.0)).strftime('%Y-%m-%d')
				if line.state == 'done':
					continue
				if line.product_id and line.product_id.product_tmpl_id.type in ('product', 'consu'):
					location_id = order.shop_id.warehouse_id.lot_stock_id.id
					if not picking_id:
						loc_dest_id = order.partner_id.property_stock_customer[0]
						picking_id = self.pool.get('stock.picking').create(cr, uid, {
							'origin': order.name,
							'type': 'out',
							'state': 'auto',
							'move_type': order.picking_policy,
							'loc_move_id': loc_dest_id,
							'sale_id': order.id,
							'address_id': order.partner_shipping_id.id,
							'note': order.note,
							'invoice_state': (order.order_policy=='picking' and '2binvoiced') or 'none',

						})

					move_id = self.pool.get('stock.move').create(cr, uid, {
						'name':line.name,
						'picking_id': picking_id,
						'product_id': line.product_id.id,
						'date_planned': date_planned,
						'product_qty': line.product_uom_qty,
						'product_uom': line.product_uom.id,
						'product_uos_qty': line.product_uos_qty,
						'product_uos': line.product_uos.id,
						'product_packaging' : line.product_packaging.id,
						'address_id' : line.address_allotment_id.id or order.partner_shipping_id.id,
						'location_id': location_id,
						'location_dest_id': output_id,
						'sale_line_id': line.id,
						'tracking_id': False,
						'state': 'waiting',
						'note': line.notes,
					})
					proc_id = self.pool.get('mrp.procurement').create(cr, uid, {
						'name': order.name,
						'origin': order.name,
						'date_planned': date_planned,
						'product_id': line.product_id.id,
						'product_qty': line.product_uom_qty,
						'product_uom': line.product_uom.id,
						'location_id': order.shop_id.warehouse_id.lot_stock_id.id,
						'procure_method': line.type,
						'move_id': move_id, 
					})
					wf_service = netsvc.LocalService("workflow")
					wf_service.trg_validate(uid, 'mrp.procurement', proc_id, 'button_confirm', cr)
					self.pool.get('sale.order.line').write(cr, uid, [line.id], {'procurement_id': proc_id})
				elif line.product_id and line.product_id.product_tmpl_id.type=='service':
					proc_id = self.pool.get('mrp.procurement').create(cr, uid, {
						'name': line.name,
						'origin': order.name,
						'date_planned': date_planned,
						'product_id': line.product_id.id,
						'product_qty': line.product_uom_qty,
						'product_uom': line.product_uom.id,
						'location_id': order.shop_id.warehouse_id.lot_stock_id.id,
						'procure_method': line.type,
					})
					wf_service = netsvc.LocalService("workflow")
					wf_service.trg_validate(uid, 'mrp.procurement', proc_id, 'button_confirm', cr)
					self.pool.get('sale.order.line').write(cr, uid, [line.id], {'procurement_id': proc_id})
				else:
					#
					# No procurement because no product in the sale.order.line.
					#
					pass

			val = {}
			if picking_id:
				wf_service = netsvc.LocalService("workflow")
				wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
				#val = {'picking_ids':[(6,0,[picking_id])]}

			if order.state=='shipping_except':
				val['state'] = 'progress'
				if (order.order_policy == 'manual') and order.invoice_ids:
					val['state'] = 'manual'
			self.write(cr, uid, [order.id], val)
		return True

	def action_ship_end(self, cr, uid, ids, context={}):
		for order in self.browse(cr, uid, ids):
			val = {'shipped':True}
			if order.state=='shipping_except':
				if (order.order_policy=='manual') and not order.invoice_ids:
					val['state'] = 'manual'
				else:
					val['state'] = 'progress'
			self.write(cr, uid, [order.id], val)
		return True

	def _log_event(self, cr, uid, ids, factor=0.7, name='Open Order'):
		invs = self.read(cr, uid, ids, ['date_order','partner_id','amount_untaxed'])
		for inv in invs:
			part=inv['partner_id'] and inv['partner_id'][0]
			pr = inv['amount_untaxed'] or 0.0
			partnertype = 'customer'
			eventtype = 'sale'
			self.pool.get('res.partner.event').create(cr, uid, {'name':'Order: '+name, 'som':False, 'description':'Order '+str(inv['id']), 'document':'', 'partner_id':part, 'date':time.strftime('%Y-%m-%d'), 'canal_id':False, 'user_id':uid, 'partner_type':partnertype, 'probability':1.0, 'planned_revenue':pr, 'planned_cost':0.0, 'type':eventtype})

	def has_stockable_products(self,cr, uid, ids, *args):
		for order in self.browse(cr, uid, ids):
			for order_line in order.order_line:
				if order_line.product_id and order_line.product_id.product_tmpl_id.type in ('product', 'consu'):
					return True
		return False
sale_order()

class sale_order_line(osv.osv):
	def copy(self, cr, uid, id, default=None, context={}):
		if not default: default = {}
		default.update( {'invoice_lines':[]})
		return super(sale_order_line, self).copy(cr, uid, id, default, context)

	def _amount_line_net(self, cr, uid, ids, field_name, arg, context):
		res = {}
		for line in self.browse(cr, uid, ids):
			if line.product_uos.id:
				res[line.id] = line.price_unit * (1 - (line.discount or 0.0) /100.0)
			else:
				res[line.id] = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
		return res

	def _amount_line(self, cr, uid, ids, field_name, arg, context):
		res = {}
		cur_obj=self.pool.get('res.currency')
		for line in self.browse(cr, uid, ids):
			if line.product_uos.id:
				res[line.id] = line.price_unit * line.product_uos_qty * (1 - (line.discount or 0.0) /100.0)
			else:
				res[line.id] = line.price_unit * line.product_uom_qty * (1 - (line.discount or 0.0) / 100.0)
			cur = line.order_id.pricelist_id.currency_id
			res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
		return res

	def _number_packages(self, cr, uid, ids, field_name, arg, context):
		res = {}
		for line in self.browse(cr, uid, ids):
			res[line.id] = int(line.product_uom_qty / line.product_packaging.qty)
		return res
	
	def _get_1st_packaging(self, cr, uid, context={}):
		cr.execute('select id from product_packaging order by id asc limit 1')
		res = cr.fetchone()
		if not res:
			return False
		return res[0]

	_name = 'sale.order.line'
	_description = 'Sale Order line'
	_columns = {
		'order_id': fields.many2one('sale.order', 'Order Ref', required=True, ondelete='cascade', select=True),
		'name': fields.char('Description', size=256, required=True, select=True),
		'sequence': fields.integer('Sequence'),
		'delay': fields.float('Delivery Delay', required=True),
		'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok','=',True)], change_default=True, relate=True),
		'invoice_lines': fields.many2many('account.invoice.line', 'sale_order_line_invoice_rel', 'order_line_id','invoice_id', 'Invoice Lines', readonly=True),
		'invoiced': fields.boolean('Invoiced', readonly=True, select=True),
		'procurement_id': fields.many2one('mrp.procurement', 'Procurement'),
		'price_unit': fields.float('Unit Price', required=True, digits=(16, int(config['price_accuracy']))),
		'price_net': fields.function(_amount_line_net, method=True, string='Net Price', digits=(16, int(config['price_accuracy']))),
		'price_subtotal': fields.function(_amount_line, method=True, string='Subtotal'),
		'tax_id': fields.many2many('account.tax', 'sale_order_tax', 'order_line_id', 'tax_id', 'Taxes'),
		'type': fields.selection([('make_to_stock','from stock'),('make_to_order','on order')],'Procure Method', required=True),
		'property_ids': fields.many2many('mrp.property', 'sale_order_line_property_rel', 'order_id', 'property_id', 'Properties'),
		'address_allotment_id' : fields.many2one('res.partner.address', 'Allotment Partner'),
		'product_uom_qty': fields.float('Quantity (UOM)', digits=(16,2), required=True),
		'product_uom': fields.many2one('product.uom', 'Product UOM', required=True),
		'product_uos_qty': fields.float('Quantity (UOS)'),
		'product_uos': fields.many2one('product.uom', 'Product UOS'),
		'product_packaging': fields.many2one('product.packaging', 'Packaging used'),
		'move_ids': fields.one2many('stock.move', 'sale_line_id', 'Inventory Moves', readonly=True),
		'property_ids': fields.many2many('mrp.property', 'sale_order_line_property_rel', 'order_id', 'property_id', 'Properties'),
		'discount': fields.float('Discount (%)', digits=(16,2)),
		'number_packages': fields.function(_number_packages, method=True, type='integer', string='Number packages'),
		'notes': fields.text('Notes'),
		'th_weight' : fields.float('Weight'),
		'state': fields.selection([('draft','Draft'),('confirmed','Confirmed'),('done','Done'),('cancel','Canceled')], 'State', required=True, readonly=True),
		'price_unit_customer': fields.float('Customer Unit Price', digits=(16, int(config['price_accuracy']))),
	}
	_order = 'sequence'
	_defaults = {
		'discount': lambda *a: 0.0,
		'delay': lambda *a: 0.0,
		'product_uom_qty': lambda *a: 1,
		'product_uos_qty': lambda *a: 1,
		'sequence': lambda *a: 10,
		'invoiced': lambda *a: 0,
		'state': lambda *a: 'draft',
		'type': lambda *a: 'make_to_stock',
		'product_packaging': _get_1st_packaging,
	}
	def invoice_line_create(self, cr, uid, ids, context={}):
		def _get_line_qty(line):
			if (line.order_id.invoice_quantity=='order') or not line.procurement_id:
				return line.product_uos_qty or line.product_uom_qty
			else:
				return self.pool.get('mrp.procurement').quantity_get(cr, uid, line.procurement_id.id, context)
		create_ids = []
		for line in self.browse(cr, uid, ids, context):
			if not line.invoiced:
				if line.product_id:
					a =  line.product_id.product_tmpl_id.property_account_income
					if not a:
						a = line.product_id.categ_id.property_account_income_categ[0]
					else:
						a = a[0]
				else:
					a = self.pool.get('ir.property').get(cr, uid, 'property_account_income_categ', 'product.category', context=context)
				uosqty = _get_line_qty(line)
				uos_id = (line.product_uos and line.product_uos.id) or False
				inv_id = self.pool.get('account.invoice.line').create(cr, uid, {
					'name': line.name,
					'account_id': a,
					'price_unit': line.price_unit,
					'quantity': uosqty,
					'discount': line.discount,
					'uos_id': uos_id,
					'product_id': line.product_id.id or False,
					'invoice_line_tax_id': [(6,0,[x.id for x in line.tax_id])],
					'note': line.notes,
				})
				cr.execute('insert into sale_order_line_invoice_rel (order_line_id,invoice_id) values (%d,%d)', (line.id, inv_id))
				self.write(cr, uid, [line.id], {'invoiced':True})
				create_ids.append(inv_id)
		return create_ids

	def button_confirm(self, cr, uid, ids, context={}):
		return self.write(cr, uid, ids, {'state':'confirmed'})

	def button_done(self, cr, uid, ids, context={}):
		return self.write(cr, uid, ids, {'state':'done'})

	def uos_change(self, cr, uid, ids, product_uos, product_uos_qty=0, product_id=None):
		if not product_id:
			return {'value': {'product_uom': product_uos, 'product_uom_qty': product_uos_qty}, 'domain':{}}
		res = self.pool.get('product.product').read(cr, uid, [product_id], ['uom_id', 'uos_id', 'uos_coeff', 'weight'])[0]
		value = {
			'product_uom' : res['uom_id'], 
		}
		try:
			value.update({
				'product_uom_qty' : product_uos_qty / res['uos_coeff'],
				'weight' : product_uos_qty / res['uos_coeff'] * res['weight']
			})
		except ZeroDivisionError:
			pass
		return {'value' : value}

	def copy(self, cr, uid, id, default=None,context={}):
		if not default:
			default = {}
		default.update({'state':'draft', 'move_ids':[], 'invoiced':False, 'invoice_lines':[]})
		return super(sale_order_line, self).copy(cr, uid, id, default, context)

	def product_id_change(self, cr, uid, ids, pricelist, product, qty=0, uom=False, qty_uos=0, uos=False, name='', partner_id=False, lang=False):
		if partner_id:
			lang=self.pool.get('res.partner').read(cr, uid, [partner_id])[0]['lang']
		context = {'lang':lang}
		if not product:
			return {'value': {'price_unit': 0.0, 'notes':'', 'weight' : 0}, 'domain':{'product_uom':[]}}
		if not pricelist:
			raise osv.except_osv('No Pricelist !', 'You have to select a pricelist in the sale form !\nPlease set one before choosing a product.')
		price = self.pool.get('product.pricelist').price_get(cr,uid,[pricelist], product, qty or 1.0, partner_id, {'uom': uom})[pricelist]
		if price is False:
			raise osv.except_osv('No valid pricelist line found !', "Couldn't find a pricelist line matching this product and quantity.\nYou have to change either the product, the quantity or the pricelist.")
		res = self.pool.get('product.product').read(cr, uid, [product], context=context)[0]
#		dt = (DateTime.now() + DateTime.RelativeDateTime(days=res['sale_delay'] or 0.0)).strftime('%Y-%m-%d')

		result = {'price_unit': price, 'type':res['procure_method'], 'delay':(res['sale_delay'] or 0.0), 'notes':res['description_sale']}

		taxes = self.pool.get('account.tax').browse(cr, uid, res['taxes_id'])
		taxep = self.pool.get('res.partner').browse(cr, uid, partner_id).property_account_tax
		if not taxep:
			result['tax_id'] = res['taxes_id']
		else:
			res5 = [taxep[0]]
			tp = self.pool.get('account.tax').browse(cr, uid, taxep[0])
			for t in taxes:
				if not t.tax_group==tp.tax_group:
					res5.append(t.id)
			result['tax_id'] = res5

		result['name'] = res['partner_ref']
		domain = {}
		if not uom and not uos:
			result['product_uom'] = res['uom_id'] and res['uom_id'][0]
			if result['product_uom']:
				result['product_uos'] = res['uos_id']
				result['product_uos_qty'] = qty * res['uos_coeff']
				result['weight'] = qty * res['weight']
				res2 = self.pool.get('product.uom').read(cr, uid, [result['product_uom']], ['category_id'])
				if res2 and res2[0]['category_id']:
					domain = {'product_uom':[('category_id','=',res2[0]['category_id'][0])]}
		elif uom: # whether uos is set or not
			default_uom = res['uom_id'] and res['uom_id'][0]
			q = self.pool.get('product.uom')._compute_qty(cr, uid, uom, qty, default_uom)
			result['product_uos'] = res['uos_id']
			result['product_uos_qty'] = q * res['uos_coeff']
			result['weight'] = q * res['weight']
		elif uos: # only happens if uom is False
			result['product_uom'] = res['uom_id'] and res['uom_id'][0]
			result['product_uom_qty'] = qty_uos / res['uos_coeff']
			result['weight'] = result['product_uom_qty'] * res['weight']
		return {'value':result, 'domain':domain}
sale_order_line()

class sale_payment_line(osv.osv):
	_name = 'sale.order.payment'
	_description = 'Sale Order payment'
	_columns = {
		'order_id': fields.many2one('sale.order', 'Order Ref', select=True),
		'name': fields.char('Description', size=64, required=True),
		'account_id': fields.many2one('account.account', 'Account'),
		'amount': fields.float('Amount', required=True),
	}
	_defaults = {
	}
sale_payment_line()

