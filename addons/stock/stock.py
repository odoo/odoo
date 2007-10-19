##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: stock.py 1005 2005-07-25 08:41:42Z nicoe $
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

import datetime
import time
import netsvc
from osv import fields,osv
import ir
from tools import config


#----------------------------------------------------------
# Incoterms
#----------------------------------------------------------
class stock_incoterms(osv.osv):
	_name = "stock.incoterms"
	_description = "Incoterms"
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'code': fields.char('Code', size=3, required=True),
		'active': fields.boolean('Active'),
	}
	_defaults = {
		'active': lambda *a: True,
	}
stock_incoterms()

class stock_lot(osv.osv):
	_name = "stock.lot"
	_description = "Lot"
	_columns = {
		'name': fields.char('Lot Name', size=64, required=True),
		'active': fields.boolean('Active'),
		'tracking': fields.char('Tracking', size=64),
		'move_ids': fields.one2many('stock.move', 'lot_id', 'Move lines'),
	}
	_defaults = {
		'active': lambda *a: True,
	}
stock_lot()


#----------------------------------------------------------
# Stock Location
#----------------------------------------------------------
class stock_location(osv.osv):
	_name = "stock.location"
	_description = "Location"
	_parent_name = "location_id"
	_columns = {
		'name': fields.char('Location Name', size=64, required=True),
		'active': fields.boolean('Active'),
		'usage': fields.selection([('supplier','Supplier Location'),('internal','Internal Location'),('customer','Customer Location'),('inventory','Inventory'),('procurement','Procurement'),('production','Production')], 'Location type'),
		'allocation_method': fields.selection([('fifo','FIFO'),('lifo','LIFO'),('nearest','Nearest')], 'Allocation Method', required=True),

		'account_id': fields.many2one('account.account', string='Inventory Account', domain=[('type','!=','view')]),
		'location_id': fields.many2one('stock.location', 'Parent Location', select=True),
		'child_ids': fields.one2many('stock.location', 'location_id', 'Contains'),

		'comment': fields.text('Additional Information'),
		'posx': fields.integer('Corridor (X)', required=True),
		'posy': fields.integer('Shelves (Y)', required=True),
		'posz': fields.integer('Height (Z)', required=True)
	}
	_defaults = {
		'active': lambda *a: 1,
		'usage': lambda *a: 'internal',
		'allocation_method': lambda *a: 'fifo',
		'posx': lambda *a: 0,
		'posy': lambda *a: 0,
		'posz': lambda *a: 0,
	}

	def _product_get_all_report(self, cr, uid, ids, product_ids=False,
			context=None):
		return self._product_get_report(cr, uid, ids, product_ids, context,
				recursive=True)

	def _product_get_report(self, cr, uid, ids, product_ids=False,
			context=None, recursive=False):
		if context is None:
			context = {}
		product_obj = self.pool.get('product.product')
		if not product_ids:
			product_ids = product_obj.search(cr, uid, [])

		products = product_obj.browse(cr, uid, product_ids, context=context)
		products_by_uom = {}
		products_by_id = {}
		for product in products:
			products_by_uom.setdefault(product.uom_id.id, [])
			products_by_uom[product.uom_id.id].append(product)
			products_by_id.setdefault(product.id, [])
			products_by_id[product.id] = product

		result = []
		for id in ids:
			for uom_id in products_by_uom.keys():
				fnc = self._product_get
				if recursive:
					fnc = self._product_all_get
				ctx = context.copy()
				ctx['uom'] = uom_id
				qty = fnc(cr, uid, id, [x.id for x in products_by_uom[uom_id]],
						context=ctx)
				for product_id in qty.keys():
					if not qty[product_id]:
						continue
					product = products_by_id[product_id]
					result.append({
						'price': product.list_price,
						'name': product.name,
						'code': product.default_code, # used by lot_overview_all report!
						'variants': product.variants or '',
						'uom': product.uom_id.name,
						'amount': qty[product_id],
					})
		return result

	def _product_get_multi_location(self, cr, uid, ids, product_ids=False, context={}, states=['done'], what=('in', 'out')):
		states_str = ','.join(map(lambda s: "'%s'" % s, states))
		if not product_ids:
			product_ids = self.pool.get('product.product').search(cr, uid, [])
		res = {}
		for id in product_ids:
			res[id] = 0.0
		if not ids:
			return res
			
		prod_ids_str = ','.join(map(str, product_ids))
		location_ids_str = ','.join(map(str, ids))
		results = []
		results2 = []
		if 'in' in what:
			# all moves from a location out of the set to a location in the set
			cr.execute(
				'select sum(product_qty), product_id, product_uom '\
				'from stock_move '\
				'where location_id not in ('+location_ids_str+') '\
				'and location_dest_id in ('+location_ids_str+') '\
				'and product_id in ('+prod_ids_str+') '\
				'and state in ('+states_str+') '\
				'group by product_id,product_uom'
			)
			results = cr.fetchall()
		if 'out' in what:
			# all moves from a location in the set to a location out of the set
			cr.execute(
				'select sum(product_qty), product_id, product_uom '\
				'from stock_move '\
				'where location_id in ('+location_ids_str+') '\
				'and location_dest_id not in ('+location_ids_str+') '\
				'and product_id in ('+prod_ids_str+') '\
				'and state in ('+states_str+') '\
				'group by product_id,product_uom'
			)
			results2 = cr.fetchall()
		uom_obj = self.pool.get('product.uom')
		for amount, prod_id, prod_uom in results:
			amount = uom_obj._compute_qty(cr, uid, prod_uom, amount,
					context.get('uom', False))
			res[prod_id] += amount
		for amount, prod_id, prod_uom in results2:
			amount = uom_obj._compute_qty(cr, uid, prod_uom, amount,
					context.get('uom', False))
			res[prod_id] -= amount
		return res

	def _product_get(self, cr, uid, id, product_ids=False, context={}, states=['done']):
		ids = id and [id] or []
		return self._product_get_multi_location(cr, uid, ids, product_ids, context, states)

	def _product_all_get(self, cr, uid, id, product_ids=False, context={}, states=['done']):
		# build the list of ids of children of the location given by id
		ids = id and [id] or []
		location_ids = self.search(cr, uid, [('location_id', 'child_of', ids)])
		return self._product_get_multi_location(cr, uid, location_ids, product_ids, context, states)

	def _product_virtual_get(self, cr, uid, id, product_ids=False, context={}, states=['done']):
		return self._product_all_get(cr, uid, id, product_ids, context, ['confirmed','waiting','assigned','done'])

	#
	# TODO:
	#	 Improve this function
	#
	# Returns:
	#	 [ (tracking_id, product_qty, location_id) ]
	#
	def _product_reserve(self, cr, uid, ids, product_id, product_qty, context={}):
		result = []
		amount = 0.0
		for id in self.search(cr, uid, [('location_id', 'child_of', ids)]):
			cr.execute("select product_uom,sum(product_qty) as product_qty from stock_move where location_dest_id=%d and product_id=%d and state='done' group by product_uom", (id,product_id))
			results = cr.dictfetchall()
			cr.execute("select product_uom,-sum(product_qty) as product_qty from stock_move where location_id=%d and product_id=%d and state in ('done', 'assigned') group by product_uom", (id,product_id))
			results += cr.dictfetchall()

			total = 0.0
			results2 = 0.0
			for r in results:
				amount = self.pool.get('product.uom')._compute_qty(cr, uid, r['product_uom'],r['product_qty'], context.get('uom',False))
				results2 += amount
				total += amount

			if total<=0.0:
				continue

			amount = results2
			if amount>0:
				if amount>min(total,product_qty):
					amount = min(product_qty,total)
				result.append((amount,id))
				product_qty -= amount
				total -= amount
				if product_qty<=0.0:
					return result
				if total<=0.0:
					continue
		return False
