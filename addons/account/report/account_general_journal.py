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
from xlwt import Workbook, easyxf
from openerp.osv import osv
from openerp.report import report_sxw
from common_report_header import common_report_header


class journal_print(report_sxw.rml_parse, common_report_header):

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
            'get_fiscalyear': self._get_fiscalyear,
            'get_account': self._get_account,
            'get_start_period': self.get_start_period,
            'get_end_period': self.get_end_period,
            'get_sortby': self._get_sortby,
            'get_filter': self._get_filter,
            'get_journal': self._get_journal,
            'get_start_date':self._get_start_date,
            'get_end_date':self._get_end_date,
            'display_currency':self._display_currency,
            'get_target_move': self._get_target_move,
        })

    def set_context(self, objects, data, ids, report_type=None):
        obj_move = self.pool.get('account.move.line')
        new_ids = ids
        self.query_get_clause = ''
        self.target_move = data['form'].get('target_move', 'all')
        if (data['model'] == 'ir.ui.menu'):
            new_ids = 'active_ids' in data['form'] and data['form']['active_ids'] or []
            self.query_get_clause = 'AND '
            self.query_get_clause += obj_move._query_get(self.cr, self.uid, obj='l', context=data['form'].get('used_context', {}))
            objects = self.pool.get('account.journal.period').browse(self.cr, self.uid, new_ids)
        if new_ids:
            self.cr.execute('SELECT period_id, journal_id FROM account_journal_period WHERE id IN %s', (tuple(new_ids),))
            res = self.cr.fetchall()
            self.period_ids, self.journal_ids = zip(*res)
        return super(journal_print, self).set_context(objects, data, ids, report_type=report_type)

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

    def lines(self, period_id):
        if not self.journal_ids:
            return []
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']
        self.cr.execute('SELECT j.code, j.name, l.amount_currency,c.symbol AS currency_code,l.currency_id, '
                        'SUM(l.debit) AS debit, SUM(l.credit) AS credit '
                        'FROM account_move_line l '
                        'LEFT JOIN account_move am ON (l.move_id=am.id) '
                        'LEFT JOIN account_journal j ON (l.journal_id=j.id) '
                        'LEFT JOIN res_currency c on (l.currency_id=c.id)'
                        'WHERE am.state IN %s AND l.period_id=%s AND l.journal_id IN %s ' + self.query_get_clause + ' '
                        'GROUP BY j.id, j.code, j.name, l.amount_currency, c.symbol, l.currency_id ',
                        (tuple(move_state), period_id, tuple(self.journal_ids)))
        return self.cr.dictfetchall()

    def _set_get_account_currency_code(self, account_id):
        self.cr.execute("SELECT c.symbol AS code "\
                        "FROM res_currency c, account_account AS ac "\
                        "WHERE ac.id = %s AND ac.currency_id = c.id" % (account_id))
        result = self.cr.fetchone()
        if result:
            self.account_currency = result[0]
        else:
            self.account_currency = False

    def _get_account(self, data):
        if data['model'] == 'account.journal.period':
            return self.pool.get('account.journal.period').browse(self.cr, self.uid, data['id']).company_id.name
        return super(journal_print, self)._get_account(data)

    def _get_fiscalyear(self, data):
        if data['model'] == 'account.journal.period':
            return self.pool.get('account.journal.period').browse(self.cr, self.uid, data['id']).fiscalyear_id.name
        return super(journal_print, self)._get_fiscalyear(data)

    def _display_currency(self, data):
        if data['model'] == 'account.journal.period':
            return True
        return data['form']['amount_currency']

    def _sum_debit_period(self, period_id, journal_id=False):
        if journal_id:
            journals = [journal_id]
        else:
            journals = self.journal_ids
        if not journals:
            return 0.0
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']
        self.cr.execute('SELECT SUM(l.debit) FROM account_move_line l '
                        'LEFT JOIN account_move am ON (l.move_id=am.id) '
                        'WHERE am.state IN %s AND l.period_id=%s AND l.journal_id IN %s ' + self.query_get_clause + ' ' \
                        'AND l.state<>\'draft\'',
                        (tuple(move_state), period_id, tuple(journals)))
        return self.cr.fetchone()[0] or 0.0

    def _sum_credit_period(self, period_id, journal_id=None):
        if journal_id:
            journals = [journal_id]
        else:
            journals = self.journal_ids
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']
        if not journals:
            return 0.0
        self.cr.execute('SELECT SUM(l.credit) FROM account_move_line l '
                        'LEFT JOIN account_move am ON (l.move_id=am.id) '
                        'WHERE am.state IN %s AND l.period_id=%s AND l.journal_id IN %s '+ self.query_get_clause + ' ' \
                        'AND l.state<>\'draft\'',
                        (tuple(move_state), period_id, tuple(journals)))
        return self.cr.fetchone()[0] or 0.0


class report_generaljournal(osv.AbstractModel):
    _name = 'report.account.report_generaljournal'
    _inherit = 'report.abstract_report'
    _template = 'account.report_generaljournal'
    _wrapped_report_class = journal_print

    def get_csv(self, data, response):
        book = Workbook()
        sheet = book.add_sheet('General Journal')

        report = journal_print(self.env.cr, self.env.uid, '', context=self.env.context)
        report.set_context(None, data, None)

        title_style = easyxf('font: bold true;', 'borders: bottom thick;')
        bold_style = easyxf('font: bold true;')

        sheet.col(1).width = 10000

        sheet.write(0, 0, 'Code', title_style)
        sheet.write(0, 1, 'Journal Name', title_style)
        sheet.write(0, 2, 'Debit', title_style)
        sheet.write(0, 3, 'Credit', title_style)
        sheet.write(0, 4, 'Balance', title_style)

        sheet.write(1, 0, 'Total:', title_style)
        sheet.write(1, 1, None, title_style)
        sheet.write(1, 2, report._sum_debit())
        sheet.write(1, 3, report._sum_credit())
        sheet.write(1, 4, report._sum_credit() - report._sum_debit())

        if report._display_currency(data):
            sheet.write(0, 5, 'Currency', title_style)
            sheet.write(1, 5, None, title_style)

        x_offset = 2

        for o in report.periods(self.env['account.journal.period'].browse(data['form']['active_ids'])):
            sheet.write(x_offset, 0, o.name, bold_style)
            sheet.write(x_offset, 2, report._sum_debit_period(o.id), bold_style)
            sheet.write(x_offset, 3, report._sum_credit_period(o.id), bold_style)
            sheet.write(x_offset, 4, report._sum_credit_period(o.id) - report._sum_debit_period(o.id), bold_style)
            x_offset += 1

            lines = report.lines(o.id)
            for x in range(0, len(lines)):
                sheet.write(x_offset + x, 0, lines[x]['code'])
                sheet.write(x_offset + x, 1, lines[x]['name'])
                sheet.write(x_offset + x, 2, lines[x]['credit'])
                sheet.write(x_offset + x, 3, lines[x]['debit'])
                sheet.write(x_offset + x, 4, lines[x]['credit'] - lines[x]['debit'])
                if report._display_currency(data) and lines[x]['currency_code']:
                    sheet.write(x_offset + x, 5, ''.join([str(lines[x]['amount_currency']), str(lines[x]['currency_code'])]))
            x_offset += len(lines)

        book.save(response.stream)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
