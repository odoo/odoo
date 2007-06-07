##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting FROM its eventual inadequacies AND bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees AND support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it AND/or
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

import pooler
import time
from report import report_sxw

SUMS  = ('credit','debit','balance','quantity','revenue')

class account_analytic_cost_ledger(report_sxw.rml_parse):
	def __init__(self, cr, uid, name, context):
		super(account_analytic_cost_ledger, self).__init__(cr, uid, name, context)
		self.localcontext.update( {
			'time': time,
			'lines': self._lines_all,
			'totals': dict.fromkeys(SUMS, 0.0)
		})

	def _lines_all(self, accounts, date1, date2):
		result = []
		for account in accounts:
			accs =  self._lines(account.id, date1, date2).values()
			result.append( {
				'code': account.code,
				'name': account.complete_name,
				'accounts': accs,
				'qty_max': account.quantity_max or '/',
				'debit_max': account.amount_max or '/'
			})
			for word in SUMS:
				s=reduce(lambda x,y:x+y[word], accs, 0.0)
				result[-1][word] = s
				self.localcontext['totals'][word] += s
		return result

	def _lines(self, account_id, date1, date2):
		lineobj = self.pool.get('account.analytic.line')
		line_ids = lineobj.search(self.cr, self.uid, [('account_id','=',account_id), ('date','>=',date1), ('date','<=',date2)])
		result = {}
		for line in lineobj.browse(self.cr, self.uid, line_ids):
			if line.general_account_id.id not in result:
				result[line.general_account_id.id] = {
					'code': line.general_account_id.code,
					'name': line.general_account_id.name,
					'lines': []
				}
				result[line.general_account_id.id].update(dict.fromkeys(SUMS, 0.0))

			revenue = 0.0
			if line.amount<0 and line.product_id and line.product_uom_id and line.account_id.pricelist_id:
				c = {
					'uom': line.product_uom_id.id
				}
				id = line.account_id.pricelist_id.id
				price = self.pool.get('product.pricelist').price_get(self.cr, self.uid, [id],
					line.product_id.id, line.unit_amount, c)[id]
				revenue = round(price * line.unit_amount, 2)
			result[line.general_account_id.id]['lines'].append( {
				'date':line.date,
				'cj':line.journal_id.code,
				'name': line.name,
				'quantity': line.unit_amount,
				'credit': line.amount <0 and -line.amount or 0,
				'debit': line.amount >0 and line.amount or 0,
				'balance': line.amount,
				'revenue': revenue
			} )
			for word in SUMS:
				result[line.general_account_id.id][word] += (result[line.general_account_id.id]['lines'][-1][word] or 0.0)
		return result

report_sxw.report_sxw('report.hr.timesheet.invoice.account.analytic.account.cost_ledger', 'account.analytic.account', 'addons/hr_timesheet_invoice/report/cost_ledger.rml',parser=account_analytic_cost_ledger)

