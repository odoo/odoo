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

class third_party_ledger(report_sxw.rml_parse):
	def __init__(self, cr, uid, name, context):
		super(third_party_ledger, self).__init__(cr, uid, name, context)
		self.localcontext.update( {
			'time': time,
			'lines': self.lines,
			'sum_debit_partner': self._sum_debit_partner,
			'sum_credit_partner': self._sum_credit_partner,
			'sum_debit': self._sum_debit,
			'sum_credit': self._sum_credit,
			'get_company': self._get_company,
			'get_currency': self._get_currency,
		})

	def preprocess(self, objects, data, ids):
		self.cr.execute(
			"SELECT DISTINCT line.partner_id " \
			"FROM account_move_line AS line, account_account AS account " \
<<<<<<< HEAD:server/bin/addons/account/report/third_party_ledger.py
			"WHERE line.partner_id IS NOT NULL AND line.date>=%s AND line.date<=%s AND line.state<>'draft' AND line.period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d) " \
			"AND line.account_id = account.id AND account.company_id = %d AND account.active",
=======
			"WHERE line.partner_id IS NOT NULL AND line.date>=%s AND line.date<=%s AND line.state<>'draft' AND line.period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d)" \
			"AND line.account_id = account.id AND account.company_id = %d",
>>>>>>> account: add multi company to third party ledger report:server/bin/addons/account/report/third_party_ledger.py
			(data['form']['date1'], data['form']['date2'], data['form']['fiscalyear'], data['form']['company_id']))
		new_ids = [id for (id,) in self.cr.fetchall()]
		self.cr.execute(
			"SELECT a.id " \
			"FROM account_account a LEFT JOIN account_account_type t ON (a.type=t.code) " \
<<<<<<< HEAD:server/bin/addons/account/report/third_party_ledger.py
			"WHERE t.partner_account=TRUE AND a.company_id = %d AND a.active", (data['form']['company_id'],))
=======
			"WHERE t.partner_account=TRUE AND a.company_id = %d", (data['form']['company_id'],))
>>>>>>> account: add multi company to third party ledger report:server/bin/addons/account/report/third_party_ledger.py
		self.account_ids = ','.join([str(a) for (a,) in self.cr.fetchall()])
		self.partner_ids = ','.join(map(str, new_ids))
		objects = self.pool.get('res.partner').browse(self.cr, self.uid, new_ids)
		super(third_party_ledger, self).preprocess(objects, data, new_ids)

	def lines(self, partner):
		self.cr.execute(
			"SELECT l.date, j.code, l.ref, l.name, l.debit, l.credit " \
			"FROM account_move_line l LEFT JOIN account_journal j ON (l.journal_id=j.id) " \
			"WHERE l.partner_id=%d " \
			"AND l.account_id IN (" + self.account_ids + ") " \
			"AND l.date>=%s AND l.date<=%s  AND state<>'draft' " \
			"AND l.period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d) "\
			"ORDER BY l.id", 
			(partner.id, self.datas['form']['date1'], self.datas['form']['date2'], self.datas['form']['fiscalyear']))
		res = self.cr.dictfetchall()
		sum = 0.0
		for r in res:
			sum += r['debit'] - r['credit']
			r['progress'] = sum 
		return res
		
	def _sum_debit_partner(self, partner):
		self.cr.execute(
			"SELECT sum(debit) " \
			"FROM account_move_line " \
			"WHERE partner_id=%d " \
			"AND account_id IN (" + self.account_ids + ") " \
			"AND date>=%s AND date<=%s AND state<>'draft' " \
			"AND period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d)",
			(partner.id, self.datas['form']['date1'], self.datas['form']['date2'], self.datas['form']['fiscalyear']))
		return self.cr.fetchone()[0] or 0.0
		
	def _sum_credit_partner(self, partner):
		self.cr.execute(
			"SELECT sum(credit) " \
			"FROM account_move_line " \
			"WHERE partner_id=%d " \
			"AND account_id IN (" + self.account_ids + ") " \
			"AND date>=%s AND date<=%s AND state<>'draft' " \
			"AND period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d)",
			(partner.id, self.datas["form"]["date1"], self.datas["form"]["date2"], self.datas['form']['fiscalyear']))
		return self.cr.fetchone()[0] or 0.0
		
	def _sum_debit(self):
		if not self.ids:
			return 0.0

		self.cr.execute(
			"SELECT sum(debit) " \
			"FROM account_move_line " \
			"WHERE partner_id IN (" + self.partner_ids + ") " \
			"AND account_id IN (" + self.account_ids + ") " \
			"AND date>=%s AND date<=%s AND state<>'draft'" \
			"AND period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d)",
			(self.datas['form']['date1'], self.datas['form']['date2'], self.datas['form']['fiscalyear']))
		return self.cr.fetchone()[0] or 0.0
		
	def _sum_credit(self):
		if not self.ids:
			return 0.0

		self.cr.execute(
			"SELECT sum(credit) " \
			"FROM account_move_line " \
			"WHERE partner_id IN (" + self.partner_ids + ") " \
			"AND account_id IN (" + self.account_ids + ") " \
			"AND date>=%s AND date<=%s AND state<>'draft'" \
			"AND period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d)",
			(self.datas['form']['date1'], self.datas['form']['date2'], self.datas['form']['fiscalyear']))
		return self.cr.fetchone()[0] or 0.0

	def _get_company(self, form):
		return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).name

	def _get_currency(self, form):
		return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).currency_id.name

report_sxw.report_sxw('report.account.third_party_ledger', 'res.partner', 'addons/account/report/third_party_ledger.rml',parser=third_party_ledger, header=False)