stock_location()


#----------------------------------------------------------
# Stock Move
#----------------------------------------------------------

class stock_move_lot(osv.osv):
	_name = "stock.move.lot"
	_description = "Move Lot"
	_columns = {
		'name': fields.char('Move Description', size=64, required=True),
		'active': fields.boolean('Active'),
		'state': fields.selection( (('draft','Draft'),('done','Moved')), 'State', readonly=True),
		'serial': fields.char('Tracking Number', size=32),
		'date_planned': fields.date('Scheduled date'),
		'date_moved': fields.date('Actual date'),
		'lot_id': fields.many2one('stock.lot','Lot', required=True),
		'loc_dest_id': fields.many2one('stock.location', 'Destination Location', required=True),
		'address_id': fields.many2one('res.partner.address', 'Destination Address'),
		'origin': fields.char('Origin', size=64),
	}
	_defaults = {
		'active': lambda *a: 1,
		'state': lambda *a: 'draft',
		'date_planned': lambda *a: time.strftime('%Y-%m-%d'),
	}
	#
	# TODO: test if valid
	# ERROR: does this function should call action_done instead of doing him self on
	# stock.move
	#
	def action_move(self, cr, uid, ids, context={}):
		for move in self.browse(cr, uid, ids, context):
			lot_remove = []
			for m in move.lot_id.move_ids:
				new_id = self.pool.get('stock.move').copy(cr, uid, m.id, {'location_id': m.location_dest_id.id, 'location_dest_id': move.loc_dest_id.id, 'date_moved': time.strftime('%Y-%m-%d'), 'picking_id': False, 'state':'draft','prodlot_id':False, 'tracking_id':False, 'lot_id': False, 'move_history_ids':[], 'move_history_ids2':[]})
				self.pool.get('stock.move').action_done(cr, uid, [new_id], context)
				cr.execute('insert into stock_move_history_ids (parent_id,child_id) values (%d,%d)', (m.id, new_id))
				lot_remove.append(m.id)
			self.pool.get('stock.move').write(cr, uid, lot_remove, {'lot_id':False})
		self.write(cr,uid, ids, {'state':'done','date_moved':time.strftime('%Y-%m-%d')})
		return True
stock_move_lot()

