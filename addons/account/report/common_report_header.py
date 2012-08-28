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

import pooler
from tools.translate import _

class common_report_header(object):

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
        self.cr.execute('SELECT SUM(debit) FROM account_move_line l '
                        'WHERE period_id IN %s AND journal_id IN %s ' + self.query_get_clause + ' ',
                        (tuple(period_id), tuple(journal_id)))
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
        self.cr.execute('SELECT SUM(credit) FROM account_move_line l '
                        'WHERE period_id IN %s AND journal_id IN %s '+ self.query_get_clause+'',
                        (tuple(period_id), tuple(journal_id)))
        return self.cr.fetchone()[0] or 0.0

    def _get_start_date(self, data):
        if data.get('form', False) and data['form'].get('date_from', False):
            return data['form']['date_from']
        return ''

    def _get_target_move(self, data):
        if data.get('form', False) and data['form'].get('target_move', False):
            if data['form']['target_move'] == 'all':
                return _('All Entries')
            return _('All Posted Entries')
        return ''

    def _get_end_date(self, data):
        if data.get('form', False) and data['form'].get('date_to', False):
            return data['form']['date_to']
        return ''

    def get_start_period(self, data):
        if data.get('form', False) and data['form'].get('period_from', False):
            return pooler.get_pool(self.cr.dbname).get('account.period').browse(self.cr,self.uid,data['form']['period_from']).name
        return ''

    def get_end_period(self, data):
        if data.get('form', False) and data['form'].get('period_to', False):
            return pooler.get_pool(self.cr.dbname).get('account.period').browse(self.cr, self.uid, data['form']['period_to']).name
        return ''

    def _get_account(self, data):
        if data.get('form', False) and data['form'].get('chart_account_id', False):
            return pooler.get_pool(self.cr.dbname).get('account.account').browse(self.cr, self.uid, data['form']['chart_account_id']).name
        return ''

    def _get_sortby(self, data):
        raise (_('Error!'), _('Not implemented.'))

    def _get_filter(self, data):
        if data.get('form', False) and data['form'].get('filter', False):
            if data['form']['filter'] == 'filter_date':
                return 'Date'
            elif data['form']['filter'] == 'filter_period':
                return 'Periods'
        return 'No Filter'

    def _sum_debit_period(self, period_id, journal_id=None):
        journals = journal_id or self.journal_ids
        if not journals:
            return 0.0
        self.cr.execute('SELECT SUM(debit) FROM account_move_line l '
                        'WHERE period_id=%s AND journal_id IN %s '+ self.query_get_clause +'',
                        (period_id, tuple(journals)))

        return self.cr.fetchone()[0] or 0.0

    def _sum_credit_period(self, period_id, journal_id=None):
        journals = journal_id or self.journal_ids
        if not journals:
            return 0.0
        self.cr.execute('SELECT SUM(credit) FROM account_move_line l '
                        'WHERE period_id=%s AND journal_id IN %s ' + self.query_get_clause +' ',
                        (period_id, tuple(journals)))
        return self.cr.fetchone()[0] or 0.0

    def _get_fiscalyear(self, data):
        if data.get('form', False) and data['form'].get('fiscalyear_id', False):
            return pooler.get_pool(self.cr.dbname).get('account.fiscalyear').browse(self.cr, self.uid, data['form']['fiscalyear_id']).name
        return ''

    def _get_company(self, data):
        if data.get('form', False) and data['form'].get('chart_account_id', False):
            return pooler.get_pool(self.cr.dbname).get('account.account').browse(self.cr, self.uid, data['form']['chart_account_id']).company_id.name
        return ''

    def _get_journal(self, data):
        codes = []
        if data.get('form', False) and data['form'].get('journal_ids', False):
            self.cr.execute('select code from account_journal where id IN %s',(tuple(data['form']['journal_ids']),))
            codes = [x for x, in self.cr.fetchall()]
        return codes

    def _get_currency(self, data):
        if data.get('form', False) and data['form'].get('chart_account_id', False):
            return pooler.get_pool(self.cr.dbname).get('account.account').browse(self.cr, self.uid, data['form']['chart_account_id']).company_id.currency_id.symbol
        return ''

#vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
