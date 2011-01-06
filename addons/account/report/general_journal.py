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
from operator import itemgetter
import pooler
import time
from report import report_sxw

#
# Use period and Journal for selection or resources
#
class journal_print(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(journal_print, self).__init__(cr, uid, name, context=context)
        self.localcontext.update( {
            'time': time,
            'lines': self.lines,
            'periods': self.periods,
            'sum_debit_period': self._sum_debit_period,
            'sum_credit_period': self._sum_credit_period,
            'sum_debit': self._sum_debit,
            'sum_credit': self._sum_credit
        })

    def set_context(self, objects, data, ids, report_type = None):
        super(journal_print, self).set_context(objects, data, ids, report_type)

        if data['model'] == 'ir.ui.menu':
            self.period_ids = data['form']['period_id'][0][2]
            self.journal_ids = data['form']['journal_id'][0][2]
        else:
            self.cr.execute('SELECT period_id, journal_id '
                            'FROM account_journal_period '
                            'WHERE id IN %s',
                            (tuple(ids),))
            res = self.cr.fetchall()
            self.period_ids, self.journal_ids = zip(*res)

    # returns a list of period objs
    def periods(self, journal_period_objs):
        dic = {}
        def filter_unique(o):
            key = o.period_id.id
            res = key in dic
            if not res:
                dic[key] = True
            return not res
        filtered_objs = filter(filter_unique, journal_period_objs)
        return map(lambda x: x.period_id, filtered_objs)

    def lines(self, period_id, journal_id=[]):
        if type(period_id)==type([]):
            ids_final = []
            journal_peroid_obj = self.pool.get('account.journal.period')
            period_obj = self.pool.get('account.period')
            for journal in journal_id:
                    for period in period_id:
                        ids_journal_period = journal_peroid_obj.search(self.cr,self.uid, [('journal_id','=',journal),('period_id','=',period)])
                        if ids_journal_period:
                            ids_final.append(ids_journal_period[0])
            data_jour_period = journal_peroid_obj.browse(self.cr, self.uid, ids_final)
            lines_data = []
            periods = []
            for data in data_jour_period:
                if not data.period_id.id in periods:
                    periods.append(data.period_id.id)
            for period in periods:
                period_data = period_obj.browse(self.cr, self.uid, period)
                self.cr.execute(
                    'SELECT j.code, j.name, '
                    'SUM(l.debit) AS debit, SUM(l.credit) AS credit '
                    'FROM account_move_line l '
                    'LEFT JOIN account_journal j ON (l.journal_id=j.id) '
                    'WHERE period_id=%s AND journal_id IN %s '
                    'AND l.state<>\'draft\' '
                    'GROUP BY j.id, j.code, j.name', (period, tuple(journal_id)))
                res = self.cr.dictfetchall()
                if res:
                    res[0].update({'period_name':period_data.name,'pid':period})
                    lines_data.append(res) 
            return lines_data
        if not self.journal_ids:
            return []
        self.cr.execute('SELECT j.code, j.name, '
                        'SUM(l.debit) AS debit, SUM(l.credit) AS credit '
                        'FROM account_move_line l '
                        'LEFT JOIN account_journal j ON (l.journal_id=j.id) '
                        'WHERE period_id=%s AND journal_id IN %s '
                        'AND l.state<>\'draft\' '
                        'GROUP BY j.id, j.code, j.name',
                        (period_id,tuple(self.journal_ids)))
        res = self.cr.dictfetchall()
        return res

    def _sum_debit_period(self, period_id,journal_id=None):
        journals = journal_id or self.journal_ids
        if not journals:
            return 0.0
        self.cr.execute('SELECT SUM(debit) FROM account_move_line '
                        'WHERE period_id=%s AND journal_id IN %s '
                        'AND state<>\'draft\'',
                        (period_id, tuple(journals)))
        return self.cr.fetchone()[0] or 0.0

    def _sum_credit_period(self, period_id,journal_id=None):
        journals = journal_id or self.journal_ids
        if not journals:
            return 0.0
        self.cr.execute('SELECT SUM(credit) FROM account_move_line '
                        'WHERE period_id=%s AND journal_id IN %s '
                        'AND state<>\'draft\'',
                        (period_id,tuple(journals)))
        return self.cr.fetchone()[0] or 0.0

    def _sum_debit(self,period_id=None,journal_id=None):
        journals = journal_id or self.journal_ids
        periods = period_id or self.period_ids
        if not (journals and periods):
            return 0.0
        self.cr.execute('SELECT SUM(debit) FROM account_move_line '
                        'WHERE period_id IN %s '
                        'AND journal_id IN %s '
                        'AND state<>\'draft\'',
                        (tuple(periods), tuple(journals)))
        return self.cr.fetchone()[0] or 0.0

    def _sum_credit(self,period_id=None,journal_id=None):
        periods = period_id or self.period_ids
        journals = journal_id or self.journal_ids
        if not (periods and journals):
            return 0.0
        self.cr.execute('SELECT SUM(credit) FROM account_move_line '
                        'WHERE period_id IN %s '
                        'AND journal_id IN %s '
                        'AND state<>\'draft\'',
                        (tuple(periods), tuple(journals)))
        return self.cr.fetchone()[0] or 0.0
report_sxw.report_sxw('report.account.general.journal', 'account.journal.period', 'addons/account/report/general_journal.rml',parser=journal_print)
report_sxw.report_sxw('report.account.general.journal.wiz', 'account.journal.period', 'addons/account/report/wizard_general_journal.rml',parser=journal_print, header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