class stock_tracking(osv.osv):
	_name = "stock.tracking"
	_description = "Stock Tracking Lots"

	def checksum(sscc):
		salt = '31' * 8 + '3'
		sum = 0
		for sscc_part, salt_part in zip(sscc, salt):
			sum += int(sscc_part) * int(salt_part)
		return (10 - (sum % 10)) % 10
	checksum = staticmethod(checksum)

	def make_sscc(self, cr, uid, context={}):
		sequence = self.pool.get('ir.sequence').get(cr, uid, 'stock.lot.tracking')
		return sequence + str(self.checksum(sequence))

	_columns = {
		'name': fields.char('Tracking', size=64, required=True),
		'active': fields.boolean('Active'),
		'serial': fields.char('Reference', size=64),
		'move_ids' : fields.one2many('stock.move', 'tracking_id', 'Moves tracked'),
		'date': fields.datetime('Date create', required=True),
	}
	_defaults = {
		'active': lambda *a: 1,
		'name' : make_sscc,
		'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
	}

	def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
		if not args:
			args=[]
		if not context:
			context={}
		ids = self.search(cr, user, [('serial','=',name)]+ args, limit=limit, context=context)
		ids += self.search(cr, user, [('name',operator,name)]+ args, limit=limit, context=context)
		return self.name_get(cr, user, ids, context)

	def name_get(self, cr, uid, ids, context={}):
		if not len(ids):
			return []
		res = [(r['id'], r['name']+' ['+(r['serial'] or '')+']') for r in self.read(cr, uid, ids, ['name','serial'], context)]
		return res

	def unlink(self, cr ,uid, ids):
		raise Exception, 'You can not remove a lot line !'
stock_tracking()

#----------------------------------------------------------
# Stock Picking
#----------------------------------------------------------
class stock_picking(osv.osv):
	_name = "stock.picking"
	_description = "Packing list"
	_columns = {
		'name': fields.char('Packing name', size=64, required=True, select=True),
		'origin': fields.char('Origin', size=64),
		'type': fields.selection([('out','Sending Goods'),('in','Getting Goods'),('internal','Internal')], 'Shipping Type', required=True, select=True),
		'active': fields.boolean('Active'),
		'note': fields.text('Notes'),

		'location_id': fields.many2one('stock.location', 'Location'),
		'location_dest_id': fields.many2one('stock.location', 'Dest. Location'),

		'move_type': fields.selection([('direct','Direct Delivery'),('one','All at once')],'Delivery Method', required=True),
		'state': fields.selection([
			('draft','Draft'),
			('auto','Waiting'),
			('confirmed','Confirmed'),
			('assigned','Assigned'),
			('done','Done'),
			('cancel','Cancel'),
			], 'State', readonly=True),
		'date':fields.datetime('Date create'),

		'move_lines': fields.one2many('stock.move', 'picking_id', 'Move lines'),

		'auto_picking': fields.boolean('Auto-Packing'),
		'work': fields.boolean('Work todo'),
		'loc_move_id': fields.many2one('stock.location', 'Final location'),
		'address_id': fields.many2one('res.partner.address', 'Partner'),
		'lot_id': fields.many2one('stock.lot', 'Consumer lot created'),
		'move_lot_id': fields.many2one('stock.move.lot', 'Moves created'),
		'invoice_state':fields.selection([
			("invoiced","Invoiced"),
			("2binvoiced","To be invoiced"),
			("none","Not from Packing")], "Invoice state"),
	}
	_defaults = {
		'name': lambda *a: '/',
		'work': lambda *a: 0,
		'active': lambda *a: 1,
		'state': lambda *a: 'draft',
		'move_type': lambda *a: 'direct',
		'type': lambda *a: 'in',
		'invoice_state': lambda *a: 'none',
		'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
	}

	def action_confirm(self, cr, uid, ids, *args):
		self.write(cr, uid, ids, {'state': 'confirmed'})
		todo = []
		for picking in self.browse(cr, uid, ids):
			number = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.%s' % picking.type)
			self.write(cr, uid, [picking.id], {'name': number})
			for r in picking.move_lines:
				if r.state=='draft':
					todo.append(r.id)
		if len(todo):
			self.pool.get('stock.move').action_confirm(cr,uid, todo)
		return True

	def test_auto_picking(self, cr, uid, ids):
		# TODO: Check locations to see if in the same location ?
		return True

	def action_assign(self, cr, uid, ids, *args):
		for pick in self.browse(cr, uid, ids):
			move_ids = [x.id for x in pick.move_lines if x.state=='confirmed']
			self.pool.get('stock.move').action_assign(cr, uid, move_ids)
		return True

	def force_assign(self, cr, uid, ids, *args):
		wf_service = netsvc.LocalService("workflow")
		for pick in self.browse(cr, uid, ids):
