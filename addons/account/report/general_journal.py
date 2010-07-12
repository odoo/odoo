# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time

import pooler
from account_journal_common_default import account_journal_common_default
from report import report_sxw
#
# Use period and Journal for selection or resources
#
class journal_print(report_sxw.rml_parse, account_journal_common_default):
    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(journal_print, self).__init__(cr, uid, name, context=context)
        self.period_ids = []
        self.journal_ids = []
        self.localcontext.update( {
            'time': time,
            'lines': self.lines,
            'periods': self.periods,
            'sum_debit_period': self._sum_debit_period,
            'sum_credit_period': self._sum_credit_period,
            'sum_debit': self._sum_debit,
            'sum_credit': self._sum_credit,
            'get_start_date': self.get_start_date,
            'get_end_date': self.get_end_date,
            'get_filter': self._get_filter
        })

    def set_context(self, objects, data, ids, report_type=None):
        new_ids = ids
        self.query_get_clause = ''
        if (data['model'] == 'ir.ui.menu'):
            new_ids = 'active_ids' in data['form'] and data['form']['active_ids'] or []
            self.query_get_clause = 'AND '
            self.query_get_clause += data['form']['query_line'] or ''
            objects = self.pool.get('account.journal.period').browse(self.cr, self.uid, new_ids)
        if new_ids:
            self.cr.execute('SELECT period_id, journal_id FROM account_journal_period WHERE id IN %s', (tuple(new_ids),))
            res = self.cr.fetchall()
            self.period_ids, self.journal_ids = zip(*res)
        return super(journal_print, self).set_context(objects, data, ids, report_type)

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
        if not self.journal_ids:
            return []
        self.cr.execute('SELECT j.code, j.name, '
                        'SUM(l.debit) AS debit, SUM(l.credit) AS credit '
                        'FROM account_move_line l '
                        'LEFT JOIN account_journal j ON (l.journal_id=j.id) '
                        'WHERE period_id=%s AND journal_id IN %s '+self.query_get_clause +''
                        'GROUP BY j.id, j.code, j.name',
                        (period_id, tuple(self.journal_ids)))

        res = self.cr.dictfetchall()
        return res

#    def _sum_debit_period(self, period_id, journal_id=None):
#        journals = journal_id or self.journal_ids
#        if not journals:
#            return 0.0
#        self.cr.execute('SELECT SUM(debit) FROM account_move_line l '
#                        'WHERE period_id=%s AND journal_id IN %s '+ self.query_get_clause +'',
#                        (period_id, tuple(journals)))
#
#        return self.cr.fetchone()[0] or 0.0
#
#    def _sum_credit_period(self, period_id, journal_id=None):
#        journals = journal_id or self.journal_ids
#        if not journals:
#            return 0.0
#        self.cr.execute('SELECT SUM(credit) FROM account_move_line l '
#                        'WHERE period_id=%s AND journal_id IN %s '+self.query_get_clause +' ',
#                        (period_id, tuple(journals)))
#        return self.cr.fetchone()[0] or 0.0

#    def _sum_debit(self, period_id=None, journal_id=None):
#        journals = journal_id or self.journal_ids
#        periods = period_id or self.period_ids
#        if not (journals and periods):
#            return 0.0
#        self.cr.execute('SELECT SUM(debit) FROM account_move_line l '
#                        'WHERE period_id IN %s '
#                        'AND journal_id IN %s '+self.query_get_clause +'',
#                        (tuple(periods), tuple(journals)))
#        res = self.cr.fetchone()[0]
#        return  res or 0.0
#
#    def _sum_credit(self, period_id=None, journal_id=None):
#        periods = period_id or self.period_ids
#        journals = journal_id or self.journal_ids
#        if not (periods and journals):
#            return 0.0
#        self.cr.execute('SELECT SUM(credit) FROM account_move_line l '
#                        'WHERE period_id IN %s '
#                        'AND journal_id IN %s '+self.query_get_clause +'',
#                        (tuple(periods), tuple(journals)))
#        return self.cr.fetchone()[0] or 0.0

    def get_start_date(self, form):
        return pooler.get_pool(self.cr.dbname).get('account.period').browse(self.cr,self.uid,form['period_from']).name

    def get_end_date(self, form):
        return pooler.get_pool(self.cr.dbname).get('account.period').browse(self.cr,self.uid,form['period_to']).name

report_sxw.report_sxw('report.account.general.journal', 'account.journal.period', 'addons/account/report/general_journal.rml', parser=journal_print, header=False)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
