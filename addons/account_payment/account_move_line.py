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

class account_move_line(osv.osv):
	_inherit = "account.move.line"

	def amount_to_pay(self, cr, uid, ids, name, arg={}, context={}):
		""" Return the amount still to pay regarding all the payemnt orders (excepting cancelled orders)"""
		if not ids:
			return {}
		cr.execute("SELECT ml.id,ml.credit - (select coalesce(sum(amount),0) from payment_line pl inner join payment_order po on (pl.order_id = po.id)where move_line_id = ml.id and po.state != 'cancel') as amount from account_move_line ml where credit > 0 and id in (%s)"% (",".join(map(str,ids))))
		r=dict(cr.fetchall())
		return r


	def _to_pay_search(self, cr, uid, obj, name, args):
		if not len(args):
			return []
		query = self.pool.get('account.move.line')._query_get(cr, uid, context={})
		where = ' and '.join(map(lambda x: '''(select l.credit - coalesce(sum(amount),0)
							from payment_line pl
							  inner join payment_order po on (pl.order_id = po.id)
							where move_line_id = l.id and po.state != 'cancel') '''+x[1]+str(x[2])+' ',args))

		cr.execute(('''select id
					   from account_move_line l
					   where account_id in (select id from account_account where type=%s and active)
					   and reconcile_id is null
					   and credit > 0
					   and '''+where+' and '+query), ('payable',) )

		res = cr.fetchall()
		if not len(res):
			return [('id','=','0')]
		return [('id','in',map(lambda x:x[0], res))]


	def line2bank(self,cr,uid,ids,payment_mode= 'manual',context=None):
		"""
		Try to return for each account move line a corresponding bank
		account according to the payment mode.  This work using one of
		the bank of the partner defined on the invoice eventually
		associated to the line.
		Return the first suitable bank for the corresponding partner.  

		"""
		if not ids: return {}
		bank_type= self.pool.get('payment.mode').suitable_bank_types(cr,uid,payment_mode,context=context)
		cr.execute('''select DISTINCT l.id,b.id,b.state
				  from account_invoice i
				    join account_move m on (i.move_id = m.id)
				    join account_move_line l on (m.id = l.move_id)
				    join res_partner p on (p.id = i.partner_id)
				    join res_partner_bank b on (p.id = b.partner_id)
				  where l.id in (%s)
				  ''' % ",".join(map(str,ids)) )

		r= cr.fetchall()
		type_ok=[]
		line2bank={}.fromkeys(ids)
		for line,bank,t in r:
			if not line2bank[line]:
				line2bank[line]= bank
				if t in bank_type:
					type_ok.append(line)
			elif (line not in  type_ok) and (t in bank_type) :
				line2bank[line]= bank
				type_ok.append(line)

		return line2bank

	_columns = {
		'amount_to_pay' : fields.function(amount_to_pay, method=True, type='float', string='Amount to pay', fnct_search=_to_pay_search),
				}
account_move_line()
