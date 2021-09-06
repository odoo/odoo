# -*- coding: utf-8 -*-
#################################################################################
# Author : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
from odoo import api, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class ReportGeneralLedgerPdf(models.AbstractModel):
    _name = 'report.flexipharmacy.general_ledger_template'
    _description = 'Report General Ledger Pdf'

    def _get_init_bal(self, from_date, company_id, account_id):
        result = []
        if from_date and company_id and account_id:
            account_config_id = self.env['res.config.settings'].search([], order='id desc', limit=1)
            current_year = datetime.strptime(from_date, '%Y-%m-%d').year
            if account_config_id and account_config_id.fiscalyear_last_month and account_config_id.fiscalyear_last_day:
                fiscal_month = account_config_id.fiscalyear_last_month
                fiscal_end_date = account_config_id.fiscalyear_last_day
                if fiscal_month == 12:
                    current_year -= 1
                fiscal_year_start_date = str(current_year) + '-' + str(fiscal_month) + '-' + str(fiscal_end_date)
                fiscal_year_start_date = datetime.strftime(
                    datetime.strptime(fiscal_year_start_date, '%Y-%m-%d') + timedelta(days=1), '%Y-%m-%d')
            else:
                fiscal_year_start_date = str(current_year) + '-01-01'
            SQL = """SELECT SUM(aml.debit) AS debit, sum(aml.credit) AS credit
                        FROM account_move_line aml, account_move am
                        WHERE 
                        aml.move_id = am.id AND
                        aml.account_id = %s
                        AND aml.company_id = %s
                        AND aml.date::timestamp::date < '%s'
                        AND am.state = 'posted'""" % (account_id, company_id, str(from_date))
            self._cr.execute(SQL)
            result = self._cr.dictfetchall()
        if result and result[0].get('debit') and result[0].get('credit'):
            result = [result[0].get('debit'), result[0].get('credit'), result[0].get('debit') - result[0].get('credit')]
        elif result and result[0].get('debit') and not result[0].get('credit'):
            result = [result[0].get('debit'), 0.0, result[0].get('debit') - 0.0]
        elif result and not result[0].get('debit') and result[0].get('credit'):
            result = [0.0, result[0].get('credit'), 0.0 - result[0].get('credit')]
        else:
            result = [0.0, 0.0, 0.0]
        return result

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        display_account = data['form'].get('display_account')
        accounts = self.env['account.account'].search([])
        date_from = data.get('form') and data.get('form').get('date_from')
        date_to = data.get('form') and data.get('form').get('date_to')
        sortby = data['form'].get('sortby', 'sort_date')
        journal_ids = data.get('form') and data.get('form').get('journal_ids')
        state = data['form'] and data['form']['target_move']

        move_lines = {line: [] for line in accounts.ids}

        SQL = """ 
            SELECT 
                l.id AS lid,
                l.account_id AS account_id,
                l.date AS ldate,
                j.code AS lcode,
                l.currency_id,
                l.amount_currency,
                l.ref AS lref,
                l.name AS lname,
                COALESCE(l.debit,0) AS debit,
                COALESCE(l.credit,0) AS credit,
                COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) AS balance,
                m.name AS move_name,
                c.symbol AS currency_code,
                p.name AS partner_name
            FROM account_move_line l
            JOIN account_move m ON (l.move_id=m.id)
            LEFT JOIN res_currency c ON (l.currency_id=c.id)
            LEFT JOIN res_partner p ON (l.partner_id=p.id)
            JOIN account_journal j ON (l.journal_id=j.id)
            JOIN account_account acc ON (l.account_id = acc.id)
        """

        where_clause = """
            WHERE l.account_id IN %s
                AND (l.move_id=m.id)
                AND (l.journal_id in %s)
        """ % (" (%s) " % ','.join(map(str, accounts.ids)),
               " (%s) " % ','.join(map(str, journal_ids)),
               )
        if date_from:
            where_clause += "AND m.date >= '%s' " % (date_from)
        if date_to:
            where_clause += "AND m.date <= '%s' " % (date_to)
        if state and state == 'posted':
            where_clause += "AND m.state = '%s' " % (state)

        group_by_clause = """
            GROUP BY l.id, l.account_id, l.date, j.code, l.currency_id, l.amount_currency,
                     l.ref, l.name, m.name, c.symbol, p.name
        """

        sql_sort = 'l.date, l.move_id'
        if sortby == 'sort_journal_partner':
            sql_sort = 'j.code, p.name, l.move_id'

        order_by_clause = " ORDER BY " + sql_sort

        sql_res = self.env.cr.execute(SQL + where_clause + group_by_clause + order_by_clause)

        for row in self.env.cr.dictfetchall():
            balance = 0
            for line in move_lines.get(row['account_id']):
                balance += line['debit'] - line['credit']
            row['balance'] += balance
            move_lines[row.pop('account_id')].append(row)

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
            if date_from and data['form'] and data['form']['include_init_balance']:
                init_bal = self._get_init_bal(date_from, account.company_id.id, account.id)
                res['init_bal'] = init_bal
                res['debit'] += init_bal[0]
                res['credit'] += init_bal[1]
                res['balance'] += init_bal[2]
            if display_account == 'all':
                account_res.append(res)
            if display_account == 'movement' and res.get('move_lines'):
                account_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(res['balance']):
                account_res.append(res)

        codes = []
        if data['form'].get('journal_ids', False):
            codes = [journal.code for journal in
                     self.env['account.journal'].search([('id', 'in', data['form']['journal_ids'])])]

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data,
            'docs': docs,
            'Accounts': account_res,
            'print_journal': codes,
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
