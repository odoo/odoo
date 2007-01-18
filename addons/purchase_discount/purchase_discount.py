##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

from osv import fields
from osv import osv
import time
import netsvc

import ir
from mx import DateTime
import pooler

class purchase_order_line(osv.osv):
	_name = "purchase.order.line"
	_inherit = "purchase.order.line"
	_columns = {
		'discount': fields.float('Discount (%)', digits=(16,2)),
		}
	_defaults = {
		'discount': lambda *a: 0.0,
	}
purchase_order_line()

class purchase_order(osv.osv):
	_name = "purchase.order"
	_inherit = "purchase.order"
	
	def _amount_untaxed(self, cr, uid, ids, field_name, arg, context):
		id_set = ",".join(map(str, ids))
		sql_req="SELECT s.id,COALESCE(SUM(l.price_unit*l.product_qty*(100-l.discount))/100.0,0)::decimal(16,2) AS amount FROM purchase_order s LEFT OUTER JOIN purchase_order_line l ON (s.id=l.order_id) WHERE s.id IN ("+id_set+") GROUP BY s.id"		
		cr.execute(sql_req)
		res = dict(cr.fetchall())
		print "_amount_untaxed : res = "+str(res)
		return res

	def _amount_tax(self, cr, uid, ids, field_name, arg, context):
		print "_amount_tax(self, cr, uid, ids, field_name, arg, context):"
		res = {}
		for order in self.browse(cr, uid, ids):
			val = 0.0
			for line in order.order_line:
				for tax in line.taxes_id:
					for c in self.pool.get('account.tax').compute(cr, uid, [tax.id], line.price_unit * (1-(line.discount or 0.0)/100.0), line.product_qty, order.partner_address_id.id):
						val+=c['amount']
			res[order.id]=round(val,2)

		print "_amount_tax : res = "+str(res)
		return res
purchase_order()
