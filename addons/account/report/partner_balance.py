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

class partner_balance(report_sxw.rml_parse):
	def __init__(self, cr, uid, name, context):
		super(partner_balance, self).__init__(cr, uid, name, context)
		self.localcontext.update( {
			'time': time,
			'lines': self.lines,
			'sum_debit': self._sum_debit,
			'sum_credit': self._sum_credit,
			'sum_litige': self._sum_litige,
			'sum_sdebit': self._sum_sdebit,
			'sum_scredit': self._sum_scredit,
			'solde_debit': self._solde_balance_debit,
			'solde_credit': self._solde_balance_credit,
			'get_company': self._get_company,
			'get_currency': self._get_currency,
		})

	def preprocess(self, objects, data, ids):
		self.cr.execute('select distinct line.partner_id \
				from account_move_line AS line, account_account AS account \
				where line.partner_id is not null and line.date>=%s and line.date<=%s \
				and line.period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d) \
				AND line.account_id = account.id AND account.company_id = %d AND account.active', (data['form']['date1'], data['form']['date2'], data['form']['fiscalyear'], data['form']['company_id']))
		new_ids = [id for (id,) in self.cr.fetchall()]
		self.cr.execute("SELECT a.id FROM account_account a LEFT JOIN account_account_type t ON (a.type=t.code) WHERE t.partner_account=TRUE AND a.company_id = %d AND a.active", (data['form']['company_id'],))
		self.account_ids = ','.join([str(a) for (a,) in self.cr.fetchall()])
		self.partner_ids = ','.join(map(str, new_ids))
		objects = self.pool.get('res.partner').browse(self.cr, self.uid, new_ids)
		super(partner_balance, self).preprocess(objects, data, new_ids)

	def lines(self):
		if not self.partner_ids:
			return []

#TODO: use an SQL CASE to compute sdebit and scredit
		self.cr.execute(
			"SELECT p.ref, p.name, sum(debit) as debit, sum(credit) as credit, " \
			"(SELECT sum(debit-credit) FROM account_move_line WHERE partner_id=p.id AND date>=%s AND date<=%s AND blocked=TRUE AND state <>'draft' AND period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d)) as enlitige " \
			"FROM account_move_line l LEFT JOIN res_partner p ON (l.partner_id=p.id) " \
			"WHERE partner_id IN (" + self.partner_ids + ") " \
			"AND account_id IN (" + self.account_ids + ") " \
			"AND l.date>=%s AND l.date<=%s " \
			"AND l.state<>'draft' " \
			"AND l.period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d) " \
			"GROUP BY p.id, p.ref, p.name " \
			"ORDER BY p.ref, p.name",
			(self.datas['form']['date1'], self.datas['form']['date2'], self.datas['form']['fiscalyear'], self.datas['form']['date1'], self.datas['form']['date2'], self.datas['form']['fiscalyear']))
		res = self.cr.dictfetchall()
		for r in res:
			r['sdebit'] = r['debit'] > r['credit'] and r['debit'] - r['credit']
			r['scredit'] = r['credit'] > r['debit'] and r['credit'] - r['debit']
		return res
		
	def _sum_debit(self):
		if not self.ids:
			return 0.0

		self.cr.execute(
			'SELECT sum(debit) ' \
			'FROM account_move_line ' \
			'WHERE partner_id IN (' + self.partner_ids + ') ' \
			'AND account_id IN (' + self.account_ids + ') ' \
			"AND state<>'draft' " \
			'AND date>=%s AND date<=%s ' \
			"AND period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d)",
			(self.datas['form']['date1'], self.datas['form']['date2'], self.datas['form']['fiscalyear']))
		return self.cr.fetchone()[0] or 0.0
		
	def _sum_credit(self):
		if not self.ids:
			return 0.0

		self.cr.execute(
			'SELECT sum(credit) ' \
			'FROM account_move_line ' \
			'WHERE partner_id IN (' + self.partner_ids + ') ' \
			'AND account_id IN (' + self.account_ids + ') ' \
			"AND state<>'draft' " \
			'AND date>=%s AND date<=%s ' \
			'AND period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d)',
			(self.datas['form']['date1'], self.datas['form']['date2'], self.datas['form']['fiscalyear']))
		return self.cr.fetchone()[0] or 0.0

	def _sum_litige(self):
		if not self.ids:
			return 0.0

		self.cr.execute(
			'SELECT sum(debit-credit) ' \
			'FROM account_move_line ' \
			'WHERE partner_id IN (' + self.partner_ids + ') ' \
			'AND account_id IN (' + self.account_ids + ') ' \
			"AND state<>'draft' " \
			'AND date>=%s AND date<=%s AND blocked=TRUE ' \
			'AND period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d)',
			(self.datas['form']['date1'], self.datas['form']['date2'], self.datas['form']['fiscalyear']))
		return self.cr.fetchone()[0] or 0.0
	
	def _sum_sdebit(self):
		if not self.ids:
			return 0.0

		self.cr.execute(
			'SELECT sum(debit-credit) ' \
			'FROM (' \
				'SELECT sum(debit), sum(credit) ' \
				'FROM account_move_line ' \
				'WHERE partner_id IN (' + self.partner_ids + ') ' \
				'AND account_id IN (' + self.account_ids + ') ' \
				'AND date>=%s AND date<=%s ' \
				"AND state<>'draft' " \
				"AND period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d) " \
				'GROUP BY partner_id' \
			') AS dc (debit,credit) ' \
			'WHERE debit>credit', 
			(self.datas['form']['date1'], self.datas['form']['date2'], self.datas['form']['fiscalyear']))
		return self.cr.fetchone()[0] or 0.0
		
	def _sum_scredit(self):
		if not self.ids:
			return 0.0

		self.cr.execute(
			'SELECT sum(credit-debit) ' \
			'FROM (' \
				'SELECT sum(debit), sum(credit) ' \
				'FROM account_move_line ' \
				'WHERE partner_id IN (' + self.partner_ids + ') ' \
				'AND account_id IN (' + self.account_ids + ') ' \
				'AND date>=%s AND date<=%s ' \
				"AND state<>'draft' " \
				"AND period_id in (SELECT id FROM account_period WHERE fiscalyear_id=%d) " \
				'GROUP BY partner_id' \
			') AS dc (debit,credit) ' \
			'WHERE credit>debit', 
			(self.datas['form']['date1'], self.datas['form']['date2'], self.datas['form']['fiscalyear']))
		return self.cr.fetchone()[0] or 0.0

	def _solde_balance_debit(self):
		debit, credit = self._sum_debit(), self._sum_credit()
		return debit > credit and debit - credit
		
	def _solde_balance_credit(self):
		debit, credit = self._sum_debit(), self._sum_credit()
		return credit > debit and credit - debit

	def _get_company(self, form):
		return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).name

	def _get_currency(self, form):
		return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).currency_id.name

report_sxw.report_sxw('report.account.partner.balance', 'res.partner', 'addons/account/report/partner_balance.rml',parser=partner_balance, header=False)

