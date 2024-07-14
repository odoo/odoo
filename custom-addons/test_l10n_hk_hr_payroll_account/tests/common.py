# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools.float_utils import float_compare


class TestL10NHkHrPayrollAccountCommon(AccountTestInvoicingCommon):

    @classmethod
    def setup_armageddon_tax(cls, tax_name, company_data):
        # Hong Kong doesn't have any tax, so this methods will throw errors if we don't return None
        return None

    @classmethod
    def setUpClass(cls, chart_template_ref='hk'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.hk').id,
        })
        cls.company = cls.env.company

        admin = cls.env['res.users'].search([('login', '=', 'admin')])
        admin.company_ids |= cls.company

        cls.env.user.tz = 'Asia/Hong_Kong'

        cls.resource_calendar_40_hours_per_week = cls.env['resource.calendar'].create({
            'name': "Test Calendar : 40 Hours/Week",
            'company_id': cls.company.id,
            'hours_per_day': 8.0,
            'tz': "Asia/Hong_Kong",
            'two_weeks_calendar': False,
            'hours_per_week': 40,
            'full_time_required_hours': 40,
            'attendance_ids': [
                (5, 0, 0),
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Saturday Morning', 'dayofweek': '5', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'work_entry_type_id': cls.env.ref('l10n_hk_hr_payroll.work_entry_type_weekend').id}),
                (0, 0, {'name': 'Saturday Afternoon', 'dayofweek': '5', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon', 'work_entry_type_id': cls.env.ref('l10n_hk_hr_payroll.work_entry_type_weekend').id}),
                (0, 0, {'name': 'Sunday Morning', 'dayofweek': '6', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'work_entry_type_id': cls.env.ref('l10n_hk_hr_payroll.work_entry_type_weekend').id}),
                (0, 0, {'name': 'Sunday Afternoon', 'dayofweek': '6', 'hour_from': 13, 'hour_to': 17.0, 'day_period': 'afternoon', 'work_entry_type_id': cls.env.ref('l10n_hk_hr_payroll.work_entry_type_weekend').id}),
            ]
        })

    @classmethod
    def _generate_payslip(cls, date_from, date_to, struct_id=False, input_line_ids=False):
        work_entries = cls.contract.generate_work_entries(date_from, date_to)
        payslip = cls.env['hr.payslip'].create([{
            'name': "Test Payslip",
            'employee_id': cls.employee.id,
            'contract_id': cls.contract.id,
            'company_id': cls.env.company.id,
            'struct_id': struct_id or cls.env.ref('l10n_hk_hr_payroll.structure_type_employee_cap57').id,
            'date_from': date_from,
            'date_to': date_to,
            'input_line_ids': input_line_ids or [],
        }])
        work_entries.action_validate()
        payslip.compute_sheet()
        return payslip

    @classmethod
    def _generate_leave(cls, date_from, date_to, holiday_status_id):
        return cls.env['hr.leave'].create({
            'holiday_type': 'employee',
            'employee_id': cls.employee.id,
            'request_date_from': date_from,
            'request_date_to': date_to,
            'holiday_status_id': cls.env.ref(holiday_status_id).id,
        }).action_validate()

    def _validate_payslip(self, payslip, results):
        error = []
        line_values = payslip._get_line_values(set(results.keys()) | set(payslip.line_ids.mapped('code')))
        for code, value in results.items():
            payslip_line_value = line_values[code][payslip.id]['total']
            if float_compare(payslip_line_value, value, 2):
                error.append("Code: %s - Expected: %s - Reality: %s" % (code, value, payslip_line_value))
        for line in payslip.line_ids:
            if line.code not in results:
                error.append("Missing Line: '%s' - %s," % (line.code, line_values[line.code][payslip.id]['total']))
        if error:
            error.append("Payslip Period: %s - %s" % (payslip.date_from, payslip.date_to))
            error.append("Payslip Actual Values: ")
            error.append("        {")
            for line in payslip.line_ids:
                error.append("            '%s': %s," % (line.code, line_values[line.code][payslip.id]['total']))
            error.append("        }")
        self.assertEqual(len(error), 0, '\n' + '\n'.join(error))