#			move_ids = [x.id for x in pick.move_lines if x.state == 'confirmed']
			move_ids = [x.id for x in pick.move_lines]
			self.pool.get('stock.move').force_assign(cr, uid, move_ids)
			wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
		return True

	def cancel_assign(self, cr, uid, ids, *args):
		wf_service = netsvc.LocalService("workflow")
		for pick in self.browse(cr, uid, ids):
			move_ids = [x.id for x in pick.move_lines]
			self.pool.get('stock.move').cancel_assign(cr, uid, move_ids)
			wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
		return True

	def action_assign_wkf(self, cr, uid, ids):
		self.write(cr, uid, ids, {'state':'assigned'})
		return True

	def test_finnished(self, cr, uid, ids):
		move_ids=self.pool.get('stock.move').search(cr,uid,[('picking_id','in',ids)])
		
		for move in self.pool.get('stock.move').browse(cr,uid,move_ids):
			if move.state not in ('done','cancel') :
				if move.product_qty != 0.0:
					return False
				else:
					move.write(cr,uid,[move.id],{'state':'done'})
		return True

	def test_assigned(self, cr, uid, ids):
		ok = True
		for pick in self.browse(cr, uid, ids):
			mt = pick.move_type
			for move in pick.move_lines:
				if (move.state in ('confirmed','draft')) and (mt=='one'):
					return False
				if (mt=='direct') and (move.state=='assigned') and (move.product_qty):
					return True
				ok = ok and (move.state in ('cancel','done','assigned'))
		return ok

	def action_cancel(self, cr, uid, ids, context={}):
		for pick in self.browse(cr, uid, ids):
			ids2 = [move.id for move in pick.move_lines]
			self.pool.get('stock.move').action_cancel(cr, uid, ids2, context)
		self.write(cr,uid, ids, {'state':'cancel', 'invoice_state':'none'})
		return True

	#
	# TODO: change and create a move if not parents
	#
	def action_done(self, cr, uid, ids, *args):
		for pick in self.browse(cr, uid, ids):
			if pick.move_type=='one' and pick.loc_move_id:
				if pick.lot_id:
					id = self.pool.get('stock.move.lot').create(cr, uid, {
						'name': 'MOVE:'+pick.name,
						'origin': 'PICK:'+str(pick.id),
						'lot_id': pick.lot_id.id,
						'loc_dest_id': pick.loc_move_id.id,
						'address_id': pick.address_id.id
					})
					self.write(cr, uid, [pick.id], {'move_lot_id':id})
		self.write(cr,uid, ids, {'state':'done'})
		return True

	def action_move(self, cr, uid, ids, context={}):
		for pick in self.browse(cr, uid, ids):
			todo = []
			for move in pick.move_lines:
				if move.state=='assigned':
					todo.append(move.id)

			if len(todo):
				self.pool.get('stock.move').action_done(cr, uid, todo)

				lot_id = self.pool.get('stock.lot').create(cr, uid, {'name':pick.name})
				self.pool.get('stock.move').write(cr,uid, todo, {'lot_id':lot_id})
				self.write(cr, uid, [pick.id], {'lot_id':lot_id})

				if pick.move_type=='direct' and pick.loc_move_id:
					id = self.pool.get('stock.move.lot').create(cr, uid, {
						'name': 'MOVE:'+pick.name,
						'origin': 'PICK:'+str(pick.id),
						'lot_id': lot_id,
						'loc_dest_id': pick.loc_move_id.id,
						'address_id': pick.address_id.id
					})
					self.write(cr, uid, [pick.id], {'move_lot_id':id})
		return True

	def action_invoice_create(self, cr, uid, ids, journal_id=False, group=False, type='out_invoice', context={}):
		res={}
		pgroup = {}
		get_ids = lambda y: map(lambda x: x.id, y or [])
		sales = {}
		for p in self.browse(cr,uid,ids, context):
			if p.invoice_state<>'2binvoiced':
				continue
			a = p.address_id.partner_id.property_account_receivable.id
			if p.address_id.partner_id and p.address_id.partner_id.property_payment_term.id:
				pay_term = p.address_id.partner_id.property_payment_term.id
			else:
				pay_term = False

			if p.sale_id:
				pinv_id = p.sale_id.partner_invoice_id.id
				pcon_id = p.sale_id.partner_order_id.id
				if p.sale_id.id not in sales:
					sales[p.sale_id.id] = [x.id for x in p.sale_id.invoice_ids]
			else:
				#
				# ideal: get_address('invoice') on partner
				#
				pinv_id = p.address_id.id
				pcon_id = p.address_id.id

			val = {
				'name': p.name,
				'origin': p.name+':'+p.origin,
				'type': type,
				'account_id': a,
				'partner_id': p.address_id.partner_id.id,
				'address_invoice_id': pinv_id,
				'address_contact_id': pcon_id,
				'comment': (p.note or '') + '\n' + (p.sale_id and p.sale_id.note or ''),
				'payment_term': pay_term,
			}
			if p.sale_id:
				val['currency_id'] = (p.sale_id and p.sale_id.pricelist_id.currency_id.id) or False
			if journal_id:
				val['journal_id'] = journal_id

			if group and p.address_id.partner_id.id in pgroup:
				invoice_id= pgroup[p.address_id.partner_id.id]
			else:
				invoice_id = self.pool.get('account.invoice').create(cr, uid, val ,context= context)
				pgroup[p.address_id.partner_id.id] = invoice_id


			res[p.id]= invoice_id

			for line in p.move_lines:
				if line.sale_line_id:
					tax_ids = map(lambda x: x.id, line.sale_line_id.tax_id)
				else:
					tax_ids = map(lambda x: x.id, line.product_id.taxes_id)
				account_id =  line.product_id.product_tmpl_id.property_account_income.id
				if not account_id:
					account_id = line.product_id.categ_id.property_account_income_categ.id
				punit = line.sale_line_id and line.sale_line_id.price_unit or line.product_id.list_price
				if type in ('in_invoice','in_refund'):
					punit = line.product_id.standard_price
				iline_id = self.pool.get('account.invoice.line').create(cr, uid, {
					'name': ((group and (p.name + ' - ')) or '') + line.name,
					'invoice_id': invoice_id,
					'uos_id': line.product_uos.id,
					'product_id': line.product_id.id,
					'account_id': account_id,
					'price_unit': line.sale_line_id and line.sale_line_id.price_unit or line.product_id.list_price,
					'discount': line.sale_line_id and line.sale_line_id.discount or 0.0,
					'quantity': line.product_uos_qty,
					'invoice_line_tax_id': [(6,0,tax_ids)],
					'account_analytic_id': (p.sale_id and p.sale_id.project_id.id) or False,
				})
				if line.sale_line_id:
					self.pool.get('sale.order.line').write(cr, uid, [line.sale_line_id.id], {
						'invoice_lines': [(6, 0, [iline_id])]
					})
			self.pool.get('account.invoice').button_compute(cr, uid, [invoice_id], {'type':'in_invoice'}, set_total=(type in ('in_invoice','in_refund')))
			self.pool.get('stock.picking').write(cr, uid, [p.id], {'invoice_state': 'invoiced'})
			if p.sale_id:
				sids = sales[p.sale_id.id]
				if invoice_id not in sids:
					sales[p.sale_id.id].append(invoice_id)
					self.pool.get('sale.order').write(cr, uid, [p.sale_id.id], {
						'invoice_ids': [(6, 0, sales[p.sale_id.id])]
					})

				self.pool.get('sale.order').write(cr, uid, [p.sale_id.id], {
					'invoiced': True
				})
		self.write(cr, uid, res.keys(), {'invoice_state': 'invoiced'})
		return res

