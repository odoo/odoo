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
import pooler
from report import report_sxw

class tax_report(report_sxw.rml_parse):

	def __init__(self, cr, uid, name, context): #name, table, rml):
		super(tax_report, self).__init__(cr, uid, name, context)
		self.localcontext.update({
			'time': time,
			'get_period': self._get_period,
			'get_codes': self._get_codes,
			'get_general': self._get_general,
			'get_company': self._get_company,
			'get_currency': self._get_currency,
		})

	def _add_header(self, node):
		return True

	def _get_period(self, period_id):
		return self.pool.get('account.period').browse(self.cr, self.uid, period_id).name

	def _get_general(self, tax_code_id, period_id, company_id):
		self.cr.execute('select sum(line.tax_amount) as tax_amount, sum(line.debit) as debit, sum(line.credit) as credit, count(*) as count, account.id as account_id \
				from account_move_line AS line, account_account AS account \
				where line.state<>%s and line.period_id=%d and line.tax_code_id=%d \
				AND line.account_id = account.id AND account.company_id = %d AND account.active \
				group by account.id', ('draft',period_id, tax_code_id, company_id))
		res = self.cr.dictfetchall()
		i = 0
		while i<len(res):
			res[i]['account'] = self.pool.get('account.account').browse(self.cr, self.uid, res[i]['account_id'])
			i+=1
		return res

	def _get_codes(self, period_id, parent=False, level=0):
		tc = self.pool.get('account.tax.code')
		ids = tc.search(self.cr, self.uid, [('parent_id','=',parent)])
		res = []
		for code in tc.browse(self.cr, self.uid, ids, {'period_id':period_id}):
			res.append((' - '*level*2, code))
			res += self._get_codes(period_id, code.id, level+1)
		return res

	def _get_company(self, form):
		return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).name

	def _get_currency(self, form):
		return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).currency_id.name

report_sxw.report_sxw('report.account.vat.declaration', 'account.tax.code',
	'addons/account/report/tax_report.rml', parser=tax_report, header=False)

