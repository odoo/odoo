# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo.tests import tagged

from .common import TestL10NHkHrPayrollAccountCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSalaryRules(TestL10NHkHrPayrollAccountCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='hk'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.work_contact = cls.env['res.partner'].create([{
            'name': "Test Employee",
            'company_id': cls.env.company.id,
        }])

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'work_contact_id': cls.work_contact.id,
            'resource_calendar_id': cls.resource_calendar_40_hours_per_week.id,
            'company_id': cls.env.company.id,
            'country_id': cls.env.ref('base.hk').id,
            'marital': "single",
        })

        cls.contract = cls.env['hr.contract'].create({
            'name': "Contract For Payslip Test",
            'employee_id': cls.employee.id,
            'resource_calendar_id': cls.resource_calendar_40_hours_per_week.id,
            'company_id': cls.env.company.id,
            'structure_type_id': cls.env.ref('l10n_hk_hr_payroll.structure_type_employee_cap57').id,
            'date_start': date(2023, 1, 1),
            'wage': 20000.0,
            'l10n_hk_internet': 200.0,
            'state': "open",
        })

        cls.resource_calendar_20_hours_per_week = cls.resource_calendar_40_hours_per_week.copy({
            'name': "Test Calendar : 20 Hours/Week",
            'hours_per_day': 4,
            'hours_per_week': 20,
            'full_time_required_hours': 40,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Saturday Morning', 'dayofweek': '5', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'work_entry_type_id': cls.env.ref('l10n_hk_hr_payroll.work_entry_type_weekend').id}),
                (0, 0, {'name': 'Sunday Morning', 'dayofweek': '6', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'work_entry_type_id': cls.env.ref('l10n_hk_hr_payroll.work_entry_type_weekend').id}),
            ]
        })

        cls.env.ref('l10n_hk_hr_payroll.holiday_type_hk_annual_leave').write({'requires_allocation': 'no'})

    def test_001_a_regular_payslip(self):
        payslip = self._generate_payslip(date(2023, 1, 1), date(2023, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 14193.55, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 22.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 176.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('HKLEAVE600'), 5806.45, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('HKLEAVE600'), 9.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('HKLEAVE600'), 72.0, places=2)

        payslip_results = {
            'BASIC': 20000.0,
            'ALW.INT': 200.0,
            '713_GROSS': 20200.0,
            'MPF_GROSS': 20200.0,
            'EEMC': 0.0,
            'ERMC': 0.0,
            'GROSS': 20200.0,
            'NET': 20200.0,
            'MEA': 20200.0,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_001_b_moving_daily_wage_computation(self):
        leaves_to_create = [
            (datetime(2023, 3, 7), datetime(2023, 3, 7), 'l10n_hk_hr_payroll.holiday_type_hk_unpaid_leave'),
            (datetime(2023, 4, 11), datetime(2023, 4, 11), 'l10n_hk_hr_payroll.holiday_type_hk_annual_leave'),
        ]
        for leave in leaves_to_create:
            self._generate_leave(leave[0], leave[1], leave[2])
        results = {
            1: {
                'moving_daily_wage': 0,
                'payslip': {
                    'BASIC': 20000.0,
                    'ALW.INT': 200.0,
                    '713_GROSS': 20200.0,
                    'MPF_GROSS': 20200.0,
                    'GROSS': 20200.0,
                    'NET': 20200.0,
                    'MEA': 20200.0,
                }
            },
            2: {
                'moving_daily_wage': 651.61,
                'payslip': {
                    'BASIC': 20000.0,
                    'COMMISSION': 10000.0,
                    'ALW.INT': 200.0,
                    '713_GROSS': 30200.0,
                    'MPF_GROSS': 30200.0,
                    'EEMC': -1500.0,
                    'ERMC': -2510.0,
                    'GROSS': 32710.0,
                    'NET': 28700.0,
                    'MEA': 28700.0,
                },
            },
            3: {
                'moving_daily_wage': 854.24,
                'payslip': {
                    'BASIC': 19354.84,
                    'ALW.INT': 193.55,
                    '713_GROSS': 19548.39,
                    'MPF_GROSS': 19548.39,
                    'EEMC': -977.42,
                    'ERMC': -977.42,
                    'GROSS': 20525.81,
                    'NET': 18570.97,
                    'MEA': 18570.97,
                },
            },
            4: {
                'moving_daily_wage': 785.94,
                'payslip': {
                    'BASIC': 20119.28,
                    'ALW.INT': 200.0,
                    '713_GROSS': 20319.28,
                    'MPF_GROSS': 20319.28,
                    'EEMC': -1015.96,
                    'ERMC': -1015.96,
                    'GROSS': 21335.24,
                    'NET': 19303.32,
                    'MEA': 19303.32,
                },
            }
        }
        for month in range(1, 5):
            payslip = self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
                input_line_ids=[(0, 0, {'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_commission').id, 'amount': 10000})] if month == 2 else False,
            )

            self.assertEqual(len(payslip.worked_days_line_ids), 3 if month in [3, 4] else 2)
            self.assertEqual(len(payslip.input_line_ids), 1 if month == 2 else 0)

            self.assertAlmostEqual(payslip._get_moving_daily_wage(),
                                   results[month]['moving_daily_wage'],
                                   delta=0.01,
                                   msg="Incorrect moving daily wage for the %s month payslip" % month)
            self._validate_payslip(payslip, results[month]['payslip'])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_001_c_maternity_leave_payslip(self):
        leaves_to_create = [
            (datetime(2023, 3, 7), datetime(2023, 3, 13), 'l10n_hk_hr_payroll.holiday_type_hk_maternity_leave'),
            (datetime(2023, 3, 14), datetime(2023, 4, 11), 'l10n_hk_hr_payroll.holiday_type_hk_maternity_leave_80'),
        ]
        for leave in leaves_to_create:
            self._generate_leave(leave[0], leave[1], leave[2])
        results = {
            3: {
                'BASIC': 26952.4,
                'ALW.INT': 200.0,
                '713_GROSS': 27152.4,
                'MPF_GROSS': 27152.4,
                'EEMC': -1357.62,
                'ERMC': -1357.62,
                'GROSS': 28510.02,
                'NET': 25794.78,
                'MEA': 25794.78,
            },
            4: {
                'BASIC': 22158.1,
                'ALW.INT': 200.0,
                '713_GROSS': 22358.1,
                'MPF_GROSS': 22358.1,
                'EEMC': -1117.91,
                'ERMC': -1117.91,
                'GROSS': 23476.01,
                'NET': 21240.2,
                'MEA': 21240.2,
            }
        }
        payslip = self._generate_payslip(
            date(2023, 2, 1),
            date(2023, 2, 28),
            input_line_ids=[(0, 0, {'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_commission').id, 'amount': 10000})])
        payslip.action_payslip_done()
        payslip.action_payslip_paid()

        payslip = self._generate_payslip(date(2023, 3, 1), date(2023, 3, 31))
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('HKLEAVE210'), 7550.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('HKLEAVE210'), 7.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('HKLEAVE210'), 56.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('HKLEAVE211'), 15531.43, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('HKLEAVE211'), 18.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('HKLEAVE211'), 144.0, places=2)
        maternity_leave_daily_wage = payslip._get_worked_days_line_amount('HKLEAVE211') / payslip._get_worked_days_line_number_of_days('HKLEAVE211')
        self._validate_payslip(payslip, results[3])
        payslip.action_payslip_done()
        payslip.action_payslip_paid()

        payslip = self._generate_payslip(date(2023, 4, 1), date(2023, 4, 30))
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('HKLEAVE211'), 9491.43, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('HKLEAVE211'), 11.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('HKLEAVE211'), 88.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('HKLEAVE211') / payslip._get_worked_days_line_number_of_days('HKLEAVE211'), maternity_leave_daily_wage, places=2)
        self._validate_payslip(payslip, results[4])
        payslip.action_payslip_done()
        payslip.action_payslip_paid()

    def test_002_a_credit_time_payslip(self):
        self.contract.write({
            'wage': 10000.0,
            'resource_calendar_id': self.resource_calendar_20_hours_per_week.id,
        })
        payslip = self._generate_payslip(date(2023, 1, 1), date(2023, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 7096.77, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 22.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 88.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('HKLEAVE600'), 2903.23, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('HKLEAVE600'), 9.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('HKLEAVE600'), 36.0, places=2)

        payslip_results = {
            'BASIC': 10000.0,
            'ALW.INT': 200.0,
            '713_GROSS': 10200.0,
            'MPF_GROSS': 10200.0,
            'EEMC': 0.0,
            'ERMC': 0.0,
            'GROSS': 10200.0,
            'NET': 10200.0,
            'MEA': 10200.0,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_002_b_credit_time_moving_daily_wage(self):
        self.contract.write({
            'wage': 10000.0,
            'resource_calendar_id': self.resource_calendar_20_hours_per_week.id,
        })

        results = {
            1: {
                'moving_daily_wage': 0,
                'payslip': {
                    'BASIC': 10000.0,
                    'ALW.INT': 200.0,
                    '713_GROSS': 10200.0,
                    'MPF_GROSS': 10200.0,
                    'GROSS': 10200.0,
                    'NET': 10200.0,
                    'MEA': 10200.0,
                },
            },
            2: {
                'moving_daily_wage': 329.03,
                'payslip': {
                    'BASIC': 10000.0,
                    'ALW.INT': 200.0,
                    '713_GROSS': 10200.0,
                    'MPF_GROSS': 10200.0,
                    'EEMC': -510.0,
                    'ERMC': -1020.0,
                    'GROSS': 11220.0,
                    'NET': 9690.0,
                    'MEA': 9690.0,
                },
            }
        }

        for month in range(1, 3):
            payslip = self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
            )

            self.assertEqual(len(payslip.worked_days_line_ids), 2)
            self.assertEqual(len(payslip.input_line_ids), 0)

            self.assertAlmostEqual(payslip._get_moving_daily_wage(),
                                   results[month]['moving_daily_wage'],
                                   delta=0.01,
                                   msg="Incorrect moving daily wage for the %s month payslip" % month)
            self._validate_payslip(payslip, results[month]['payslip'])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_003_internet_allowance(self):
        self.contract.write({
            'date_start': date(2023, 1, 10),
        })
        self._generate_leave(datetime(2023, 1, 18), datetime(2023, 1, 20), 'l10n_hk_hr_payroll.holiday_type_hk_unpaid_leave')
        payslip = self._generate_payslip(date(2023, 1, 1), date(2023, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 4)
        self.assertEqual(len(payslip.input_line_ids), 0)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 8387.1, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 13.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 104.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE90'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE90'), 3.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE90'), 24.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('HKLEAVE600'), 3870.97, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('HKLEAVE600'), 6.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('HKLEAVE600'), 48.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('OUT'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('OUT'), 9.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('OUT'), 72.0, places=2)

        payslip_results = {
            'BASIC': 12258.07,
            'ALW.INT': 122.58,
            '713_GROSS': 12380.65,
            'MPF_GROSS': 12380.65,
            'GROSS': 12380.65,
            'NET': 12380.65,
            'MEA': 12380.65,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_004_a_mpf_computation(self):
        payslip_results = {
            1: {
                'BASIC': 20000.0,
                'ALW.INT': 200.0,
                '713_GROSS': 20200.0,
                'MPF_GROSS': 20200.0,
                'EEMC': 0.0,
                'ERMC': 0.0,
                'GROSS': 20200.0,
                'NET': 20200.0,
                'MEA': 20200.0,
            },
            2: {
                'BASIC': 20000.0,
                'ALW.INT': 200.0,
                '713_GROSS': 20200.0,
                'MPF_GROSS': 20200.0,
                'EEMC': -1010.0,
                'ERMC': -2020.0,
                'GROSS': 22220.0,
                'NET': 19190.0,
                'MEA': 19190.0,
            },
            3: {
                'BASIC': 20000.0,
                'COMMISSION': 10000.0,
                'ALW.INT': 200.0,
                '713_GROSS': 30200.0,
                'MPF_GROSS': 30200.0,
                'EEMC': -1500.0,
                'ERMC': -1500.0,
                'GROSS': 31700.0,
                'NET': 28700.0,
                'MEA': 28700.0,
            },
        }
        for month in range(1, 4):
            payslip = self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
                input_line_ids=[(0, 0, {'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_commission').id, 'amount': 10000})] if month == 3 else False,
            )
            self._validate_payslip(payslip, payslip_results[month])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_004_b_mpf_first_contribution(self):
        self.contract.write({
            'date_start': date(2023, 2, 1),
        })
        payslip_results = {
            2: {
                'BASIC': 20000.0,
                'ALW.INT': 200.0,
                '713_GROSS': 20200.0,
                'MPF_GROSS': 20200.0,
                'GROSS': 20200.0,
                'NET': 20200.0,
                'MEA': 20200.0,
            },
            3: {
                'BASIC': 20000.0,
                'ALW.INT': 200.0,
                '713_GROSS': 20200.0,
                'MPF_GROSS': 20200.0,
                'GROSS': 20200.0,
                'NET': 20200.0,
                'MEA': 20200.0,
            },
            4: {
                'BASIC': 20000.0,
                'ALW.INT': 200.0,
                '713_GROSS': 20200.0,
                'MPF_GROSS': 20200.0,
                'EEMC': -1010.0,
                'ERMC': -3030.0,
                'GROSS': 23230.0,
                'NET': 19190.0,
                'MEA': 19190.0,
            },
            5: {
                'BASIC': 20000.0,
                'ALW.INT': 200.0,
                '713_GROSS': 20200.0,
                'MPF_GROSS': 20200.0,
                'EEMC': -1010.0,
                'ERMC': -1010.0,
                'GROSS': 21210.0,
                'NET': 19190.0,
                'MEA': 19190.0,
            },
        }
        for month in range(2, 6):
            payslip = self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
            )
            self._validate_payslip(payslip, payslip_results[month])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_004_c_mpf_volunteer_contribution_fixed(self):
        self.contract.write({
            'wage': 21000.0,
            'l10n_hk_internet': 0.0,
        })
        payslip = self._generate_payslip(date(2023, 1, 1), date(2023, 1, 31))
        payslip.action_payslip_done()
        payslip.action_payslip_paid()
        self.employee.write({
            'l10n_hk_mpf_vc_option': 'custom',
            'l10n_hk_mpf_vc_percentage': 0.05
        })
        inputs = {
            2: {
                'wage': 21000.0,
                'commission': 0.0,
                'vc_percentage': 0.05
            },
            3: {
                'wage': 21000.0,
                'commission': 0.0,
                'vc_percentage': 0.05
            },
            4: {
                'wage': 32000.0,
                'commission': 0.0,
                'vc_percentage': 0.05
            },
            5: {
                'wage': 22000.0,
                'commission': 0.0,
                'vc_percentage': 0.03
            },
            6: {
                'wage': 22000.0,
                'commission': 13000.0,
                'vc_percentage': 0.03
            },
        }
        payslip_results = {
            2: {
                'BASIC': 21000.0,
                '713_GROSS': 21000.0,
                'MPF_GROSS': 21000.0,
                'EEMC': -1050.0,
                'ERMC': -2100.0,
                'EEVC': -1050.0,
                'ERVC': -1050.0,
                'GROSS': 24150.0,
                'NET': 18900.0,
                'MEA': 18900.0,
            },
            3: {
                'BASIC': 21000.0,
                '713_GROSS': 21000.0,
                'MPF_GROSS': 21000.0,
                'EEMC': -1050.0,
                'ERMC': -1050.0,
                'EEVC': -1050.0,
                'ERVC': -1050.0,
                'GROSS': 23100.0,
                'NET': 18900.0,
                'MEA': 18900.0,
            },
            4: {
                'BASIC': 32000.0,
                '713_GROSS': 32000.0,
                'MPF_GROSS': 32000.0,
                'EEMC': -1500.0,
                'ERMC': -1500.0,
                'EEVC': -1600.0,
                'ERVC': -1600.0,
                'GROSS': 35100.0,
                'NET': 28900.0,
                'MEA': 28900.0,
            },
            5: {
                'BASIC': 22000.0,
                '713_GROSS': 22000.0,
                'MPF_GROSS': 22000.0,
                'EEMC': -1100.0,
                'ERMC': -1100.0,
                'EEVC': -660.0,
                'ERVC': -660.0,
                'GROSS': 23760.0,
                'NET': 20240.0,
                'MEA': 20240.0,
            },
            6: {
                'BASIC': 22000.0,
                'COMMISSION': 13000.0,
                '713_GROSS': 35000.0,
                'MPF_GROSS': 35000.0,
                'EEMC': -1500.0,
                'ERMC': -1500.0,
                'EEVC': -1050.0,
                'ERVC': -1050.0,
                'GROSS': 37550.0,
                'NET': 32450.0,
                'MEA': 32450.0,
            }
        }
        for month in range(2, 7):
            self.employee.write({'l10n_hk_mpf_vc_percentage': inputs[month]['vc_percentage']})
            self.contract.write({'wage': inputs[month]['wage']})
            payslip = self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
                input_line_ids=[(0, 0, {'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_commission').id, 'amount': inputs[month]['commission']})] if inputs[month]['commission'] else False,
            )
            self._validate_payslip(payslip, payslip_results[month])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_004_d_mpf_volunteer_contribution_cap(self):
        self.contract.write({
            'wage': 21000.0,
            'l10n_hk_internet': 0.0,
        })
        payslip = self._generate_payslip(date(2023, 1, 1), date(2023, 1, 31))
        payslip.action_payslip_done()
        payslip.action_payslip_paid()
        self.employee.write({'l10n_hk_mpf_vc_option': 'max'})
        inputs = {
            2: {
                'wage': 21000.0,
                'commission': 0.0
            },
            3: {
                'wage': 21000.0,
                'commission': 0.0
            },
            4: {
                'wage': 32000.0,
                'commission': 0.0
            },
            5: {
                'wage': 22000.0,
                'commission': 0.0
            },
            6: {
                'wage': 22000.0,
                'commission': 13000.0
            },
        }
        payslip_results = {
            2: {
                'BASIC': 21000.0,
                '713_GROSS': 21000.0,
                'MPF_GROSS': 21000.0,
                'EEMC': -1050.0,
                'ERMC': -2100.0,
                'EEVC': 0,
                'ERVC': 0,
                'GROSS': 23100.0,
                'NET': 19950.0,
                'MEA': 19950.0,
            },
            3: {
                'BASIC': 21000.0,
                '713_GROSS': 21000.0,
                'MPF_GROSS': 21000.0,
                'EEMC': -1050.0,
                'ERMC': -1050.0,
                'EEVC': 0,
                'ERVC': 0,
                'GROSS': 22050.0,
                'NET': 19950.0,
                'MEA': 19950.0,
            },
            4: {
                'BASIC': 32000.0,
                '713_GROSS': 32000.0,
                'MPF_GROSS': 32000.0,
                'EEMC': -1500.0,
                'ERMC': -1500.0,
                'EEVC': -100.0,
                'ERVC': -100.0,
                'GROSS': 33600.0,
                'NET': 30400.0,
                'MEA': 30400.0,
            },
            5: {
                'BASIC': 22000.0,
                '713_GROSS': 22000.0,
                'MPF_GROSS': 22000.0,
                'EEMC': -1100.0,
                'ERMC': -1100.0,
                'EEVC': 0,
                'ERVC': 0,
                'GROSS': 23100.0,
                'NET': 20900.0,
                'MEA': 20900.0,
            },
            6: {
                'BASIC': 22000.0,
                'COMMISSION': 13000.0,
                '713_GROSS': 35000.0,
                'MPF_GROSS': 35000.0,
                'EEMC': -1500.0,
                'ERMC': -1500.0,
                'EEVC': -250.0,
                'ERVC': -250.0,
                'GROSS': 36750.0,
                'NET': 33250.0,
                'MEA': 33250.0,
            },
        }
        for month in range(2, 7):
            self.contract.write({'wage': inputs[month]['wage']})
            payslip = self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
                input_line_ids=[(0, 0, {'input_type_id': self.env.ref('l10n_hk_hr_payroll.input_commission').id, 'amount': inputs[month]['commission']})] if inputs[month]['commission'] else False,
            )
            self._validate_payslip(payslip, payslip_results[month])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_004_e_mpf_first_contribution_special_case(self):
        self.contract.write({
            'date_start': date(2023, 7, 3),
        })
        payslip_results = {
            7: {
                'BASIC': 18709.68,
                'ALW.INT': 187.1,
                '713_GROSS': 18896.78,
                'MPF_GROSS': 18896.78,
                'GROSS': 18896.78,
                'NET': 18896.78,
                'MEA': 18896.78,
            },
            8: {
                'BASIC': 20000.0,
                'ALW.INT': 200.0,
                '713_GROSS': 20200.0,
                'MPF_GROSS': 20200.0,
                'ERMC': -1954.84,
                'GROSS': 22154.84,
                'NET': 20200.0,
                'MEA': 20200.0,
            },
            9: {
                'BASIC': 20000.0,
                'ALW.INT': 200.0,
                '713_GROSS': 20200.0,
                'MPF_GROSS': 20200.0,
                'EEMC': -1010.0,
                'ERMC': -1010.0,
                'GROSS': 21210.0,
                'NET': 19190.0,
                'MEA': 19190.0,
            },
            10: {
                'BASIC': 20000.0,
                'ALW.INT': 200.0,
                '713_GROSS': 20200.0,
                'MPF_GROSS': 20200.0,
                'EEMC': -1010.0,
                'ERMC': -1010.0,
                'GROSS': 21210.0,
                'NET': 19190.0,
                'MEA': 19190.0,
            },
        }
        for month in range(7, 11):
            payslip = self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
            )
            self._validate_payslip(payslip, payslip_results[month])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_004_f_mpf_below_mpf_threshold_include_ermc(self):
        self.contract.write({
            'wage': 5000.0,
            'l10n_hk_internet': 0.0,
        })
        payslip = self._generate_payslip(date(2023, 1, 1), date(2023, 1, 31))
        payslip.action_payslip_done()
        payslip.action_payslip_paid()

        payslip_results = {
            2: {
                'BASIC': 5000.0,
                '713_GROSS': 5000.0,
                'MPF_GROSS': 5000.0,
                'ERMC': -500,
                'GROSS': 5500.0,
                'NET': 5000.0,
                'MEA': 5000.0,
            },
            3: {
                'BASIC': 5000.0,
                '713_GROSS': 5000.0,
                'MPF_GROSS': 5000.0,
                'ERMC': -250,
                'GROSS': 5250.0,
                'NET': 5000.0,
                'MEA': 5000.0,
            }
        }

        for month in range(2, 4):
            payslip = self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
            )
            self._validate_payslip(payslip, payslip_results[month])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_005_a_end_of_year_payment(self):
        for month in range(1, 12):
            self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
            ).action_payslip_done()

        payslip = self._generate_payslip(date(2023, 12, 1), date(2023, 12, 31))
        payslip_results = {
            'BASIC': 20000.0,
            'ALW.INT': 200.0,
            '713_GROSS': 20200.0,
            'END_OF_YEAR_PAYMENT': 20235.28,
            'MPF_GROSS': 40435.28,
            'EEMC': -1500.0,
            'ERMC': -1500.0,
            'GROSS': 41935.28,
            'NET': 38935.28,
            'MEA': 38935.28,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_005_b_incomplete_year_end_of_year_payment(self):
        self.contract.write({
            'date_start': date(2023, 7, 3),
        })
        for month in range(7, 12):
            self._generate_payslip(
                date(2023, month, 1),
                date(2023, month, 1) + relativedelta(day=31),
            ).action_payslip_done()

        payslip = self._generate_payslip(date(2023, 12, 1), date(2023, 12, 31))
        payslip_results = {
            'BASIC': 20000.0,
            'ALW.INT': 200.0,
            '713_GROSS': 20200.0,
            'END_OF_YEAR_PAYMENT': 10013.69,
            'MPF_GROSS': 30213.69,
            'EEMC': -1500.0,
            'ERMC': -1500.0,
            'GROSS': 31713.69,
            'NET': 28713.69,
            'MEA': 28713.69,
        }
        self._validate_payslip(payslip, payslip_results)
