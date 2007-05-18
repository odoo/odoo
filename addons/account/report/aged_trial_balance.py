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
import pooler
from report import report_sxw

class aged_trial_report(report_sxw.rml_parse):
	def __init__(self, cr, uid, name, context):
		super(aged_trial_report, self).__init__(cr, uid, name, context)
		self.localcontext.update({
			'time': time,
			'get_lines': self._get_lines,
			'get_total': self._get_total,
			'get_before': self._get_before,
			'get_for_period': self._get_for_period,
		})
	
	def _add_header(self, node):
		return True

	def _get_lines(self, form):
		res = []
		self.cr.execute("SELECT DISTINCT res_partner.id AS id, res_partner.name AS name \
						FROM res_partner, account_move_line AS line, account_account \
						WHERE (line.account_id=account_account.id) AND (line.reconcile_id IS NULL) \
						AND (line.partner_id=res_partner.id) AND (line.state<>'draft') \
						AND (line.period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d))\
						ORDER BY res_partner.name" % (form['fiscalyear'],))
		partners = self.cr.dictfetchall()
		for partner in partners:
			values = {}
			self.cr.execute("SELECT SUM(debit-credit) FROM account_move_line AS line, account_account \
				WHERE (line.account_id=account_account.id) AND (account_account.type IN ('payable','receivable')) \
				AND (date<'%s') AND (partner_id=%d) AND (reconcile_id IS NULL) AND (line.state<>'draft') AND (line.period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d))" % (form['0']['start'], partner['id'], form['fiscalyear']))
			before = self.cr.fetchone()
			values['before'] = before and before[0] or ""
			for i in range(5):
				self.cr.execute("SELECT SUM(debit-credit) FROM account_move_line AS line, account_account \
									WHERE (line.account_id=account_account.id) AND (account_account.type IN ('payable','receivable')) \
										AND (date>='%s') AND (date<='%s') AND (partner_id=%d) AND (reconcile_id IS NULL) AND line.state<>'draft' AND (line.period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d))" % (form[str(i)]['start'], form[str(i)]['stop'], partner['id'], form['fiscalyear']))
				during = self.cr.fetchone()
				values[str(i)] = during and during[0] or ""

			self.cr.execute("SELECT SUM(debit-credit) FROM account_move_line AS line, account_account \
								WHERE (line.account_id=account_account.id) AND (account_account.type IN ('payable','receivable')) \
									AND (partner_id=%d) AND (reconcile_id IS NULL) AND (line.state<>'draft') AND (line.period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d))" % (partner['id'], form['fiscalyear']))
			total = self.cr.fetchone()
			values['total'] = total and total[0] or 0.0
			values['name'] = partner['name']
			t = 0.0
			for i in range(5)+['before']:
				t+= float(values.get(str(i), 0.0) or 0.0)
			if values['total']:
				res.append(values)
		total = 0.0
		totals = {}
		for r in res:
			total += float(r['total'] or 0.0)
			for i in range(5)+['before']:
				totals.setdefault(str(i), 0.0)
				totals[str(i)] += float(r[str(i)] or 0.0)
		return res
	
	def _get_total(self, fiscalyear):
		self.cr.execute("SELECT SUM(debit-credit) FROM account_move_line AS line, account_account \
							WHERE (line.account_id=account_account.id) AND (account_account.type IN ('payable','receivable')) AND reconcile_id IS NULL AND (line.state<>'draft') and partner_id is not null AND (line.period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d))" % (fiscalyear,))
		total = self.cr.fetchone()
		return total and total[0] or 0.0
	
	def _get_before(self, date, fiscalyear):
		self.cr.execute("SELECT SUM(debit-credit) FROM account_move_line AS line, account_account \
							WHERE (line.account_id=account_account.id) AND (account_account.type IN ('payable','receivable')) AND reconcile_id IS NULL AND (date<'%s') and (line.state<>'draft') and partner_id is not null AND (line.period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d))" % (date, fiscalyear))
		before = self.cr.fetchone()
		return before and before[0] or 0.0

	def _get_for_period(self, period, fiscalyear):
		self.cr.execute("SELECT SUM(debit-credit) FROM account_move_line AS line, account_account \
							WHERE (line.account_id=account_account.id) AND (account_account.type IN ('payable','receivable')) \
								AND reconcile_id IS NULL AND (date>='%s') AND (date<='%s') and (line.state<>'draft') and partner_id is not null AND (line.period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d))" % (period['start'], period['stop'], fiscalyear))
		period = self.cr.fetchone()
		return period and period[0] or 0.0
	
report_sxw.report_sxw(
	'report.account.aged.trial.balance',
	'res.partner',
	'addons/account/report/aged_trial_balance.rml',
	parser=aged_trial_report)

