# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Swetha Anand (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
import calendar
import io
import json
from datetime import datetime
import xlsxwriter
from odoo import api, fields, models
from odoo.tools.date_utils import get_month, get_fiscal_year, \
    get_quarter_number, subtract


class AccountTrialBalance(models.TransientModel):
    """For creating Trial Balance report"""
    _name = 'account.trial.balance'
    _description = 'Trial Balance Report'

    @api.model
    def view_report(self):
        """
        Generates a trial balance report for multiple accounts.
        Retrieves account information and calculates total debit and credit
        amounts for each account within the specified date range. Returns a list
        of dictionaries containing account details and transaction totals.

        :return: List of dictionaries representing the trial balance report.
        :rtype: list
        """
        account_ids = self.env['account.move.line'].search([]).mapped(
            'account_id')
        today = fields.Date.today()
        move_line_list = []
        for account_id in account_ids:
            initial_move_line_ids = self.env['account.move.line'].search(
                [('date', '<', get_month(today)[0]),
                 ('account_id', '=', account_id.id),
                 ('parent_state', '=', 'posted')])
            initial_total_debit = round(
                sum(initial_move_line_ids.mapped('debit')), 2)
            initial_total_credit = round(
                sum(initial_move_line_ids.mapped('credit')), 2)
            move_line_ids = self.env['account.move.line'].search(
                [('date', '>=', get_month(today)[0]),
                 ('account_id', '=', account_id.id),
                 ('date', '<=', get_month(today)[1]),
                 ('parent_state', '=', 'posted')])
            total_debit = round(sum(move_line_ids.mapped('debit')), 2)
            total_credit = round(sum(move_line_ids.mapped('credit')), 2)
            sum_debit = initial_total_debit + total_debit
            sum_credit = initial_total_credit + total_credit
            diff_credit_debit = sum_debit - sum_credit
            if diff_credit_debit > 0:
                end_total_debit = diff_credit_debit
                end_total_credit = 0.0
            else:
                end_total_debit = 0.0
                end_total_credit = abs(diff_credit_debit)
            data = {
                'account': account_id.display_name,
                'account_id': account_id.id,
                'journal_ids': self.env['account.journal'].search_read([], ['name']),
                'initial_total_debit': "{:,.2f}".format(initial_total_debit),
                'initial_total_credit': "{:,.2f}".format(initial_total_credit),
                'total_debit': total_debit,
                'total_credit': total_credit,
                'end_total_debit': "{:,.2f}".format(end_total_debit),
                'end_total_credit': "{:,.2f}".format(end_total_credit)
            }
            move_line_list.append(data)
        journal = {
            'journal_ids': self.env['account.journal'].search_read([], [
                'name'])
        }
        return move_line_list, journal

    @api.model
    def get_filter_values(self, start_date, end_date, comparison_number,
                          comparison_type, journal_list, analytic, options,
                          method):
        """
        Retrieves and calculates filtered values for generating a financial
        report.
        Retrieves and processes account movement data based on the provided
        filters. Calculates initial, dynamic, and end total debit and credit
        amounts for each account,considering date range, comparison type, and
        other filter criteria.

        :param str start_date: Start date of the reporting period.
        :param str end_date: End date of the reporting period.
        :param int comparison_number: Number of periods for comparison.
        :param str comparison_type: Type of comparison (month, year, quarter).
        :param list[int] journal_list: List of selected journal IDs.
        :param list[int] analytic: List of selected analytic line IDs.
        :param dict options: Additional filtering options (e.g., 'draft').
        :param dict method: Find the method.
        :return: List of dictionaries representing the financial report.
        :rtype: list
        """

        if options == {}:
            options = None
        if options is None:
            option_domain = ['posted']
        elif 'draft' in options:
            option_domain = ['posted', 'draft']
        if method == {}:
            method = None
        dynamic_total_debit = {}
        dynamic_date_num = {}
        dynamic_total_credit = {}
        account_ids = self.env['account.move.line'].search([]).mapped(
            'account_id')
        move_line_list = []
        start_date_first = \
            get_fiscal_year(datetime.strptime(start_date, "%Y-%m-%d").date())[
                0] if comparison_type == 'year' else datetime.strptime(
                start_date, "%Y-%m-%d").date()
        end_date_first = \
            get_fiscal_year(datetime.strptime(end_date, "%Y-%m-%d").date())[
                1] if comparison_type == 'year' else datetime.strptime(end_date,
                                                                       "%Y-%m-%d").date()
        for account_id in account_ids:
            start_date = start_date_first
            end_date = end_date_first
            if comparison_number:
                if comparison_type == 'month':
                    initial_start_date = subtract(start_date, months=eval(
                        comparison_number))
                elif comparison_type == 'year':
                    initial_start_date = subtract(start_date, years=eval(
                        comparison_number))
                else:
                    initial_start_date = subtract(start_date, months=eval(
                        comparison_number) * 3)
            else:
                initial_start_date = start_date
            domain = [('date', '<', initial_start_date),
                      ('account_id', '=', account_id.id),
                      ('parent_state', 'in', option_domain), ]
            if journal_list:
                domain.append(
                    ('journal_id', 'in', journal_list), )
            if analytic:
                domain.append(
                    ('analytic_line_ids', 'in', analytic))
            if method is not None and 'cash' in method:
                domain.append(('journal_id', 'in',
                               self.env.company.tax_cash_basis_journal_id.ids))
            initial_move_line_ids = self.env['account.move.line'].search(
                domain)
            initial_total_debit = round(
                sum(initial_move_line_ids.mapped('debit')), 2)
            initial_total_credit = round(
                sum(initial_move_line_ids.mapped('credit')), 2)
            if comparison_number:
                if comparison_type == 'year':
                    for i in range(1, eval(comparison_number) + 1):
                        com_start_date = subtract(start_date, years=i)
                        com_end_date = subtract(end_date, years=i)
                        domain = [('date', '>=', com_start_date),
                                  ('account_id', '=', account_id.id),
                                  ('date', '<=', com_end_date),
                                  ('parent_state', 'in', option_domain), ]
                        if journal_list:
                            domain.append(
                                ('journal_id', 'in', journal_list), )
                        if analytic:
                            domain.append(
                                ('analytic_line_ids', 'in', analytic))
                        if method is not None and 'cash' in method:
                            domain.append(('journal_id', 'in',
                                           self.env.company.tax_cash_basis_journal_id.ids))
                        move_lines = self.env['account.move.line'].search(
                            domain)
                        dynamic_total_debit[
                            f"dynamic_total_debit_{i}"] = round(
                            sum(move_lines.mapped('debit')), 2)
                        dynamic_total_credit[
                            f"dynamic_total_credit_{i}"] = round(
                            sum(move_lines.mapped('credit')), 2)
                if comparison_type == 'month':
                    dynamic_date_num[
                        f"dynamic_date_num{0}"] = self.get_month_name(
                        start_date) + ' ' + str(
                        start_date.year)
                    for i in range(1, eval(comparison_number) + 1):
                        com_start_date = subtract(start_date, months=i)
                        com_end_date = subtract(end_date, months=i)
                        domain = [('date', '>=', com_start_date),
                                  ('account_id', '=', account_id.id),
                                  ('date', '<=', com_end_date),
                                  ('parent_state', 'in', option_domain)]
                        if journal_list:
                            domain.append(
                                ('journal_id', 'in', journal_list), )
                        if analytic:
                            domain.append(
                                ('analytic_line_ids', 'in', analytic))
                        if method is not None and 'cash' in method:
                            domain.append(('journal_id', 'in',
                                           self.env.company.tax_cash_basis_journal_id.ids), )
                        move_lines = self.env['account.move.line'].search(
                            domain)
                        dynamic_date_num[
                            f"dynamic_date_num{i}"] = self.get_month_name(
                            com_start_date) + ' ' + str(
                            com_start_date.year)
                        dynamic_total_debit[
                            f"dynamic_total_debit_{i}"] = round(
                            sum(move_lines.mapped('debit')), 2)
                        dynamic_total_credit[
                            f"dynamic_total_credit_{i}"] = round(
                            sum(move_lines.mapped('credit')), 2)
                if comparison_type == 'quarter':
                    dynamic_date_num[
                        f"dynamic_date_num{0}"] = 'Q' + ' ' + str(
                        get_quarter_number(start_date)) + ' ' + str(
                        start_date.year)
                    for i in range(1, eval(comparison_number) + 1):
                        com_start_date = subtract(start_date, months=i * 3)
                        com_end_date = subtract(end_date, months=i * 3)
                        domain = [('date', '>=', com_start_date),
                                  ('account_id', '=', account_id.id),
                                  ('date', '<=', com_end_date),
                                  ('parent_state', 'in', option_domain), ]
                        if journal_list:
                            domain.append(
                                ('journal_id', 'in', journal_list))
                        if analytic:
                            domain.append(
                                ('analytic_line_ids', 'in', analytic))
                        if method is not None and 'cash' in method:
                            domain.append(('journal_id', 'in',
                                           self.env.company.tax_cash_basis_journal_id.ids))
                        move_lines = self.env['account.move.line'].search(domain)
                        dynamic_date_num[
                            f"dynamic_date_num{i}"] = 'Q' + ' ' + str(
                            get_quarter_number(com_start_date)) + ' ' + str(
                            com_start_date.year)
                        dynamic_total_debit[
                            f"dynamic_total_debit_{i}"] = round(
                            sum(move_lines.mapped('debit')), 2)
                        dynamic_total_credit[
                            f"dynamic_total_credit_{i}"] = round(
                            sum(move_lines.mapped('credit')), 2)
            domain = [('date', '>=', start_date),
                      ('account_id', '=', account_id.id),
                      ('date', '<=', end_date),
                      ('parent_state', 'in', option_domain)]
            if journal_list:
                domain.append(
                    ('journal_id', 'in', journal_list), )
            if analytic:
                domain.append(
                    ('analytic_line_ids', 'in', analytic))
            if method is not None and 'cash' in method:
                domain.append(('journal_id', 'in',
                               self.env.company.tax_cash_basis_journal_id.ids))
            move_line_ids = self.env['account.move.line'].search(domain)
            total_debit = round(sum(move_line_ids.mapped('debit')), 2)
            total_credit = round(sum(move_line_ids.mapped('credit')), 2)
            sum_debit = initial_total_debit + sum(
                dynamic_total_debit.values()) + total_debit
            sum_credit = initial_total_credit + sum(
                dynamic_total_credit.values()) + total_credit
            diff_credit_debit = sum_debit - sum_credit
            if diff_credit_debit > 0:
                end_total_debit = diff_credit_debit
                end_total_credit = 0.0
            else:
                end_total_debit = 0.0
                end_total_credit = abs(diff_credit_debit)
            data = {
                'account': account_id.display_name,
                'account_id': account_id.id,
                'journal_ids': self.env['account.journal'].search_read([], [
                    'name']),
                'initial_total_debit': initial_total_debit,
                'initial_total_credit': initial_total_credit,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'end_total_debit': end_total_debit,
                'end_total_credit': end_total_credit
            }
            if comparison_number:
                if dynamic_date_num:
                    data['dynamic_date_num'] = dynamic_date_num
                for i in range(1, eval(comparison_number) + 1):
                    data[f'dynamic_total_debit_{i}'] = dynamic_total_debit.get(
                        f"dynamic_total_debit_{eval(comparison_number) + 1 - i}",
                        0.0)
                    data[
                        f'dynamic_total_credit_{i}'] = dynamic_total_credit.get(
                        f"dynamic_total_credit_{eval(comparison_number) + 1 - i}",
                        0.0)
            move_line_list.append(data)
        return move_line_list

    @api.model
    def get_month_name(self, date):
        """
        Retrieve the abbreviated name of the month for a given date.
        :param date: The date for which to retrieve the month's abbreviated name.
        :type date: datetime.date
        :return: Abbreviated name of the month (e.g., 'Jan', 'Feb', ..., 'Dec').
        :rtype: str
        """
        month_names = calendar.month_abbr
        return month_names[date.month]

    @api.model
    def get_xlsx_report(self, data, response, report_name, report_action):
        """
        Generate an XLSX report based on provided data and response stream.
        Generates an Excel workbook with specified report format, including
        subheadings,column headers, and row data for the given financial report
        data.
        :param str data: JSON-encoded data for the report.
        :param response: Response object to stream the generated report.
        :param str report_name: Name of the financial report.
        """
        data = json.loads(data)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        start_date = data['filters']['start_date'] if \
            data['filters']['start_date'] else ''
        end_date = data['filters']['end_date'] if \
            data['filters']['end_date'] else ''
        head = workbook.add_format(
            {'font_size': 15, 'align': 'center', 'bold': True})
        sheet = workbook.add_worksheet()
        sub_heading = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px',
             'border': 1, 'bg_color': '#D3D3D3',
             'border_color': 'black'})
        filter_head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px',
             'border': 1, 'bg_color': '#D3D3D3',
             'border_color': 'black'})
        filter_body = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px'})
        side_heading_sub = workbook.add_format(
            {'align': 'left', 'bold': True, 'font_size': '10px',
             'border': 1,
             'border_color': 'black'})
        side_heading_sub.set_indent(1)
        txt_name = workbook.add_format({'font_size': '10px', 'border': 1})
        txt_name.set_indent(2)
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 15)
        col = 0
        sheet.write('A1:b1', report_name, head)
        sheet.write('B3:b4', 'Date Range', filter_head)
        sheet.write('B4:b4', 'Comparison', filter_head)
        sheet.write('B5:b4', 'Journal', filter_head)
        sheet.write('B6:b4', 'Account', filter_head)
        sheet.write('B7:b4', 'Option', filter_head)
        if start_date or end_date:
            sheet.merge_range('C3:G3', f"{start_date} to {end_date}",
                              filter_body)
        if data['filters']['comparison_number_range']:
            sheet.merge_range('C4:G4',
                              f"{data['filters']['comparison_type']} : {data['filters']['comparison_number_range']}",
                              filter_body)
        if data['filters']['journal']:
            display_names = [journal for
                             journal in data['filters']['journal']]
            display_names_str = ', '.join(display_names)
            sheet.merge_range('C5:G5', display_names_str, filter_body)
        if data['filters']['account']:
            account_keys = [account.get('display_name', 'undefined') for
                            account in data['filters']['account']]
            account_keys_str = ', '.join(account_keys)
            sheet.merge_range('C6:G6', account_keys_str, filter_body)
        if data['filters']['options']:
            option_keys = list(data['filters']['options'].keys())
            option_keys_str = ', '.join(option_keys)
            sheet.merge_range('C7:G7', option_keys_str, filter_body)
        sheet.write(9, col, '', sub_heading)
        # sheet.merge_range(9, col + 1, 9, col + 2, 'Initial Balance',
        #                   sub_heading)
        i = 1  # starting offset

        # Initial Balance header
        sheet.merge_range(9, col + i, 9, col + i + 1, 'Initial Balance', sub_heading)
        sheet.write(10, col + i, 'Debit', sub_heading)
        sheet.write(10, col + i + 1, 'Credit', sub_heading)
        i += 2

        # Dynamic date headers (safely)
        dynamic_dates = {}
        if data.get('data') and len(data['data']) > 0 and len(data['data'][0]) > 0:
            dynamic_dates = data['data'][0][0].get('dynamic_date_num', {})

        if data.get('apply_comparison') and dynamic_dates:
            for key, display in dynamic_dates.items():
                sheet.merge_range(9, col + i, 9, col + i + 1, display, sub_heading)
                sheet.write(10, col + i, 'Debit', sub_heading)
                sheet.write(10, col + i + 1, 'Credit', sub_heading)
                i += 2
        else:
            for date_view in data.get('date_viewed', []):
                sheet.merge_range(9, col + i, 9, col + i + 1, date_view, sub_heading)
                sheet.write(10, col + i, 'Debit', sub_heading)
                sheet.write(10, col + i + 1, 'Credit', sub_heading)
                i += 2

        # End Balance header
        sheet.merge_range(9, col + i, 9, col + i + 1, 'End Balance', sub_heading)
        sheet.write(10, col + i, 'Debit', sub_heading)
        sheet.write(10, col + i + 1, 'Credit', sub_heading)

        if data:
            if report_action == 'dynamic_accounts_report.action_trial_balance':
                row = 11
                for move_line in data['data'][0]:
                    sheet.write(row, col, move_line['account'],
                                side_heading_sub)
                    sheet.write(row, col + 1, move_line['initial_total_debit'],
                                txt_name)
                    sheet.write(row, col + 2,
                                move_line['initial_total_credit'], txt_name)
                    j = 3
                    if data['apply_comparison']:
                        number_of_periods = data['comparison_number_range']
                        for num in number_of_periods:
                            sheet.write(row, col + j, move_line[
                                'dynamic_total_debit_' + str(num)], txt_name)
                            sheet.write(row, col + j + 1, move_line[
                                'dynamic_total_credit_' + str(num)], txt_name)
                            j += 2
                    sheet.write(row, col + j, move_line['total_debit'],
                                txt_name)
                    sheet.write(row, col + j + 1, move_line['total_credit'],
                                txt_name)
                    sheet.write(row, col + j + 2, move_line['end_total_debit'],
                                txt_name)
                    sheet.write(row, col + j + 3,
                                move_line['end_total_credit'], txt_name)
                    row += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
