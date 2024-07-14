# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io

from collections import defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_date, xlsxwriter

from odoo.addons.l10n_hk_hr_payroll.models.l10n_hk_ird import MONTH_SELECTION


class L10nHkManulifeMpf(models.Model):
    _name = 'l10n_hk.manulife.mpf'
    _description = 'Manulife MPF'
    _order = 'period'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != 'HK':
            raise UserError(_('You must be logged in a Hong Kong company to use this feature.'))
        if not self.env.company.l10n_hk_manulife_mpf_scheme:
            raise UserError(_('You must set a Manulife MPF Scheme Number in your company settings first.'))
        if not self.env.company.l10n_hk_employer_name:
            raise UserError(_('You must set an Employer Name in your company settings first.'))
        return super().default_get(field_list)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    manulife_mpf_scheme = fields.Char('Scheme Number', required=True, related='company_id.l10n_hk_manulife_mpf_scheme')
    year = fields.Integer(required=True, default=lambda self: fields.Date.today().year)
    month = fields.Selection(MONTH_SELECTION, required=True, default=lambda self: str(fields.Date.today().month))
    period = fields.Date('Period', compute='_compute_period', store=True)
    cheque_no = fields.Char('Cheque No.')
    second_cheque_no = fields.Char('Second Cheque No.')
    line_ids = fields.One2many('l10n_hk.manulife.mpf.line', 'sheet_id', string='Lines', compute='_compute_line_ids', store=True, readonly=False)
    sequence_no = fields.Char('Sequence No.', default='', copy=False)
    xlsx_attachment_id = fields.Many2one('ir.attachment', 'XLSX Attachment', readonly=True)
    xlsx_file = fields.Binary('XLSX File', related='xlsx_attachment_id.datas', readonly=True)
    xlsx_filename = fields.Char('XLSX Filename', compute="_compute_filename")

    @api.depends('year', 'month')
    def _compute_period(self):
        for record in self:
            record.period = date(record.year, int(record.month), 1)

    @api.depends('manulife_mpf_scheme', 'sequence_no', 'period')
    def _compute_filename(self):
        for record in self:
            period_str = format_date(self.env, record.period, date_format="YMMM", lang_code='en_US').upper()
            record.xlsx_filename = "PD%sMANULIFE%s%s.xlsx" % (record.manulife_mpf_scheme, record.sequence_no, period_str)

    @api.depends('period', 'company_id')
    def _compute_line_ids(self):
        for sheet in self:
            end_period = sheet.period + relativedelta(months=1, days=-1)
            all_payslips = self.env['hr.payslip'].search([
                ('state', 'in', ['done', 'paid']),
                ('company_id', '=', sheet.company_id.id),
                ('date_from', '>=', sheet.period),
                ('date_to', '<=', end_period),
            ])
            sheet.update({
                'line_ids': [(5, 0, 0)] + [
                    (0, 0, {'employee_id': employee.id}) for employee in all_payslips.employee_id
                ]
            })

    @api.depends('xlsx_filename')
    def _compute_display_name(self):
        for sheet in self:
            sheet.display_name = sheet.xlsx_filename

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('sequence_no'):
                vals['sequence_no'] = self.env['ir.sequence'].next_by_code('manulife.mpf')
        return super().create(vals_list)

    def _get_report_data(self):
        self.ensure_one()
        salary_structure = self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_employee_salary')
        end_period = self.period + relativedelta(months=1, days=-1)
        all_payslips = self.env['hr.payslip'].search([
            ('state', 'in', ['done', 'paid']),
            ('date_from', '>=', self.period),
            ('date_to', '<=', end_period),
            ('employee_id', 'in', self.line_ids.employee_id.ids),
            ('struct_id', '=', salary_structure.id),
        ])
        if not all_payslips:
            raise UserError(_('There are no confirmed payslips for this period.'))
        all_employees = all_payslips.employee_id

        employee_payslips = defaultdict(lambda: self.env['hr.payslip'])
        for payslip in all_payslips:
            employee_payslips[payslip.employee_id] |= payslip

        line_codes = ['MPF_GROSS', 'EEMC', 'ERMC', 'EEVC', 'ERVC']
        all_line_values = all_payslips._get_line_values(line_codes, vals_list=['total', 'quantity'])

        main_data = {
            'company_name': self.company_id.l10n_hk_employer_name,
            'sub_scheme_no': self.manulife_mpf_scheme[1:] + '-01',
            'cheque_no': self.cheque_no or '',
            'second_cheque_no': self.second_cheque_no or '',
        }
        employees_data = []
        for employee in employee_payslips:
            line = self.line_ids.filtered(lambda l: l.employee_id == employee)
            payslips = employee_payslips[employee]

            mapped_total = {
                code: sum(all_line_values[code][p.id]['total'] for p in payslips)
                for code in line_codes}

            employee_data = {
                'member_acount': line.employee_id.l10n_hk_mpf_manulife_account or '',
                'hkid': line.employee_id.identification_id or line.employee_id.passport_id or '',
                'surname': line.employee_id.l10n_hk_surname or '',
                'given_name': line.employee_id.l10n_hk_given_name or '',
                'period_start': self.period.strftime('%m/%d/%Y'),
                'period_end': (self.period + relativedelta(months=1, days=-1)).strftime('%m/%d/%Y'),
                'relevant_income': mapped_total['MPF_GROSS'],
                'amount_eemc': abs(mapped_total['EEMC']),
                'amount_ermc': abs(mapped_total['ERMC']),
                'amount_eevc': abs(mapped_total['EEVC']),
                'amount_ervc': abs(mapped_total['ERVC']),
                'surcharge_percentage': line.surcharge_percentage,
                'amount_surcharge': line.amount_surcharge,
                'basic_salary': employee.contract_id.wage,
                'last_date_of_employment': employee.contract_id.date_end.strftime('%m/%d/%Y') if employee.contract_id.date_end and employee.contract_id.date_end <= end_period else '',
            }
            if not employee_data['member_acount'] and employee_data['hkid']:
                employee_data['surname'] = ''
                employee_data['given_name'] = ' '.join([line.employee_id.l10n_hk_surname, line.employee_id.l10n_hk_given_name])
            employees_data.append(employee_data)

        total_data = {
            'total_amount_eemc': abs(sum(all_line_values['EEMC'][p.id]['total'] for p in all_payslips)),
            'total_amount_ermc': abs(sum(all_line_values['ERMC'][p.id]['total'] for p in all_payslips)),
            'total_amount_eevc': abs(sum(all_line_values['EEVC'][p.id]['total'] for p in all_payslips)),
            'total_amount_ervc': abs(sum(all_line_values['ERVC'][p.id]['total'] for p in all_payslips)),
            'total_amount_surcharge': sum(self.line_ids.mapped('amount_surcharge')),
            'total_basic_salary': sum(all_employees.contract_id.mapped('wage')),
        }
        return {'data': main_data, 'employees_data': employees_data, 'total_data': total_data}

    def action_generat_xlsx(self):
        self.ensure_one()

        employees = self.line_ids.mapped('employee_id')
        if not employees:
            raise UserError(_('No employees to generate the report for.'))

        file = io.BytesIO()
        workbook = xlsxwriter.Workbook(file, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        # Set up default formats and content
        default_field_format = workbook.add_format({'font_size': 8, 'font_name': 'Arial', 'bg_color': '#ccffcc', 'bold': True, 'text_wrap': True, 'border': 1})
        default_header_format = workbook.add_format({'font_size': 8, 'font_name': 'Arial', 'bg_color': '#ccffcc', 'bold': True, 'text_wrap': True, 'valign': 'top', 'border': 1})
        default_note_left_format = workbook.add_format({'font_size': 11, 'font_name': 'Calibri', 'bg_color': '#ccffcc', 'text_wrap': True, 'valign': 'top', 'border': 1, 'right': 0})
        default_note_right_format = workbook.add_format({'font_size': 11, 'font_name': 'Calibri', 'bg_color': '#ccffcc', 'text_wrap': True, 'valign': 'top', 'border': 1, 'left': 0})

        worksheet.set_row(0, 45)
        worksheet.set_row(1, 206)
        worksheet.set_row(2, 67)
        worksheet.set_column('A:A', 17)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 17)
        worksheet.set_column('D:D', 17)
        worksheet.set_column('E:E', 21)
        worksheet.set_column('F:F', 18)
        worksheet.set_column('G:G', 15)
        worksheet.set_column('H:H', 15)
        worksheet.set_column('I:I', 17)
        worksheet.set_column('J:J', 21)
        worksheet.set_column('K:K', 16)
        worksheet.set_column('L:L', 16)
        worksheet.set_column('M:M', 13)
        worksheet.set_column('N:N', 20)
        worksheet.set_column('O:O', 19)
        worksheet.write('A1', 'Employer (Company) Name\n僱主(公司)名稱', default_field_format)
        worksheet.write('C1', 'If pay by cheque, please input\nCheque No.(1)\n支票號碼(1)', default_field_format)
        worksheet.merge_range('E1:H2', 'NOTES :\n注意事項：\n1. Complete this worksheet in English \n    請以英文填寫本工作紙\n2. DO NOT modify the format and the pre-filled items in this file\n    請勿修改本檔案的格式及已預填之項目\n3. Input the Member Account number or Member HKID number\n    請提供成員帳戶號碼或成員身份証號碼\n4. If Member Account Number is provided, input the Member Surname\n    (e.g. CHAN) & Other Name (e.g. TAI MAN) into 2 separate columns\n    如提供成員帳戶號碼, 請分開輸入成員姓氏(如: CHAN)\n    及成員名稱(如: TAI MAN)\n5. If Member HKID Number is provided, input the full name \n    (e.g. CHAN TAI MAN) into the "Member Other Name" column\n   如提供成員身份証號碼, 請將成員姓名(如: CHAN TAI MAN) \n   輸入到「成員名稱」欄內', default_note_left_format)
        worksheet.merge_range('I1:O2', '\n\n6. If Relevant Income is zero, input "0" for both Member Mandatory Contribution and Employer Mandatory Contribution\n   如有關入息為零， 請於僱主及成員強制性供款欄內輸入"0"\n7. If the voluntary contribution is calculated based on Basic Salary, please input the relevant amount into "Basic Salary" column\n   如以基本薪金來計算自願性供款金額，請將有關金額輸入到「基本薪金」欄內\n8. If there is no voluntary contribution or surcharge amount, leaves the relevant fields blank\n   如沒有自願性供款或供款附加費, 則母須填寫有關資料\n9. DO NOT PRINT AND SEND THE HARDCOPY OF THIS FILE TO MANULIFE\n   請勿列印及提交此結算書的編印版本予宏利\n10. The last day of employment for which employee termination without involving LSP/SP and employee termination reason is “Termination \n       of Employment”. For the termination with LSP/SP or termination reason other than “Termination of Employment”, please submit a duly signed\n       (with company chop) "Notice of Employee Termination" .        最後受僱日期只適用於不涉及長期服務金/遣散費，以及終止受僱理由為「終止受僱」的強積金僱員離職之用。就涉及長期服務金    費或終止受僱理由為「終止受僱」以外的強積金僱員離職申報，請提交妥為簽署（附公司印章）的「僱員終止受僱通知書」。', default_note_right_format)
        worksheet.write('A2', 'Sub-Scheme Number\n附屬計劃編號', default_field_format)
        worksheet.write('C2', 'Cheque No.(2)\n支票號碼(2)', default_field_format)
        worksheet.write('A3', 'Member Account Number\n成員帳戶號碼', default_header_format)
        worksheet.write('B3', 'Member HKID Number\n成員身份證號碼', default_header_format)
        worksheet.write('C3', 'Member Surname\n成員姓氏', default_header_format)
        worksheet.write('D3', 'Member Other Name\n成員名稱', default_header_format)
        worksheet.write('E3', 'Payroll Period Start Date\n支薪期開始日\n(mm/dd/yyyy)', default_header_format)
        worksheet.write('F3', 'Payroll Period End Date\n支薪期終結日\n(mm/dd/yyyy)', default_header_format)
        worksheet.write('G3', 'Relevant Income\n有關入息', default_header_format)
        worksheet.write('H3', 'Member Mandatory Contribution\n成員強制性供款', default_header_format)
        worksheet.write('I3', 'Employer Mandatory Contribution\n僱主強制性供款', default_header_format)
        worksheet.write('J3', 'Member Voluntary Contribution\n(if applicable)\n成員自願性供款\n(如適用)', default_header_format)
        worksheet.write('K3', 'Employer Voluntary Contribution\n(if applicable)\n僱主自願性供款\n(如適用)', default_header_format)
        worksheet.write('L3', 'Surcharge %\n(if applicable)\n供款附加費百分比\n(如適用)', default_header_format)
        worksheet.write('M3', 'Surcharge Amount\n(if applicable)\n供款附加費數目\n(如適用)', default_header_format)
        worksheet.write('N3', 'Basic Salary (if applicable)\n基本薪金 (如適用)', default_header_format)
        worksheet.write('O3', 'Last Date of Employment (if applicable)\n最後受僱日期\n(mm/dd/yyyy)', default_header_format)

        # Write data
        default_format = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'border': 1, 'text_wrap': True})
        defailt_bold_format = workbook.add_format({'font_name': 'Arial', 'font_size': 8, 'border': 1, 'text_wrap': True, 'bold': True, 'align': 'right'})
        default_date_format = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'border': 1, 'text_wrap': True, 'num_format': 'mm/dd/yyyy'})
        default_money_format = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'border': 1, 'text_wrap': True, 'num_format': '#,##0.00'})
        default_percentage_format = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'border': 1, 'text_wrap': True, 'num_format': '0%'})
        report_data = self._get_report_data()
        worksheet.write_string('B1', report_data['data']['company_name'], default_format)
        worksheet.write_string('D1', report_data['data']['cheque_no'], default_format)
        worksheet.write_string('B2', report_data['data']['sub_scheme_no'], default_format)
        worksheet.write_string('D2', report_data['data']['second_cheque_no'], default_format)
        row_index = 3
        for employee in report_data['employees_data']:
            worksheet.write_string(row_index, 0, employee['member_acount'], default_format)
            worksheet.write_string(row_index, 1, employee['hkid'], default_format)
            worksheet.write_string(row_index, 2, employee['surname'], default_format)
            worksheet.write_string(row_index, 3, employee['given_name'], default_format)
            worksheet.write_string(row_index, 4, employee['period_start'], default_date_format)
            worksheet.write_string(row_index, 5, employee['period_end'], default_date_format)
            worksheet.write_number(row_index, 6, employee['relevant_income'], default_money_format)
            worksheet.write_number(row_index, 7, employee['amount_eemc'], default_money_format)
            worksheet.write_number(row_index, 8, employee['amount_ermc'], default_money_format)
            worksheet.write_number(row_index, 9, employee['amount_eevc'], default_money_format)
            worksheet.write_number(row_index, 10, employee['amount_ervc'], default_money_format)
            worksheet.write_number(row_index, 11, employee['surcharge_percentage'], default_percentage_format)
            worksheet.write_number(row_index, 12, employee['amount_surcharge'], default_money_format)
            worksheet.write_number(row_index, 13, employee['basic_salary'], default_money_format)
            worksheet.write_string(row_index, 14, employee['last_date_of_employment'], default_date_format)
            row_index += 1

        worksheet.set_row(row_index, 22)
        worksheet.merge_range(row_index, 0, row_index, 6, 'Total\n合共', defailt_bold_format)
        worksheet.write_number(row_index, 7, report_data['total_data']['total_amount_eemc'], default_money_format)
        worksheet.write_number(row_index, 8, report_data['total_data']['total_amount_ermc'], default_money_format)
        worksheet.write_number(row_index, 9, report_data['total_data']['total_amount_eevc'], default_money_format)
        worksheet.write_number(row_index, 10, report_data['total_data']['total_amount_ervc'], default_money_format)
        worksheet.write_string(row_index, 11, '', default_format)
        worksheet.write_number(row_index, 12, report_data['total_data']['total_amount_surcharge'], default_money_format)
        worksheet.write_number(row_index, 13, report_data['total_data']['total_basic_salary'], default_money_format)
        worksheet.write_string(row_index, 14, '', default_format)

        workbook.close()

        if not self.xlsx_attachment_id:
            attachment = self.env["ir.attachment"].create({
                "name": self.xlsx_filename,
                "raw": file.getvalue(),
                "res_model": "l10n_hk.manulife.mpf",
                "res_id": self.id,
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            })
            self.xlsx_attachment_id = attachment
        else:
            self.xlsx_attachment_id.update({
                "name": self.xlsx_filename,
                "raw": file.getvalue(),
            })


class L10nHkManulifeMpfLine(models.Model):
    _name = 'l10n_hk.manulife.mpf.line'
    _description = 'Manulife MPF Line'

    _sql_constraints = [
        ('unique_employee', 'unique(employee_id, sheet_id)', 'An employee can only have one line per sheet'),
    ]

    employee_id = fields.Many2one('hr.employee', required=True)
    surcharge_percentage = fields.Float('Surcharge Percentage')
    amount_surcharge = fields.Monetary('Amount Surcharge')
    currency_id = fields.Many2one('res.currency', related='sheet_id.currency_id')
    sheet_id = fields.Many2one('l10n_hk.manulife.mpf', required=True, ondelete='cascade')