stock_picking()

class stock_production_lot(osv.osv):

	def name_get(self, cr, uid, ids, context={}):
		if not ids:
			return []
		reads = self.read(cr, uid, ids, ['name', 'ref'], context)
		res=[]
		for record in reads:
			name=record['name']
			if record['ref']:
				name=name+'/'+record['ref']
			res.append((record['id'], name))
		return res

	_name = 'stock.production.lot'
	_description = 'Production lot'

	_columns = {
		'name': fields.char('Serial', size=64, required=True),
		'ref': fields.char('Reference', size=64),
		'date': fields.datetime('Date create', required=True),
		'revisions': fields.one2many('stock.production.lot.revision','lot_id','Revisions'),
	}
	_defaults = {
		'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'name': lambda x,y,z,c: x.pool.get('ir.sequence').get(y,z,'stock.lot.serial'),
	}
	_sql_constraints = [
		('name_ref_uniq', 'unique (name, ref)', 'The serial/ref must be unique !'),
	]

stock_production_lot()

class stock_production_lot_revision(osv.osv):
	_name = 'stock.production.lot.revision'
	_description = 'Production lot revisions'
	_columns = {
		'name': fields.char('Revision name', size=64, required=True),
		'description': fields.text('Description'),
		'date': fields.date('Revision date'),
		'indice': fields.char('Revision', size=16),
		'author_id': fields.many2one('res.users', 'Author'),
		'lot_id': fields.many2one('stock.production.lot', 'Production lot', select=True),
	}

	_defaults = {
		'author_id': lambda x,y,z,c: z,
		'date': lambda *a: time.strftime('%Y-%m-%d'),
	}
stock_production_lot_revision()

# ----------------------------------------------------
# Move
# ----------------------------------------------------

