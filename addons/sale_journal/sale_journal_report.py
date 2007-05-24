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

from osv import fields,osv

class report_sale_journal_sale(osv.osv):
	_name = "sale_journal.sale.stats"
	_description = "Sales Orders by Journal"
	_auto = False
	_columns = {
		'name': fields.date('Month', readonly=True),
		'state': fields.selection([
			('draft','Quotation'),
			('waiting_date','Waiting Schedule'),
			('manual','Manual in progress'),
			('progress','In progress'),
			('shipping_except','Shipping Exception'),
			('invoice_except','Invoice Exception'),
			('done','Done'),
			('cancel','Cancel')
		], 'Order State', readonly=True),
		'journal_id':fields.many2one('sale_journal.sale.journal', 'Journal', readonly=True),
		'quantity': fields.float('Quantities', readonly=True),
		'price_total': fields.float('Total Price', readonly=True),
		'price_average': fields.float('Average Price', readonly=True),
		'count': fields.integer('# of Lines', readonly=True),
	}
	_order = 'journal_id,name desc,price_total desc'
	def init(self, cr):
		cr.execute("""
			create or replace view sale_journal_sale_stats as (
				select
					min(l.id) as id,
					substring(s.date_order for 7)||'-'||'01' as name,
					s.state,
					s.journal_id,
					sum(l.product_uom_qty) as quantity,
					count(*),
					sum(l.product_uom_qty*l.price_unit) as price_total,
					(sum(l.product_uom_qty*l.price_unit)/sum(l.product_uom_qty))::decimal(16,2) as price_average
				from sale_order s
					right join sale_order_line l on (s.id=l.order_id)
				group by s.journal_id, substring(s.date_order for 7),s.state
			)
		""")
report_sale_journal_sale()


