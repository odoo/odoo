# -*- coding: utf-8 -*-

import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportGeneralLedger(models.AbstractModel):
    _name = 'report.accounting_pdf_reports.report_general_ledger'
    _description = 'General Ledger Report'

    def _get_account_move_entry(self, accounts, analytic_account_ids,
                                partner_ids, init_balance,
                                sortby, display_account):
        """
        :param:
                accounts: the recordset of accounts
                analytic_account_ids: the recordset of analytic accounts
                init_balance: boolean value of initial_balance
                sortby: sorting by date or partner and journal
                display_account: type of account(receivable, payable and both)

        Returns a dictionary of accounts with following key and value {
                'code': account code,
                'name': account name,
                'debit': sum of total debit amount,
                'credit': sum of total credit amount,
                'balance': total balance,
                'amount_currency': sum of amount_currency,
                'move_lines': list of move line
        }
        """
        cr = self.env.cr
        MoveLine = self.env['account.move.line']
        move_lines = {x: [] for x in accounts.ids}

        # Prepare initial sql query and Get the initial move lines
        if init_balance:
            context = dict(self.env.context)
            context['date_from'] = self.env.context.get('date_from')
            context['date_to'] = False
            context['initial_bal'] = True
            if analytic_account_ids:
                context['analytic_account_ids'] = analytic_account_ids
            if partner_ids:
                context['partner_ids'] = partner_ids
            init_tables, init_where_clause, init_where_params = MoveLine.with_context(context)._query_get()
            init_wheres = [""]
            if init_where_clause.strip():
                init_wheres.append(init_where_clause.strip())
            init_filters = " AND ".join(init_wheres)
            filters = init_filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')
            sql = ("""SELECT 0 AS lid, l.account_id AS account_id, '' AS ldate,
                '' AS lcode, 0.0 AS amount_currency, 
                aaa.name AS analytic_account_id, '' AS lref, 
                'Initial Balance' AS lname, COALESCE(SUM(l.debit),0.0) AS debit, 
                COALESCE(SUM(l.credit),0.0) AS credit, 
                COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance, 
                '' AS lpartner_id,\
                '' AS move_name, '' AS mmove_id, '' AS currency_code,\
                NULL AS currency_id,\
                '' AS invoice_id, '' AS invoice_type, '' AS invoice_number,\
                '' AS partner_name\
                FROM account_move_line l\
                LEFT JOIN account_move m ON (l.move_id=m.id)\
                LEFT JOIN account_analytic_account aaa ON (aaa.id=l.analytic_account_id)
                LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                LEFT JOIN res_partner p ON (l.partner_id=p.id)\
                JOIN account_journal j ON (l.journal_id=j.id)\
                WHERE l.account_id IN %s""" + filters + ' GROUP BY l.account_id, aaa.name')
            params = (tuple(accounts.ids),) + tuple(init_where_params)
            cr.execute(sql, params)
            for row in cr.dictfetchall():
                move_lines[row.pop('account_id')].append(row)

        sql_sort = 'l.date, l.move_id'
        if sortby == 'sort_journal_partner':
            sql_sort = 'j.code, p.name, l.move_id'

        # Prepare sql query base on selected parameters from wizard
        context = dict(self.env.context)
        if analytic_account_ids:
            context['analytic_account_ids'] = analytic_account_ids
        if partner_ids:
            context['partner_ids'] = partner_ids
        tables, where_clause, where_params = MoveLine.with_context(context)._query_get()
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        filters = filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')

        # Get move lines base on sql query and Calculate the total balance of move lines
        sql = ('''SELECT l.id AS lid, l.account_id AS account_id, 
            l.date AS ldate, j.code AS lcode, l.currency_id, 
            l.amount_currency, aaa.name AS analytic_account_id,
            l.ref AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit, 
            COALESCE(l.credit,0) AS credit, 
            COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) AS balance,\
            m.name AS move_name, c.symbol AS currency_code, 
            p.name AS partner_name\
            FROM account_move_line l\
            JOIN account_move m ON (l.move_id=m.id)\
            LEFT JOIN res_currency c ON (l.currency_id=c.id)\
            LEFT JOIN res_partner p ON (l.partner_id=p.id)\
            JOIN account_journal j ON (l.journal_id=j.id)\
            LEFT JOIN account_analytic_account aaa ON (aaa.id=l.account_id)\
            JOIN account_account acc ON (l.account_id = acc.id) \
            WHERE l.account_id IN %s ''' + filters + ''' GROUP BY l.id, 
            l.account_id, l.date, j.code, l.currency_id, l.amount_currency, 
            l.ref, l.name, m.name, c.symbol, p.name, aaa.name ORDER BY ''' + sql_sort)
        params = (tuple(accounts.ids),) + tuple(where_params)
        cr.execute(sql, params)

        for row in cr.dictfetchall():
            balance = 0
            for line in move_lines.get(row['account_id']):
                balance += line['debit'] - line['credit']
            row['balance'] += balance
            move_lines[row.pop('account_id')].append(row)

        # Calculate the debit, credit and balance for Accounts
        account_res = []
        for account in accounts:
            currency = account.currency_id and account.currency_id or account.company_id.currency_id
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            res['code'] = account.code
            res['name'] = account.name
            res['move_lines'] = move_lines[account.id]
            for line in res.get('move_lines'):
                res['debit'] += line['debit']
                res['credit'] += line['credit']
                res['balance'] = line['balance']
            if display_account == 'all':
                account_res.append(res)
            if display_account == 'movement' and res.get('move_lines'):
                account_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(res['balance']):
                account_res.append(res)
        return account_res

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        init_balance = data['form'].get('initial_balance', True)
        sortby = data['form'].get('sortby', 'sort_date')
        display_account = data['form']['display_account']
        codes = []
        if data['form'].get('journal_ids', False):
            codes = [journal.code for journal in
                     self.env['account.journal'].search(
                         [('id', 'in', data['form']['journal_ids'])])]
        analytic_account_ids = False
        if data['form'].get('analytic_account_ids', False):
            analytic_account_ids = self.env['account.analytic.account'].search(
                [('id', 'in', data['form']['analytic_account_ids'])])
        partner_ids = False
        if data['form'].get('partner_ids', False):
            partner_ids = self.env['res.partner'].search(
                [('id', 'in', data['form']['partner_ids'])])
        if model == 'account.account':
            accounts = docs
        else:
            domain = []
            if data['form'].get('account_ids', False):
                domain.append(('id', 'in', data['form']['account_ids']))
            accounts = self.env['account.account'].search(domain)
        accounts_res = self.with_context(
            data['form'].get('used_context', {}))._get_account_move_entry(
            accounts,
            analytic_account_ids,
            partner_ids,
            init_balance, sortby, display_account)
        return {
            'doc_ids': docids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'Accounts': accounts_res,
            'print_journal': codes,
            'accounts': accounts,
            'partner_ids': partner_ids,
            'analytic_account_ids': analytic_account_ids,
        }
