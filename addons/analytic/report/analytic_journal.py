# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from openerp.osv import osv
from openerp.report import report_sxw


#
# Use period and Journal for selection or resources
#
class account_analytic_journal(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(account_analytic_journal, self).__init__(cr, uid, name, context=context)
        self.localcontext.update( {
            'time': time,
            'lines': self._lines,
            'lines_a': self._lines_a,
            'sum_general': self._sum_general,
            'sum_analytic': self._sum_analytic,
        })

    def _lines(self, journal_id, date1, date2):
        self.cr.execute('SELECT DISTINCT move_id FROM account_analytic_line WHERE (date>=%s) AND (date<=%s) AND (journal_id=%s) AND (move_id is not null)', (date1, date2, journal_id,))
        ids = map(lambda x: x[0], self.cr.fetchall())
        return self.pool.get('account.move.line').browse(self.cr, self.uid, ids)

    def _lines_a(self, move_id, journal_id, date1, date2):
        ids = self.pool.get('account.analytic.line').search(self.cr, self.uid, [('move_id','=',move_id), ('journal_id','=',journal_id), ('date','>=',date1), ('date','<=',date2)])
        if not ids:
            return []
        return self.pool.get('account.analytic.line').browse(self.cr, self.uid, ids)
        
    def _sum_general(self, journal_id, date1, date2):
        self.cr.execute('SELECT SUM(debit-credit) FROM account_move_line WHERE id IN (SELECT move_id FROM account_analytic_line WHERE (date>=%s) AND (date<=%s) AND (journal_id=%s) AND (move_id is not null))', (date1, date2, journal_id,))
        return self.cr.fetchall()[0][0] or 0

    def _sum_analytic(self, journal_id, date1, date2):
        self.cr.execute("SELECT SUM(amount) FROM account_analytic_line WHERE date>=%s AND date<=%s AND journal_id=%s", (date1, date2, journal_id))
        res = self.cr.dictfetchone()
        return res['sum'] or 0


class report_analyticjournal(osv.AbstractModel):
    _name = 'report.account.report_analyticjournal'
    _inherit = 'report.abstract_report'
    _template = 'analytic.report_analyticjournal'
    _wrapped_report_class = account_analytic_journal
