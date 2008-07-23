# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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

class account_analytic_quantity_cost_ledger(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(account_analytic_quantity_cost_ledger, self).__init__(cr, uid,
                name, context)
        self.localcontext.update( {
            'time': time,
            'lines_g': self._lines_g,
            'lines_a': self._lines_a,
            'sum_quantity': self._sum_quantity,
            'account_sum_quantity': self._account_sum_quantity,
        })

    def _lines_g(self, account_id, date1, date2, journals):
        if not journals or not journals[0][2]:
            self.cr.execute("SELECT sum(aal.unit_amount) AS quantity, \
                        aa.code AS code, aa.name AS name, aa.id AS id \
                    FROM account_account AS aa, account_analytic_line AS aal \
                    WHERE (aal.account_id=%d) AND (aal.date>=%s) \
                        AND (aal.date<=%s) AND (aal.general_account_id=aa.id) \
                        AND aa.active \
                    GROUP BY aa.code, aa.name, aa.id ORDER BY aa.code",
                    (account_id, date1, date2))
        else:
            journal_ids = journals[0][2]
            self.cr.execute("SELECT sum(aal.unit_amount) AS quantity, \
                        aa.code AS code, aa.name AS name, aa.id AS id \
                    FROM account_account AS aa, account_analytic_line AS aal \
                    WHERE (aal.account_id=%d) AND (aal.date>=%s) \
                        AND (aal.date<=%s) AND (aal.general_account_id=aa.id) \
                        AND aa.active \
                        AND (aal.journal_id IN (" +
                        ','.join(map(str, journal_ids)) + ")) \
                    GROUP BY aa.code, aa.name, aa.id ORDER BY aa.code",
                    (account_id, date1, date2))
        res = self.cr.dictfetchall()
        return res

    def _lines_a(self, general_account_id, account_id, date1, date2, journals):
        if not journals or not journals[0][2]:
            self.cr.execute("SELECT aal.name AS name, aal.code AS code, \
                        aal.unit_amount AS quantity, aal.date AS date, \
                        aaj.code AS cj \
                    FROM account_analytic_line AS aal, \
                        account_analytic_journal AS aaj \
                    WHERE (aal.general_account_id=%d) AND (aal.account_id=%d) \
                        AND (aal.date>=%s) AND (aal.date<=%s) \
                        AND (aal.journal_id=aaj.id) \
                    ORDER BY aal.date, aaj.code, aal.code",
                    (general_account_id, account_id, date1, date2))
        else:
            journal_ids = journals[0][2]
            self.cr.execute("SELECT aal.name AS name, aal.code AS code, \
                        aal.unit_amount AS quantity, aal.date AS date, \
                        aaj.code AS cj \
                    FROM account_analytic_line AS aal, \
                        account_analytic_journal AS aaj \
                    WHERE (aal.general_account_id=%d) AND (aal.account_id=%d) \
                        AND (aal.date>=%s) AND (aal.date<=%s) \
                        AND (aal.journal_id=aaj.id) AND (aaj.id IN (" +
                        ','.join(map(str, journal_ids)) + ")) \
                    ORDER BY aal.date, aaj.code, aal.code",
                    (general_account_id, account_id, date1, date2))
        res = self.cr.dictfetchall()
        return res

    def _account_sum_quantity(self, account_id, date1, date2, journals):
        if not journals or not journals[0][2]:
            self.cr.execute("SELECT sum(unit_amount) \
                    FROM account_analytic_line \
                    WHERE account_id=%d AND date>=%s AND date<=%s",
                    (account_id, date1, date2))
        else:
            journal_ids = journals[0][2]
            self.cr.execute("SELECT sum(unit_amount) \
                    FROM account_analytic_line \
                    WHERE account_id = %d AND date >= %s AND date <= %s \
                        AND journal_id IN (" +
                        ','.join(map(str, journal_ids)) + ")",
                        (account_id, date1, date2))
        return self.cr.fetchone()[0] or 0.0

    def _sum_quantity(self, accounts, date1, date2, journals):
        ids = map(lambda x: x.id, accounts)
        if not len(ids):
            return 0.0
        if not journals or not journals[0][2]:
            self.cr.execute("SELECT sum(unit_amount) \
                    FROM account_analytic_line \
                    WHERE account_id IN (" +
                    ','.join(map(str, ids)) + ") AND date>=%s AND date<=%s",
                    (date1, date2))
        else:
            journal_ids = journals[0][2]
            self.cr.execute("SELECT sum(unit_amount) \
                    FROM account_analytic_line \
                    WHERE account_id IN (" +
                    ','.join(map(str, ids)) + ") AND date >= %s AND date <= %s \
                        AND journal_id IN (" +
                        ','.join(map(str, journal_ids)) + ")",
                        (date1, date2))
        return self.cr.fetchone()[0] or 0.0

report_sxw.report_sxw('report.account.analytic.account.quantity_cost_ledger',
        'account.analytic.account',
        'addons/account/project/report/quantity_cost_ledger.rml',
        parser=account_analytic_quantity_cost_ledger, header=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

