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

class account_analytic_year_to_date_check(report_sxw.rml_parse):
	def __init__(self, cr, uid, name, context):
		super(account_analytic_year_to_date_check, self).__init__(cr, uid, name, context)
		self.localcontext.update( {
			'time': time,
			'start_date': self._get_start_date,
			'end_date': self._get_end_date,
			'lines_p': self._lines_p,
			'general_debit': self._gen_deb,
			'general_credit': self._gen_cred,
			'analytic_debit': self._ana_deb,
			'analytic_credit': self._ana_cred,
			'delta_debit': self._delta_deb,
			'delta_credit': self._delta_cred,
		})

	def _get_periods(self, date1, date2):
		self.cr.execute("SELECT name, date_start, date_stop FROM account_period WHERE (date_start>=%s) AND (date_stop<=%s) ORDER BY date_start, date_stop", (date1, date2))
		return self.cr.dictfetchall()
	
	def _get_start_date(self, date1, date2):
		periods = self._get_periods(date1, date2)
		return periods[0]['date_start']
		
	def _get_end_date(self, date1, date2):
		periods = self._get_periods(date1, date2)
		return periods[-1]['date_stop']

	def _lines_p(self, date1, date2):
		periods = self._get_periods(date1, date2)
		for r in periods:
			self.cr.execute("SELECT sum(debit),sum(credit) FROM account_move_line WHERE (date>=%s) AND (date<=%s) AND state<>'draft'", (r['date_start'], r['date_stop']))
			(gd, gc) = self.cr.fetchone()
			gd = gd or 0.0
			gc = gc or 0.0
			self.cr.execute("SELECT sum(amount) AS balance FROM account_analytic_line WHERE (date>=%s) AND (date<=%s) AND (amount>0)", (r['date_start'], r['date_stop']))
			(ad,) = self.cr.fetchone()
			ad = ad or 0.0

			self.cr.execute("SELECT sum(amount) AS balance FROM account_analytic_line WHERE (date>=%s) AND (date<=%s) AND (amount<0)", (r['date_start'], r['date_stop']))
			(ac,) = self.cr.fetchone()
			ac = ac or 0.0

			r['gen_debit'] = '%.2f' % gd
			r['gen_credit'] = '%.2f' % gc
			r['ana_debit'] = '%.2f' % ad
			r['ana_credit'] = '%.2f' % ac
			r['delta_debit'] = '%.2f' % (gd - ad) or ''
			r['delta_credit'] = '%.2f' % (gc - ac) or ''
		return periods


	def _gen_deb(self, date1, date2):
		start = self._get_start_date(date1, date2)
		stop = self._get_end_date(date1, date2)
		self.cr.execute("SELECT sum(debit) FROM account_move_line WHERE date>=%s AND date<=%s AND state<>'draft'", (start, stop))
		return self.cr.fetchone()[0] or 0.0
	
	def _gen_cred(self, date1, date2):
		start = self._get_start_date(date1, date2)
		stop = self._get_end_date(date1, date2)
		self.cr.execute("SELECT sum(credit) FROM account_move_line WHERE date>=%s AND date<=%s AND state<>'draft'", (start, stop))
		return self.cr.fetchone()[0] or 0.0
	
	def _ana_deb(self, date1, date2):
		start = self._get_start_date(date1, date2)
		stop = self._get_end_date(date1, date2)
		self.cr.execute("SELECT sum(amount) FROM account_analytic_line WHERE date>=%s AND date<=%s AND amount>0", (start, stop))
		return self.cr.fetchone()[0] or 0.0
	
	def _ana_cred(self, date1, date2):
		start = self._get_start_date(date1, date2)
		stop = self._get_end_date(date1, date2)
		self.cr.execute("SELECT sum(amount) FROM account_analytic_line WHERE date>=%s AND date<=%s AND amount<0", (start, stop))
		res = self.cr.fetchone()[0] or 0.0
		return abs(res)
	
	def _delta_deb(self, date1, date2):
		return (self._gen_deb(date1,date2)-self._ana_deb(date1,date2))
		
	def _delta_cred(self, date1, date2):
		return (self._gen_cred(date1,date2)-self._ana_cred(date1,date2))

report_sxw.report_sxw('report.account.analytic.account.year_to_date_check', 'account.analytic.account', 'addons/account/project/report/year_to_date_check.rml',parser=account_analytic_year_to_date_check)

