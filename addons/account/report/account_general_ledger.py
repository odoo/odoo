# -*- coding: utf-8 -*-

import time
from openerp import api, models


class ReportGeneralLedger(models.AbstractModel):
    _name = 'report.account.report_generalledger'

    def _compute_accounts(self, accounts):
        cr = self.env.cr
        res = {}
        cr.execute("SELECT account_id AS id, SUM(debit) AS debit, sum(credit) AS credit, (sum(debit) - sum(credit)) AS balance, sum(amount_currency) AS currency_amount, acc.name, acc.code FROM " +self.tables+ " JOIN account_account acc ON (account_id = acc.id) WHERE (account_id IN %s) " +self.filters+" GROUP BY account_id, acc.name, acc.code"
                ,((tuple(accounts.ids),) + tuple(self.where_params)))
        for row in self.env.cr.dictfetchall():
            row['move_line'] = []
            res[row.pop('id')] = row
        if self.init_balance:
            cr.execute("SELECT account_id AS id, sum(debit) AS debit, sum(credit) AS credit, (sum(debit) - sum(credit)) AS balance, sum(amount_currency) AS currency_amount FROM " +self.tables+ " WHERE (account_id IN %s) " + self.init_filters + " GROUP BY account_id"
                    ,((tuple(accounts.ids),) + tuple(self.init_where_params)))
            # Add initial balance to the result
            for row in self.env.cr.dictfetchall():
                res[row['id']]['debit'] += row['debit']
                res[row['id']]['credit'] += row['credit']
                res[row['id']]['balance'] += row['balance']
        if self.display_account in ['movement', 'all']:
            for account in accounts:
                if account.id not in res.keys():
                    res[account.id] = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance', 'currency_amount'])
                    res[account.id]['code'] = account.code
                    res[account.id]['name'] = account.name
                    res[account.id]['move_line'] = []
        return res

    def _get_account_move_lines(self, accounts, res):
        """ Return all the account_move_line of account with their account """

        cr = self.env.cr
        if res and self.init_balance:
            #FIXME: replace the label of lname with a string translatable
            filters = self.init_filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')
            sql = ("SELECT 0 AS lid, l.account_id AS account_id, '' AS ldate, '' AS lcode, COALESCE(SUM(l.amount_currency),0.0) AS amount_currency, '' AS lref, 'Initial Balance' AS lname, COALESCE(SUM(l.debit),0.0) AS debit, COALESCE(SUM(l.credit),0.0) AS credit, COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance, '' AS lpartner_id,\
                '' AS move_name, '' AS mmove_id, '' AS currency_code,\
                NULL AS currency_id,\
                '' AS invoice_id, '' AS invoice_type, '' AS invoice_number,\
                '' AS partner_name\
                FROM account_move_line l\
                LEFT JOIN account_move m ON (l.move_id=m.id)\
                LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                LEFT JOIN res_partner p ON (l.partner_id=p.id)\
                LEFT JOIN account_invoice i ON (m.id =i.move_id)\
                JOIN account_journal j ON (l.journal_id=j.id)\
                WHERE l.account_id IN %s" + filters + ' GROUP BY l.account_id')
            params = (tuple(accounts.ids),) + tuple(self.init_where_params)
            cr.execute(sql, params)
            for row in cr.dictfetchall():
                res[row.pop('account_id')]['move_line'].append(row)

        sql_sort = 'l.date, l.move_id'
        if self.sortby == 'sort_journal_partner':
            sql_sort = 'j.code, p.name, l.move_id'
        filters = self.filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')

        sql = ('SELECT l.id AS lid, l.account_id AS account_id, l.date AS ldate, j.code AS lcode, l.currency_id, l.amount_currency, l.ref AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) AS balance,\
            m.name AS move_name, c.symbol AS currency_code, p.name AS partner_name\
            FROM account_move_line l\
            JOIN account_move m ON (l.move_id=m.id)\
            LEFT JOIN res_currency c ON (l.currency_id=c.id)\
            LEFT JOIN res_partner p ON (l.partner_id=p.id)\
            JOIN account_journal j ON (l.journal_id=j.id)\
            JOIN account_account acc ON (l.account_id = acc.id) \
            WHERE l.account_id IN %s ' + filters + ' GROUP BY l.id, l.account_id, l.date, j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, p.name ORDER BY ' + sql_sort)
        params = (tuple(accounts.ids),) + tuple(self.where_params)

        cr.execute(sql, params)
        for row in cr.dictfetchall():
            move_line = res[row['account_id']]['move_line']
            balance = 0
            if move_line:
                for line in move_line:
                    balance += line['debit'] - line['credit']
            row['balance'] += balance
            move_line.append(row)
        return res

    @api.multi
    def render_html(self, data):
        self.model = self.env.context.get('active_model')
        MoveLine = self.env['account.move.line']
        docs = self.env[self.model].browse(self.env.context.get('active_id'))
        self.ctx = data['form'].get('used_context',{}).copy()

        tables, where_clause, self.where_params = MoveLine.with_context(self.ctx)._query_get()
        self.tables = tables.replace('"','')
        self.wheres = [""]
        if where_clause.strip():
            self.wheres.append(where_clause.strip())
        self.filters = " AND ".join(self.wheres)

        self.init_balance = data['form'].get('initial_balance', True)
        if self.init_balance:
            self.ctx.update({'initial_bal': True})
            init_tables, init_where_clause, self.init_where_params = MoveLine.with_context(self.ctx)._query_get()
            self.init_wheres = [""]
            if init_where_clause.strip():
                self.init_wheres.append(init_where_clause.strip())
            self.init_filters = " AND ".join(self.init_wheres)

        self.sortby = data['form'].get('sortby', 'sort_date')
        self.display_account = data['form']['display_account']
        codes = []
        if data['form'].get('journal_ids', False):
            self.env.cr.execute('SELECT code FROM account_journal WHERE id IN %s',(tuple(data['form']['journal_ids']),))
            codes = [x for x, in self.env.cr.fetchall()]
        accounts = self.env['account.account'].search([])
        accounts_res = self._get_account_move_lines(accounts, self._compute_accounts(accounts))
        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'Accounts': accounts_res,
            'print_journal': codes,
        }
        return self.env['report'].render('account.report_generalledger', docargs)