#
# Fields:
#	location_dest_id is only used for predicting futur stocks
#
class stock_move(osv.osv):
	def _getSSCC(self, cr, uid, context={}):
		cr.execute('select id from stock_tracking where create_uid=%d order by id desc limit 1', (uid,))
		res = cr.fetchone()
		return (res and res[0]) or False
	_name = "stock.move"
	_description = "Stock Move"

	_columns = {
		'name': fields.char('Name', size=64, required=True, select=True),
		'priority': fields.selection([('0','Not urgent'),('1','Urgent')], 'Priority'),

		'date': fields.datetime('Date Created'),
		'date_planned': fields.date('Scheduled date', required=True),

		'product_id': fields.many2one('product.product', 'Product', required=True),

		'product_qty': fields.float('Quantity', required=True),
		'product_uom': fields.many2one('product.uom', 'Product UOM', required=True),
		'product_uos_qty': fields.float('Quantity (UOS)'),
		'product_uos': fields.many2one('product.uom', 'Product UOS'),
		'product_packaging' : fields.many2one('product.packaging', 'Packaging'),

		'location_id': fields.many2one('stock.location', 'Source Location', required=True),
		'location_dest_id': fields.many2one('stock.location', 'Dest. Location', required=True),
		'address_id' : fields.many2one('res.partner.address', 'Dest. Address'),

		'prodlot_id' : fields.many2one('stock.production.lot', 'Production lot', help="Production lot is used to put a serial number on the production"),
		'tracking_id': fields.many2one('stock.tracking', 'Tracking lot', select=True, help="Tracking lot is the code that will be put on the logistic unit/pallet"),
		'lot_id': fields.many2one('stock.lot', 'Consumer lot', select=True, readonly=True),

		'move_dest_id': fields.many2one('stock.move', 'Dest. Move'),
		'move_history_ids': fields.many2many('stock.move', 'stock_move_history_ids', 'parent_id', 'child_id', 'Move History'),
		'move_history_ids2': fields.many2many('stock.move', 'stock_move_history_ids', 'child_id', 'parent_id', 'Move History'),
		'picking_id': fields.many2one('stock.picking', 'Packing list', select=True),

		'note': fields.text('Notes'),

		'state': fields.selection([('draft','Draft'),('waiting','Waiting'),('confirmed','Confirmed'),('assigned','Assigned'),('done','Done'),('cancel','cancel')], 'State', readonly=True, select=True),
		'price_unit': fields.float('Unit Price',
			digits=(16, int(config['price_accuracy']))),
	}
	_defaults = {
		'state': lambda *a: 'draft',
		'priority': lambda *a: '1',
		'product_qty': lambda *a: 1.0,
		'date_planned': lambda *a: time.strftime('%Y-%m-%d'),
		'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
	}

	def _auto_init(self, cursor):
		super(stock_move, self)._auto_init(cursor)
		cursor.execute('SELECT indexname \
				FROM pg_indexes \
				WHERE indexname = \'stock_move_location_id_location_dest_id_product_id_state\'')
		if not cursor.fetchone():
			cursor.execute('CREATE INDEX stock_move_location_id_location_dest_id_product_id_state \
					ON stock_move (location_id, location_dest_id, product_id, state)')
			cursor.commit()


	def onchange_product_id(self, cr, uid, context, prod_id=False, loc_id=False, loc_dest_id=False):
		if not prod_id:
			return {}
		product = self.pool.get('product.product').browse(cr, uid, [prod_id])[0]
		result = {
			'name': product.name,
			'product_uom': product.uom_id.id,
		}
		if loc_id:
			result['location_id'] = loc_id
		if loc_dest_id:
			result['location_dest_id'] = loc_dest_id
		return {'value':result}

	def action_confirm(self, cr, uid, ids, context={}):
		self.write(cr, uid, ids, {'state':'confirmed'})
		return True

	def action_assign(self, cr, uid, ids, *args):
		todo = []
		for move in self.browse(cr, uid, ids):
			if move.state in ('confirmed','waiting'):
				todo.append(move.id)
		res = self.check_assign(cr, uid, todo)
		return res

	def force_assign(self, cr, uid, ids, context={}):
		self.write(cr, uid, ids, {'state' : 'assigned'})
		return True

	def cancel_assign(self, cr, uid, ids, context={}):
		self.write(cr, uid, ids, {'state': 'confirmed'})
		return True

	#
	# Duplicate stock.move
	#
	def check_assign(self, cr, uid, ids, context={}):
		done = []
		count=0
		pickings = {}
		for move in self.browse(cr, uid, ids):
			if move.product_id.type == 'consu':
				if mode.state in ('confirmed', 'waiting'):
					done.append(move.id)
				pickings[move.picking_id.id] = 1
				continue
			if move.state in ('confirmed','waiting'):
				res = self.pool.get('stock.location')._product_reserve(cr, uid, [move.location_id.id], move.product_id.id, move.product_qty, {'uom': move.product_uom.id})
				if res:
					done.append(move.id)
					pickings[move.picking_id.id] = 1
					r = res.pop(0)
					cr.execute('update stock_move set location_id=%d, product_qty=%f where id=%d', (r[1],r[0], move.id))

					while res:
						r = res.pop(0)
						move_id = self.copy(cr, uid, move.id, {'product_qty':r[0], 'location_id':r[1]})
						done.append(move_id)
						#cr.execute('insert into stock_move_history_ids values (%d,%d)', (move.id,move_id))
		if done:
			count += len(done)
			self.write(cr, uid, done, {'state':'assigned'})

		if count:
			for pick_id in pickings:
				wf_service = netsvc.LocalService("workflow")
				wf_service.trg_write(uid, 'stock.picking', pick_id, cr)
		return count

	#
	# Cancel move => cancel others move and pickings
	#
	def action_cancel(self, cr, uid, ids, context={}):
		if not len(ids):
			return True
		pickings = {}
		for move in self.browse(cr, uid, ids):
			if move.state in ('confirmed','waiting','assigned','draft'):
				if move.picking_id:
					pickings[move.picking_id.id] = True
		self.write(cr, uid, ids, {'state':'cancel'})
		ids_lst = ','.join(map(str,ids))
		for pick_id in pickings:
			wf_service = netsvc.LocalService("workflow")
			wf_service.trg_validate(uid, 'stock.picking', pick_id, 'button_cancel', cr)
		ids2 = []
		for res in self.read(cr, uid, ids, ['move_dest_id']):
			if res['move_dest_id']:
				ids2.append(res['move_dest_id'][0])

		wf_service = netsvc.LocalService("workflow")
		for id in ids:
			wf_service.trg_trigger(uid, 'stock.move', id, cr)
		self.action_cancel(cr,uid, ids2, context)
		return True

	def action_done(self, cr, uid, ids, *args):
		for move in self.browse(cr, uid, ids):
			if move.move_dest_id.id and (move.state != 'done'):
				mid = move.move_dest_id.id
				if move.move_dest_id.id:
					cr.execute('insert into stock_move_history_ids (parent_id,child_id) values (%d,%d)', (move.id, move.move_dest_id.id))
				if move.move_dest_id.state in ('waiting','confirmed'):
					self.write(cr, uid, [move.move_dest_id.id], {'state':'assigned'})
					if move.move_dest_id.picking_id:
						wf_service = netsvc.LocalService("workflow")
						wf_service.trg_write(uid, 'stock.picking', move.move_dest_id.picking_id.id, cr)
					else:
						pass
						# self.action_done(cr, uid, [move.move_dest_id.id])

			#
			# Accounting Entries
			#
			acc_src = None
			acc_dest = None
			if move.location_id.account_id:
				acc_src =  move.location_id.account_id.id
			if move.location_dest_id.account_id:
				acc_dest =  move.location_dest_id.account_id.id
			if acc_src or acc_dest:
				test = [('product.product', move.product_id.id)]
				if move.product_id.categ_id:
					test.append( ('product.category', move.product_id.categ_id.id) )
				if not acc_src:
					acc_src = move.product_id.product_tmpl_id.\
							property_stock_account_output.id
					if not acc_src:
						acc_src = move.product_id.categ_id.\
								property_stock_account_output_categ.id
					if not acc_src:
						raise osv.except_osv('Error!',
								'There is no stock output account defined ' \
										'for this product: "%s" (id: %d)' % \
										(move.product_id.name,
											move.product_id.id,))
				if not acc_dest:
					acc_dest = move.product_id.product_tmpl_id.\
							property_stock_account_input.id
					if not acc_dest:
						acc_dest = move.product_id.categ_id.\
								property_stock_account_input_categ.id
					if not acc_dest:
						raise osv.except_osv('Error!',
								'There is no stock input account defined ' \
										'for this product: "%s" (id: %d)' % \
										(move.product_id.name,
											move.product_id.id,))
				if not move.product_id.categ_id.property_stock_journal.id:
					raise osv.except_osv('Error!',
							'There is no journal defined '\
							'on the product category: "%s" (id: %d)' % \
							(move.product_id.categ_id.name,
								move.product_id.categ_id.id,))
				journal_id = move.product_id.categ_id.property_stock_journal.id
				if acc_src != acc_dest:
					ref = move.picking_id and move.picking_id.name or False

					if move.product_id.cost_method == 'average' and move.price_unit:
						amount = move.product_qty * move.price_unit
					else:
						amount = move.product_qty * move.product_id.standard_price

					date = time.strftime('%Y-%m-%d')
					lines = [
							(0, 0, {
								'name': move.name,
								'quantity': move.product_qty,
								'credit': amount,
								'account_id': acc_src,
								'ref': ref,
								'date': date}),
							(0, 0, {
								'name': move.name,
								'quantity': move.product_qty,
								'debit': amount,
								'account_id': acc_dest,
								'ref': ref,
								'date': date})
					]
					self.pool.get('account.move').create(cr, uid,
							{
								'name': move.name,
								'journal_id': journal_id,
								'line_id': lines,
								'ref': ref,
							})
		self.write(cr, uid, ids, {'state':'done'})

		wf_service = netsvc.LocalService("workflow")
		for id in ids:
			wf_service.trg_trigger(uid, 'stock.move', id, cr)
		return True

