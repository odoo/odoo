# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, fields


class report_account_consolidated_journal(models.AbstractModel):
    _name = "account.consolidated.journal"
    _description = "Consolidated Journals Report"
    _inherit = 'account.report'

    filter_multi_company = None
    filter_date = {'mode': 'range', 'filter': 'this_year'}
    filter_all_entries = False
    filter_journals = True
    filter_unfold_all = False

    # Override: disable multicompany
    def _get_filter_journals(self):
        return self.env['account.journal'].search([('company_id', 'in', [self.env.company.id, False])], order="company_id, name")

    @api.model
    def _get_options(self, previous_options=None):
        options = super(report_account_consolidated_journal, self)._get_options(previous_options=previous_options)
        # We do not want multi company for this report
        options.setdefault('date', {})
        options['date'].setdefault('date_to', fields.Date.context_today(self))
        return options

    def _get_report_name(self):
        return _("Consolidated Journals")

    def _get_columns_name(self, options):
        columns = [{'name': _('Journal Name (Code)')}, {'name': _('Debit'), 'class': 'number'}, {'name': _('Credit'), 'class': 'number'}, {'name': _('Balance'), 'class': 'number'}]
        return columns

    def _get_sum(self, results, lambda_filter):
        sum_debit = self.format_value(sum([r['debit'] for r in results if lambda_filter(r)]))
        sum_credit = self.format_value(sum([r['credit'] for r in results if lambda_filter(r)]))
        sum_balance = self.format_value(sum([r['balance'] for r in results if lambda_filter(r)]))
        return [sum_debit, sum_credit, sum_balance]

    def _get_journal_line(self, options, current_journal, results, record):
        return {
                'id': 'journal_%s' % current_journal,
                'name': '%s (%s)' % (record['journal_name'], record['journal_code']),
                'level': 2,
                'columns': [{'name': n} for n in self._get_sum(results, lambda x: x['journal_id'] == current_journal)],
                'unfoldable': True,
                'unfolded': self._need_to_unfold('journal_%s' % (current_journal,), options),
            }

    def _get_account_line(self, options, current_journal, current_account, results, record):
        return {
                'id': 'account_%s_%s' % (current_account,current_journal),
                'name': '%s %s' % (record['account_code'], record['account_name']),
                'level': 3,
                'columns': [{'name': n} for n in self._get_sum(results, lambda x: x['account_id'] == current_account)],
                'unfoldable': True,
                'unfolded': self._need_to_unfold('account_%s_%s' % (current_account, current_journal), options),
                'parent_id': 'journal_%s' % (current_journal),
            }

    def _get_line_total_per_month(self, options, current_company, results):
        convert_date = self.env['ir.qweb.field.date'].value_to_html
        lines = []
        lines.append({
                    'id': 'Total_all_%s' % (current_company),
                    'name': _('Total'),
                    'class': 'total',
                    'level': 1,
                    'columns': [{'name': n} for n in self._get_sum(results, lambda x: x['company_id'] == current_company)]
        })
        lines.append({
                    'id': 'blank_line_after_total_%s' % (current_company),
                    'name': '',
                    'columns': [{'name': ''} for n in ['debit', 'credit', 'balance']]
        })
        # get range of date for company_id
        dates = []
        for record in results:
            date = '%s-%s' % (record['yyyy'], record['month'])
            if date not in dates:
                dates.append(date)
        if dates:
            lines.append({'id': 'Detail_%s' % (current_company),
                        'name': _('Details per month'),
                        'level': 1,
                        'columns': [{},{},{}]
                        })
            for date in sorted(dates):
                year, month = date.split('-')
                sum_debit = self.format_value(sum([r['debit'] for r in results if (r['month'] == month and r['yyyy'] == year) and r['company_id'] == current_company]))
                sum_credit = self.format_value(sum([r['credit'] for r in results if (r['month'] == month and r['yyyy'] == year) and r['company_id'] == current_company]))
                sum_balance = self.format_value(sum([r['balance'] for r in results if (r['month'] == month and r['yyyy'] == year) and r['company_id'] == current_company]))
                vals = {
                        'id': 'Total_month_%s_%s' % (date, current_company),
                        'name': convert_date('%s-01' % (date), {'format': 'MMM yyyy'}),
                        'level': 2,
                        'columns': [{'name': v} for v in [sum_debit, sum_credit, sum_balance]]
                }
                lines.append(vals)
        return lines

    @api.model
    def _need_to_unfold(self, line_id, options):
        return line_id in options.get('unfolded_lines') or options.get('unfold_all')

    @api.model
    def _get_lines(self, options, line_id=None):
        # 1.Build SQL query
        lines = []
        convert_date = self.env['ir.qweb.field.date'].value_to_html
        select = """
            SELECT to_char("account_move_line".date, 'MM') as month,
                   to_char("account_move_line".date, 'YYYY') as yyyy,
                   COALESCE(SUM("account_move_line".balance), 0) as balance,
                   COALESCE(SUM("account_move_line".debit), 0) as debit,
                   COALESCE(SUM("account_move_line".credit), 0) as credit,
                   j.id as journal_id,
                   j.name as journal_name, j.code as journal_code,
                   account.name as account_name, account.code as account_code,
                   j.company_id, account_id
            FROM %s, account_journal j, account_account account, res_company c
            WHERE %s
              AND "account_move_line".journal_id = j.id
              AND "account_move_line".account_id = account.id
              AND j.company_id = c.id
            GROUP BY month, account_id, yyyy, j.id, account.id, j.company_id
            ORDER BY j.id, account_code, yyyy, month, j.company_id
        """
        tables, where_clause, where_params = self.env['account.move.line'].with_context(strict_range=True)._query_get()
        line_model = None
        if line_id:
            split_line_id = line_id.split('_')
            line_model = split_line_id[0]
            model_id = split_line_id[1]
            where_clause += line_model == 'account' and ' AND account_id = %s AND j.id = %s' or  ' AND j.id = %s'
            where_params += [str(model_id)]
            if line_model == 'account':
                where_params +=[str(split_line_id[2])] # We append the id of the parent journal in case of an account line

        # 2.Fetch data from DB
        select = select % (tables, where_clause)
        self.env.cr.execute(select, where_params)
        results = self.env.cr.dictfetchall()
        if not results:
            return lines

        # 3.Build report lines
        current_account = None
        current_journal = line_model == 'account' and results[0]['journal_id'] or None # If line_id points toward an account line, we don't want to regenerate the parent journal line
        for values in results:
            if values['journal_id'] != current_journal:
                current_journal = values['journal_id']
                lines.append(self._get_journal_line(options, current_journal, results, values))

            if self._need_to_unfold('journal_%s' % (current_journal,), options) and values['account_id'] != current_account:
                current_account = values['account_id']
                lines.append(self._get_account_line(options, current_journal, current_account, results, values))

            # If we need to unfold the line
            if self._need_to_unfold('account_%s_%s' % (values['account_id'], values['journal_id']), options):
                vals = {
                    'id': 'month_%s__%s_%s_%s' % (values['journal_id'], values['account_id'], values['month'], values['yyyy']),
                    'name': convert_date('%s-%s-01' % (values['yyyy'], values['month']), {'format': 'MMM YYYY'}),
                    'caret_options': True,
                    'level': 4,
                    'parent_id': "account_%s_%s" % (values['account_id'], values['journal_id']),
                    'columns': [{'name': n} for n in [self.format_value(values['debit']), self.format_value(values['credit']), self.format_value(values['balance'])]],
                }
                lines.append(vals)

        # Append detail per month section
        if not line_id:
            lines.extend(self._get_line_total_per_month(options, values['company_id'], results))
        return lines
