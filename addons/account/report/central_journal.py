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

import time
from report import report_sxw

#
# Use period and Journal for selection or resources
#
class journal_print(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(journal_print, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'lines': self.lines,
            'sum_debit': self._sum_debit,
            'sum_credit': self._sum_credit
        })

    def lines(self, period_id, journal_id, *args):
        if type(period_id)==type([]):
            ids_final = []
            journal_obj = self.pool.get('account.journal')
            period_obj = self.pool.get('account.period')
            journal_period_obj = self.pool.get('account.journal.period')
            for journal in journal_id:
                a = {'journal':journal_obj.browse(self.cr, self.uid, journal)}
                for period in period_id:
                    ids_journal_period = journal_period_obj.search(self.cr,self.uid, [('journal_id','=',journal),('period_id','=',period)])
                    if ids_journal_period:
                        self.cr.execute('select a.code, a.name, sum(debit) as debit, sum(credit) as credit from account_move_line l left join account_account a on (l.account_id=a.id) where l.period_id=%s and l.journal_id=%s and l.state<>\'draft\' group by a.id, a.code, a.name, l.journal_id, l.period_id', (period, journal))
                        res = self.cr.dictfetchall()
                        if res:
                            a.update({'period':period_obj.browse(self.cr, self.uid, period)})
                            res[0].update(a)
                            ids_final.append(res)
            return ids_final
        self.cr.execute('select a.code, a.name, sum(debit) as debit, sum(credit) as credit from account_move_line l left join account_account a on (l.account_id=a.id) where l.period_id=%s and l.journal_id=%s and l.state<>\'draft\' group by a.id, a.code, a.name', (period_id, journal_id))
        res = self.cr.dictfetchall()
        return res

    def _sum_debit(self, period_id, journal_id):
        self.cr.execute('select sum(debit) from account_move_line where period_id=%s and journal_id=%s and state<>\'draft\'', (period_id, journal_id))
        return self.cr.fetchone()[0] or 0.0

    def _sum_credit(self, period_id, journal_id):
        self.cr.execute('select sum(credit) from account_move_line where period_id=%s and journal_id=%s and state<>\'draft\'', (period_id, journal_id))
        return self.cr.fetchone()[0] or 0.0
report_sxw.report_sxw('report.account.central.journal', 'account.journal.period', 'addons/account/report/central_journal.rml',parser=journal_print, header=False)
report_sxw.report_sxw('report.account.central.journal.wiz', 'account.journal.period', 'addons/account/report/wizard_central_journal.rml',parser=journal_print, header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

