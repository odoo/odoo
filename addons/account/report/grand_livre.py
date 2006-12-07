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

class grand_livre(report_sxw.rml_parse):
	def __init__(self, cr, uid, name, context):
		super(grand_livre, self).__init__(cr, uid, name, context)
		self.localcontext.update( {
			'time': time,
			'lines': self.lines,
			'sum_debit_account': self._sum_debit_account,
			'sum_credit_account': self._sum_credit_account,
			'sum_debit': self._sum_debit,
			'sum_credit': self._sum_credit
		})

	def preprocess(self, objects, data, ids):
		# compute the list of accounts to work on, that is: the accounts the user
		# selected AND all their childs
		def _rec_account_get(cr, uid, accounts, found=None):
			if not found:
				found = []
			for acc in accounts:
				if acc.id not in found:
					found.append(acc.id)
					_rec_account_get(cr, uid, acc.child_id, found)
			return found
		toprocess = self.pool.get('account.account').browse(self.cr, self.uid, ids)
		newids = _rec_account_get(self.cr, self.uid, toprocess)
		# filter out accounts which have no transaction in them
		self.cr.execute(
			"SELECT DISTINCT account_id " \
			"FROM account_move_line l " \
			"WHERE date>=%s AND date<=%s " \
			"AND l.state<>'draft' " \
			"AND account_id IN (" + ','.join(map(str,newids)) + ")",
			(data['form']['date1'], data['form']['date2']))
		newids = [id for (id,) in self.cr.fetchall()]
		objects = self.pool.get('account.account').browse(self.cr, self.uid, newids)
		super(grand_livre, self).preprocess(objects, data, newids)

	def lines(self, account):
		self.cr.execute(
			"select l.date, j.code, l.ref, l.name, l.debit, l.credit " \
			"from account_move_line l left join account_journal j on (l.journal_id=j.id) " \
			"where account_id=%d and date>=%s and date<=%s and (l.state<>'draft') " \
			"order by l.id",
			(account.id, self.datas['form']['date1'], self.datas['form']['date2']))
		res = self.cr.dictfetchall()
		sum = 0.0
		for r in res:
			sum += r['debit'] - r['credit']
			r['progress'] = sum 
		return res
		
	def _sum_debit_account(self, account):
		self.cr.execute("select sum(debit) from account_move_line where account_id=%d and date>=%s and date<=%s and (state<>'draft')", (account.id, self.datas['form']['date1'], self.datas['form']['date2']))
		return self.cr.fetchone()[0] or 0.0
		
	def _sum_credit_account(self, account):
		self.cr.execute("select sum(credit) from account_move_line where account_id=%d and date>=%s and date<=%s and (state<>'draft')", (account.id, self.datas['form']['date1'], self.datas['form']['date2']))
		return self.cr.fetchone()[0] or 0.0
		
	def _sum_debit(self):
		if not self.ids:
			return 0.0
		self.cr.execute("select sum(debit) from account_move_line where account_id in (" + ','.join(map(str, self.ids)) + ") and date>=%s and date<=%s and (state<>'draft')", (self.datas['form']['date1'], self.datas['form']['date2']))
		return self.cr.fetchone()[0] or 0.0
		
	def _sum_credit(self):
		if not self.ids:
			return 0.0
		self.cr.execute("select sum(credit) from account_move_line where account_id in (" +','.join(map(str, self.ids)) + ") and date>=%s and date<=%s and (state<>'draft')", (self.datas['form']['date1'], self.datas['form']['date2']))
		return self.cr.fetchone()[0] or 0.0
report_sxw.report_sxw('report.account.grand.livre', 'account.account', 'addons/account/report/grand_livre.rml',parser=grand_livre)

