# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import re

from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare


class Payslip(models.Model):
    _inherit = 'hr.payslip'

    l10n_hk_worked_days_leaves_count = fields.Integer(
        'Worked Days Leaves Count',
        compute='_compute_worked_days_leaves_count')
    l10n_hk_713_gross = fields.Monetary(
        '713 Gross',
        compute='_compute_gross',
        store=True)
    l10n_hk_mpf_gross = fields.Monetary(
        'MPF Gross',
        compute='_compute_gross',
        store=True)
    l10n_hk_autopay_gross = fields.Monetary(
        'AutoPay Gross',
        compute='_compute_gross',
        store=True)
    l10n_hk_second_batch_autopay_gross = fields.Monetary(
        'Second Batch AutoPay Gross',
        compute='_compute_gross',
        store=True)

    @api.depends('worked_days_line_ids')
    def _compute_worked_days_leaves_count(self):
        for payslip in self:
            payslip.l10n_hk_worked_days_leaves_count = len(payslip.worked_days_line_ids.filtered(lambda wd: wd.l10n_hk_leave_id))

    @api.depends('line_ids.total')
    def _compute_gross(self):
        line_values = (self._origin)._get_line_values(['713_GROSS', 'MPF_GROSS', 'MEA', 'SBA'])
        for payslip in self:
            payslip.l10n_hk_713_gross = line_values['713_GROSS'][payslip._origin.id]['total']
            payslip.l10n_hk_mpf_gross = line_values['MPF_GROSS'][payslip._origin.id]['total']
            payslip.l10n_hk_autopay_gross = line_values['MEA'][payslip._origin.id]['total']
            payslip.l10n_hk_second_batch_autopay_gross = line_values['SBA'][payslip._origin.id]['total']

    def _get_paid_amount(self):
        self.ensure_one()
        res = super()._get_paid_amount()
        if self.struct_id.country_id.code != 'HK':
            return res
        if float_compare(res, self._get_contract_wage(), precision_rounding=0.1) == 0:
            return self._get_contract_wage()
        return res

    @api.model
    def _get_last_year_payslips_domain(self, date_from, date_to, employee_ids=None):
        domain = [
            ('state', 'in', ['paid', 'done']),
            ('date_from', '>=', date_from + relativedelta(months=-12, day=1)),
            ('date_to', '<', date_to + relativedelta(day=1)),
            ('struct_id', '=', self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_employee_salary').id),
        ]
        if employee_ids:
            domain = expression.AND([domain, [('employee_id', 'in', employee_ids)]])
        return domain

    def _get_moving_daily_wage(self):
        self.ensure_one()

        moving_daily_wage = sum(self.input_line_ids.filtered(lambda line: line.code == 'MOVING_DAILY_WAGE').mapped('amount'))
        if moving_daily_wage:
            return moving_daily_wage

        payslips_per_employee = self._get_last_year_payslips_per_employee(self.date_from, self.date_to)
        payslips = payslips_per_employee[self.employee_id]
        domain = self._get_last_year_payslips_domain(self.date_from, self.date_to)
        last_year_payslips = payslips.filtered_domain(domain).sorted(lambda slip: slip.date_from)
        if last_year_payslips:
            gross = last_year_payslips._get_line_values(['713_GROSS'], compute_sum=True)['713_GROSS']['sum']['total']
            gross -= last_year_payslips._get_total_non_full_pay()
            number_of_days = last_year_payslips._get_number_of_worked_days(only_full_pay=True)
            if number_of_days > 0:
                return gross / number_of_days
        return 0

    def _get_number_of_non_full_pay_days(self):
        wds = self.worked_days_line_ids.filtered(lambda wd: wd.work_entry_type_id.l10n_hk_non_full_pay)
        return sum([wd.number_of_days for wd in wds])

    def _get_number_of_worked_days(self, only_full_pay=False):
        wds = self.worked_days_line_ids.filtered(lambda wd: wd.code not in ['LEAVE90', 'OUT'])
        number_of_days = sum([wd.number_of_days for wd in wds])
        if only_full_pay:
            return number_of_days - self._get_number_of_non_full_pay_days()
        return number_of_days

    def _get_last_year_payslips_per_employee(self, date_from, date_to):
        domain = self._get_last_year_payslips_domain(date_from, date_to, self.employee_id.ids)
        payslips = self.env['hr.payslip'].search(domain)
        payslips_per_employee = defaultdict(lambda: self.env['hr.payslip'])
        for payslip in payslips:
            payslips_per_employee[payslip.employee_id] += payslip
        return payslips_per_employee

    def _get_credit_time_lines(self):
        if self.struct_id.country_id.code != 'HK':
            return super()._get_credit_time_lines()
        return []

    def _get_worked_day_lines_values(self, domain=None):
        self.ensure_one()
        res = super()._get_worked_day_lines_values(domain)
        if self.struct_id.country_id.code != 'HK':
            return res

        current_month_domain = expression.AND(
            [domain, ['|', ('leave_id', '=', False), ('leave_id.date_from', '>=', self.date_from)]])
        res = super()._get_worked_day_lines_values(current_month_domain)

        hours_per_day = self._get_worked_day_lines_hours_per_day()
        date_from = datetime.combine(self.date_from, datetime.min.time())
        date_to = datetime.combine(self.date_to, datetime.max.time())
        remainig_work_entries_domain = expression.AND([domain, [('leave_id.date_from', '<', self.date_from)]])
        work_entries_dict = self.env['hr.work.entry']._read_group(
            self.contract_id._get_work_hours_domain(date_from, date_to, domain=remainig_work_entries_domain, inside=True),
            ['leave_id', 'work_entry_type_id'],
            ['duration:sum'],
        )
        work_entries = defaultdict(tuple)
        work_entries.update({
            (work_entry_type.id, leave.id): hours
            for leave, work_entry_type, hours in work_entries_dict
        })
        for work_entry, hours in work_entries.items():
            work_entry_id, leave_id = work_entry
            work_entry_type = self.env['hr.work.entry.type'].browse(work_entry_id)
            days = round(hours / hours_per_day, 5) if hours_per_day else 0
            day_rounded = self._round_days(work_entry_type, days)
            res.append({
                'sequence': work_entry_type.sequence,
                'work_entry_type_id': work_entry_id,
                'number_of_days': day_rounded,
                'number_of_hours': hours,
                'l10n_hk_leave_id': leave_id,
            })
        return res

    def _get_worked_day_lines(self, domain=None, check_out_of_contract=True):
        self.ensure_one()
        res = super()._get_worked_day_lines(domain, check_out_of_contract)
        if self.struct_id.country_id.code != 'HK':
            return res

        contract = self.contract_id
        if contract.resource_calendar_id:
            if not check_out_of_contract:
                return res
            out_days, out_hours = 0, 0
            reference_calendar = self._get_out_of_contract_calendar()
            domain = expression.AND([domain, [('work_entry_type_id.is_leave', '=', True)]])
            if self.date_from < contract.date_start:
                start = fields.Datetime.to_datetime(self.date_from)
                stop = fields.Datetime.to_datetime(contract.date_start) + relativedelta(days=-1, hour=23, minute=59)
                out_time = reference_calendar.get_work_duration_data(start, stop, compute_leaves=False, domain=domain)
                out_days += out_time['days']
                out_hours += out_time['hours']
            if contract.date_end and contract.date_end < self.date_to:
                start = fields.Datetime.to_datetime(contract.date_end) + relativedelta(days=1)
                stop = fields.Datetime.to_datetime(self.date_to) + relativedelta(hour=23, minute=59)
                out_time = reference_calendar.get_work_duration_data(start, stop, compute_leaves=False, domain=domain)
                out_days += out_time['days']
                out_hours += out_time['hours']
            if out_days or out_hours:
                work_entry_type = self.env.ref('hr_payroll.hr_work_entry_type_out_of_contract')
                existing = False
                for worked_days in res:
                    if worked_days['work_entry_type_id'] == work_entry_type.id:
                        worked_days['number_of_days'] += out_days
                        worked_days['number_of_hours'] += out_hours
                        existing = True
                        break
                if not existing:
                    res.append({
                        'sequence': work_entry_type.sequence,
                        'work_entry_type_id': work_entry_type.id,
                        'number_of_days': out_days,
                        'number_of_hours': out_hours,
                    })
        return res

    def _get_total_non_full_pay(self):
        total = 0
        for wd_line in self.worked_days_line_ids:
            if not wd_line.work_entry_type_id.l10n_hk_non_full_pay:
                continue
            total += wd_line.amount
        return total

    def _generate_h2h_autopay(self, header_data: dict) -> str:
        ctime = datetime.now()
        header = (
            f'H{header_data["digital_pic_id"]:<11}HKMFPS02{"":<3}'
            f'{header_data["customer_ref"]:<35}{ctime:%Y/%m/%d%H:%M:%S}'
            f'{"":<1}{header_data["authorisation_type"]}{"":<2}PH{"":<79}\n'
        )
        return header

    def _generate_hsbc_autopay(self, header_data: dict, payments_data: dict) -> str:
        acc_number = re.sub(r"[^0-9]", "", header_data['autopay_partner_bank_id'].acc_number)
        header = (
            f'PHF{header_data["payment_set_code"]}{header_data["ref"]:<12}{header_data["payment_date"]:%Y%m%d}'
            f'{acc_number + "SA" + header_data["currency"]:<35}'
            f'{header_data["currency"]}{header_data["payslips_count"]:07}{int(header_data["amount_total"] * 100):017}'
            f'{"":<1}{"":<311}\n'
        )
        datas = []
        for payment in payments_data:
            datas.append(
                f'PD{payment["bank_code"]:<3}{payment["type"].upper()}{payment["autopay_field"]:<34}'
                f'{int(payment["amount"] * 100):017}{payment["identifier"]:<35}{payment["ref"]:<35}'
                f'{payment["bank_account_name"]:<140}{"":<130}'
            )
        data = '\n'.join(datas)
        return header + data

    def _create_apc_file(self, payment_date, payment_set_code: str, batch_type: str = 'first', ref: str = None, file_name: str = None, **kwargs):
        invalid_payslips = self.filtered(lambda p: p.currency_id.name not in ['HKD', 'CNY'])
        if invalid_payslips:
            raise UserError(_("Only accept HKD or CNY currency.\nInvalid currency for the following payslips:\n%s", '\n'.join(invalid_payslips.mapped('name'))))
        companies = self.mapped('company_id')
        if len(companies) > 1:
            raise UserError(_("Only support generating the HSBC autopay report for one company."))
        currencies = self.mapped('currency_id')
        if len(currencies) > 1:
            raise UserError(_("Only support generating the HSBC autopay report for one currency"))
        invalid_employees = self.mapped('employee_id').filtered(lambda e: not e.bank_account_id)
        if invalid_employees:
            raise UserError(_("Some employees (%s) don't have a bank account.", ','.join(invalid_employees.mapped('name'))))
        invalid_employees = self.mapped('employee_id').filtered(lambda e: not e.l10n_hk_autopay_account_type)
        if invalid_employees:
            raise UserError(_("Some employees (%s) haven't set the autopay type.", ','.join(invalid_employees.mapped('name'))))
        invalid_banks = self.employee_id.bank_account_id.mapped('bank_id').filtered(lambda b: not b.l10n_hk_bank_code)
        if invalid_banks:
            raise UserError(_("Some banks (%s) don't have a bank code", ','.join(invalid_banks.mapped('name'))))
        invalid_bank_accounts = self.mapped('employee_id').filtered(
            lambda e: e.l10n_hk_autopay_account_type in ['bban', 'hkid'] and not e.bank_account_id.acc_holder_name)
        if invalid_bank_accounts:
            raise UserError(_("Some bank accounts (%s) don't have a bank account name.", ','.join(invalid_bank_accounts.mapped('bank_account_id.acc_number'))))
        rule_code = {'first': 'MEA', 'second': 'SBA'}[batch_type]
        payslips = self.filtered(lambda p: p.struct_id.code == 'CAP57MONTHLY' and p.line_ids.filtered(lambda line: line.code == rule_code))
        if not payslips:
            raise UserError(_("No payslip to generate the HSBC autopay report."))

        autopay_type = self.company_id.l10n_hk_autopay_type
        if autopay_type == 'h2h':
            h2h_header_data = {
                'authorisation_type': kwargs.get('authorisation_type'),
                'customer_ref': kwargs.get('customer_ref', ''),
                'digital_pic_id': kwargs.get('digital_pic_id'),
                'payment_date': payment_date,
            }

        header_data = {
            'ref': ref,
            'currency': payslips.currency_id.name,
            'amount_total': sum(payslips.line_ids.filtered(lambda line: line.code == rule_code).mapped('amount')),
            'payment_date': payment_date,
            'payslips_count': len(payslips),
            'payment_set_code': payment_set_code,
            'autopay_partner_bank_id': payslips.company_id.l10n_hk_autopay_partner_bank_id,
        }

        payments_data = []
        for payslip in payslips:
            payments_data.append({
                'id': payslip.id,
                'ref': payslip.employee_id.l10n_hk_autopay_ref or '',
                'type': payslip.employee_id.l10n_hk_autopay_account_type,
                'amount': sum(payslip.line_ids.filtered(lambda line: line.code == rule_code).mapped('amount')),
                'identifier': re.sub(r'[^a-zA-Z0-9]', '', payslip.employee_id.identification_id or ''),
                'bank_code': payslip.employee_id.get_l10n_hk_autopay_bank_code(),
                'autopay_field': payslip.employee_id.get_l10n_hk_autopay_field(),
                'bank_account_name': payslip.employee_id.bank_account_id.acc_holder_name or '',
            })

        apc_doc = payslips._generate_hsbc_autopay(header_data, payments_data)
        if autopay_type == 'h2h':
            apc_doc = payslips._generate_h2h_autopay(h2h_header_data) + apc_doc
        apc_binary = base64.encodebytes(apc_doc.encode('ascii'))

        file_name = file_name and file_name.replace('.apc', '')
        if batch_type == 'first':
            payslips.mapped('payslip_run_id').write({
                'l10n_hk_autopay_export_first_batch_date': payment_date,
                'l10n_hk_autopay_export_first_batch': apc_binary,
                'l10n_hk_autopay_export_first_batch_filename': (file_name or 'HSBC_Autopay_export_first_batch') + '.apc',
            })
        else:
            payslips.mapped('payslip_run_id').write({
                'l10n_hk_autopay_export_second_batch_date': payment_date,
                'l10n_hk_autopay_export_second_batch': apc_binary,
                'l10n_hk_autopay_export_second_batch_filename': (file_name or 'HSBC_Autopay_export_second_batch') + '.apc',
            })

    def write(self, vals):
        res = super().write(vals)
        if 'input_line_ids' in vals:
            self.filtered(lambda p: p.struct_id.country_id.code == 'HK' and p.state in ['draft', 'verify']).action_refresh_from_work_entries()
        return res

    def action_payslip_done(self):
        res = super().action_payslip_done()
        if self.struct_id.country_id.code != 'HK':
            return res
        future_payslips = self.sudo().search([
            ('id', 'not in', self.ids),
            ('state', 'in', ['draft', 'verify']),
            ('employee_id', 'in', self.mapped('employee_id').ids),
            ('date_from', '>=', min(self.mapped('date_to'))),
        ])
        if future_payslips:
            future_payslips.action_refresh_from_work_entries()
        return res
