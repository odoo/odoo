# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import pooler
import time
from report import report_sxw

class account_analytic_quantity_cost_ledger(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(account_analytic_quantity_cost_ledger, self).__init__(cr, uid, name, context=context)
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
                    WHERE (aal.account_id=%s) AND (aal.date>=%s) \
                        AND (aal.date<=%s) AND (aal.general_account_id=aa.id) \
                        AND aa.active \
                    GROUP BY aa.code, aa.name, aa.id ORDER BY aa.code",
                    (account_id, date1, date2))
        else:
            journal_ids = journals[0][2]
            self.cr.execute("SELECT sum(aal.unit_amount) AS quantity, \
                        aa.code AS code, aa.name AS name, aa.id AS id \
                    FROM account_account AS aa, account_analytic_line AS aal \
                    WHERE (aal.account_id=%s) AND (aal.date>=%s) \
                        AND (aal.date<=%s) AND (aal.general_account_id=aa.id) \
                        AND aa.active \
                        AND (aal.journal_id IN %s) \
                    GROUP BY aa.code, aa.name, aa.id ORDER BY aa.code",
                    (account_id, date1, date2, tuple(journal_ids)))
        res = self.cr.dictfetchall()
        return res

    def _lines_a(self, general_account_id, account_id, date1, date2, journals):
        if not journals or not journals[0][2]:
            self.cr.execute("SELECT aal.name AS name, aal.code AS code, \
                        aal.unit_amount AS quantity, aal.date AS date, \
                        aaj.code AS cj \
                    FROM account_analytic_line AS aal, \
                        account_analytic_journal AS aaj \
                    WHERE (aal.general_account_id=%s) AND (aal.account_id=%s) \
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
                    WHERE (aal.general_account_id=%s) AND (aal.account_id=%s) \
                        AND (aal.date>=%s) AND (aal.date<=%s) \
                        AND (aal.journal_id=aaj.id) AND (aaj.id IN %s) \
                    ORDER BY aal.date, aaj.code, aal.code",
                    (general_account_id, account_id,
                     date1, date2, tuple(journal_ids)))
        res = self.cr.dictfetchall()
        return res

    def _account_sum_quantity(self, account_id, date1, date2, journals):
        if not journals or not journals[0][2]:
            self.cr.execute("SELECT sum(unit_amount) \
                    FROM account_analytic_line \
                    WHERE account_id=%s AND date>=%s AND date<=%s",
                    (account_id, date1, date2))
        else:
            journal_ids = journals[0][2]
            self.cr.execute("SELECT sum(unit_amount) \
                    FROM account_analytic_line \
                    WHERE account_id = %s AND date >= %s AND date <= %s \
                        AND journal_id IN %s",
                        (account_id, date1, date2, tuple(journal_ids)))
        return self.cr.fetchone()[0] or 0.0

    def _sum_quantity(self, accounts, date1, date2, journals):
        ids = map(lambda x: x.id, accounts)
        if not len(ids):
            return 0.0
        if not journals or not journals[0][2]:
            self.cr.execute("SELECT sum(unit_amount) \
                    FROM account_analytic_line \
                    WHERE account_id IN %s AND date>=%s AND date<=%s",
                    (tuple(ids), date1, date2))
        else:
            journal_ids = journals[0][2]
            self.cr.execute("SELECT sum(unit_amount) \
                    FROM account_analytic_line \
                    WHERE account_id IN %s AND date >= %s AND date <= %s \
                        AND journal_id IN %s",
                        (tuple(ids), date1, date2, tuple(journal_ids)))
        return self.cr.fetchone()[0] or 0.0

report_sxw.report_sxw('report.account.analytic.account.quantity_cost_ledger',
        'account.analytic.account',
        'addons/account/project/report/quantity_cost_ledger.rml',
        parser=account_analytic_quantity_cost_ledger, header=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

