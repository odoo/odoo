import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportBankBook(models.AbstractModel):
    _name = 'report.om_account_daily_reports.report_bankbook'
    _description = 'Bank Book'

    def _get_account_move_entry(self, accounts, init_balance, sortby, display_account):
        """
        :param:
                accounts: the record set of accounts
                init_balance: boolean value of initial_balance
                sortby: sorting by date or partner and journal
                display_account: type of account (receivable, payable and both)

        Returns a dictionary of accounts with following key and value:
            {
                'code': account code,
                'name': account name,
                'debit': sum of total debit amount,
                'credit': sum of total credit amount,
                'balance': total balance,
                'amount_currency': sum of amount_currency,
                'move_lines': list of move lines
            }
        """
        cr = self.env.cr
        MoveLine = self.env['account.move.line']
        move_lines = {x: [] for x in accounts.ids}

        # Prepare initial SQL query and get the initial move lines
        if init_balance:
            init_tables, init_where_clause, init_where_params = MoveLine.with_context(
                date_from=self.env.context.get('date_from'),
                date_to=False,
                initial_bal=True
            )._query_get()

            init_wheres = [""]
            if init_where_clause.strip():
                init_wheres.append(init_where_clause.strip())
            init_filters = " AND ".join(init_wheres)
            filters = init_filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')

            sql = ("""
                SELECT 0 AS lid, 
                       l.account_id AS account_id, 
                       '' AS ldate, '' AS lcode, 0.0 AS amount_currency, 
                       '' AS lref, 'Initial Balance' AS lname, 
                       COALESCE(SUM(l.credit), 0.0) AS credit,
                       COALESCE(SUM(l.debit), 0.0) AS debit,
                       COALESCE(SUM(l.debit), 0) - COALESCE(SUM(l.credit), 0) AS balance, 
                       '' AS lpartner_id, '' AS move_name, '' AS currency_code, 
                       NULL AS currency_id, '' AS partner_name,
                       '' AS mmove_id, '' AS invoice_id, '' AS invoice_type, '' AS invoice_number
                FROM account_move_line l 
                LEFT JOIN account_move m ON (l.move_id = m.id) 
                LEFT JOIN res_currency c ON (l.currency_id = c.id) 
                LEFT JOIN res_partner p ON (l.partner_id = p.id) 
                JOIN account_journal j ON (l.journal_id = j.id) 
                JOIN account_account acc ON (l.account_id = acc.id) 
                WHERE l.account_id IN %s """ + filters + 'GROUP BY l.account_id'
                   )

            params = (tuple(accounts.ids),) + tuple(init_where_params)
            cr.execute(sql, params)
            for row in cr.dictfetchall():
                move_lines[row.pop('account_id')].append(row)

        sql_sort = 'l.date, l.move_id'
        if sortby == 'sort_journal_partner':
            sql_sort = 'j.code, p.name, l.move_id'

        # Prepare SQL query based on selected parameters from wizard
        tables, where_clause, where_params = MoveLine._query_get()
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres).replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')

        if not accounts:
            journals = self.env['account.journal'].search([('type', '=', 'bank')])
            accounts = self.env['account.account']
            for journal in journals:
                for acc_out in journal.outbound_payment_method_line_ids:
                    if acc_out.payment_account_id:
                        accounts += acc_out.payment_account_id
                for acc_in in journal.inbound_payment_method_line_ids:
                    if acc_in.payment_account_id:
                        accounts += acc_in.payment_account_id

        sql = ('''
            SELECT l.id AS lid, l.account_id AS account_id, l.date AS ldate, j.code AS lcode, 
                   l.currency_id, l.amount_currency, l.ref AS lref, l.name AS lname, 
                   COALESCE(l.debit, 0) AS debit, COALESCE(l.credit, 0) AS credit, 
                   COALESCE(SUM(l.debit), 0) - COALESCE(SUM(l.credit), 0) AS balance,
                   m.name AS move_name, c.symbol AS currency_code, p.name AS partner_name
            FROM account_move_line l
            JOIN account_move m ON (l.move_id = m.id)
            LEFT JOIN res_currency c ON (l.currency_id = c.id)
            LEFT JOIN res_partner p ON (l.partner_id = p.id)
            JOIN account_journal j ON (l.journal_id = j.id)
            JOIN account_account acc ON (l.account_id = acc.id)
            WHERE l.account_id IN %s ''' + filters + ''' 
            GROUP BY l.id, l.account_id, l.date, j.code, l.currency_id, l.amount_currency, 
                     l.ref, l.name, m.name, c.symbol, p.name 
            ORDER BY ''' + sql_sort
               )

        params = (tuple(accounts.ids),) + tuple(where_params)
        cr.execute(sql, params)

        for row in cr.dictfetchall():
            balance = 0
            for line in move_lines.get(row['account_id']):
                balance += line['debit'] - line['credit']
            row['balance'] += balance
            move_lines[row.pop('account_id')].append(row)

        # Calculate the debit, credit and balance for accounts
        account_res = []
        for account in accounts:
            currency = account.currency_id or self.env.company.currency_id
            res = {fn: 0.0 for fn in ['credit', 'debit', 'balance']}
            res.update({'code': account.code, 'name': account.name, 'move_lines': move_lines[account.id]})

            for line in res.get('move_lines'):
                res['debit'] += line['debit']
                res['credit'] += line['credit']
                res['balance'] = line['balance']

            if display_account == 'all':
                account_res.append(res)
            elif display_account == 'movement' and res.get('move_lines'):
                account_res.append(res)
            elif display_account == 'not_zero' and not currency.is_zero(res['balance']):
                account_res.append(res)

        return account_res

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        init_balance = data['form'].get('initial_balance', True)
        display_account = data['form'].get('display_account')

        sortby = data['form'].get('sortby', 'sort_date')
        codes = []

        if data['form'].get('journal_ids', False):
            codes = [journal.code for journal in self.env['account.journal'].browse(data['form']['journal_ids'])]

        accounts = self.env['account.account'].browse(data['form']['account_ids'])
        if not accounts:
            journals = self.env['account.journal'].search([('type', '=', 'bank')])
            accounts = self.env['account.account']
            for journal in journals:
                for acc_out in journal.outbound_payment_method_line_ids:
                    if acc_out.payment_account_id:
                        accounts += acc_out.payment_account_id
                for acc_in in journal.inbound_payment_method_line_ids:
                    if acc_in.payment_account_id:
                        accounts += acc_in.payment_account_id

        record = self.with_context(data['form'].get('comparison_context', {}))._get_account_move_entry(
            accounts, init_balance, sortby, display_account
        )

        return {
            'doc_ids': docids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'Accounts': record,
            'print_journal': codes,
        }
