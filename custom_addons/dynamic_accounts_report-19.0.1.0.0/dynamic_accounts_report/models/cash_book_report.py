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
import io
import json
from dateutil.relativedelta import relativedelta
import xlsxwriter
from datetime import datetime
from odoo.tools import date_utils
from odoo import api, fields, models


class CashBookReport(models.TransientModel):
    """For creating Cash Book report"""
    _name = 'cash.book.report'
    _description = 'Account Cash Book Report'

    @api.model
    def view_report(self):
        """
        Retrieves and formats data for the cash book report.

        Returns a dictionary containing the following data:
        - 'move_lines_total': A dictionary containing the total debit, total
                              credit, and currency symbol for each account in
                              the cash journal.
        - 'accounts': A list of dictionaries, each representing an account
                      in the cash journal. Each dictionary contains the
                      'display_name' and 'name' of the account.
        - Additional data for each account: The key is the 'display_name' of the
                                            account, and the value is a list of
                                            dictionaries, each representing a
                                            move line for that account. Each
                                            move line dictionary contains the
                                            following
          data: 'date', 'journal_id', 'partner_id', 'move_name', 'debit',
                 'move_id', 'credit', 'name', and 'ref'.
        """
        data = {}
        move_lines_total = {}
        journals = self.env['account.journal'].search(
            [('type', '=', 'cash')])
        account_move_lines = self.env['account.move.line'].search(
            [('parent_state', '=', 'posted'),
             ('journal_id', 'in', journals.ids)])
        accounts = account_move_lines.mapped('account_id').read(
            ['display_name', 'name'])
        for account in accounts:
            move_lines = account_move_lines.filtered(
                lambda x: x.account_id.id == account['id'])
            move_line_data = move_lines.read(
                ['date', 'journal_id', 'partner_id', 'move_name', 'debit',
                 'move_id',
                 'credit', 'name', 'ref'])
            data[move_lines.mapped('account_id').display_name] = move_line_data
            currency_id = self.env.company.currency_id.symbol
            move_lines_total[move_lines.mapped('account_id').display_name] = {
                'total_debit': round(sum(move_lines.mapped('debit')), 2),
                'total_credit': round(sum(move_lines.mapped('credit')), 2),
                'currency_id': currency_id}
        data['move_lines_total'] = move_lines_total
        data['accounts'] = accounts
        return data

    @api.model
    def get_filter_values(self, partner_id, data_range, account_list, options):
        """
        Retrieves and formats filtered data for the cash book report based on
        the provided filter criteria.
        :param partner_id: List of partner IDs to filter the data by.
        :type partner_id: list
        :param data_range: Specifies the date range filter. Possible values are
                            'month', 'year', 'quarter', 'last-month',
                            'last-year', 'last-quarter', or a dictionary
                            containing 'start_date' and/or 'end_date' fields.
        :type data_range: str or dict
        :param account_list: List of account IDs to filter the data by.
        :type account_list: list
        :param options: Dictionary containing additional options for filtering
                        the data. The 'draft' option indicates
                        whether to include draft journal entries in the data.
        :type options: dict

        :return: A dictionary containing the following data:
                 - 'move_lines_total': A dictionary containing the total debit,
                                       total credit, and currency symbol
                                       for each account in the cash journal.
                 - Additional data for each account: The key is the
                                                    'display_name' of account,
                                                    and the value is a list of
                                                    dictionaries, each
                                                    representing a move line for
                                                    that account. Each move line
                                                     dictionary contains the
                                                     following
                   data: 'date', 'journal_id', 'partner_id', 'move_name',
                          debit', 'move_id', 'credit', 'name', and 'ref'.
        :rtype: dict
        """
        data = {}
        move_lines_total = {}
        today = fields.Date.today()
        quarter_start, quarter_end = date_utils.get_quarter(today)
        previous_quarter_start = quarter_start - relativedelta(months=3)
        previous_quarter_end = quarter_start - relativedelta(days=1)
        journals = self.env['account.journal'].search([('type', '=', 'cash')])
        option_domain = ['posted']
        if options is not None:
            if 'draft' in options:
                option_domain = ['posted', 'draft']
        if partner_id:
            domain = [('parent_state', 'in', option_domain),
                      ('journal_id', 'in', journals.ids),
                      ('partner_id', 'in', partner_id), ]
        else:
            domain = [('parent_state', 'in', option_domain),
                      ('journal_id', 'in', journals.ids), ]
        if account_list:
            domain += ('account_id', 'in', account_list),
        if data_range:
            if data_range == 'month':
                account_move_lines = self.env['account.move.line'].search(
                    domain).filtered(
                    lambda x: x.date.month == fields.Date.today().month)
            elif data_range == 'year':
                account_move_lines = self.env['account.move.line'].search(
                    domain).filtered(
                    lambda x: x.date.year == fields.Date.today().year)
            elif data_range == 'quarter':
                domain += ('date', '>=', quarter_start), (
                    'date', '<=', quarter_end)
                account_move_lines = self.env['account.move.line'].search(
                    domain)
            elif data_range == 'last-month':
                account_move_lines = self.env['account.move.line'].search(
                    domain).filtered(
                    lambda x: x.date.month == fields.Date.today().month - 1)
            elif data_range == 'last-year':
                account_move_lines = self.env['account.move.line'].search(
                    domain).filtered(
                    lambda x: x.date.year == fields.Date.today().year - 1)
            elif data_range == 'last-quarter':
                domain += ('date', '>=', previous_quarter_start), (
                    'date', '<=', previous_quarter_end)
                account_move_lines = self.env['account.move.line'].search(
                    domain)
            elif 'start_date' in data_range and 'end_date' in data_range:
                start_date = datetime.strptime(data_range['start_date'],
                                               '%Y-%m-%d').date()
                end_date = datetime.strptime(data_range['end_date'],
                                             '%Y-%m-%d').date()
                domain += ('date', '>=', start_date), ('date', '<=', end_date),
                account_move_lines = self.env['account.move.line'].search(
                    domain)
            elif 'start_date' in data_range:
                start_date = datetime.strptime(data_range['start_date'],
                                               '%Y-%m-%d').date()
                domain.append(('date', '>=', start_date))
                account_move_lines = self.env['account.move.line'].search(
                    domain)
            elif 'end_date' in data_range:
                end_date = datetime.strptime(data_range['end_date'],
                                             '%Y-%m-%d').date()
                domain.append(('date', '<=', end_date))
                account_move_lines = self.env['account.move.line'].search(
                    domain)
        else:
            account_move_lines = self.env['account.move.line'].search(domain)
        accounts = account_move_lines.mapped('account_id').read(
            ['display_name'])
        for account in accounts:
            move_lines = account_move_lines.filtered(
                lambda x: x.account_id.id == account['id'])
            move_line_data = move_lines.read(
                ['date', 'journal_id', 'partner_id', 'move_name', 'debit',
                 'move_id', 'credit', 'name', 'ref'])
            data[move_lines.mapped('account_id').display_name] = move_line_data
            currency_id = self.env.company.currency_id.symbol
            move_lines_total[move_lines.mapped('account_id').display_name] = {
                'total_debit': round(sum(move_lines.mapped('debit')), 2),
                'total_credit': round(sum(move_lines.mapped('credit')), 2),
                'currency_id': currency_id}
        data['move_lines_total'] = move_lines_total
        return data

    @api.model
    def get_xlsx_report(self, data, response, report_name, report_action):
        """
        Generate an Excel report based on the provided data.
        :param data: The data used to generate the report.
        :type data: str (JSON format)
        :param response: The response object to write the report to.
        :type response: object
        :param report_name: The name of the report.
        :type report_name: str
        :return: None
        """
        data = json.loads(data)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        start_date = data['filters']['start_date'] if \
            data['filters']['start_date'] else ''
        end_date = data['filters']['end_date'] if \
            data['filters']['end_date'] else ''
        sheet = workbook.add_worksheet()
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '15px'})
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
        sheet.write('B4:b4', 'Partners', filter_head)
        sheet.write('B5:b4', 'Accounts', filter_head)
        sheet.write('B6:b4', 'Options', filter_head)
        if start_date or end_date:
            sheet.merge_range('C3:G3', f"{start_date} to {end_date}",
                              filter_body)
        if data['filters']['partner']:
            display_names = [partner.get('display_name', 'undefined') for
                             partner in data['filters']['partner']]
            display_names_str = ', '.join(display_names)
            sheet.merge_range('C4:G4', display_names_str, filter_body)
        if data['filters']['account']:
            account_keys_str = ', '.join(data['filters']['account'])
            sheet.merge_range('C5:G5', account_keys_str, filter_body)
        if data['filters']['options']:
            option_keys = list(data['filters']['options'].keys())
            option_keys_str = ', '.join(option_keys)
            sheet.merge_range('C6:G6', option_keys_str, filter_body)
        if data:
            if report_action == 'dynamic_accounts_report.action_cash_book':
                sheet.write(8, col, ' ', sub_heading)
                sheet.merge_range('B9:C9', 'Journal', sub_heading)
                sheet.merge_range('D9:E9', 'Partner', sub_heading)
                sheet.merge_range('F9:G9', 'Ref', sub_heading)
                sheet.merge_range('H9:I9', 'Move', sub_heading)
                sheet.merge_range('J9:K9', 'Entry Label', sub_heading)
                sheet.merge_range('L9:M9', 'Debit', sub_heading)
                sheet.merge_range('N9:O9', 'Credit', sub_heading)
                sheet.merge_range('P9:Q9', 'Balance', sub_heading)
                row = 8
                for move_line in data['move_lines']:
                    row += 1
                    sheet.write(row, col, move_line, txt_name)
                    sheet.merge_range(row, col + 1, row, col + 2, ' ',
                                      txt_name)
                    sheet.merge_range(row, col + 3, row, col + 4, ' ',
                                      txt_name)
                    sheet.merge_range(row, col + 5, row, col + 6, ' ',
                                      txt_name)
                    sheet.merge_range(row, col + 7, row, col + 8, ' ',
                                      txt_name)
                    sheet.merge_range(row, col + 9, row, col + 10, ' ',
                                      txt_name)
                    sheet.merge_range(row, col + 11, row, col + 12,
                                      data['total'][move_line]['total_debit'],
                                      txt_name)
                    sheet.merge_range(row, col + 13, row, col + 14,
                                      data['total'][move_line]['total_credit'],
                                      txt_name)
                    sheet.merge_range(row, col + 15, row, col + 16,
                                      data['total'][move_line]['total_debit'] -
                                      data['total'][move_line]['total_credit'],
                                      txt_name)
                    for rec in data['data'][move_line]:
                        row += 1
                        if rec['partner_id']:
                            partner = rec['partner_id'][1]
                        else:
                            partner = ' '
                        sheet.write(row, col, rec['date'], txt_name)
                        sheet.merge_range(row, col + 1, row, col + 2,
                                          rec['journal_id'][1],
                                          txt_name)
                        sheet.merge_range(row, col + 3, row, col + 4, partner,
                                          txt_name)
                        sheet.merge_range(row, col + 5, row, col + 6,
                                          rec['ref'], txt_name)
                        sheet.merge_range(row, col + 7, row, col + 8,
                                          rec['move_name'],
                                          txt_name)
                        sheet.merge_range(row, col + 9, row, col + 10,
                                          rec['name'],
                                          txt_name)
                        sheet.merge_range(row, col + 11, row, col + 12,
                                          rec['debit'], txt_name)
                        sheet.merge_range(row, col + 13, row, col + 14,
                                          rec['credit'], txt_name)
                        sheet.merge_range(row, col + 15, row, col + 16, ' ',
                                          txt_name)
                sheet.merge_range(row + 1, col, row + 1, col + 10, 'Total',
                                  filter_head)
                sheet.merge_range(row + 1, col + 11, row + 1, col + 12,
                                  data['grand_total']['total_debit'],
                                  filter_head)
                sheet.merge_range(row + 1, col + 13, row + 1, col + 14,
                                  data['grand_total']['total_credit'],
                                  filter_head)
                sheet.merge_range(row + 1, col + 15, row + 1, col + 16,
                                  float(data['grand_total']['total_debit']) -
                                  float(data['grand_total']['total_credit']),
                                  filter_head)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
