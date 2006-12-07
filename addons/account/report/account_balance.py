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

import pooler
import time
from report import report_sxw

class account_balance(report_sxw.rml_parse):
	def __init__(self, cr, uid, name, context):
		super(account_balance, self).__init__(cr, uid, name, context)
		self.localcontext.update({
			'time': time,
			'lines': self.lines,
			'sum_debit': self._sum_debit,
			'sum_credit': self._sum_credit,
			'sum_sdebit': self._sum_sdebit,
			'sum_scredit': self._sum_scredit
		})
		self.context = context

	def lines(self, ids=None, done=None, level=0):
		ids = ids or self.ids
		done = done or {}
		if not self.ids:
			return []
		result = []
		for account in self.pool.get('account.account').browse(self.cr, self.uid, ids, self.context):
			if account.id in done:
				continue
			done[account.id] = 1
			res = {
				'code': account.code,
				'name': account.name,
				'debit': account.debit,
				'credit': account.credit,
				'level': level,
				'sdebit': account.debit > account.credit and account.debit - account.credit,
				'scredit': account.debit < account.credit and account.credit - account.debit,
				'balance': account.balance
			}
			if not (res['credit'] or res['debit']) and not account.child_id:
				continue
			result.append(res)
			ids2 = [(x.code,x.id) for x in account.child_id]
			ids2.sort()
			result += self.lines([x[1] for x in ids2], done, level+1)
		self.ids = done
		return result

	def _sum_debit(self):
		if not self.ids:
			return 0.0

		self.cr.execute('select sum(debit) from account_move_line where account_id in (' + ','.join(map(str, self.ids)) + ') and date>=%s and date<=%s and state<>\'draft\'', (self.datas['form']['date1'], self.datas['form']['date2']))
		return self.cr.fetchone()[0] or 0.0

	def _sum_credit(self):
		if not self.ids:
			return 0.0

		self.cr.execute('select sum(credit) from account_move_line where account_id in (' + ','.join(map(str, self.ids)) + ') and date>=%s and date<=%s and state<>\'draft\'', (self.datas['form']['date1'], self.datas['form']['date2']))
		return self.cr.fetchone()[0] or 0.0
	
	def _sum_sdebit(self):
		debit, credit = self._sum_debit(), self._sum_credit()
		return debit > credit and debit - credit
		
	def _sum_scredit(self):
		debit, credit = self._sum_debit(), self._sum_credit()
		return credit > debit and credit - debit
	
report_sxw.report_sxw('report.account.account.balance', 'account.account', 'addons/account/report/account_balance.rml', parser=account_balance)

