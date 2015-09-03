# -*- coding: utf-8 -*-

import time
from openerp import api, models


class ReportPartnerLedger(models.AbstractModel):

    _name = 'report.account.report_partnerledger'

    def _get_account_move_lines(self, account_ids, initial_balance, reconcil):
        """
        :param:
                account_ids: the ID of a accounts record
                initial_balance: boolean value of initial_balance
                reconcil: boolean value to get only unreconciled entry

        Returns a dictionary of partners with following key and value {
                'ref': ref of partne,
                'name': name of partner,
                'debit': sum of total debit amount,
                'credit': sum of total credit amount,
                'balance': total balance,
                'amount_currency': sum of amount_currency,
                'move_lines': list of move_line
        }
        """

        RECONCILE_TAG = " "
        if not reconcil:
            RECONCILE_TAG = "AND l.reconciled IS False"
        MoveLine = self.env['account.move.line']

        # Prepare sql query base on selected parameters from wizard
        tables, where_clause, where_params = MoveLine._query_get()
        tables = tables.replace('"', '')
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)

        # Prepare initial sql query and Get the initial move lines
        init_res = {}
        if initial_balance:
            init_tables, init_where_clause, init_where_params = MoveLine.with_context(date_to=self.env.context.get('date_from'), date_from=False)._query_get()
            init_wheres = [""]
            if init_where_clause.strip():
                init_wheres.append(init_where_clause.strip())
            init_filters = " AND ".join(init_wheres)

            self.env.cr.execute(
                "SELECT account_move_line.partner_id, '' AS ldate, '' AS code, '' AS a_code, '' AS move_name, '' AS ref, 'Initial Balance' AS name, COALESCE(SUM(debit),0.0) AS debit, COALESCE(SUM(credit),0.0) AS credit, COALESCE(sum(debit-credit), 0.0) AS balance, SUM(amount_currency) AS amount_currency FROM " \
                + tables +
                " WHERE account_id IN %s" \
                " " + RECONCILE_TAG + " "\
                + init_filters + " GROUP BY account_move_line.partner_id ",
                ((tuple(account_ids),) + tuple(init_where_params)))
            for row in self.env.cr.dictfetchall():
                init_res[row.pop('partner_id')] = row

        # Get the normal move lines base on sql query
        query = filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')
        self.env.cr.execute(
            "SELECT l.partner_id, l.id, l.date AS ldate, j.code, acc.code AS a_code, l.ref, m.name AS move_name, l.name, SUM(l.debit) AS debit, SUM(l.credit) AS credit, (SUM(l.debit) - SUM(l.credit)) AS balance, SUM(l.amount_currency) AS amount_currency, l.currency_id, c.symbol AS currency_code " \
            "FROM account_move_line l " \
            "LEFT JOIN account_journal j ON (l.journal_id = j.id) " \
            "LEFT JOIN account_account acc ON (l.account_id = acc.id) " \
            "LEFT JOIN res_currency c ON (l.currency_id=c.id)" \
            "LEFT JOIN account_move m ON (m.id=l.move_id)" \
            "WHERE l.account_id IN %s " + query +" " + RECONCILE_TAG + " "\
            "GROUP BY l.partner_id, l.id, l.date, j.code, acc.code, l.ref, m.name, l.name, l.currency_id, c.symbol ORDER BY l.date",
            ((tuple(account_ids),) + tuple(where_params)))

        res = self.env.cr.dictfetchall()
        # fecthing partner_ids
        partner_ids = list(set(map(lambda x: x['partner_id'], res)))
        move_lines = dict(map(lambda x: (x, []), partner_ids))
        for row in init_res:
            if row in move_lines:
                move_lines.get(row).append(init_res[row])
        # Calculate the total balance of move lines
        for row in res:
            balance = 0
            for line in move_lines.get(row['partner_id']):
                balance += line['debit'] - line['credit']
            row['balance'] += balance
            move_lines[row.pop('partner_id')].append(row)

        # Calculate the debit, credit and balance for partners
        partner_res = []
        for partner in self.env['res.partner'].browse(partner_ids):
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance', 'amount_currency'])
            res['ref'] = partner.ref
            res['name'] = partner.name
            res['move_lines'] = move_lines[partner.id]
            for line in res.get('move_lines'):
                res['debit'] += line['debit']
                res['credit'] += line['credit']
                res['balance'] = line['balance']
                res['amount_currency'] += line['amount_currency']
            partner_res.append(res)

        return partner_res

    @api.multi
    def render_html(self, data):

        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_id'))
        reconcil = False if data['form']['filters'] == 'unreconciled' else True
        initial_balance = data['form'].get('initial_balance', True)
        result_selection = data['form'].get('result_selection', 'customer')
        if result_selection == 'supplier':
            account_type = ['payable']
        elif result_selection == 'customer':
            account_type = ['receivable']
        else:
            account_type = ['payable', 'receivable']

        account_ids = self.env['account.account'].search([('internal_type', 'in', account_type)]).ids
        partners_res = self.with_context(data['form'].get('used_context', {}))._get_account_move_lines(account_ids, initial_balance, reconcil)
        codes = []
        if data['form'].get('journal_ids', False):
            codes = [journal.code for journal in self.env['account.journal'].search([('id', 'in', data['form']['journal_ids'])])]

        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'print_journal': codes,
            'Partners': partners_res,
        }
        if data['form'].get('page_split'):
            return self.env['report'].render('account.report_partnerledgerother', docargs)
        return self.env['report'].render('account.report_partnerledger', docargs)
