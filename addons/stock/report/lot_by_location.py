# -*-encoding: iso8859-1 -*-
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

import time
from report import report_sxw
from osv import osv

class lot_by_location(report_sxw.rml_parse):
	def __init__(self, cr, uid, name, context):
		super(lot_by_location, self).__init__(cr, uid, name, context)
		print "Init report";
		self.localcontext.update({
			'time': time,
			'stock' : self.stock,
		})
# 													from the stock move

	def stock(self,location_id):
		print location_id;

		stock_detail={}
		stock=[];

		self.cr.execute(('select pl.name, product_qty from stock_move sm,stock_location sl, product_product p ,product_template pl where sl.id = sm.location_id and sl.id = %d and  p.product_tmpl_id = sm.product_id and pl.id=p.product_tmpl_id')%(location_id))
		res = self.cr.fetchall();
		for r in res:
			stock_detail = {'product':"",'qty':""}
			stock_detail['product']=r[0]
			stock_detail['qty']=r[1]
			stock.append(stock_detail)

		print "stock------------------------------------------",stock;
		return stock;

# 								from stock inventory  line

#	def lot_details(self,location_id):
#		print location_id;

#		res = self.pool.get('stock_inventory_line').read(self.cr,self.uid,[location_id]);

#		return res;


report_sxw.report_sxw('report.lot.by.location','stock.location','addons/stock/report/lot_by_location.rml',parser=lot_by_location)
