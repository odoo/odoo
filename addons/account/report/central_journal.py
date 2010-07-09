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

from report import report_sxw
import pooler
#
# Use period and Journal for selection or resources
#
class journal_print(report_sxw.rml_parse):

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

    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(journal_print, self).__init__(cr, uid, name, context=context)
        self.period_ids = []
        self.journal_ids = []
        self.localcontext.update({
            'time': time,
            'lines': self.lines,
            'sum_debit': self._sum_debit,
            'sum_credit': self._sum_credit,
            'get_start_date': self.get_start_date,
            'get_end_date': self.get_end_date
        })

    def lines(self, period_id, journal_id):
        self.cr.execute('SELECT a.code, a.name, SUM(debit) AS debit, SUM(credit) AS credit from account_move_line l LEFT JOIN account_account a ON (l.account_id=a.id) WHERE l.period_id=%s AND l.journal_id=%s '+self.query_get_clause+' GROUP BY a.id, a.code, a.name', (period_id, journal_id))
        res = self.cr.dictfetchall()
        return res

    def _sum_debit(self, period_id, journal_id):
        self.cr.execute('SELECT SUM(debit) FROM account_move_line l WHERE period_id=%s AND journal_id=%s '+self.query_get_clause+' ', (period_id, journal_id))
        return self.cr.fetchone()[0] or 0.0

    def _sum_credit(self, period_id, journal_id):
        self.cr.execute('SELECT SUM(credit) FROM account_move_line l WHERE period_id=%s AND journal_id=%s '+self.query_get_clause+'', (period_id, journal_id))
        return self.cr.fetchone()[0] or 0.0

    def get_start_date(self, form):
        return pooler.get_pool(self.cr.dbname).get('account.period').browse(self.cr,self.uid,form['period_from']).name

    def get_end_date(self, form):
        return pooler.get_pool(self.cr.dbname).get('account.period').browse(self.cr,self.uid,form['period_to']).name

report_sxw.report_sxw('report.account.central.journal', 'account.journal.period', 'addons/account/report/central_journal.rml', parser=journal_print, header=False)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
