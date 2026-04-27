# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


class TestL10NHkHrPayrollAccountCommon(TestPayslipValidationCommon):

    @classmethod
    def setup_armageddon_tax(cls, tax_name, company_data):
        # Hong Kong doesn't have any tax, so this methods will throw errors if we don't return None
        return None

    @classmethod
    @TestPayslipValidationCommon.setup_country('hk')
    def setUpClass(cls):
        super().setUpClass()

        resource_calendar = cls.env['resource.calendar'].create({
            'name': "Test Calendar : 40 Hours/Week",
            'company_id': cls.env.company.id,
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

        cls._setup_common(
            country=cls.env.ref('base.hk'),
            structure=cls.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_employee_salary'),
            structure_type=cls.env.ref('l10n_hk_hr_payroll.structure_type_employee_cap57'),
            resource_calendar=resource_calendar,
            contract_fields={
                'date_start': date(2023, 1, 1),
                'wage': 20000.0,
                'l10n_hk_internet': 200.0,
            },
            employee_fields={
                'marital': "single",
            }
        )

        admin = cls.env['res.users'].search([('login', '=', 'admin')])
        admin.company_ids |= cls.env.company

        cls.env.user.tz = 'Asia/Hong_Kong'
