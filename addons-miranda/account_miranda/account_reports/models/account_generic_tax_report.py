# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields
from odoo.tools import safe_eval
from odoo.tools.translate import _
from odoo.tools.misc import formatLang, format_date
from odoo.exceptions import UserError, RedirectWarning
from odoo.addons.web.controllers.main import clean_action
from dateutil.relativedelta import relativedelta
import json
import base64
from collections import defaultdict

class generic_tax_report(models.AbstractModel):
    _inherit = 'account.report'
    _name = 'account.generic.tax.report'
    _description = 'Generic Tax Report'

    filter_multi_company = None
    filter_date = {'mode': 'range', 'filter': 'last_month'}
    filter_all_entries = False
    filter_comparison = {'date_from': '', 'date_to': '', 'filter': 'no_comparison', 'number_period': 1}
    filter_tax_grids = True

    @api.model
    def _get_options(self, previous_options=None):
        # We want the filter_tax_grids option to only be available if tax report line
        # objects are available for the country of our company.
        if not self.env['account.tax.report.line'].search_count([('country_id', '=', self.env.company.country_id.id)]):
            self.filter_tax_grids = None

        rslt = super(generic_tax_report, self)._get_options(previous_options)
        rslt['date']['strict_range'] = True
        return rslt

    def _get_reports_buttons(self):
        res = super(generic_tax_report, self)._get_reports_buttons()
        res.append({'name': _('Closing Journal Entry'), 'action': 'periodic_tva_entries', 'sequence': 8})
        return res

    def _compute_vat_closing_entry(self, raise_on_empty):
        """ This method returns the one2many commands to balance the tax accounts for the selected period, and
        a dictionnary that will help balance the different accounts set per tax group.
        """
        # first, for each tax group, gather the tax entries per tax and account
        self.env['account.tax'].flush(['name', 'tax_group_id'])
        self.env['account.move.line'].flush(['account_id', 'debit', 'credit', 'move_id', 'tax_line_id', 'date', 'tax_exigible', 'company_id', 'display_type'])
        self.env['account.move'].flush(['state'])
        sql = """SELECT "account_move_line".tax_line_id as tax_id,
                    tax.tax_group_id as tax_group_id,
                    tax.name as tax_name,
                    "account_move_line".account_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0) as amount
                    FROM account_tax tax, %s
                    WHERE %s AND tax.id = "account_move_line".tax_line_id AND "account_move_line".tax_exigible
                    GROUP BY tax.tax_group_id, "account_move_line".tax_line_id, tax.name, "account_move_line".account_id
                """
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        query = sql % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.dictfetchall()
        if not len(results):
            if raise_on_empty:
                raise UserError(_("Nothing to process"))
            else:
                return [], {}

        tax_group_ids = [r['tax_group_id'] for r in results]
        tax_groups = {}
        for tg, result in zip(self.env['account.tax.group'].browse(tax_group_ids), results):
            if tg not in tax_groups:
                tax_groups[tg] = {}
            if result.get('tax_id') not in tax_groups[tg]:
                tax_groups[tg][result.get('tax_id')] = []
            tax_groups[tg][result.get('tax_id')].append((result.get('tax_name'), result.get('account_id'), result.get('amount')))

        # then loop on previous results to
        #    * add the lines that will balance their sum per account
        #    * make the total per tax group's account triplet
        # (if 2 tax groups share the same 3 accounts, they should consolidate in the vat closing entry)
        move_vals_lines = []
        tax_group_subtotal = {}
        for tg, values in tax_groups.items():
            total = 0
            # ignore line that have no property defined on tax group
            if not tg.property_tax_receivable_account_id or not tg.property_tax_payable_account_id:
                continue
            for dummy, value in values.items():
                for v in value:
                    tax_name, account_id, amt = v
                    # Line to balance
                    move_vals_lines.append((0, 0, {'name': tax_name, 'debit': abs(amt) if amt < 0 else 0, 'credit': amt if amt > 0 else 0, 'account_id': account_id}))
                    total += amt

            if total != 0:
                # Add total to correct group
                key = (tg.property_advance_tax_payment_account_id.id or False, tg.property_tax_receivable_account_id.id, tg.property_tax_payable_account_id.id)

                if tax_group_subtotal.get(key):
                    tax_group_subtotal[key] += total
                else:
                    tax_group_subtotal[key] = total
        return move_vals_lines, tax_group_subtotal

    def _add_tax_group_closing_items(self, tax_group_subtotal, end_date):
        """this method transforms the parameter tax_group_subtotal dictionnary into one2many commands
        to balance the tax group accounts for the creation of the vat closing entry.
        """
        def _add_line(account, name):
            self.env.cr.execute(sql_account, (account, end_date))
            result = self.env.cr.dictfetchall()[0]
            advance_balance = result.get('balance') or 0
            # Deduct/Add advance payment
            if advance_balance != 0:
                line_ids_vals.append((0, 0, {
                    'name': name,
                    'debit': abs(advance_balance) if advance_balance < 0 else 0,
                    'credit': abs(advance_balance) if advance_balance > 0 else 0,
                    'account_id': account
                }))
            return advance_balance

        sql_account = '''
            SELECT sum(aml.debit)-sum(aml.credit) AS balance
            FROM account_move_line aml
            LEFT JOIN account_move a
            ON a.id = aml.move_id
            where aml.account_id = %s
                and aml.date <= %s
                and a.state = 'posted'
        '''
        line_ids_vals = []
        # keep track of already balanced account, as one can be used in several tax group
        account_already_balanced = []
        for key, value in tax_group_subtotal.items():
            total = value
            # Search if any advance payment done for that configuration
            if key[0] and key[0] not in account_already_balanced:
                total += _add_line(key[0], _('Balance tax advance payment account'))
                account_already_balanced.append(key[0])
            if key[1] and key[1] not in account_already_balanced:
                total += _add_line(key[1], _('Balance tax current account (receivable)'))
                account_already_balanced.append(key[1])
            if key[2] and key[2] not in account_already_balanced:
                total += _add_line(key[2], _('Balance tax current account (payable)'))
                account_already_balanced.append(key[2])
            # Balance on the receivable/payable tax account
            if total != 0:
                line_ids_vals.append((0, 0, {
                    'name': total < 0 and _('Payable tax amount') or _('Receivable tax amount'),
                    'debit': total if total > 0 else 0,
                    'credit': abs(total) if total < 0 else 0,
                    'account_id': key[2] if total < 0 else key[1]
                }))
        return line_ids_vals

    def _find_create_move(self, date_from, date_to, company_id):
        move = self.env['account.move'].search([('is_tax_closing', '=', True), ('date', '>=', date_from), ('date', '<=', date_to)], limit=1, order='date desc')
        if len(move):
            return move
        else:
            next_date_deadline = date_to + relativedelta(days=company_id.account_tax_periodicity_reminder_day)
            vals = {
                'company_id': company_id,
                'account_tax_periodicity': company_id.account_tax_periodicity,
                'account_tax_periodicity_journal_id': company_id.account_tax_periodicity_journal_id,
                'account_tax_periodicity_next_deadline': next_date_deadline,
            }
            return self.env['res.config.settings']._create_edit_tax_reminder(vals)

    def _generate_tax_closing_entry(self, options, move=False, raise_on_empty=False):
        """ This method is used to automatically post a move for the VAT declaration by doing the following
         Search on all taxes line in the given period, group them by tax_group (each tax group might have its own
         tax receivable/payable account). Create a move line that balance each tax account and add the differene in
         the correct receivable/payable account. Also takes into account amount already paid via advance tax payment account.
        """
        # make the preliminary checks
        company = self.env.company
        if options.get('multi_company'):
            # Ensure that we only have one company selected
            selected_company = False
            for c in options.get('multi_company'):
                if c.get('selected') and selected_company:
                    raise UserError(_("You can only post tax entries for one company at a time"))
                elif c.get('selected'):
                    selected_company = c.get('id')
            if selected_company:
                company = self.env['res.company'].browse(selected_company)

        start_date = fields.Date.from_string(options.get('date').get('date_from'))
        end_date = fields.Date.from_string(options.get('date').get('date_to'))
        if not move:
            move = self._find_create_move(start_date, end_date, company)
        if move.state == 'posted':
            return move
        if company.tax_lock_date and company.tax_lock_date >= end_date:
            raise UserError(_("This period is already closed"))

        # get tax entries by tax_group for the period defined in options
        line_ids_vals, tax_group_subtotal = self._compute_vat_closing_entry(raise_on_empty=raise_on_empty)
        if len(line_ids_vals):
            line_ids_vals += self._add_tax_group_closing_items(tax_group_subtotal, end_date)
        if move.line_ids:
            line_ids_vals += [(2, aml.id) for aml in move.line_ids]
        # create new move
        move_vals = {}
        if len(line_ids_vals):
            move_vals['line_ids'] = line_ids_vals
        else:
            if raise_on_empty:
                action = self.env.ref('account.action_tax_group')
                msg = _('It seems that you have no entries to post, are you sure you correctly configured the accounts on your tax groups?')
                raise RedirectWarning(msg, action.id, _('Configure your TAX accounts'))
        move_vals['tax_report_control_error'] = bool(options.get('tax_report_control_error'))
        if options.get('tax_report_control_error'):
            move.message_post(body=options.get('tax_report_control_error'))
        move.write(move_vals)
        return move

    def _get_columns_name(self, options):
        columns_header = [{}]

        if options.get('tax_grids'):
            columns_header.append({'name': '%s \n %s' % (_('Balance'), self.format_date(options)), 'class': 'number', 'style': 'white-space: pre;'})
            if options.get('comparison') and options['comparison'].get('periods'):
                for p in options['comparison']['periods']:
                    columns_header += [{'name': '%s \n %s' % (_('Balance'), p.get('string')), 'class': 'number', 'style': 'white-space: pre;'}]
        else:
            columns_header += [{'name': '%s \n %s' % (_('NET'), self.format_date(options)), 'class': 'number', 'style': 'white-space: pre;'}, {'name': _('TAX'), 'class': 'number'}]
            if options.get('comparison') and options['comparison'].get('periods'):
                for p in options['comparison']['periods']:
                    columns_header += [{'name': '%s \n %s' % (_('NET'), p.get('string')), 'class': 'number', 'style': 'white-space: pre;'}, {'name': _('TAX'), 'class': 'number'}]

        return columns_header

    def _get_templates(self):
        """ Overridden to add an option to the tax report to display it grouped by tax grid.
        """
        rslt = super(generic_tax_report, self)._get_templates()
        rslt['search_template'] = 'account_reports.search_template_generic_tax_report'
        return rslt

    def _sql_cash_based_taxes(self):
        sql = """SELECT id, sum(base) AS base, sum(net) AS net FROM (
                    SELECT tax.id,
                    SUM("account_move_line".balance) AS base,
                    0.0 AS net
                    FROM account_move_line_account_tax_rel rel, account_tax tax, %s
                    WHERE (tax.tax_exigibility = 'on_payment')
                    AND (rel.account_move_line_id = "account_move_line".id)
                    AND (tax.id = rel.account_tax_id)
                    AND ("account_move_line".tax_exigible)
                    AND %s
                    GROUP BY tax.id
                    UNION
                    SELECT tax.id,
                    0.0 AS base,
                    SUM("account_move_line".balance) AS net
                    FROM account_tax tax, %s
                    WHERE (tax.tax_exigibility = 'on_payment')
                    AND "account_move_line".tax_line_id = tax.id
                    AND ("account_move_line".tax_exigible)
                    AND %s
                    GROUP BY tax.id) cash_based
                    GROUP BY id;"""
        return sql

    def _sql_tax_amt_regular_taxes(self):
        sql = """SELECT "account_move_line".tax_line_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0)
                    FROM account_tax tax, %s
                    WHERE %s AND tax.tax_exigibility = 'on_invoice' AND tax.id = "account_move_line".tax_line_id
                    GROUP BY "account_move_line".tax_line_id"""
        return sql

    def _sql_net_amt_regular_taxes(self):
        return '''
            SELECT 
                tax.id,
                 COALESCE(SUM(account_move_line.balance))
            FROM %s
            JOIN account_move_line_account_tax_rel rel ON rel.account_move_line_id = account_move_line.id
            JOIN account_tax tax ON tax.id = rel.account_tax_id
            WHERE %s AND tax.tax_exigibility = 'on_invoice' 
            GROUP BY tax.id

            UNION ALL

            SELECT 
                child_tax.id,
                 COALESCE(SUM(account_move_line.balance))
            FROM %s
            JOIN account_move_line_account_tax_rel rel ON rel.account_move_line_id = account_move_line.id
            JOIN account_tax tax ON tax.id = rel.account_tax_id
            JOIN account_tax_filiation_rel child_rel ON child_rel.parent_tax = tax.id
            JOIN account_tax child_tax ON child_tax.id = child_rel.child_tax
            WHERE %s 
                AND child_tax.tax_exigibility = 'on_invoice' 
                AND tax.amount_type = 'group' 
                AND child_tax.amount_type != 'group'
            GROUP BY child_tax.id
        '''

    def _compute_from_amls(self, options, dict_to_fill, period_number):
        """ Fills dict_to_fill with the data needed to generate the report.
        """
        if options.get('tax_grids'):
            self._compute_from_amls_grids(options, dict_to_fill, period_number)
        else:
            self._compute_from_amls_taxes(options, dict_to_fill, period_number)

    def _compute_from_amls_grids(self, options, dict_to_fill, period_number):
        """ Fills dict_to_fill with the data needed to generate the report, when
        the report is set to group its line by tax grid.
        """
        tables, where_clause, where_params = self._query_get(options)
        sql = """SELECT account_tax_report_line_tags_rel.account_tax_report_line_id,
                        SUM(coalesce(account_move_line.balance, 0) * CASE WHEN acc_tag.tax_negate THEN -1 ELSE 1 END
                                                 * CASE WHEN account_journal.type = 'sale' THEN -1 ELSE 1 END
                                                 * CASE WHEN account_move.type in ('in_refund', 'out_refund') THEN -1 ELSE 1 END)
                        AS balance
                 FROM %s
                 JOIN account_move
                 ON account_move_line.move_id = account_move.id
                 JOIN account_account_tag_account_move_line_rel aml_tag
                 ON aml_tag.account_move_line_id = account_move_line.id
                 JOIN account_journal
                 ON account_move.journal_id = account_journal.id
                 JOIN account_account_tag acc_tag
                 ON aml_tag.account_account_tag_id = acc_tag.id
                 JOIN account_tax_report_line_tags_rel
                 ON acc_tag.id = account_tax_report_line_tags_rel.account_account_tag_id
                 WHERE account_move_line.tax_exigible AND %s
                 GROUP BY account_tax_report_line_tags_rel.account_tax_report_line_id
        """ %(tables, where_clause)
        self.env.cr.execute(sql, where_params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in dict_to_fill:
                dict_to_fill[result[0]]['periods'][period_number]['balance'] = result[1]
                dict_to_fill[result[0]]['show'] = True

    def _compute_from_amls_taxes(self, options, dict_to_fill, period_number):
        """ Fills dict_to_fill with the data needed to generate the report, when
        the report is set to group its line by tax.
        """
        sql = self._sql_cash_based_taxes()
        tables, where_clause, where_params = self._query_get(options)
        query = sql % (tables, where_clause, tables, where_clause)
        self.env.cr.execute(query, where_params + where_params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in dict_to_fill:
                dict_to_fill[result[0]]['periods'][period_number]['net'] = result[1]
                dict_to_fill[result[0]]['periods'][period_number]['tax'] = result[2]
                dict_to_fill[result[0]]['show'] = True

        # Tax base amount.
        sql = self._sql_net_amt_regular_taxes()
        query = sql % (tables, where_clause, tables, where_clause)
        self.env.cr.execute(query, where_params + where_params)

        for tax_id, balance in self.env.cr.fetchall():
            if tax_id in dict_to_fill:
                dict_to_fill[tax_id]['periods'][period_number]['net'] += balance
                dict_to_fill[tax_id]['show'] = True

        sql = self._sql_tax_amt_regular_taxes()
        query = sql % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in dict_to_fill:
                dict_to_fill[result[0]]['periods'][period_number]['tax'] = result[1]
                dict_to_fill[result[0]]['show'] = True

    def _get_type_tax_use_string(self, value):
        return [option[1] for option in self.env['account.tax']._fields['type_tax_use'].selection if option[0] == value][0]

    @api.model
    def _get_lines(self, options, line_id=None):
        data = self._compute_tax_report_data(options)
        if options.get('tax_grids'):
            return self._get_lines_by_grid(options, line_id, data)
        return self._get_lines_by_tax(options, line_id, data)

    def _get_lines_by_grid(self, options, line_id, grids):
        # Fetch the report layout to use
        country = self.env.company.country_id
        report_lines = self.env['account.tax.report.line'].search([('country_id', '=', country.id), ('parent_id', '=', False)])

        # Build the report, line by line
        lines = []
        lines_stack = list(report_lines) # first element of the list is the top of the stack
        deferred_total_lines = [] # list of tuples (index where to add the total in lines, tax report line object)
        while lines_stack:
            # Pop the first section off the stack
            current_line = lines_stack.pop(0)

            hierarchy_level = self._get_hierarchy_level(current_line)

            if current_line.formula:
                # Then it's a total line
                # We defer the adding of total lines, since their balance depends
                # on the rest of the report. We use a special dictionnary for that,
                # keeping track of hierarchy level
                lines.append({'id': 'deferred_total', 'level': hierarchy_level})
                deferred_total_lines.append((len(lines)-1, current_line))
            elif current_line.tag_name:
                # Then it's a tax grid line
                lines.append(self._build_tax_grid_line(grids[current_line.id], hierarchy_level))
            else:
                # Then it's a title line
                lines.append(self._build_tax_section_line(current_line, hierarchy_level))

            # Put current section's children on top the stack and update hierarchy if necessary
            if current_line.children_line_ids:
                lines_stack = list(current_line.children_line_ids) + lines_stack

        # Fill in in the total for each title line and get a mapping linking line codes to balances
        balances_by_code = self._postprocess_lines(lines, options)
        for (index, total_line) in deferred_total_lines:
            hierarchy_level = self._get_hierarchy_level(total_line)
            # number_period option contains 1 if no comparison, or the number of periods to compare with if there is one.
            total_period_number = 1 + (options['comparison'].get('periods') and options['comparison']['number_period'] or 0)
            lines[index] = self._build_total_line(total_line, balances_by_code, hierarchy_level, total_period_number, options)

        return lines

    def _get_hierarchy_level(self, report_line):
        """ Returns the hierarchy level to be used by a tax report line, depending
        on its parents.
        A line with no parent will have a hierarchy of 1.
        A line with n parents will have a hierarchy of 2n+1.
        """
        return 1 + 2 * (len(report_line.parent_path[:-1].split('/')) - 1)

    def _postprocess_lines(self, lines, options):
        """ Postprocesses the report line dictionaries generated for a grouped
        by tax grid report, in order to compute the balance of each of its non-total sections.

        :param lines: The list of dictionnaries conaining all the line data generated for this report.
                      Title lines will be modified in place to have a balance corresponding to the sum
                      of their children's

        :param options: The dictionary of options used to buld the report.

        :return: A dictionary mapping the line codes defined in this report to the corresponding balances.
        """
        balances_by_code = {}
        totals_by_line = {}
        active_sections_stack = []
        col_nber = len(options['comparison']['periods']) + 1

        def assign_active_section(col_nber):
            line_to_assign = active_sections_stack.pop()
            total_balance_col = totals_by_line.get(line_to_assign['id'], [0] * col_nber)
            line_to_assign['columns'] = [{'name': self.format_value(balance), 'style': 'white-space:nowrap;', 'balance': balance} for balance in total_balance_col]

            if line_to_assign.get('line_code'):
                balances_by_code[line_to_assign['line_code']] = total_balance_col

        for line in lines:
            while active_sections_stack and line['level'] <= active_sections_stack[-1]['level']:
                assign_active_section(col_nber)

            if line['id'] == 'deferred_total':
                pass
            elif str(line['id']).startswith('section_'):
                active_sections_stack.append(line)
            else:
                if line.get('line_code'):
                    balances_by_code[line['line_code']] = [col['balance'] for col in line['columns']]

                if active_sections_stack:
                    for active_section in active_sections_stack:
                        line_balances = [col['balance'] for col in line['columns']]
                        rslt_balances = totals_by_line.get(active_section['id'])
                        totals_by_line[active_section['id']] = line_balances if not rslt_balances else [line_balances[i] + rslt_balances[i] for i in range(0, len(rslt_balances))]

        self.compute_check(lines, options)

        #Treat the last sections (the one that were not followed by a line with lower level)
        while active_sections_stack:
            assign_active_section(col_nber)

        return balances_by_code

    def compute_check(self, lines, options):
        if not self.get_checks_to_perform(defaultdict(lambda: 0)):
            return  # nothing to do here


        col_nber = len(options['comparison']['periods']) + 1
        mapping = {}
        controls = []
        html_lines = []
        for line in lines:
            if line.get('line_code'):
                mapping[line['line_code']] = line['columns'][0]['balance']
        for i, calc in enumerate(self.get_checks_to_perform(mapping)):
            if calc[1]:
                if isinstance(calc[1], float):
                    value = self.format_value(calc[1])
                else:
                    value = calc[1]
                controls.append({'name': calc[0], 'id': 'control_' + str(i), 'columns': [{'name': value, 'style': 'white-space:nowrap;', 'balance': calc[1]}]})
                html_lines.append("<tr><td>{name}</td><td>{amount}</td></tr>".format(name=calc[0], amount=value))
        if controls:
            lines.extend([{'id': 'section_control', 'name': _('Controls failed'), 'unfoldable': False, 'columns': [{'name': '', 'style': 'white-space:nowrap;', 'balance': ''}] * col_nber, 'level': 0, 'line_code': False}] + controls)
            options['tax_report_control_error'] = "<table width='100%'><tr><th>Control</th><th>Difference</th></tr>{}</table>".format("".join(html_lines))

    def get_checks_to_perform(self, d):
        """ To override in localizations
        If value is a float, it will be formatted with format_value
        The line is not displayed if it is falsy (0, 0.0, False, ...)
        :param d: the mapping dictionay between codes and values
        :return: iterable of tuple (name, value)
        """
        return ()

    def _get_total_line_eval_dict(self, period_balances_by_code, period_date_from, period_date_to, options):
        """ By default, this function only returns period_balances_by_code; but it
        is meant to be overridden in the few situations where we need to evaluate
        something we cannot compute with only tax report line codes.
        """
        return period_balances_by_code

    def _build_total_line(self, report_line, balances_by_code, hierarchy_level, number_periods, options):
        """ Returns the report line dictionary corresponding to a given total line,
        computing if from its formula.
        """
        columns = []
        for period_index in range(0, number_periods):
            period_balances_by_code = {code: balances[period_index] for code, balances in balances_by_code.items()}
            period_date_from = (period_index==0) and options['date']['date_from'] or options['comparison']['periods'][period_index-1]['date_from']
            period_date_to = (period_index==0) and options['date']['date_to'] or options['comparison']['periods'][period_index-1]['date_to']

            eval_dict = self._get_total_line_eval_dict(period_balances_by_code, period_date_from, period_date_to, options)
            period_total = safe_eval(report_line.formula, eval_dict)
            columns.append({'name': '' if period_total is None else self.format_value(period_total), 'style': 'white-space:nowrap;', 'balance': period_total or 0.0})

        return {
            'id': 'total_' + str(report_line.id),
            'name': report_line.name,
            'unfoldable': False,
            'columns': columns,
            'level': hierarchy_level,
            'line_code': report_line.code
        }


    def _build_tax_section_line(self, section, hierarchy_level):
        """ Returns the report line dictionary corresponding to a given section,
        when grouping the report by tax grid.
        """
        return {
            'id': 'section_' + str(section.id),
            'name': section.name,
            'unfoldable': False,
            'columns': [],
            'level': hierarchy_level,
            'line_code': section.code,
        }

    def _build_tax_grid_line(self, grid_data, hierarchy_level):
        """ Returns the report line dictionary corresponding to a given tax grid,
        when grouping the report by tax grid.
        """
        columns = []
        for period in grid_data['periods']:
            columns += [{'name': self.format_value(period['balance']), 'style': 'white-space:nowrap;', 'balance': period['balance']}]

        rslt = {
            'id': grid_data['obj'].id,
            'name': grid_data['obj'].name,
            'unfoldable': False,
            'columns': columns,
            'level': hierarchy_level,
            'line_code': grid_data['obj'].code,
        }

        if grid_data['obj'].report_action_id:
            rslt['action_id'] = grid_data['obj'].report_action_id.id
        else:
            rslt['caret_options'] = 'account.tax.report.line'

        return rslt

    def _get_lines_by_tax(self, options, line_id, taxes):
        lines = []
        types = ['sale', 'purchase']
        groups = dict((tp, {}) for tp in types)
        for key, tax in taxes.items():

            # 'none' taxes are skipped.
            if tax['obj'].type_tax_use == 'none':
                continue

            if tax['obj'].amount_type == 'group':

                # Group of taxes without child are skipped.
                if not tax['obj'].children_tax_ids:
                    continue

                # - If at least one children is 'none', show the group of taxes.
                # - If all children are different of 'none', only show the children.

                tax['children'] = []
                tax['show'] = False
                for child in tax['obj'].children_tax_ids:

                    if child.type_tax_use != 'none':
                        continue

                    tax['show'] = True
                    for i, period_vals in enumerate(taxes[child.id]['periods']):
                        tax['periods'][i]['tax'] += period_vals['tax']

            groups[tax['obj'].type_tax_use][key] = tax

        period_number = len(options['comparison'].get('periods'))
        line_id = 0
        for tp in types:
            if not any([tax.get('show') for key, tax in groups[tp].items()]):
                continue
            sign = tp == 'sale' and -1 or 1
            lines.append({
                    'id': tp,
                    'name': self._get_type_tax_use_string(tp),
                    'unfoldable': False,
                    'columns': [{} for k in range(0, 2 * (period_number + 1) or 2)],
                    'level': 1,
                })
            for key, tax in sorted(groups[tp].items(), key=lambda k: k[1]['obj'].sequence):
                if tax['show']:
                    columns = []
                    for period in tax['periods']:
                        columns += [{'name': self.format_value(period['net'] * sign), 'style': 'white-space:nowrap;'},{'name': self.format_value(period['tax'] * sign), 'style': 'white-space:nowrap;'}]

                    if tax['obj'].amount_type == 'group':
                        report_line_name = tax['obj'].name
                    else:
                        report_line_name = '%s (%s)' % (tax['obj'].name, tax['obj'].amount)

                    lines.append({
                        'id': tax['obj'].id,
                        'name': report_line_name,
                        'unfoldable': False,
                        'columns': columns,
                        'level': 4,
                        'caret_options': 'account.tax',
                    })
                    for child in tax.get('children', []):
                        columns = []
                        for period in child['periods']:
                            columns += [{'name': self.format_value(period['net'] * sign), 'style': 'white-space:nowrap;'},{'name': self.format_value(period['tax'] * sign), 'style': 'white-space:nowrap;'}]
                        lines.append({
                            'id': child['obj'].id,
                            'name': '   ' + child['obj'].name + ' (' + str(child['obj'].amount) + ')',
                            'unfoldable': False,
                            'columns': columns,
                            'level': 4,
                            'caret_options': 'account.tax',
                        })
            line_id += 1
        return lines

    @api.model
    def _compute_tax_report_data(self, options):
        rslt = {}
        grouping_key = options.get('tax_grids') and 'account.tax.report.line' or 'account.tax'
        search_domain = options.get('tax_grids') and [('country_id', '=', self.env.company.country_id.id)] or [('company_id', '=', self.env.company.id)]
        empty_data_dict = options.get('tax_grids') and {'balance': 0} or {'net': 0, 'tax': 0}
        for record in self.env[grouping_key].with_context(active_test=False).search(search_domain):
            rslt[record.id] = {'obj': record, 'show': False, 'periods': [empty_data_dict.copy()]}
            for period in options['comparison'].get('periods'):
                rslt[record.id]['periods'].append(empty_data_dict.copy())

        period_number = 0
        self._compute_from_amls(options, rslt, period_number)
        for period in options['comparison'].get('periods'):
            period_number += 1
            self.with_context(date_from=period.get('date_from'), date_to=period.get('date_to'))._compute_from_amls(options, rslt, period_number)

        return rslt

    @api.model
    def _get_report_name(self):
        return _('Tax Report')
