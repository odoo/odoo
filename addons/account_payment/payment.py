##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA	 02111-1307, USA.
#
##############################################################################

from osv import fields
from osv import osv
import time
import netsvc
class payment_type(osv.osv):
	_name= 'payment.type'
	_description= 'Payment type'
	_columns= {
		'name': fields.char('Name', size=64, required=True),
		'suitable_bank_types': fields.many2many('res.partner.bank.type',
						'bank_type_payment_type_rel',
						'pay_type_id','bank_type_id',
						'Suitable bank types')
				}

	
payment_type()


class payment_mode(osv.osv):
	_name= 'payment.mode'
	_description= 'Payment mode'
	_columns= {
		'name': fields.char('Name', size=64, required=True),
		'code': fields.char('Code', size=64, required=True,unique=True,select=True),
		'bank_id': fields.many2one('res.partner.bank',"Bank account",required=True),
		'journal': fields.many2one('account.journal','Journal',required=True,domain=[('type','=','cash')]),
		'type': fields.many2one('payment.type','Payment type',required=True),
		}

	def suitable_bank_types(self,cr,uid,payment_code,context):
		""" Return the codes of the bank type that are suitable for the given payment mode"""
		cr.execute(""" select t.code
				   from res_partner_bank_type t
					join bank_type_payment_type_rel r on (r.bank_type_id = t.id)
					join payment_type pt on (r.pay_type_id = pt.id)
					join payment_mode m on (pt.id=m.type) 
				   where m.code = %s""", [payment_code])
		return [x[0] for x in cr.fetchall()]

payment_mode()


class payment_order(osv.osv):
	_name = 'payment.order'
	_description = 'Payment Order'
	_rec_name = 'date'

	def _total(self, cr, uid, ids, name, args, context={}):
		if not ids: return {}
		cr.execute("""select o.id, coalesce(sum(amount),0)
			from payment_order o left join payment_line l on (o.id = l.order_id)
			where o.id in (%s) group by o.id"""% ','.join(map(str,ids)))
		return dict(cr.fetchall())

	def nb_line(self, cr, uid, ids, name, args, context={}):
		if not ids: return {}
		res= {}.fromkeys(ids,0)
		cr.execute("""select "order_id",count(*)
		              from payment_line 
			          where "order_id" in (%s) group by "order_id" """% ','.join(map(str,ids)))
		res.update(dict(cr.fetchall()))
		return res

	def mode_get(self, cr, uid, context={}):
		pay_type_obj = self.pool.get('payment.mode')
		ids = pay_type_obj.search(cr, uid, [])
		res = pay_type_obj.read(cr, uid, ids, ['code','name'], context)
		return [(r['code'],r['name']) for r in res] + [('manual', 'Manual')]

	_columns = {
		'date_planned': fields.date('Date if fixed'),
		'reference': fields.char('Reference',size=128),
		'mode': fields.selection(mode_get, 'Payment mode',size=16,required=True, select=True),
		'state': fields.selection([('draft', 'Draft'),('open','Open'),
				   ('cancel','Cancelled'),('done','Done')], 'State', select=True),
		'line_ids': fields.one2many('payment.line','order_id','Payment lines'),
		'total': fields.function(_total, string="Total", method=True, type='float'),
		'user_id': fields.many2one('res.users','User',required=True),
		'nb_line': fields.function(nb_line,string='Number of payment',method=True, type='integer'),
		'date_prefered': fields.selection([('now','Directly'),('due','Due date'),('fixed','Fixed date')],"Prefered date",required=True),
		'date_created': fields.date('Creation date',readonly=True),
		'date_done': fields.date('Execution date',readonly=True),
	}

	_defaults = {
		'user_id': lambda self,cr,uid,context: uid, 
		'mode': lambda *a : 'manual',
		'state': lambda *a: 'draft',
		'date_prefered': lambda *a: 'due',
		'date_created': lambda *a: time.strftime('%Y-%m-%d'),
	   }

	def set_to_draft(self, cr, uid, ids, *args):
		self.write(cr, uid, ids, {'state':'draft'})
		wf_service = netsvc.LocalService("workflow")
		for id in ids:
			wf_service.trg_create(uid, 'payment.order', id, cr)
		return True

	def action_open(self, cr, uid, ids, *args):
		for order in self.read(cr,uid,ids,['reference']):
			if not order['reference']:
				reference = self.pool.get('ir.sequence').get(cr, uid, 'payment.order')
				self.write(cr,uid,order['id'],{'reference':reference})
		return True

	def action_done(self, cr, uid, ids, *args):
		self.write(cr,uid,ids,{'date_done':time.strftime('%Y-%m-%d')})
		return True

payment_order()

class payment_line(osv.osv):
	_name = 'payment.line'
	_description = 'Payment Line'
	_rec_name = 'move_line_id'

	def partner_payable(self, cr, uid, ids, name, args, context={}):
		if not ids: return {}
		partners= self.read(cr, uid, ids, ['partner_id'], context)
		partners= dict(map(lambda x: (x['id'],x['partner_id']),partners))
		debit= self.pool.get('res.partner')._debit_get(cr, uid, partners.values(), name, args, context)
		for i in partners:
			partners[i]= debit[partners[i]]
		return partners
		
	def translate(self,orig):
		return {"to_pay":"credit",
				"due_date":"date_maturity",
				"reference":"ref"}.get(orig,orig)

	def select_by_name(self, cr, uid, ids, name, args, context={}):
		if not ids: return {}
		cr.execute("""SELECT pl.id, ml.%s 
						from account_move_line ml 
							inner join payment_line pl on (ml.id= pl.move_line_id)
						where pl.id in (%s)"""% (self.translate(name),','.join(map(str,ids))) )
		return dict(cr.fetchall())


	_columns = {
		'move_line_id': fields.many2one('account.move.line','Entry line',required=True),
		'amount': fields.float('Payment Amount', digits=(16,2), required=True),
		'bank_id': fields.many2one('res.partner.bank','Bank account'),
		'order_id': fields.many2one('payment.order','Order', ondelete='cascade', select=True),
		'partner_id': fields.function(select_by_name, string="Partner", method=True, type='many2one', obj='res.partner'),
		'to_pay': fields.function(select_by_name, string="To pay", method=True, type='float'),
		'due_date': fields.function(select_by_name, string="Due date", method=True, type='date'),
		'date_created': fields.function(select_by_name, string="Creation date", method=True, type='date'),
		'reference': fields.function(select_by_name, string="Ref", method=True, type='char'),
		'partner_payable': fields.function(partner_payable, string="Partner payable", method=True, type='float'),
	 }
	def onchange_move_line(self, cr, uid, id, move_line_id, type,context={}):
		if not move_line_id:
			return {}
		line=self.pool.get('account.move.line').browse(cr,uid,move_line_id)
		return {'value': {'amount': line.amount_to_pay,
						  'to_pay': line.amount_to_pay,
						  'partner_id': line.partner_id,
						  'reference': line.ref,
						  'date_created': line.date_created,
						  'bank_id': self.pool.get('account.move.line').line2bank(cr,uid,[move_line_id],type,context)[move_line_id]
						  }}

payment_line()
