# -*- coding: utf-8 -*-

import time
from openerp import api, models
from common_report_header import CommonReportHeader


class ReportPartnerBalance(models.AbstractModel, CommonReportHeader):
    _name = 'report.account.report_partnerbalance'

    def lines(self):

        full_account = []
        filters = self.filters.replace('account_move_line__move_id', 'am').replace('account_move_line', 'l')
        params = tuple(self.where_params) + (tuple(self.ACCOUNT_TYPE),) + tuple(self.where_params)
        self.env.cr.execute(
            "SELECT p.ref,l.account_id,ac.name AS account_name,ac.code AS code,p.name, sum(debit) AS debit, sum(credit) AS credit, " \
                    "CASE WHEN sum(debit) > sum(credit) " \
                        "THEN sum(debit) - sum(credit) " \
                        "ELSE 0 " \
                    "END AS sdebit, " \
                    "CASE WHEN sum(debit) < sum(credit) " \
                        "THEN sum(credit) - sum(debit) " \
                        "ELSE 0 " \
                    "END AS scredit, " \
                    "(SELECT sum(debit-credit) " \
                        "FROM account_move_line l, account_move am " \
                        "WHERE l.partner_id = p.id " \
                            + filters + " " \
                            "AND blocked = TRUE " \
                    ") AS enlitige " \
            "FROM account_move_line l LEFT JOIN res_partner p ON (l.partner_id=p.id) " \
            "JOIN account_account ac ON (l.account_id = ac.id)" \
            "JOIN account_move am ON (am.id = l.move_id)" \
            " WHERE ac.internal_type IN %s" \
            + filters + " " \
            "GROUP BY p.id, p.ref, p.name,l.account_id,ac.name,ac.code " \
            "ORDER BY l.account_id,p.name",
            (params))
        res = self.env.cr.dictfetchall()

        full_account = [r for r in res if r['sdebit'] > 0 or r['scredit'] > 0]
        if self.display_partner == 'all':
            full_account = [r for r in res]

        for rec in full_account:
            if not rec.get('name', False):
                rec.update({'name': 'Unknown Partner'})

        ## We will now compute Total
        return self._add_subtotal(full_account)

    def _add_subtotal(self, cleanarray):
        i = 0
        completearray = []
        tot_debit = tot_credit = tot_scredit = tot_sdebit = tot_enlitige = 0.0

        for r in cleanarray:
            # For the first element we always add the line
            # type = 1 is the line is the first of the account
            # type = 2 is an other line of the account
            if i==0:
                # We add the first as the header
                new_header = {}
                new_header['ref'] = ''
                new_header['name'] = r['account_name']
                new_header['code'] = r['code']
                new_header['debit'] = r['debit']
                new_header['credit'] = r['credit']
                new_header['scredit'] = tot_scredit
                new_header['sdebit'] = tot_sdebit
                new_header['enlitige'] = tot_enlitige
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
                tot_enlitige = (r['enlitige'] or 0.0)
                #
            else:
                if cleanarray[i]['account_id'] <> cleanarray[i-1]['account_id']:

                    new_header['debit'] = tot_debit
                    new_header['credit'] = tot_credit
                    new_header['scredit'] = tot_scredit
                    new_header['sdebit'] = tot_sdebit
                    new_header['enlitige'] = tot_enlitige
                    new_header['balance'] = float(tot_sdebit) - float(tot_scredit)
                    new_header['type'] = 3
                    # we reset the counter
                    tot_debit = r['debit']
                    tot_credit = r['credit']
                    tot_scredit = r['scredit']
                    tot_sdebit = r['sdebit']
                    tot_enlitige = (r['enlitige'] or 0.0)

                    new_header = {}
                    new_header['ref'] = ''
                    new_header['name'] = r['account_name']
                    new_header['code'] = r['code']
                    new_header['debit'] = tot_debit
                    new_header['credit'] = tot_credit
                    new_header['scredit'] = tot_scredit
                    new_header['sdebit'] = tot_sdebit
                    new_header['enlitige'] = tot_enlitige
                    new_header['balance'] = float(tot_sdebit) - float(tot_scredit)
                    new_header['type'] = 3

                    completearray.append(new_header)

                    r['type'] = 1

                    r['balance'] = float(r['sdebit']) - float(r['scredit'])

                    completearray.append(r)

                if cleanarray[i]['account_id'] == cleanarray[i-1]['account_id']:
                    # we reset the counter

                    new_header['debit'] = tot_debit
                    new_header['credit'] = tot_credit
                    new_header['scredit'] = tot_scredit
                    new_header['sdebit'] = tot_sdebit
                    new_header['enlitige'] = tot_enlitige
                    new_header['balance'] = float(tot_sdebit) - float(tot_scredit)
                    new_header['type'] = 3

                    tot_debit = tot_debit + r['debit']
                    tot_credit = tot_credit + r['credit']
                    tot_scredit = tot_scredit + r['scredit']
                    tot_sdebit = tot_sdebit + r['sdebit']
                    tot_enlitige = tot_enlitige + (r['enlitige'] or 0.0)

                    new_header['debit'] = tot_debit
                    new_header['credit'] = tot_credit
                    new_header['scredit'] = tot_scredit
                    new_header['sdebit'] = tot_sdebit
                    new_header['enlitige'] = tot_enlitige
                    new_header['balance'] = float(tot_sdebit) - float(tot_scredit)

                    r['type'] = 2

                    r['balance'] = float(r['sdebit']) - float(r['scredit'])

                    completearray.append(r)

            i = i + 1
        return completearray

    def _get_partners(self):

        if self.result_selection == 'customer':
            return 'Receivable Accounts'
        elif self.result_selection == 'supplier':
            return 'Payable Accounts'
        elif self.result_selection == 'customer_supplier':
            return 'Receivable and Payable Accounts'
        return ''

    @api.multi
    def render_html(self, data):
        self.model = self.env.context.get('active_model')
        MoveLine = self.env['account.move.line']
        self.account_ids = []
        docs = self.env[self.model].browse(self.env.context.get('active_id'))
        tables, where_clause, self.where_params = MoveLine.with_context(data['form'].get('used_context', {}))._query_get()
        self.tables = tables.replace('"','')
        self.wheres = [""]
        if where_clause.strip():
            self.wheres.append(where_clause.strip())
        self.filters = " AND ".join(self.wheres)

        self.display_partner = data['form'].get('display_partner', 'non-zero_balance')
        self.result_selection = data['form'].get('result_selection')

        if (self.result_selection == 'customer' ):
            self.ACCOUNT_TYPE = ["receivable"]
        elif (self.result_selection == 'supplier'):
            self.ACCOUNT_TYPE = ["payable"]
        else:
            self.ACCOUNT_TYPE = ["payable", "receivable"]

        self.env.cr.execute("SELECT a.id FROM account_account a " \
                    "WHERE a.internal_type IN %s ", (tuple(self.ACCOUNT_TYPE),))
        self.account_ids = [a for (a,) in self.env.cr.fetchall()]
        lines = self.lines()
        sum_debit = sum_credit = sum_litige = 0
        for line in filter(lambda x: x['type'] == 3, lines):
            sum_debit += line['debit'] or 0
            sum_credit += line['credit'] or 0
            sum_litige += line['enlitige'] or 0

        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'get_journal': self._get_journal,
            'get_partners':self._get_partners,
            'get_target_move': self._get_target_move,
            'lines': lambda: lines,
            'sum_debit': lambda: sum_debit,
            'sum_credit': lambda: sum_credit,
            'sum_litige': lambda: sum_litige,
        }
        return self.env['report'].render('account.report_partnerbalance', docargs)
