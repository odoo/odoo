# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import time

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import users, warmup, tagged, new_test_user

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install', 'au_payroll_perf')
class TestPerformance(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('au')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.au').id,
            'street': 'Rue du Paradis',
            'zip': '6870',
            'city': 'Eghezee',
            'vat': '83914571673',
            'phone': '061928374',
            "l10n_au_bms_id": "ODOO_TEST_BMS_ID",
            "email": "au_company@odoo.com",
            'l10n_au_branch_code': '100'
        })

        cls.company = cls.env.company

        admin = cls.env['res.users'].search([('login', '=', 'admin')])
        admin.company_ids |= cls.company

        cls.env.user.tz = 'Australia/Sydney'

        cls.resource_calendar_40_hours_per_week = cls.env['resource.calendar'].create([{
            'name': "Test Calendar : 38 Hours/Week",
            'company_id': cls.env.company.id,
            'hours_per_day': 7.6,
            'tz': "Australia/Sydney",
            'two_weeks_calendar': False,
            'hours_per_week': 38.0,
            'full_time_required_hours': 38.0,
            'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                'name': "Attendance",
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'day_period': day_period,
                'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 12.0, "morning"),
                ("0", 12.0, 13.0, "lunch"),
                ("0", 13.0, 16.6, "afternoon"),
                ("1", 8.0, 12.0, "morning"),
                ("1", 12.0, 13.0, "lunch"),
                ("1", 13.0, 16.6, "afternoon"),
                ("2", 8.0, 12.0, "morning"),
                ("2", 12.0, 13.0, "lunch"),
                ("2", 13.0, 16.6, "afternoon"),
                ("3", 8.0, 12.0, "morning"),
                ("3", 12.0, 13.0, "lunch"),
                ("3", 13.0, 16.6, "afternoon"),
                ("4", 8.0, 12.0, "morning"),
                ("4", 12.0, 13.0, "lunch"),
                ("4", 13.0, 16.6, "afternoon"),
            ]],
        }])

        cls.EMPLOYEES_COUNT = 100

        cls.date_from = date(2023, 8, 1)
        cls.date_to = date(2023, 8, 31)

        cls.addresses = cls.env['res.partner'].create([{
            'name': "Test Private Address %i" % i,
            'company_id': cls.company.id,
            'street': 'Brussels Street',
            'city': 'Brussels',
            'zip': '2928',
            'country_id': cls.env.ref('base.au').id,
        } for i in range(cls.EMPLOYEES_COUNT)])

        cls.employees = cls.env['hr.employee'].create([{
            'name': "Test Employee %i" % i,
            'work_contact_id': cls.addresses[i].id,
            'resource_calendar_id': cls.resource_calendar_40_hours_per_week.id,
            'company_id': cls.company.id,
            'country_id': cls.env.ref('base.au').id,
            'lang': 'en_US',
            'spouse_birthdate': datetime.today() + relativedelta(years=-25, month=1, day=1),
            'gender': 'male',
            'birthday': "1990-01-01",
            'private_email': "test%i@example.com" % i,
            'private_phone': '123456789',
            'private_street': 'My Street',
            'private_city': 'Sydney',
            'private_zip': '2000',
            "private_state_id": cls.env.ref("base.state_au_2").id,
            'private_country_id': cls.env.ref('base.au').id,
        } for i in range(cls.EMPLOYEES_COUNT)])

        cls.super_fund = cls.env['l10n_au.super.fund'].create({
            'display_name': 'Fund A',
            'abn': '2345678912',
            'address_id': cls.env['res.partner'].create({'name': "Fund A Partner"}).id,
        })

        cls.env['l10n_au.super.account'].create([{
            "employee_id": cls.employees[i].id,
            "date_from": date(2018, 12, 31),
            "fund_id": cls.super_fund.id,
        } for i in range(cls.EMPLOYEES_COUNT)])

        cls.employees[1].user_id = new_test_user(cls.env, login='employee1', groups='hr.group_hr_manager')
        cls.company.l10n_au_hr_super_responsible_id = cls.employees[1]
        cls.company.l10n_au_stp_responsible_id = cls.employees[1]

        cls.contracts = cls.env['hr.contract'].create([{
            'name': "Contract For Payslip Test %i" % i,
            'employee_id': cls.employees[i].id,
            'resource_calendar_id': cls.resource_calendar_40_hours_per_week.id,
            'company_id': cls.company.id,
            'date_generated_from': datetime(2020, 9, 1, 0, 0, 0),
            'date_generated_to': datetime(2020, 9, 1, 0, 0, 0),
            'structure_type_id': cls.env.ref('l10n_au_hr_payroll.structure_type_schedule_1').id,
            'date_start': date(2018, 12, 31),
            'wage': 10000,
            'state': "open",
        } for i in range(cls.EMPLOYEES_COUNT)])

        # Public Holiday (global)
        cls.env['resource.calendar.leaves'].create([{
            'name': "Public Holiday (global)",
            'calendar_id': cls.resource_calendar_40_hours_per_week.id,
            'company_id': cls.company.id,
            'date_from': datetime(2023, 8, 15, 5, 0, 0),
            'date_to': datetime(2023, 8, 15, 23, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': cls.env.ref('l10n_au_hr_payroll.l10n_au_work_entry_type_other').id
        }])

        # Everyone takes a legal leave the same day
        legal_leave = cls.env.ref('hr_work_entry_contract.work_entry_type_legal_leave')
        cls.env['resource.calendar.leaves'].create([{
            'name': "Legal Leave %i" % i,
            'calendar_id': cls.resource_calendar_40_hours_per_week.id,
            'company_id': cls.company.id,
            'resource_id': cls.employees[i].resource_id.id,
            'date_from': datetime(2023, 1, 2, 5, 0, 0),
            'date_to': datetime(2023, 1, 2, 23, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': legal_leave.id,
        } for i in range(cls.EMPLOYEES_COUNT)])

        # todo this most likely shouldn't be required, superstream should be optional.
        super_fund = cls.env['l10n_au.super.fund'].create({
            'display_name': 'Fund A',
            'abn': '2345678912',
            'address_id': cls.env['res.partner'].create({'name': "Fund A Partner"}).id,
        })
        cls.env['l10n_au.super.account'].create([{
            "date_from": date(2023, 6, 1),
            "employee_id": employee.id,
            "fund_id": super_fund.id
        } for employee in cls.employees])

    @users('admin')
    @warmup
    def test_performance_l10n_au_payroll_whole_flow(self):
        # Create Opening Balances
        self.company._create_ytd_values(self.employees, self.date_from)

        # Work entry generation
        self.employees.generate_work_entries(self.date_from, self.date_to)

        structure = self.env.ref('l10n_au_hr_payroll.hr_payroll_structure_au_regular')
        payslips_values = [{
            'name': "Test Payslip %i" % i,
            'employee_id': self.employees[i].id,
            'contract_id': self.contracts[i].id,
            'company_id': self.company.id,
            'struct_id': structure.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
        } for i in range(self.EMPLOYEES_COUNT)]

        # Payslip Creation
        with self.assertQueryCount(admin=1300):  # randomness
            start_time = time.time()
            payslips = self.env['hr.payslip'].with_context(allowed_company_ids=self.company.ids).create(payslips_values)
            # --- 0.11892914772033691 seconds ---
            _logger.info("Payslips Creation: --- %s seconds ---", time.time() - start_time)

        # Payslip Computation
        with self.assertQueryCount(admin=1500):  # query count patch l10n_au_hr_payroll
            start_time = time.time()
            payslips.compute_sheet()
            # --- 2.032362699508667 seconds ---
            _logger.info("Payslips Computation: --- %s seconds ---", time.time() - start_time)

        # Payslip Validation
        with self.assertQueryCount(admin=600):
            start_time = time.time()
            payslips.action_payslip_done()
            # --- 0.3815627098083496 seconds ---
            _logger.info("Payslips Validation: --- %s seconds ---", time.time() - start_time)

        # STP Submission
        with self.assertQueryCount(admin=2000):
            start_time = time.time()
            stp = payslips._get_payslip_stp()[payslips[0].id]
            self.assertTrue(stp, "The STP record should have been created when the payslip was created")
            self.assertEqual(stp.state, "draft", "The STP record should be in draft state")
            stp.submit_date = stp.submit_date or date.today()
            action = self.env['l10n_au.stp.submit'].create(
                {'l10n_au_stp_id': stp.id}
            )
            action.stp_terms = True
            action.action_submit()

            self.assertTrue(stp.xml_file, "The XML file should have been generated")
            self.assertEqual(stp.state, "sent", "The STP record should be in sent state")
            # --- 0.0 seconds ---
            _logger.info("STP Submission: --- %s seconds ---", time.time() - start_time)
