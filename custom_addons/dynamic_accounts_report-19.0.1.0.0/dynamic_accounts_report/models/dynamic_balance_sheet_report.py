# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Swetha Anand (odoo@cybrosys.com)
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
import datetime
import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.date_utils import get_month, get_fiscal_year, get_quarter, \
    subtract


class ProfitLossReport(models.TransientModel):
    """For creating Profit and Loss and Balance sheet report."""
    _name = 'dynamic.balance.sheet.report'
    _description = 'Profit Loss Report'

    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company,
                                 help='Select the company to which this'
                                      'record belongs.')
    journal_ids = fields.Many2many('account.journal',
                                   string='Journals', required=True,
                                   default=[],
                                   help='Select one or more journals.')
    account_ids = fields.Many2many("account.account", string="Accounts",
                                   help='Select one or more accounts.')
    analytic_ids = fields.Many2many(
        "account.analytic.account", string="Analytic Accounts",
        help="Analytic accounts associated with the current record.")
    target_move = fields.Selection([('posted', 'Posted'), ('draft', 'Draft')],
                                   string='Target Move', required=True,
                                   default='posted',
                                   help='Select the target move status.')
    date_from = fields.Date(string="Start date",
                            help="Specify the start date.")
    date_to = fields.Date(string="End date", help="Specify the end date.")

    @api.model_create_multi
    def create(self, vals):
        """Create one or more records of ProfitLossReport.
        :param vals: A dictionary or a list of dictionaries containing the field values for the records to be created.
        :return: A recordset of the created ProfitLossReport records."""
        return super(ProfitLossReport, self).create({})

    @api.model
    def view_report(self, option, comparison, comparison_type):
        datas = []
        account_types = {
            'income': 'income',
            'income_other': 'income_other',
            'expense': 'expense',
            'expense_depreciation': 'expense_depreciation',
            'expense_direct_cost': 'expense_direct_cost',
            'asset_receivable': 'asset_receivable',
            'asset_cash': 'asset_cash',
            'asset_current': 'asset_current',
            'asset_non_current': 'asset_non_current',
            'asset_prepayments': 'asset_prepayments',
            'asset_fixed': 'asset_fixed',
            'liability_payable': 'liability_payable',
            'liability_credit_card': 'liability_credit_card',
            'liability_current': 'liability_current',
            'liability_non_current': 'liability_non_current',
            'equity': 'equity',
            'equity_unaffected': 'equity_unaffected',
        }
        financial_report_id = self.browse(option)
        current_year = fields.Date.today().year
        current_date = fields.Date.today()
        if financial_report_id.target_move == 'draft':
            target_move = ['posted', 'draft']
        else:
            target_move = ['posted']
        if comparison:
            for count in range(0, int(comparison) + 1):
                if comparison_type == "month":
                    account_move_lines = self.env['account.move.line'].search(
                        [(
                            'parent_state', 'in', target_move),
                            ('date', '>=', (current_date - datetime.timedelta(
                                days=30 * count)).strftime('%Y-%m-01')),
                            ('date', '<=', (current_date - datetime.timedelta(
                                days=30 * count)).strftime('%Y-%m-12'))])
                elif comparison_type == "year":
                    account_move_lines = self.env['account.move.line'].search(
                        [(
                            'parent_state', 'in', target_move),
                            ('date', '>=', f'{current_year - count}-01-01'),
                            ('date', '<=', f'{current_year - count}-12-31')])
                lists = [{'id': rec.id, 'value': [eval(i) for i in
                                                  rec.analytic_distribution.keys()]}
                         for rec in account_move_lines if
                         rec.analytic_distribution]
                if financial_report_id.analytic_ids:
                    account_move_lines = account_move_lines.filtered(lambda
                                                                         rec: rec.id in [
                        lst['id'] for lst in lists if lst['value'] and any(
                            i in financial_report_id.analytic_ids.mapped('id')
                            for i in lst['value'])])
                account_move_lines = account_move_lines.filtered(lambda
                                                                     a: not financial_report_id.journal_ids or a.journal_id in financial_report_id.journal_ids)
                account_move_lines = account_move_lines.filtered(lambda
                                                                     a: not financial_report_id.account_ids or a.account_id in financial_report_id.account_ids)
                account_move_lines = account_move_lines.filtered(lambda
                                                                     a: not financial_report_id.date_from or a.date >= financial_report_id.date_from)
                account_move_lines = account_move_lines.filtered(lambda
                                                                     a: not financial_report_id.date_to or a.date <= financial_report_id.date_to)
                account_entries = {}
                for account_type in account_types.values():
                    account_entries[account_type] = self._get_entries(
                        account_move_lines, self.env['account.account'].search(
                            [('account_type', '=', account_type)]),
                        account_type)
                total_income = sum(
                    float(entry['amount'].replace(',', '')) for account_type
                    in
                    ['income', 'income_other'] for entry in
                    account_entries[account_type][0]) - sum(
                    float(entry['amount'].replace(',', '')) for entry in
                    account_entries['expense_direct_cost'][0])
                total_expense = sum(
                    float(entry['amount'].replace(',', '')) for account_type
                    in
                    ['expense', 'expense_depreciation'] for entry in
                    account_entries[account_type][0])
                total_current_asset = sum(
                    float(entry['amount'].replace(',', '')) for account_type
                    in
                    ['asset_receivable', 'asset_current', 'asset_cash',
                     'asset_prepayments'] for entry in
                    account_entries[account_type][0])
                total_assets = total_current_asset + sum(
                    float(entry['amount'].replace(',', '')) for account_type
                    in
                    ['asset_fixed', 'asset_non_current'] for entry in
                    account_entries[account_type][0])
                total_current_liability = sum(
                    float(entry['amount'].replace(',', '')) for account_type
                    in
                    ['liability_current', 'liability_payable'] for entry in
                    account_entries[account_type][0])
                total_liability = total_current_liability + sum(
                    float(entry['amount'].replace(',', '')) for account_type
                    in
                    ['liability_non_current'] for entry in
                    account_entries[account_type][0])
                total_unallocated_earning = (
                                                    total_income - total_expense) + sum(
                    float(entry['amount'].replace(',', '')) for account_type
                    in
                    ['equity_unaffected'] for entry in
                    account_entries[account_type][0])
                total_equity = total_unallocated_earning + sum(
                    float(entry['amount'].replace(',', '')) for account_type
                    in
                    ['equity'] for entry in
                    account_entries[account_type][0])
                total = total_liability + total_equity
                data = {
                    'total': total_income - total_expense,
                    'total_expense': "{:,.2f}".format(total_expense),
                    'total_income': "{:,.2f}".format(total_income),
                    'total_current_asset': "{:,.2f}".format(
                        total_current_asset),
                    'total_assets': "{:,.2f}".format(total_assets),
                    'total_current_liability': "{:,.2f}".format(
                        total_current_liability),
                    'total_liability': "{:,.2f}".format(total_liability),
                    'total_earnings': "{:,.2f}".format(
                        total_income - total_expense),
                    'total_unallocated_earning': "{:,.2f}".format(
                        total_unallocated_earning),
                    'total_equity': "{:,.2f}".format(total_equity),
                    'total_balance': "{:,.2f}".format(total),
                    **account_entries}
                datas.append(data)
        else:
            current_year = fields.Date.today().year
            date_from = financial_report_id.date_from or f'{current_year}-01-01'
            date_to = financial_report_id.date_to or f'{current_year}-12-31'
            account_move_lines = self.env['account.move.line'].search(
                [('parent_state', 'in', target_move),
                 ('date', '>=', date_from),
                 ('date', '<=', date_to)])
            lists = [{'id': rec.id,
                      'value': [eval(i) for i in
                                rec.analytic_distribution.keys()]}
                     for rec in account_move_lines if
                     rec.analytic_distribution]
            if financial_report_id.analytic_ids:
                account_move_lines = account_move_lines.filtered(
                    lambda rec: rec.id in [lst['id'] for lst in lists if
                                           lst['value'] and any(
                                               i in financial_report_id.analytic_ids.mapped(
                                                   'id') for i in
                                               lst['value'])])
            account_move_lines = account_move_lines.filtered(lambda
                                                                 a: not financial_report_id.journal_ids or a.journal_id in financial_report_id.journal_ids)
            account_move_lines = account_move_lines.filtered(lambda
                                                                 a: not financial_report_id.account_ids or a.account_id in financial_report_id.account_ids)
            account_move_lines = account_move_lines.filtered(lambda
                                                                 a: not financial_report_id.date_from or a.date >= financial_report_id.date_from)
            account_move_lines = account_move_lines.filtered(lambda
                                                                 a: not financial_report_id.date_to or a.date <= financial_report_id.date_to)
            account_entries = {}
            for account_type in account_types.values():
                account_entries[account_type] = self._get_entries(
                    account_move_lines, self.env['account.account'].search(
                        [('account_type', '=', account_type)]), account_type)
            total_income = sum(
                float(entry['amount'].replace(',', '')) for account_type in
                ['income', 'income_other'] for entry in
                account_entries[account_type][0]) - sum(
                float(entry['amount'].replace(',', '')) for entry in
                account_entries['expense_direct_cost'][0])
            total_expense = sum(
                float(entry['amount'].replace(',', '')) for account_type in
                ['expense', 'expense_depreciation'] for entry in
                account_entries[account_type][0])
            total_current_asset = sum(
                float(entry['amount'].replace(',', '')) for account_type in
                ['asset_receivable', 'asset_current', 'asset_cash',
                 'asset_prepayments'] for entry in
                account_entries[account_type][0])
            total_assets = total_current_asset + sum(
                float(entry['amount'].replace(',', '')) for account_type in
                ['asset_fixed', 'asset_non_current'] for entry in
                account_entries[account_type][0])
            total_current_liability = sum(
                float(entry['amount'].replace(',', '')) for account_type in
                ['liability_current', 'liability_payable'] for entry in
                account_entries[account_type][0])
            total_liability = total_current_liability + sum(
                float(entry['amount'].replace(',', '')) for account_type in
                ['liability_non_current'] for entry in
                account_entries[account_type][0])
            total_unallocated_earning = (total_income - total_expense) + sum(
                float(entry['amount'].replace(',', '')) for account_type in
                ['equity_unaffected'] for entry in
                account_entries[account_type][0])
            total_equity = total_unallocated_earning + sum(
                float(entry['amount'].replace(',', '')) for account_type in
                ['equity'] for entry in account_entries[account_type][0])
            total = total_liability + total_equity
            data = {
                'total': total_income - total_expense,
                'total_expense': "{:,.2f}".format(total_expense),
                'total_income': "{:,.2f}".format(total_income),
                'total_current_asset': "{:,.2f}".format(total_current_asset),
                'total_assets': "{:,.2f}".format(total_assets),
                'total_current_liability': "{:,.2f}".format(
                    total_current_liability),
                'total_liability': "{:,.2f}".format(total_liability),
                'total_earnings': "{:,.2f}".format(
                    total_income - total_expense),
                'total_unallocated_earning': "{:,.2f}".format(
                    total_unallocated_earning),
                'total_equity': "{:,.2f}".format(total_equity),
                'total_balance': "{:,.2f}".format(total),
                **account_entries}
            datas.append(data)
        filters = self._get_filter_data()
        return data, filters, datas

    def _get_entries(self, account_move_lines, account_ids, account_type):
        """
            Get the entries for the specified account type.
            :param account_move_lines: The account move lines to filter.
            :param account_ids: The account IDs to filter.
            :param account_type: The account type.
            :return: A tuple containing the entries and the total amount.
            """
        entries = []
        total = 0
        for account in account_ids:
            filtered_lines = account_move_lines.filtered(
                lambda line: line.account_id == account)
            if filtered_lines:
                if account_type in ['income', 'income_other',
                                    'liability_payable', 'liability_current',
                                    'liability_non_current', 'equity',
                                    'equity_unaffected']:
                    amount = -(sum(filtered_lines.mapped('debit')) - sum(
                        filtered_lines.mapped('credit')))
                else:
                    amount = sum(filtered_lines.mapped('debit')) - sum(
                        filtered_lines.mapped('credit'))
                entries.append({
                    'name': "{} - {}".format(account.code, account.name),
                    'amount': "{:,.2f}".format(amount),
                })
                total += amount
            else:
                entries.append({
                    'name': "{} - {}".format(account.code, account.name),
                    'amount': "{:,.2f}".format(0),
                })
        return entries, "{:,.2f}".format(total)

    def filter(self, vals):
        """
            Update the filter criteria based on the provided values.
            :param vals: A dictionary containing the filter values to update.
            :return: The updated record.
            """
        filter = []
        today = fields.Date.today()
        if vals == 'month':
            vals = {
                'date_from': get_month(today)[0].strftime("%Y-%m-%d"),
                'date_to': get_month(today)[1].strftime("%Y-%m-%d"),
            }
        elif vals == 'quarter':
            vals = {
                'date_from': get_quarter(today)[0].strftime("%Y-%m-%d"),
                'date_to': get_quarter(today)[1].strftime("%Y-%m-%d"),
            }
        elif vals == 'year':
            vals = {
                'date_from': get_fiscal_year(today)[0].strftime("%Y-%m-%d"),
                'date_to': get_fiscal_year(today)[1].strftime("%Y-%m-%d"),
            }
        elif vals == 'last-month':
            last_month_date = subtract(today, months=1)
            vals = {
                'date_from': get_month(last_month_date)[0].strftime(
                    "%Y-%m-%d"),
                'date_to': get_month(last_month_date)[1].strftime("%Y-%m-%d"),
            }
        elif vals == 'last-quarter':
            last_quarter_date = subtract(today, months=3)
            vals = {
                'date_from': get_quarter(last_quarter_date)[0].strftime(
                    "%Y-%m-%d"),
                'date_to': get_quarter(last_quarter_date)[1].strftime(
                    "%Y-%m-%d"),
            }
        elif vals == 'last-year':
            last_year_date = subtract(today, years=1)
            vals = {
                'date_from': get_fiscal_year(last_year_date)[0].strftime(
                    "%Y-%m-%d"),
                'date_to': get_fiscal_year(last_year_date)[1].strftime(
                    "%Y-%m-%d"),
            }
        if 'date_from' in vals:
            self.write({'date_from': vals['date_from']})
        if 'date_to' in vals:
            self.write({'date_to': vals['date_to']})
        if 'journal_ids' in vals:
            if int(vals['journal_ids']) in self.journal_ids.mapped('id'):
                self.update({'journal_ids': [(3, int(vals['journal_ids']))]})
            else:
                self.write({'journal_ids': [(4, int(vals['journal_ids']))]})
            filter.append({'journal_ids': self.journal_ids.mapped('code')})
        if 'account_ids' in vals:
            if int(vals['account_ids']) in self.account_ids.mapped('id'):
                self.update(
                    {'account_ids': [(3, int(vals['account_ids']))]})
            else:
                self.write({'account_ids': [(4, int(vals['account_ids']))]})
            filter.append({'account_ids': self.account_ids.mapped('name')})
        if 'analytic_ids' in vals:
            if int(vals['analytic_ids']) in self.analytic_ids.mapped('id'):
                self.update(
                    {'analytic_ids': [(3, int(vals['analytic_ids']))]})
            else:
                self.write({'analytic_ids': [(4, int(vals['analytic_ids']))]})
            filter.append({'analytic_ids': self.analytic_ids.mapped('name')})
        if 'target' in vals:
            self.write({'target_move': vals['target']})
            filter.append({'target_move': self.target_move})
        return filter

    def _get_filter_data(self):
        """
            Retrieve the filter data for journals and accounts.

            :return: A dictionary containing the filter data.
            """
        journal_ids = self.env['account.journal'].search([])
        journal = [{'id': journal.id, 'name': journal.name} for journal in
                   journal_ids]

        account_ids = self.env['account.account'].search([])
        account = [{'id': account.id, 'name': account.name} for account in
                   account_ids]

        analytic_ids = self.env['account.analytic.account'].search([])
        analytic = [{'id': analytic.id, 'name': analytic.name} for analytic in
                    analytic_ids]

        filter = {
            'journal': journal,
            'account': account,
            'analytic': analytic
        }
        return filter

    @api.model
    def comparison_filter(self, options, count):
        today = fields.Date.today()
        if not count:
            raise ValidationError(_("Please select the count."))
        last_month_date_list = []
        for i in range(1, int(count) + 1):
            last_month_date = subtract(today, months=i)
            vals = {
                'date_from': get_month(last_month_date)[0].strftime(
                    "%Y-%m-%d"),
                'date_to': get_month(last_month_date)[1].strftime("%Y-%m-%d"),
            }
            last_month_date_list.append(vals)
        return last_month_date_list

    @api.model
    def comparison_filter_year(self, options, count):
        today = fields.Date.today()
        if not count:
            raise ValidationError(_("Please select the count."))
        last_year_date_list = []
        for i in range(1, int(count) + 1):
            last_year_date = subtract(today, years=i)
            vals = {
                'date_from': get_fiscal_year(last_year_date)[0].strftime(
                    "%Y-%m-%d"),
                'date_to': get_fiscal_year(last_year_date)[1].strftime(
                    "%Y-%m-%d"),
            }
            last_year_date_list.append(vals)
        return last_year_date_list

    @api.model
    def get_xlsx_report(self, data, response, report_name, report_action):
        """Generate and return an XLSX report based on the provided data.
            :param data: The report data in JSON format.
            :param report_name: Name of the report.
            :param response: The response object to write the generated report to.
            """
        data = json.loads(data)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        sub_heading = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px',
             'border': 1,
             'border_color': 'black'})
        side_heading_sub = workbook.add_format(
            {'align': 'left', 'bold': True, 'font_size': '10px',
             'border': 1,
             'border_color': 'black'})
        side_heading_sub.set_indent(1)
        # Filter formats
        filter_heading = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '9px', 'border': 1,
             'bg_color': '#D3D3D3'})
        filter_text = workbook.add_format(
            {'align': 'left', 'font_size': '9px', 'border': 1})
        txt_name = workbook.add_format({'font_size': '10px', 'border': 1})
        txt_name_left = workbook.add_format(
            {'align': 'left', 'font_size': '10px', 'border': 1})
        txt_name.set_indent(2)
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 15)
        col = 0
        sheet.write('A3:b4', report_name, sub_heading)
        sheet.write(5, col, '', sub_heading)
        for date in data['year']:
            sheet.write(4, col + 1, date, sub_heading)
            sheet.write(5, col + 1, 'Balance', sub_heading)
            col += 1
        col = 0
        current_row = 0

        # Report Title
        sheet.merge_range(current_row, 0, current_row, 5, report_name, sub_heading)
        current_row += 1
        if data:
            if report_action == 'dynamic_accounts_report.action_dynamic_profit_and_loss':

                # --- FILTERS TABLE BELOW REPORT NAME ---
                # Filter table headers
                sheet.write(current_row, 0, 'Date Range', filter_heading)
                sheet.write(current_row, 1, 'Comparison', filter_heading)
                sheet.write(current_row, 2, 'Account', filter_heading)
                sheet.write(current_row, 3, 'Journal', filter_heading)
                sheet.write(current_row, 4, 'Analytic Account', filter_heading)
                sheet.write(current_row, 5, 'Target move', filter_heading)
                current_row += 1

                # Filter values
                # Date Range
                date_range = ''
                if data.get('date_from') and data.get('date_to'):
                    date_range = f"{data.get('date_from')} – {data.get('date_to')}"
                elif data.get('date_range'):
                    date_range = data.get('date_range')
                else:
                    date_range = 'All'
                sheet.write(current_row, 0, date_range, filter_text)

                # Comparison
                comparison = data.get('comparison', '-') if data.get('comparison') else '-'
                sheet.write(current_row, 1, comparison, filter_text)

                # Account
                account_ids = data.get('account_ids')
                account_text = ', '.join(map(str, account_ids)) if account_ids else 'All'
                sheet.write(current_row, 2, account_text,filter_text)

                # Journal
                journal_ids = data.get('journal_ids')
                journal_text = ', '.join(map(str, journal_ids)) if journal_ids else 'All'
                sheet.write(current_row, 3, journal_text,filter_text)

                # Analytic Account
                analytic_ids = data.get('analytic_ids')
                analytic_text = ', '.join(map(str, analytic_ids)) if analytic_ids else 'All'
                sheet.write(current_row, 4, analytic_text,filter_text)

                # Target move
                target_text = data.get('target', 'All') if data.get('target') else 'All'
                sheet.write(current_row, 5, target_text, filter_text)

                current_row += 2  # Leave a blank row

                # --- REPORT TITLE ---

                sheet.write(current_row, col, 'Net Profit', sub_heading)
                for datas in data['datas']:
                    sheet.write(current_row, col + 1, datas['total'], side_heading_sub)
                    current_row += 1
                    col += 1
                col = 0
                sheet.write(current_row, col, 'Income', side_heading_sub)
                sheet.write(current_row, col + 1, ' ', side_heading_sub)
                current_row += 1
                sheet.write(current_row, col, 'Operating Income', txt_name_left)
                for datas in data['datas']:
                    sheet.write(current_row, col + 1, datas['income'][1], txt_name)
                    current_row += 1
                    col += 1
                row = current_row
                index = 0
                for datas in data['datas']:
                    if index == 0:
                        for accounts in datas['income'][0]:
                            account_name = accounts['name']
                            account_value = 0
                            for datas in data['datas']:
                                for account in datas['income'][0]:
                                    if account_name == account['name'] and \
                                            account['amount'] != '0.00':
                                        account_value = 1
                            if account_value == 1:
                                row += 1
                                col = 0
                                sheet.write(row, col, accounts['name'],
                                            txt_name)
                                for datas in data['datas']:
                                    for account in datas['income'][0]:
                                        if account_name == account['name']:
                                            sheet.write(row, col + 1,
                                                        account['amount'],
                                                        txt_name)
                                            col += 1
                    index += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Cost of Revenue', txt_name_left)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['expense_direct_cost'][1],
                                txt_name)
                    col += 1
                index = 0
                for datas in data['datas']:
                    if index == 0:
                        for accounts in datas['expense_direct_cost'][0]:
                            account_name = accounts['name']
                            account_value = 0
                            for datas in data['datas']:
                                for account in datas['expense_direct_cost'][0]:
                                    if account_name == account['name'] and \
                                            account['amount'] != '0.00':
                                        account_value = 1
                            if account_value == 1:
                                row += 1
                                col = 0
                                sheet.write(row, col, accounts['name'],
                                            txt_name)
                                for datas in data['datas']:
                                    for account in \
                                            datas['expense_direct_cost'][0]:
                                        if account_name == account['name']:
                                            sheet.write(row, col + 1,
                                                        account['amount'],
                                                        txt_name)
                                            col += 1
                    index += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Other Income', txt_name_left)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['income_other'][1],
                                txt_name)
                    col += 1
                index = 0
                for datas in data['datas']:
                    if index == 0:
                        for accounts in datas['income_other'][0]:
                            account_name = accounts['name']
                            account_value = 0
                            for datas in data['datas']:
                                for account in datas['income_other'][0]:
                                    if account_name == account['name'] and \
                                            account['amount'] != '0.00':
                                        account_value = 1
                            if account_value == 1:
                                row += 1
                                col = 0
                                sheet.write(row, col, accounts['name'],
                                            txt_name)
                                for datas in data['datas']:
                                    for account in datas['income_other'][0]:
                                        if account_name == account['name']:
                                            sheet.write(row, col + 1,
                                                        account['amount'],
                                                        txt_name)
                                            col += 1
                    index += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Total Income', side_heading_sub)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['total_income'],
                                side_heading_sub)
                    col += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Expense', side_heading_sub)
                sheet.write(row, col + 1, '', side_heading_sub)
                row += 1
                col = 0
                sheet.write(row, col, 'Expense', txt_name_left)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['expense'][1], txt_name)
                    col += 1
                index = 0
                for datas in data['datas']:
                    if index == 0:
                        for accounts in datas['expense'][0]:
                            account_name = accounts['name']
                            account_value = 0
                            for datas in data['datas']:
                                for account in datas['expense'][0]:
                                    if account_name == account['name'] and \
                                            account['amount'] != '0.00':
                                        account_value = 1
                            if account_value == 1:
                                row += 1
                                col = 0
                                sheet.write(row, col, accounts['name'],
                                            txt_name)
                                for datas in data['datas']:
                                    for account in datas['expense'][0]:
                                        if account_name == account['name']:
                                            sheet.write(row, col + 1,
                                                        account['amount'],
                                                        txt_name)
                                            col += 1
                    index += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Depreciation', txt_name_left)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['expense_depreciation'][1],
                                txt_name)
                    col += 1
                index = 0
                for datas in data['datas']:
                    if index == 0:
                        for accounts in datas['expense_depreciation'][0]:
                            account_name = accounts['name']
                            account_value = 0
                            for datas in data['datas']:
                                for account in datas['expense_depreciation'][
                                    0]:
                                    if account_name == account['name'] and \
                                            account['amount'] != '0.00':
                                        account_value = 1
                            if account_value == 1:
                                row += 1
                                col = 0
                                sheet.write(row, col, accounts['name'],
                                            txt_name)
                                for datas in data['datas']:
                                    for account in \
                                            datas['expense_depreciation'][
                                                0]:
                                        if account_name == account['name']:
                                            sheet.write(row, col + 1,
                                                        account['amount'],
                                                        txt_name)
                                            col += 1
                    index += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Total Expenses', side_heading_sub)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['total_expense'],
                                side_heading_sub)
                    col += 1
            else:
                sheet.write(6, col, 'ASSETS', sub_heading)
                sheet.write(6, col + 1, ' ', side_heading_sub)
                sheet.write(7, col, 'Current Assets', side_heading_sub)
                sheet.write(7, col + 1, ' ', side_heading_sub)
                sheet.write(8, col, 'Bank and Cash Accounts', txt_name_left)
                for datas in data['datas']:
                    sheet.write(8, col + 1, datas['asset_cash'][1], txt_name)
                    col += 1
                row = 8
                index = 0
                for datas in data['datas']:
                    if index == 0:
                        for accounts in datas['asset_cash'][0]:
                            account_name = accounts['name']
                            account_value = 0
                            for datas in data['datas']:
                                for account in datas['asset_cash'][0]:
                                    if account_name == account['name'] and \
                                            account['amount'] != '0.00':
                                        account_value = 1
                            if account_value == 1:
                                row += 1
                                col = 0
                                sheet.write(row, col, accounts['name'],
                                            txt_name)
                                for datas in data['datas']:
                                    for account in datas['asset_cash'][0]:
                                        if account_name == account['name']:
                                            sheet.write(row, col + 1,
                                                        account['amount'],
                                                        txt_name)
                                            col += 1
                    index += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Receivables', txt_name_left)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['asset_receivable'][1],
                                txt_name)
                    col += 1
                index = 0
                for datas in data['datas']:
                    if index == 0:
                        for accounts in datas['asset_receivable'][0]:
                            account_name = accounts['name']
                            account_value = 0
                            for datas in data['datas']:
                                for account in datas['asset_receivable'][0]:
                                    if account_name == account['name'] and \
                                            account['amount'] != '0.00':
                                        account_value = 1
                            if account_value == 1:
                                row += 1
                                col = 0
                                sheet.write(row, col, accounts['name'],
                                            txt_name)
                                for datas in data['datas']:
                                    for account in datas['asset_receivable'][
                                        0]:
                                        if account_name == account['name']:
                                            sheet.write(row, col + 1,
                                                        account['amount'],
                                                        txt_name)
                                            col += 1
                    index += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Current Assets', txt_name_left)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['asset_current'][1],
                                txt_name)
                    col += 1
                index = 0
                for datas in data['datas']:
                    if index == 0:
                        for accounts in datas['asset_current'][0]:
                            account_name = accounts['name']
                            account_value = 0
                            for datas in data['datas']:
                                for account in datas['asset_current'][0]:
                                    if account_name == account['name'] and \
                                            account['amount'] != '0.00':
                                        account_value = 1
                            if account_value == 1:
                                row += 1
                                col = 0
                                sheet.write(row, col, accounts['name'],
                                            txt_name)
                                for datas in data['datas']:
                                    for account in datas['asset_current'][0]:
                                        if account_name == account['name']:
                                            sheet.write(row, col + 1,
                                                        account['amount'],
                                                        txt_name)
                                            col += 1
                    index += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Prepayments', txt_name_left)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['asset_prepayments'][1],
                                txt_name)
                    col += 1
                index = 0
                for datas in data['datas']:
                    if index == 0:
                        for accounts in datas['asset_prepayments'][0]:
                            account_name = accounts['name']
                            account_value = 0
                            for datas in data['datas']:
                                for account in datas['asset_prepayments'][0]:
                                    if account_name == account['name'] and \
                                            account['amount'] != '0.00':
                                        account_value = 1
                            if account_value == 1:
                                row += 1
                                col = 0
                                sheet.write(row, col, accounts['name'],
                                            txt_name)
                                for datas in data['datas']:
                                    for account in datas['asset_prepayments'][
                                        0]:
                                        if account_name == account['name']:
                                            sheet.write(row, col + 1,
                                                        account['amount'],
                                                        txt_name)
                                            col += 1
                    index += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Total Current Assets', side_heading_sub)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['total_current_asset'],
                                side_heading_sub)
                    col += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Plus Fixed Assets', txt_name_left)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['asset_fixed'][1],
                                txt_name)
                    col += 1
                index = 0
                for datas in data['datas']:
                    if index == 0:
                        for accounts in datas['asset_fixed'][0]:
                            account_name = accounts['name']
                            account_value = 0
                            for datas in data['datas']:
                                for account in datas['asset_fixed'][0]:
                                    if account_name == account['name'] and \
                                            account['amount'] != '0.00':
                                        account_value = 1
                            if account_value == 1:
                                row += 1
                                col = 0
                                sheet.write(row, col, accounts['name'],
                                            txt_name)
                                for datas in data['datas']:
                                    for account in datas['asset_fixed'][
                                        0]:
                                        if account_name == account['name']:
                                            sheet.write(row, col + 1,
                                                        account['amount'],
                                                        txt_name)
                                            col += 1
                    index += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Plus Non-current Assets', txt_name_left)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['asset_non_current'][1],
                                txt_name)
                    col += 1
                index = 0
                for datas in data['datas']:
                    if index == 0:
                        for accounts in datas['asset_non_current'][0]:
                            account_name = accounts['name']
                            account_value = 0
                            for datas in data['datas']:
                                for account in datas['asset_non_current'][0]:
                                    if account_name == account['name'] and \
                                            account['amount'] != '0.00':
                                        account_value = 1
                            if account_value == 1:
                                row += 1
                                col = 0
                                sheet.write(row, col, accounts['name'],
                                            txt_name)
                                for datas in data['datas']:
                                    for account in datas['asset_non_current'][
                                        0]:
                                        if account_name == account['name']:
                                            sheet.write(row, col + 1,
                                                        account['amount'],
                                                        txt_name)
                                            col += 1
                    index += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Total Assets', side_heading_sub)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['total_assets'],
                                side_heading_sub)
                    col += 1
                col = 0
                row += 1
                sheet.write(row, col, 'LIABILITIES', sub_heading)
                sheet.write(row, col + 1, '', sub_heading)
                row += 1
                sheet.write(row, col, 'Current Liabilities', side_heading_sub)
                sheet.write(row, col + 1, ' ', side_heading_sub)
                row += 1
                sheet.write(row, col, 'Current Liabilities', txt_name_left)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['liability_current'][1],
                                txt_name)
                    col += 1
                index = 0
                for datas in data['datas']:
                    if index == 0:
                        for accounts in datas['liability_current'][0]:
                            account_name = accounts['name']
                            account_value = 0
                            for datas in data['datas']:
                                for account in datas['liability_current'][0]:
                                    if account_name == account['name'] and \
                                            account['amount'] != '0.00':
                                        account_value = 1
                            if account_value == 1:
                                row += 1
                                col = 0
                                sheet.write(row, col, accounts['name'],
                                            txt_name)
                                for datas in data['datas']:
                                    for account in datas['liability_current'][
                                        0]:
                                        if account_name == account['name']:
                                            sheet.write(row, col + 1,
                                                        account['amount'],
                                                        txt_name)
                                            col += 1
                    index += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Payables', txt_name_left)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['liability_payable'][1],
                                txt_name)
                    col += 1
                index = 0
                for datas in data['datas']:
                    if index == 0:
                        for accounts in datas['liability_payable'][0]:
                            account_name = accounts['name']
                            account_value = 0
                            for datas in data['datas']:
                                for account in datas['liability_payable'][0]:
                                    if account_name == account['name'] and \
                                            account['amount'] != '0.00':
                                        account_value = 1
                            if account_value == 1:
                                row += 1
                                col = 0
                                sheet.write(row, col, accounts['name'],
                                            txt_name)
                                for datas in data['datas']:
                                    for account in datas['liability_payable'][
                                        0]:
                                        if account_name == account['name']:
                                            sheet.write(row, col + 1,
                                                        account['amount'],
                                                        txt_name)
                                            col += 1
                    index += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Total Current Liabilities',
                            side_heading_sub)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['total_current_liability'],
                                side_heading_sub)
                    col += 1
                col = 0
                row += 1
                sheet.write(row, col, 'Plus Non-current Liabilities',
                            txt_name_left)
                for datas in data['datas']:
                    sheet.write(row, col + 1,
                                datas['liability_non_current'][1],
                                txt_name)
                    col += 1
                index = 0
                for datas in data['datas']:
                    if index == 0:
                        for accounts in datas['liability_non_current'][0]:
                            account_name = accounts['name']
                            account_value = 0
                            for datas in data['datas']:
                                for account in datas['liability_non_current'][
                                    0]:
                                    if account_name == account['name'] and \
                                            account['amount'] != '0.00':
                                        account_value = 1
                            if account_value == 1:
                                row += 1
                                col = 0
                                sheet.write(row, col, accounts['name'],
                                            txt_name)
                                for datas in data['datas']:
                                    for account in \
                                            datas['liability_non_current'][
                                                0]:
                                        if account_name == account['name']:
                                            sheet.write(row, col + 1,
                                                        account['amount'],
                                                        txt_name)
                                            col += 1
                    index += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Total Liabilities',
                            side_heading_sub)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['total_liability'],
                                side_heading_sub)
                    col += 1
                col = 0
                row += 1
                sheet.write(row, col, 'EQUITY', sub_heading)
                sheet.write(row, col + 1, '', sub_heading)
                row += 1
                sheet.write(row, col, 'Unallocated Earnings', side_heading_sub)
                sheet.write(row, col + 1, ' ', side_heading_sub)
                row += 1
                sheet.write(row, col, 'Current Earnings', txt_name)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['total_earnings'],
                                txt_name)
                    col += 1
                col = 0
                row += 1
                sheet.write(row, col, 'Current Allocated Earnings',
                            txt_name_left)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['equity_unaffected'][1],
                                txt_name)
                    col += 1
                index = 0
                for datas in data['datas']:
                    if index == 0:
                        for accounts in datas['equity_unaffected'][0]:
                            account_name = accounts['name']
                            account_value = 0
                            for datas in data['datas']:
                                for account in datas['equity_unaffected'][
                                    0]:
                                    if account_name == account['name'] and \
                                            account['amount'] != '0.00':
                                        account_value = 1
                            if account_value == 1:
                                row += 1
                                col = 0
                                sheet.write(row, col, accounts['name'],
                                            txt_name)
                                for datas in data['datas']:
                                    for account in \
                                            datas['equity_unaffected'][
                                                0]:
                                        if account_name == account['name']:
                                            sheet.write(row, col + 1,
                                                        account['amount'],
                                                        txt_name)
                                            col += 1
                    index += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Total Unallocated Earnings',
                            side_heading_sub)
                for datas in data['datas']:
                    sheet.write(row, col + 1,
                                datas['total_unallocated_earning'],
                                side_heading_sub)
                    col += 1
                col = 0
                row += 1
                sheet.write(row, col, 'Retained Earnings', txt_name_left)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['equity'][1],
                                txt_name)
                    col += 1
                index = 0
                for datas in data['datas']:
                    if index == 0:
                        for accounts in datas['equity'][0]:
                            account_name = accounts['name']
                            account_value = 0
                            for datas in data['datas']:
                                for account in datas['equity'][
                                    0]:
                                    if account_name == account['name'] and \
                                            account['amount'] != '0.00':
                                        account_value = 1
                            if account_value == 1:
                                row += 1
                                col = 0
                                sheet.write(row, col, accounts['name'],
                                            txt_name)
                                for datas in data['datas']:
                                    for account in datas['equity'][0]:
                                        if account_name == account['name']:
                                            sheet.write(row, col + 1,
                                                        account['amount'],
                                                        txt_name)
                                            col += 1
                    index += 1
                row += 1
                col = 0
                sheet.write(row, col, 'Total EQUITY', side_heading_sub)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['total_equity'],
                                side_heading_sub)
                    col += 1
                col = 0
                row += 1
                sheet.write(row, col, 'LIABILITIES + EQUITY', side_heading_sub)
                for datas in data['datas']:
                    sheet.write(row, col + 1, datas['total_balance'],
                                side_heading_sub)
                    col += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
