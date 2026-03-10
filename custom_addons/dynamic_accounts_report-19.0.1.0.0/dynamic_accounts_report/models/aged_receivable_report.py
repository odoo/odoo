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

import xlsxwriter
from odoo import models, fields, api


class AgeReceivableReport(models.TransientModel):
    """For creating Age Receivable report"""
    _name = 'age.receivable.report'
    _description = 'Aged Receivable Report'

    @api.model
    def view_report(self):
        """
        Generate a report with move line data categorized by partner and debit
        difference. This method retrieves move line data from the
        'account.move.line' model, filters the records based on specific
        criteria (parent_state, account_type, reconciled), and categorizes the
        data by each partner's name. For each move line, it calculates the debit
        difference based on the number of days between today's date and the
        maturity date of the move line.
        Returns:
        dict: Dictionary containing move line data categorized by partner names.
              Each partner's data includes debit amounts and debit differences
              based on days between maturity date and today.
              The 'partner_totals' key contains summary data for each partner.
        """
        partner_total = {}
        move_line_list = {}
        paid = self.env['account.move.line'].search(
            [('parent_state', '=', 'posted'),
             ('account_type', '=', 'asset_receivable'),
             ('reconciled', '=', False)])
        currency_id = self.env.company.currency_id.symbol
        partner_ids = paid.mapped('partner_id')
        today = fields.Date.today()

        # Define a helper function to format numbers with thousand separators
        def format_number(value):
            return "{:,.2f}".format(value)  # Adds thousand separator and 2 decimal places

        for partner_id in partner_ids:
            move_line_ids = paid.filtered(
                lambda rec: rec.partner_id in partner_id)
            move_line_data = move_line_ids.read(
                ['name', 'move_name', 'date', 'amount_currency', 'account_id',
                 'date_maturity', 'currency_id', 'debit', 'move_id'])
            for val in move_line_data:
                difference = 0  # Initialize difference to avoid undefined variable
                if val['date_maturity']:
                    difference = (today - val['date_maturity']).days
                # Keep raw numeric values for calculations
                val['raw_amount_currency'] = val['amount_currency']
                val['raw_debit'] = val['debit']
                val['diff0'] = val['debit'] if difference <= 0 else 0.0
                val['diff1'] = val['debit'] if 0 < difference <= 30 else 0.0
                val['diff2'] = val['debit'] if 30 < difference <= 60 else 0.0
                val['diff3'] = val['debit'] if 60 < difference <= 90 else 0.0
                val['diff4'] = val['debit'] if 90 < difference <= 120 else 0.0
                val['diff5'] = val['debit'] if difference > 120 else 0.0
                # Keep raw values for diff fields
                val['raw_diff0'] = val['diff0']
                val['raw_diff1'] = val['diff1']
                val['raw_diff2'] = val['diff2']
                val['raw_diff3'] = val['diff3']
                val['raw_diff4'] = val['diff4']
                val['raw_diff5'] = val['diff5']
                # Format the numeric fields for display
                val['amount_currency'] = format_number(val['amount_currency'])
                val['debit'] = format_number(val['debit'])
                val['diff0'] = format_number(val['diff0'])
                val['diff1'] = format_number(val['diff1'])
                val['diff2'] = format_number(val['diff2'])
                val['diff3'] = format_number(val['diff3'])
                val['diff4'] = format_number(val['diff4'])
                val['diff5'] = format_number(val['diff5'])
            move_line_list[partner_id.name] = move_line_data
            partner_total[partner_id.name] = {
                'debit_sum': sum(val['raw_debit'] for val in move_line_data),
                'diff0_sum': round(sum(val['raw_diff0'] for val in move_line_data), 2),
                'diff1_sum': round(sum(val['raw_diff1'] for val in move_line_data), 2),
                'diff2_sum': round(sum(val['raw_diff2'] for val in move_line_data), 2),
                'diff3_sum': round(sum(val['raw_diff3'] for val in move_line_data), 2),
                'diff4_sum': round(sum(val['raw_diff4'] for val in move_line_data), 2),
                'diff5_sum': round(sum(val['raw_diff5'] for val in move_line_data), 2),
                # Format the summary fields for display
                'debit_sum_display': format_number(sum(val['raw_debit'] for val in move_line_data)),
                'diff0_sum_display': format_number(round(sum(val['raw_diff0'] for val in move_line_data), 2)),
                'diff1_sum_display': format_number(round(sum(val['raw_diff1'] for val in move_line_data), 2)),
                'diff2_sum_display': format_number(round(sum(val['raw_diff2'] for val in move_line_data), 2)),
                'diff3_sum_display': format_number(round(sum(val['raw_diff3'] for val in move_line_data), 2)),
                'diff4_sum_display': format_number(round(sum(val['raw_diff4'] for val in move_line_data), 2)),
                'diff5_sum_display': format_number(round(sum(val['raw_diff5'] for val in move_line_data), 2)),
                'currency_id': currency_id,
                'partner_id': partner_id.id
            }
        move_line_list['partner_totals'] = partner_total
        return move_line_list

    @api.model
    def get_filter_values(self, date, partner):
        """
         Retrieve move line data categorized by partner and debit difference.

         Parameters:
             date (str): Date for filtering move lines (format: 'YYYY-MM-DD').
             partner (list): List of partner IDs to filter move lines for.

         Returns:
             dict: Dictionary containing move line data categorized by partner
                   names.Includes debit amount categorization based on days
                   difference.Contains partner-wise summary under
                   'partner_totals' key.
         """
        partner_total = {}
        move_line_list = {}
        if date:
            paid = self.env['account.move.line'].search(
                [('parent_state', '=', 'posted'),
                 ('account_type', '=', 'asset_receivable'),
                 ('reconciled', '=', False), ('date', '<=', date)])
        else:
            paid = self.env['account.move.line'].search(
                [('parent_state', '=', 'posted'),
                 ('account_type', '=', 'asset_receivable'),
                 ('reconciled', '=', False)])
        currency_id = self.env.company.currency_id.symbol
        if partner:
            partner_ids = self.env['res.partner'].search(
                [('id', 'in', partner)])
        else:
            partner_ids = paid.mapped('partner_id')
        today = fields.Date.today()
        for partner_id in partner_ids:
            move_line_ids = paid.filtered(
                lambda rec: rec.partner_id in partner_id)
            move_line_data = move_line_ids.read(
                ['name', 'move_name', 'date', 'amount_currency', 'account_id',
                 'date_maturity', 'currency_id', 'debit', 'move_id'])
            for val in move_line_data:
                diffrence = 0
                if val['date_maturity']:
                    diffrence = (today - val['date_maturity']).days
                val['diff0'] = val['debit'] if diffrence <= 0 else 0.0
                val['diff1'] = val['debit'] if 0 < diffrence <= 30 else 0.0
                val['diff2'] = val['debit'] if 30 < diffrence <= 60 else 0.0
                val['diff3'] = val['debit'] if 60 < diffrence <= 90 else 0.0
                val['diff4'] = val['debit'] if 90 < diffrence <= 120 else 0.0
                val['diff5'] = val['debit'] if diffrence > 120 else 0.0
            move_line_list[partner_id.name] = move_line_data
            partner_total[partner_id.name] = {
                'debit_sum': sum(val['debit'] for val in move_line_data),
                'diff0_sum': round(sum(val['diff0'] for val in move_line_data),
                                   2),
                'diff1_sum': round(sum(val['diff1'] for val in move_line_data),
                                   2),
                'diff2_sum': round(sum(val['diff2'] for val in move_line_data),
                                   2),
                'diff3_sum': round(sum(val['diff3'] for val in move_line_data),
                                   2),
                'diff4_sum': round(sum(val['diff4'] for val in move_line_data),
                                   2),
                'diff5_sum': round(sum(val['diff5'] for val in move_line_data),
                                   2),
                'currency_id': currency_id,
                'partner_id': partner_id.id
            }
        move_line_list['partner_totals'] = partner_total
        return move_line_list

    @api.model
    def get_xlsx_report(self, data, response, report_name, report_action):
        """
        Generate an Excel report based on the provided data with thousand separators.

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
        # Define a number format with thousand separator
        num_format = workbook.add_format({'font_size': '10px', 'border': 1, 'num_format': '#,##0.00'})
        num_format.set_indent(2)
        # Define a number format for totals with thousand separator
        total_num_format = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px',
             'border': 1, 'bg_color': '#D3D3D3',
             'border_color': 'black', 'num_format': '#,##0.00'})
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 15)
        col = 0
        sheet.write('A1:b1', report_name, head)
        sheet.write('B3:b4', 'Date Range', filter_head)
        sheet.write('B4:b4', 'Partners', filter_head)
        if end_date:
            sheet.merge_range('C3:G3', f"{end_date}", filter_body)
        if data['filters']['partner']:
            display_names = [partner.get('display_name', 'undefined') for
                             partner in data['filters']['partner']]
            display_names_str = ', '.join(display_names)
            sheet.merge_range('C4:G4', display_names_str, filter_body)
        if data:
            if report_action == 'dynamic_accounts_report.action_aged_receivable':
                sheet.write(6, col, ' ', sub_heading)
                sheet.write(6, col + 1, 'Invoice Date', sub_heading)
                sheet.write(6, col + 2, 'Amount Currency', sub_heading)
                sheet.write(6, col + 3, 'Currency', sub_heading)
                sheet.merge_range(6, col + 4, 6, col + 5, 'Account',
                                  sub_heading)
                sheet.merge_range(6, col + 6, 6, col + 7, 'Expected Date',
                                  sub_heading)
                sheet.write(6, col + 8, 'At Date', sub_heading)
                sheet.write(6, col + 9, '1-30', sub_heading)
                sheet.write(6, col + 10, '31-60', sub_heading)
                sheet.write(6, col + 11, '61-90', sub_heading)
                sheet.write(6, col + 12, '91-120', sub_heading)
                sheet.write(6, col + 13, 'Older', sub_heading)
                sheet.write(6, col + 14, 'Total', sub_heading)
                row = 6
                for move_line in data['move_lines']:
                    row += 1
                    sheet.write(row, col, move_line, txt_name)
                    sheet.write(row, col + 1, ' ', txt_name)
                    sheet.write(row, col + 2, ' ', txt_name)
                    sheet.write(row, col + 3, ' ', txt_name)
                    sheet.merge_range(row, col + 4, row, col + 5, ' ',
                                      txt_name)
                    sheet.merge_range(row, col + 6, row, col + 7, ' ',
                                      txt_name)
                    sheet.write(row, col + 8,
                                data['total'][move_line]['diff0_sum'],
                                num_format)
                    sheet.write(row, col + 9,
                                data['total'][move_line]['diff1_sum'],
                                num_format)
                    sheet.write(row, col + 10,
                                data['total'][move_line]['diff2_sum'],
                                num_format)
                    sheet.write(row, col + 11,
                                data['total'][move_line]['diff3_sum'],
                                num_format)
                    sheet.write(row, col + 12,
                                data['total'][move_line]['diff4_sum'],
                                num_format)
                    sheet.write(row, col + 13,
                                data['total'][move_line]['diff5_sum'],
                                num_format)
                    sheet.write(row, col + 14,
                                data['total'][move_line]['debit_sum'],
                                num_format)
                    for rec in data['data'][move_line]:
                        row += 1
                        if not rec['name']:
                            rec['name'] = ' '
                        sheet.write(row, col, rec['move_name'] + rec['name'],
                                    txt_name)
                        sheet.write(row, col + 1, rec['date'],
                                    txt_name)
                        sheet.write(row, col + 2, rec['amount_currency'],
                                    num_format)
                        sheet.write(row, col + 3, rec['currency_id'][1],
                                    txt_name)
                        sheet.merge_range(row, col + 4, row, col + 5,
                                          rec['account_id'][1],
                                          txt_name)
                        sheet.merge_range(row, col + 6, row, col + 7,
                                          rec['date_maturity'],
                                          txt_name)
                        sheet.write(row, col + 8, rec['diff0'], num_format)
                        sheet.write(row, col + 9, rec['diff1'], num_format)
                        sheet.write(row, col + 10, rec['diff2'], num_format)
                        sheet.write(row, col + 11, rec['diff3'], num_format)
                        sheet.write(row, col + 12, rec['diff4'], num_format)
                        sheet.write(row, col + 13, rec['diff5'], num_format)
                        sheet.write(row, col + 14, ' ', txt_name)
                sheet.merge_range(row + 1, col, row + 1, col + 7, 'Total',
                                  filter_head)
                sheet.write(row + 1, col + 8,
                            data['grand_total']['diff0_sum'],
                            total_num_format)
                sheet.write(row + 1, col + 9,
                            data['grand_total']['diff1_sum'],
                            total_num_format)
                sheet.write(row + 1, col + 10,
                            data['grand_total']['diff2_sum'],
                            total_num_format)
                sheet.write(row + 1, col + 11,
                            data['grand_total']['diff3_sum'],
                            total_num_format)
                sheet.write(row + 1, col + 12,
                            data['grand_total']['diff4_sum'],
                            total_num_format)
                sheet.write(row + 1, col + 13,
                            data['grand_total']['diff5_sum'],
                            total_num_format)
                sheet.write(row + 1, col + 14,
                            data['grand_total']['total_debit'],
                            total_num_format)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()