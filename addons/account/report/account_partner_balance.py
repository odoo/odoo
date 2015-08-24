# -*- coding: utf-8 -*-

import time
from openerp import api, models


class ReportPartnerBalance(models.AbstractModel):
    _name = 'report.account.report_partnerbalance'

    def _get_account_move_entry(self, account_type, display_partner):

        full_account = []
        # Prepare sql query base on selected parameters from wizard
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '')
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        filters = filters.replace('account_move_line__move_id', 'am').replace('account_move_line', 'l')
        params = tuple(where_params) + (tuple(account_type),) + tuple(where_params)
        # Get the move lines base on sql query
        self.env.cr.execute(
            "SELECT p.ref, l.account_id, ac.name AS account_name,ac.code AS code, p.name, SUM(debit) AS debit, SUM(credit) AS credit, " \
                    "CASE WHEN SUM(debit) > SUM(credit) " \
                        "THEN SUM(debit) - SUM(credit) " \
                        "ELSE 0 " \
                    "END AS sdebit, " \
                    "CASE WHEN SUM(debit) < SUM(credit) " \
                        "THEN SUM(credit) - SUM(debit) " \
                        "ELSE 0 " \
                    "END AS scredit, " \
                    "(SELECT SUM(debit-credit) " \
                        "FROM account_move_line l, account_move am " \
                        "WHERE l.partner_id = p.id " \
                            + filters + " " \
                            "AND blocked = TRUE " \
                    ") AS litigiated " \
            "FROM account_move_line l LEFT JOIN res_partner p ON (l.partner_id=p.id) " \
            "JOIN account_account ac ON (l.account_id = ac.id)" \
            "JOIN account_move am ON (am.id = l.move_id)" \
            " WHERE ac.internal_type IN %s" \
            + filters + " " \
            "GROUP BY p.id, p.ref, p.name, l.account_id, ac.name, ac.code " \
            "ORDER BY l.account_id, p.name",
            (params))
        res = self.env.cr.dictfetchall()
        full_account = [r for r in res if r['sdebit'] > 0 or r['scredit'] > 0]
        if display_partner == 'all':
            full_account = [r for r in res]

        for rec in full_account:
            if not rec.get('name', False):
                rec.update({'name': 'Unknown Partner'})

        # We will now compute Total
        return self._add_subtotal(full_account)

    def _add_subtotal(self, move_lines):
        i = 0
        completearray = []
        tot_debit = tot_credit = tot_scredit = tot_sdebit = tot_litigiated = 0.0

        for r in move_lines:
            # For the first element we always add the line
            # type = 1 is the line is the first of the account
            # type = 2 is an other line of the account
            if i==0:
                # We add the first row as the header
                new_header = {}
                new_header['ref'] = ''
                new_header['name'] = r['account_name']
                new_header['code'] = r['code']
                new_header['debit'] = r['debit']
                new_header['credit'] = r['credit']
                new_header['scredit'] = tot_scredit
                new_header['sdebit'] = tot_sdebit
                new_header['litigiated'] = tot_litigiated
                new_header['balance'] = r['debit'] - r['credit']
                new_header['type'] = 3
                completearray.append(new_header)
                r['type'] = 1
                r['balance'] = float(r['sdebit']) - float(r['scredit'])

                completearray.append(r)
                tot_debit = r['debit']
                tot_credit = r['credit']
                tot_scredit = r['scredit']
                tot_sdebit = r['sdebit']
                tot_litigiated = (r['litigiated'] or 0.0)
            else:
                if move_lines[i]['account_id'] <> move_lines[i-1]['account_id']:
                    new_header['debit'] = tot_debit
                    new_header['credit'] = tot_credit
                    new_header['scredit'] = tot_scredit
                    new_header['sdebit'] = tot_sdebit
                    new_header['litigiated'] = tot_litigiated
                    new_header['balance'] = float(tot_sdebit) - float(tot_scredit)
                    new_header['type'] = 3
                    # we reset the counter
                    tot_debit = r['debit']
                    tot_credit = r['credit']
                    tot_scredit = r['scredit']
                    tot_sdebit = r['sdebit']
                    tot_litigiated = (r['litigiated'] or 0.0)

                    new_header = {}
                    new_header['ref'] = ''
                    new_header['name'] = r['account_name']
                    new_header['code'] = r['code']
                    new_header['debit'] = tot_debit
                    new_header['credit'] = tot_credit
                    new_header['scredit'] = tot_scredit
                    new_header['sdebit'] = tot_sdebit
                    new_header['litigiated'] = tot_litigiated
                    new_header['balance'] = float(tot_sdebit) - float(tot_scredit)
                    new_header['type'] = 3

                    completearray.append(new_header)

                    r['type'] = 1

                    r['balance'] = float(r['sdebit']) - float(r['scredit'])

                    completearray.append(r)

                if move_lines[i]['account_id'] == move_lines[i-1]['account_id']:
                    # we reset the counter
                    new_header['debit'] = tot_debit
                    new_header['credit'] = tot_credit
                    new_header['scredit'] = tot_scredit
                    new_header['sdebit'] = tot_sdebit
                    new_header['litigiated'] = tot_litigiated
                    new_header['balance'] = float(tot_sdebit) - float(tot_scredit)
                    new_header['type'] = 3

                    tot_debit = tot_debit + r['debit']
                    tot_credit = tot_credit + r['credit']
                    tot_scredit = tot_scredit + r['scredit']
                    tot_sdebit = tot_sdebit + r['sdebit']
                    tot_litigiated = tot_litigiated + (r['litigiated'] or 0.0)

                    new_header['debit'] = tot_debit
                    new_header['credit'] = tot_credit
                    new_header['scredit'] = tot_scredit
                    new_header['sdebit'] = tot_sdebit
                    new_header['litigiated'] = tot_litigiated
                    new_header['balance'] = float(tot_sdebit) - float(tot_scredit)

                    r['type'] = 2

                    r['balance'] = float(r['sdebit']) - float(r['scredit'])

                    completearray.append(r)

            i = i + 1
        return completearray

    @api.multi
    def render_html(self, data):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_id'))

        display_partner = data['form'].get('display_partner', 'non-zero_balance')
        result_selection = data['form'].get('result_selection')

        if result_selection == 'customer' :
            account_type = ["receivable"]
        elif result_selection == 'supplier':
            account_type = ["payable"]
        else:
            account_type = ["payable", "receivable"]

        partner_lines = self.with_context(data['form'].get('used_context', {}))._get_account_move_entry(account_type, display_partner)
        sum_debit = sum_credit = sum_litige = 0
        # Compute sum of credit, debit and balance for first header(Total) row
        for line in filter(lambda x: x['type'] == 3, partner_lines):
            sum_debit += line['debit'] or 0
            sum_credit += line['credit'] or 0
            sum_litige += line['litigiated'] or 0

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
            'partner_lines': partner_lines,
            'sum_debit': sum_debit,
            'sum_credit': sum_credit,
            'sum_litige': sum_litige,
        }
        return self.env['report'].render('account.report_partnerbalance', docargs)
