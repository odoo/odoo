# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005-2006 CamptoCamp
# Copyright (c) 2006-2010 OpenERP S.A
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
##############################################################################

from openerp import models,api
from openerp.tools.translate import _
from common_report_header import common_report_header

class GeneralLedgerReport(models.AbstractModel, common_report_header):
    _name = 'report.account.report_generalledger'

    @api.multi
    def _sum_currency_amount_account(self, account):
        self._cr.execute('SELECT sum(l.amount_currency) AS tot_currency \
                FROM account_move_line l \
                WHERE l.account_id = %s %s' % (account.id, self.query))
        sum_currency = self._cr.fetchone()[0] or 0.0
        if self.init_balance:
            self._cr.execute('SELECT sum(l.amount_currency) AS tot_currency \
                            FROM account_move_line l \
                            WHERE l.account_id = %s %s' % (account.id, self.init_query))
            sum_currency += self._cr.fetchone()[0] or 0.0
        return sum_currency

    @api.multi
    def _get_children_accounts(self, account):
        res = []
        account_obj = self.env['account.account']
        ids_acc = account._get_children_and_consol()
        currency = account.currency_id and account.currency_id or account.company_id.currency_id
        for child_account in account_obj.browse(ids_acc):
            self._cr_execute('SELECT count(id) \
                                FROM account_move_line AS l \
                                WHERE l.account_id = %s %s' % (child_account.id, self.query))
            num_entry = self._cr.fetchone()[0] or 0
            sold_account = self._sum_balance_account(child_account)
            self.sold_accounts[child_account.id] = sold_account
            if self.display_account == 'movement':
                if num_entry <> 0:
                    res.append(child_account)
            elif self.display_account == 'not_zero':
                if num_entry <> 0:
                    if not currency.is_zero(sold_account):
                        res.append(child_account)
            else:
                res.append(child_account)
        if not res:
            return [account]
        return res

    @api.multi
    def _sum_debit_account(self, account):
        if account.user_type.type == 'view':
            return account.debit
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted','']
        self._cr.execute('SELECT sum(debit) \
                FROM account_move_line l \
                JOIN account_move am ON (am.id = l.move_id) \
                WHERE (l.account_id = %s) \
                AND (am.state IN %s)' + self.query
                ,(account.id, tuple(move_state)))
        sum_debit = self._cr.fetchone()[0] or 0.0
        if self.init_balance:
            self._cr.execute('SELECT sum(debit) \
                    FROM account_move_line l \
                    JOIN account_move am ON (am.id = l.move_id) \
                    WHERE (l.account_id = %s) \
                    AND (am.state IN %s)'+ self.init_query
                    ,(account.id, tuple(move_state)))
            # Add initial balance to the result
            sum_debit += self._cr.fetchone()[0] or 0.0
        return sum_debit

    @api.multi
    def _sum_credit_account(self, account):
        if account.user_type.type == 'view':
            return account.credit
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted','']
        self._cr.execute('SELECT sum(credit) \
                FROM account_move_line l \
                JOIN account_move am ON (am.id = l.move_id) \
                WHERE (l.account_id = %s) \
                AND (am.state IN %s)' + self.query
                ,(account.id, tuple(move_state)))
        sum_credit = self._cr.fetchone()[0] or 0.0
        if self.init_balance:
            self._cr.execute('SELECT sum(credit) \
                    FROM account_move_line l \
                    JOIN account_move am ON (am.id = l.move_id) \
                    WHERE (l.account_id = %s) \
                    AND (am.state IN %s)' + self.init_query
                    ,(account.id, tuple(move_state)))
            # Add initial balance to the result
            sum_credit += self._cr.fetchone()[0] or 0.0
        return sum_credit

    @api.multi
    def _sum_balance_account(self, account):
        if account.user_type.type == 'view':
            return account.balance
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted','']
        self._cr.execute('SELECT (sum(debit) - sum(credit)) as tot_balance \
                FROM account_move_line l \
                JOIN account_move am ON (am.id = l.move_id) \
                WHERE (l.account_id = %s) \
                AND (am.state IN %s)' + self.query
                ,(account.id, tuple(move_state)))
        sum_balance = self._cr.fetchone()[0] or 0.0
        if self.init_balance:
            self._cr.execute('SELECT (sum(debit) - sum(credit)) as tot_balance \
                    FROM account_move_line l \
                    JOIN account_move am ON (am.id = l.move_id) \
                    WHERE (l.account_id = %s) \
                    AND (am.state IN %s)' + self.init_query
                    ,(account.id, tuple(move_state)))
            # Add initial balance to the result
            sum_balance += self._cr.fetchone()[0] or 0.0
        return sum_balance

    @api.multi
    def _lines(self, account):
        """ Return all the account_move_line of account with their account code counterparts """
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted', '']
        # First compute all counterpart strings for every move_id where this account appear.
        # Currently, the counterpart info is used only in landscape mode
        sql = """
            SELECT m1.move_id,
                array_to_string(ARRAY(SELECT DISTINCT a.code
                                          FROM account_move_line m2
                                          LEFT JOIN account_account a ON (m2.account_id=a.id)
                                          WHERE m2.move_id = m1.move_id
                                          AND m2.account_id<>%%s), ', ') AS counterpart
                FROM (SELECT move_id
                        FROM account_move_line l
                        LEFT JOIN account_move am ON (am.id = l.move_id)
                        WHERE am.state IN %s %s AND l.account_id = %%s GROUP BY move_id) m1
        """% (tuple(move_state), self.query)
        self._cr.execute(sql, (account.id, account.id))
        counterpart_res = self._cr.dictfetchall()
        counterpart_accounts = {}
        for i in counterpart_res:
            counterpart_accounts[i['move_id']] = i['counterpart']
        del counterpart_res

        # Then select all account_move_line of this account
        if self.sortby == 'sort_journal_partner':
            sql_sort='j.code, p.name, l.move_id'
        else:
            sql_sort='l.date, l.move_id'
        sql = """
            SELECT l.id AS lid, l.date AS ldate, j.code AS lcode, l.currency_id,l.amount_currency,l.ref AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, l.partner_id AS lpartner_id,
            m.name AS move_name, m.id AS mmove_id,
            c.symbol AS currency_code,
            i.id AS invoice_id, i.type AS invoice_type, i.number AS invoice_number,
            p.name AS partner_name
            FROM account_move_line l
            JOIN account_move m on (l.move_id=m.id)
            LEFT JOIN res_currency c on (l.currency_id=c.id)
            LEFT JOIN res_partner p on (l.partner_id=p.id)
            LEFT JOIN account_invoice i on (m.id =i.move_id)
            JOIN account_journal j on (l.journal_id=j.id)
            WHERE m.state IN %s %s AND l.account_id = %%s  ORDER by %s
        """ %(tuple(move_state), self.query, sql_sort)
        self._cr.execute(sql, (account.id,))
        res_lines = self._cr.dictfetchall()
        res_init = []
        if res_lines and self.init_balance:
            #FIXME: replace the label of lname with a string translatable
            sql = """
                SELECT 0 AS lid, '' AS ldate, '' AS lcode, COALESCE(SUM(l.amount_currency),0.0) AS amount_currency, '' AS lref, 'Initial Balance' AS lname, COALESCE(SUM(l.debit),0.0) AS debit, COALESCE(SUM(l.credit),0.0) AS credit, '' AS lpartner_id,
                '' AS move_name, '' AS mmove_id,
                '' AS currency_code,
                NULL AS currency_id,
                '' AS invoice_id, '' AS invoice_type, '' AS invoice_number,
                '' AS partner_name
                FROM account_move_line l
                LEFT JOIN account_move m on (l.move_id=m.id)
                LEFT JOIN res_currency c on (l.currency_id=c.id)
                LEFT JOIN res_partner p on (l.partner_id=p.id)
                LEFT JOIN account_invoice i on (m.id =i.move_id)
                JOIN account_journal j on (l.journal_id=j.id)
                WHERE %s AND m.state IN %s AND l.account_id = %%s
            """ %(self.init_query, tuple(move_state))
            self._cr.execute(sql, (account.id,))
            res_init = self._cr.dictfetchall()
        res = res_init + res_lines
        account_sum = 0.0
        for l in res:
            l['move'] = l['move_name'] != '/' and l['move_name'] or ('*'+str(l['mmove_id']))
            l['partner'] = l['partner_name'] or ''
            account_sum += l['debit'] - l['credit']
            l['progress'] = account_sum
            l['line_corresp'] = l['mmove_id'] == '' and ' ' or counterpart_accounts[l['mmove_id']].replace(', ',',')
            # Modification of amount Currency
            if l['credit'] > 0:
                if l['amount_currency'] != None:
                    l['amount_currency'] = abs(l['amount_currency']) * -1
            if l['amount_currency'] != None:
                self.tot_currency = self.tot_currency + l['amount_currency']
        return res

    @api.model
    def _get_sortby(self):
        if self.sortby == 'sort_journal_partner':
            return _('Journal & Partner')
        return _('Date')

    @api.multi
    def render_html(self, data=None):
        self.tot_currency = 0.0
        self.sold_accounts = {}
        new_ids = self.ids
        obj_move = self.env['account.move.line']
        self.sortby = data['form'].get('sortby', 'sort_date')
        obj_move.with_context(data['form'].get('used_context',{}))
        self.query = obj_move._query_get(obj='l')
        self.init_balance = data['form'].get('initial_balance', True)
        if self.init_balance:
            ctx2 = data['form'].get('used_context',{})
            ctx2.update({'initial_bal': True})
            obj_move.with_context(ctx2)
        self.init_query = obj_move._query_get(obj='l')
        self.display_account = data['form']['display_account']
        self.target_move = data['form'].get('target_move', 'all')
        if (data['model'] == 'ir.ui.menu'):
            new_ids = [data['form']['chart_account_id']]
        objects = self.env['account.account'].browse(new_ids)

        report_obj = self.env['report']
        module_report = report_obj._get_report_from_name('account.report_generalledger')
        docargs = {
            'doc_ids': self.ids,
            'doc_model': module_report.model,
            'docs': objects,
            'data': data,
            'get_account': self._get_account,
            'get_fiscalyear': self._get_fiscalyear,
            'get_journal': self._get_journal,
            'get_sortby': self._get_sortby,
            'get_start_date':self._get_start_date,
            'get_end_date':self._get_end_date,
            'get_target_move': self._get_target_move,
            'sum_debit_account': self._sum_debit_account,
            'sum_credit_account': self._sum_credit_account,
            'sum_balance_account': self._sum_balance_account,
            'sum_currency_amount_account': self._sum_currency_amount_account,
            'get_children_accounts': self._get_children_accounts,
            'lines': self._lines
        }

        return report_obj.render('account.report_generalledger', docargs)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