stock_move()

class stock_inventory(osv.osv):
	_name = "stock.inventory"
	_description = "Inventory"
	_columns = {
		'name': fields.char('Inventory', size=64, required=True),
		'date': fields.datetime('Date create', required=True),
		'date_done': fields.datetime('Date done'),
		'inventory_line_id': fields.one2many('stock.inventory.line', 'inventory_id', 'Inventories'),
		'move_ids': fields.many2many('stock.move', 'stock_inventory_move_rel', 'inventory_id', 'move_id', 'Created Moves'),
		'state': fields.selection( (('draft','Draft'),('done','Done')), 'State', readonly=True),
	}
	_defaults = {
		'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'state': lambda *a: 'draft',
	}
	#
	# Update to support tracking
	#
	def action_done(self, cr, uid, ids, *args):
		for inv in self.browse(cr,uid,ids):
			move_ids = []
			move_line=[]
			for line in inv.inventory_line_id:
				pid=line.product_id.id
				price=line.product_id.standard_price or 0.0
				amount=self.pool.get('stock.location')._product_get(cr, uid, line.location_id.id, [pid], {'uom': line.product_uom.id})[pid]
				change=line.product_qty-amount
				if change:
					location_id = line.product_id.product_tmpl_id.property_stock_inventory.id
					value = {
						'name': 'INV:'+str(line.inventory_id.id)+':'+line.inventory_id.name,
						'product_id': line.product_id.id,
						'product_uom': line.product_uom.id,
						'date': inv.date,
						'date_planned': inv.date,
						'state': 'assigned'
					}
					if change>0:
						value.update( {
							'product_qty': change,
							'location_id': location_id,
							'location_dest_id': line.location_id.id,
						})
					else:
						value.update( {
							'product_qty': -change,
							'location_id': line.location_id.id,
							'location_dest_id': location_id,
						})
					move_ids.append(self.pool.get('stock.move').create(cr, uid, value))
			if len(move_ids):
				self.pool.get('stock.move').action_done(cr, uid, move_ids)
			self.write(cr, uid, [inv.id], {'state':'done', 'date_done': time.strftime('%Y-%m-%d %H:%M:%S'), 'move_ids': [(6,0,move_ids)]})
		return True

	def action_cancel(self, cr, uid, ids, context={}):
		for inv in self.browse(cr,uid,ids):
			self.pool.get('stock.move').action_cancel(cr, uid, [x.id for x in inv.move_ids], context)
			self.write(cr, uid, [inv.id], {'state':'draft'})
		return True
