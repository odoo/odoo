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
from openerp.osv import osv
from openerp.report import report_sxw
from common_report_header import common_report_header


class journal_print(report_sxw.rml_parse, common_report_header):

    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(journal_print, self).__init__(cr, uid, name, context=context)
        self.period_ids = []
        self.last_move_id = False
        self.journal_ids = []
        self.sort_selection = 'am.name'
        self.localcontext.update({
            'time': time,
            'lines': self.lines,
            'sum_debit': self._sum_debit,
            'sum_credit': self._sum_credit,
            'get_start_period': self.get_start_period,
            'get_end_period': self.get_end_period,
            'get_account': self._get_account,
            'get_filter': self._get_filter,
            'get_start_date': self._get_start_date,
            'get_end_date': self._get_end_date,
            'get_fiscalyear': self._get_fiscalyear,
            'display_currency':self._display_currency,
            'get_sortby': self._get_sortby,
            'get_target_move': self._get_target_move,
            'check_last_move_id': self.check_last_move_id,
            'set_last_move_id': self.set_last_move_id,
            'tax_codes': self.tax_codes,
            'sum_vat': self._sum_vat,
    })

    def set_context(self, objects, data, ids, report_type=None):
        obj_move = self.pool.get('account.move.line')
        new_ids = ids
        self.query_get_clause = ''
        self.target_move = data['form'].get('target_move', 'all')
        if (data['model'] == 'ir.ui.menu'):
            self.period_ids = tuple(data['form']['periods'])
            self.journal_ids = tuple(data['form']['journal_ids'])
            new_ids = data['form'].get('active_ids', [])
            self.query_get_clause = 'AND '
            self.query_get_clause += obj_move._query_get(self.cr, self.uid, obj='l', context=data['form'].get('used_context', {}))
            self.sort_selection = data['form'].get('sort_selection', 'date')
            objects = self.pool.get('account.journal.period').browse(self.cr, self.uid, new_ids)
        elif new_ids:
            #in case of direct access from account.journal.period object, we need to set the journal_ids and periods_ids
            self.cr.execute('SELECT period_id, journal_id FROM account_journal_period WHERE id IN %s', (tuple(new_ids),))
            res = self.cr.fetchall()
            self.period_ids, self.journal_ids = zip(*res)
        return super(journal_print, self).set_context(objects, data, ids, report_type=report_type)

    def set_last_move_id(self, move_id):
        self.last_move_id = move_id

    def check_last_move_id(self, move_id):
        '''
        return True if we need to draw a gray line above this line, used to separate moves
        '''
        if self.last_move_id:
            return not(self.last_move_id == move_id)
        return False

    def tax_codes(self, period_id, journal_id):
        ids_journal_period = self.pool.get('account.journal.period').search(self.cr, self.uid, 
            [('journal_id', '=', journal_id), ('period_id', '=', period_id)])
        self.cr.execute(
            'select distinct tax_code_id from account_move_line ' \
            'where period_id=%s and journal_id=%s and tax_code_id is not null and state<>\'draft\'',
            (period_id, journal_id)
        )
        ids = map(lambda x: x[0], self.cr.fetchall())
        tax_code_ids = []
        if ids:
            self.cr.execute('select id from account_tax_code where id in %s order by code', (tuple(ids),))
            tax_code_ids = map(lambda x: x[0], self.cr.fetchall())
        tax_codes = self.pool.get('account.tax.code').browse(self.cr, self.uid, tax_code_ids)
        return tax_codes

    def _sum_vat(self, period_id, journal_id, tax_code_id):
        self.cr.execute('select sum(tax_amount) from account_move_line where ' \
                        'period_id=%s and journal_id=%s and tax_code_id=%s and state<>\'draft\'',
                        (period_id, journal_id, tax_code_id))
        return self.cr.fetchone()[0] or 0.0

    def _sum_debit(self, period_id=False, journal_id=False):
        if journal_id and isinstance(journal_id, int):
            journal_id = [journal_id]
        if period_id and isinstance(period_id, int):
            period_id = [period_id]
        if not journal_id:
            journal_id = self.journal_ids
        if not period_id:
            period_id = self.period_ids
        if not (period_id and journal_id):
            return 0.0
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']

        self.cr.execute('SELECT SUM(debit) FROM account_move_line l, account_move am '
                        'WHERE l.move_id=am.id AND am.state IN %s AND l.period_id IN %s AND l.journal_id IN %s ' + self.query_get_clause + ' ',
                        (tuple(move_state), tuple(period_id), tuple(journal_id)))
        return self.cr.fetchone()[0] or 0.0

    def _sum_credit(self, period_id=False, journal_id=False):
        if journal_id and isinstance(journal_id, int):
            journal_id = [journal_id]
        if period_id and isinstance(period_id, int):
            period_id = [period_id]
        if not journal_id:
            journal_id = self.journal_ids
        if not period_id:
            period_id = self.period_ids
        if not (period_id and journal_id):
            return 0.0
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']

        self.cr.execute('SELECT SUM(l.credit) FROM account_move_line l, account_move am '
                        'WHERE l.move_id=am.id AND am.state IN %s AND l.period_id IN %s AND l.journal_id IN %s '+ self.query_get_clause+'',
                        (tuple(move_state), tuple(period_id), tuple(journal_id)))
        return self.cr.fetchone()[0] or 0.0

    def lines(self, period_id, journal_id=False):
        if not journal_id:
            journal_id = self.journal_ids
        else:
            journal_id = [journal_id]
        obj_mline = self.pool.get('account.move.line')
        self.cr.execute('update account_journal_period set state=%s where journal_id IN %s and period_id=%s and state=%s', ('printed', self.journal_ids, period_id, 'draft'))
        self.pool.get('account.journal.period').invalidate_cache(self.cr, self.uid, ['state'], context=self.context)

        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']

        self.cr.execute('SELECT l.id FROM account_move_line l, account_move am WHERE l.move_id=am.id AND am.state IN %s AND l.period_id=%s AND l.journal_id IN %s ' + self.query_get_clause + ' ORDER BY '+ self.sort_selection + ', l.move_id',(tuple(move_state), period_id, tuple(journal_id) ))
        ids = map(lambda x: x[0], self.cr.fetchall())
        return obj_mline.browse(self.cr, self.uid, ids)

    def _set_get_account_currency_code(self, account_id):
        self.cr.execute("SELECT c.symbol AS code "\
                "FROM res_currency c,account_account AS ac "\
                "WHERE ac.id = %s AND ac.currency_id = c.id" % (account_id))
        result = self.cr.fetchone()
        if result:
            self.account_currency = result[0]
        else:
            self.account_currency = False

    def _get_fiscalyear(self, data):
        if data['model'] == 'account.journal.period':
            return self.pool.get('account.journal.period').browse(self.cr, self.uid, data['id']).fiscalyear_id.name
        return super(journal_print, self)._get_fiscalyear(data)

    def _get_account(self, data):
        if data['model'] == 'account.journal.period':
            return self.pool.get('account.journal.period').browse(self.cr, self.uid, data['id']).company_id.name
        return super(journal_print, self)._get_account(data)

    def _display_currency(self, data):
        if data['model'] == 'account.journal.period':
            return True
        return data['form']['amount_currency']

    def _get_sortby(self, data):
        # TODO: deprecated, to remove in trunk
        if self.sort_selection == 'date':
            return self._translate('Date')
        elif self.sort_selection == 'ref':
            return self._translate('Reference Number')
        return self._translate('Date')


class report_journal(osv.AbstractModel):
    _name = 'report.account.report_journal'
    _inherit = 'report.abstract_report'
    _template = 'account.report_journal'
    _wrapped_report_class = journal_print


class report_salepurchasejournal(osv.AbstractModel):
    _name = 'report.account.report_salepurchasejournal'
    _inherit = 'report.abstract_report'
    _template = 'account.report_salepurchasejournal'
    _wrapped_report_class = journal_print

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
