# -*- coding: utf-8 -*-
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

import time
from report import report_sxw
from osv import osv
import pooler

class order(report_sxw.rml_parse):
	def __init__(self, cr, uid, name, context):
		super(order, self).__init__(cr, uid, name, context)
		self.localcontext.update({
			'time': time,
			'get_line_tax': self._get_line_tax,
			'get_tax': self._get_tax,
			'get_product_code': self._get_product_code,
		})
	def _get_line_tax(self, line_obj):
		self.cr.execute("SELECT tax_id FROM purchase_order_taxe WHERE order_line_id=%d" % (line_obj.id))
		res = self.cr.fetchall() or None
		if not res:
			return ""
		if isinstance(res, list):
			tax_ids = [t[0] for t in res]
		else:
			tax_ids = res[0]
		res = [tax.name for tax in pooler.get_pool(cr.dbname).get('account.tax').browse(self.cr, self.uid, tax_ids)]
		return ",\n ".join(res)
	
	def _get_tax(self, order_obj):
		self.cr.execute("SELECT DISTINCT tax_id FROM purchase_order_taxe, purchase_order_line, purchase_order \
			WHERE (purchase_order_line.order_id=purchase_order.id) AND (purchase_order.id=%d)" % (order_obj.id))
		res = self.cr.fetchall() or None
		if not res:
			return []
		if isinstance(res, list):
			tax_ids = [t[0] for t in res]
		else:
			tax_ids = res[0]
		tax_obj = pooler.get_pool(cr.dbname).get('account.tax')
		res = []
		for tax in tax_obj.browse(self.cr, self.uid, tax_ids):
			self.cr.execute("SELECT DISTINCT order_line_id FROM purchase_order_line, purchase_order_taxe \
				WHERE (purchase_order_taxe.tax_id=%d) AND (purchase_order_line.order_id=%d)" % (tax.id, order_obj.id))
			lines = self.cr.fetchall() or None
			if lines:
				if isinstance(lines, list):
					line_ids = [l[0] for l in lines]
				else:
					line_ids = lines[0]
				base = 0
				for line in pooler.get_pool(cr.dbname).get('purchase.order.line').browse(self.cr, self.uid, line_ids):
					base += line.price_subtotal
				res.append({'code':tax.name,
					'base':base,
					'amount':base*tax.amount})
		return res
	def _get_product_code(self, product_id, partner_id):
		product_obj=pooler.get_pool(self.cr.dbname).get('product.product')
		return product_obj._product_code(self.cr, self.uid, [product_id], name=None, arg=None, context={'partner_id': partner_id})[product_id]

report_sxw.report_sxw('report.purchase.order','purchase.order','addons/purchase/report/order.rml',parser=order)