stock_inventory()


class stock_inventory_line(osv.osv):
	_name = "stock.inventory.line"
	_description = "Inventory line"
	_columns = {
		'inventory_id': fields.many2one('stock.inventory','Inventory', ondelete='cascade', select=True),
		'location_id': fields.many2one('stock.location','Location', required=True),
		'product_id': fields.many2one('product.product', 'Product', required=True ),
		'product_uom': fields.many2one('product.uom', 'Product UOM', required=True ),
		'product_qty': fields.float('Quantity')
	}
	def on_change_product_id(self, cr, uid, ids, location_id, product, uom=False):
		if not product:
			return {}
		if not uom:
			prod = self.pool.get('product.product').browse(cr, uid, [product], {'uom': uom})[0]
			uom = prod.uom_id.id
		amount=self.pool.get('stock.location')._product_get(cr, uid, location_id, [product], {'uom': uom})[product]
		result = {'product_qty':amount, 'product_uom':uom}
		return {'value':result}
stock_inventory_line()


#----------------------------------------------------------
# Stock Warehouse
#----------------------------------------------------------
class stock_warehouse(osv.osv):
	_name = "stock.warehouse"
	_description = "Warehouse"
	_columns = {
		'name': fields.char('Name', size=60, required=True),
#		'partner_id': fields.many2one('res.partner', 'Owner'),
		'partner_address_id': fields.many2one('res.partner.address', 'Owner Address'),
		'lot_input_id': fields.many2one('stock.location', 'Location Input', required=True ),
		'lot_stock_id': fields.many2one('stock.location', 'Location Stock', required=True ),
		'lot_output_id': fields.many2one('stock.location', 'Location Output', required=True ),
	}
stock_warehouse()


# Product
class product_product(osv.osv):
	_inherit = "product.product"
	#
	# Utiliser browse pour limiter les queries !
	#
	def view_header_get(self, cr, user, view_id, view_type, context):
		if (not context.get('location', False)):
			return False
		cr.execute('select name from stock_location where id=%d', (context['location'],))
		j = cr.fetchone()[0]
		if j:
			return 'Products: '+j
		return False

	def _get_product_available_func(states, what):
		def _product_available(self, cr, uid, ids, name, arg, context={}):
			if context.get('shop', False):
				cr.execute('select warehouse_id from sale_shop where id=%d', (int(context['shop']),))
				res2 = cr.fetchone()
				if res2:
					context['warehouse'] = res2[0]

			if context.get('warehouse', False):
				cr.execute('select lot_stock_id from stock_warehouse where id=%d', (int(context['warehouse']),))
				res2 = cr.fetchone()
				if res2:
					context['location'] = res2[0]

			if context.get('location', False):
				location_ids = [context['location']]
			else:
				# get the list of ids of the stock location of all warehouses
				cr.execute("select lot_stock_id from stock_warehouse")
				location_ids = [id for (id,) in cr.fetchall()]
				
			# build the list of ids of children of the location given by id
			location_ids = self.pool.get('stock.location').search(cr, uid, [('location_id', 'child_of', location_ids)])
			res = self.pool.get('stock.location')._product_get_multi_location(cr, uid, location_ids, ids, context, states, what)
			for id in ids:
				res.setdefault(id, 0.0)
			return res
		return _product_available
	_product_qty_available = _get_product_available_func(('done',), ('in', 'out'))
	_product_virtual_available = _get_product_available_func(('confirmed','waiting','assigned','done'), ('in', 'out'))
	_product_outgoing_qty = _get_product_available_func(('confirmed','waiting','assigned'), ('out',))
	_product_incoming_qty = _get_product_available_func(('confirmed','waiting','assigned'), ('in',))
	_columns = {
		'qty_available': fields.function(_product_qty_available, method=True, type='float', string='Real Stock'),
		'virtual_available': fields.function(_product_virtual_available, method=True, type='float', string='Virtual Stock'),
		'incoming_qty': fields.function(_product_incoming_qty, method=True, type='float', string='Incoming'),
		'outgoing_qty': fields.function(_product_outgoing_qty, method=True, type='float', string='Outgoing'),
	}
product_product()
