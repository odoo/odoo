# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import time

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo.tests.common import tagged
from odoo.addons.test_l10n_ch_hr_payroll_account.tests.common import TestL10NChHrPayrollAccountCommon
from odoo.tests.common import users, warmup

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install', 'ch_payroll_perf')
class TestPerformance(TestL10NChHrPayrollAccountCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='ch'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.EMPLOYEES_COUNT = 100

        cls.date_from = date(2023, 1, 1)
        cls.date_to = date(2023, 1, 31)

        cls.addresses = cls.env['res.partner'].create([{
            'name': "Test Private Address %i" % i,
            'company_id': cls.company.id,
            'street': 'Brussels Street',
            'city': 'Brussels',
            'zip': '2928',
            'country_id': cls.env.ref('base.be').id,
        } for i in range(cls.EMPLOYEES_COUNT)])

        cls.employees = cls.env['hr.employee'].create([{
            'name': "Test Employee %i" % i,
            'work_contact_id': cls.addresses[i].id,
            'resource_calendar_id': cls.resource_calendar_40_hours_per_week.id,
            'company_id': cls.company.id,
            'l10n_ch_canton': 'FR',
            'country_id': cls.env.ref('base.ch').id,
            'lang': 'en_US',
            'l10n_ch_tax_scale': 'A',
            'l10n_ch_sv_as_number': '756.1848.4786.64',
            'l10n_ch_marital_from': datetime.today() + relativedelta(years=-1, month=1, day=1),
            'l10n_ch_spouse_sv_as_number': '756.6549.9078.26',
            'spouse_birthdate': datetime.today() + relativedelta(years=-25, month=1, day=1),
            'l10n_ch_spouse_work_canton': 'BE',
            'l10n_ch_spouse_work_start_date': datetime.today() + relativedelta(years=-3),
            'l10n_ch_municipality': '351',
            'certificate': 'higherEducationMaster',
            'gender': 'male',
        } for i in range(cls.EMPLOYEES_COUNT)])

        cls.contracts = cls.env['hr.contract'].create([{
            'name': "Contract For Payslip Test %i" % i,
            'employee_id': cls.employees[i].id,
            'resource_calendar_id': cls.resource_calendar_40_hours_per_week.id,
            'company_id': cls.company.id,
            'date_generated_from': datetime(2020, 9, 1, 0, 0, 0),
            'date_generated_to': datetime(2020, 9, 1, 0, 0, 0),
            'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id,
            'date_start': date(2018, 12, 31),
            'wage': 10000,
            'state': "open",
            'l10n_ch_social_insurance_id': cls.social_insurance.id,
            'l10n_ch_accident_insurance_line_id': cls.accident_insurance.line_ids.id,
            'l10n_ch_additional_accident_insurance_line_ids': [(4, cls.additional_accident_insurance.line_ids.id)],
            'l10n_ch_sickness_insurance_line_ids': [(4, cls.sickness_insurance.line_ids.id)],
            'l10n_ch_lpp_insurance_id': cls.lpp_insurance.id,
            'l10n_ch_compensation_fund_id': cls.compensation_fund.id,
            'l10n_ch_thirteen_month': True,
        } for i in range(cls.EMPLOYEES_COUNT)])

        # Public Holiday (global)
        cls.env['resource.calendar.leaves'].create([{
            'name': "Public Holiday (global)",
            'calendar_id': cls.resource_calendar_40_hours_per_week.id,
            'company_id': cls.company.id,
            'date_from': datetime(2020, 9, 22, 5, 0, 0),
            'date_to': datetime(2020, 9, 22, 23, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': cls.env.ref('l10n_ch_hr_payroll.work_entry_type_bank_holiday').id
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

    @users('admin')
    @warmup
    def test_performance_l10n_ch_payroll_whole_flow(self):
        # Work entry generation
        self.employees.generate_work_entries(self.date_from, self.date_to)

        structure = self.env.ref('l10n_ch_hr_payroll.hr_payroll_structure_ch_employee_salary')
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
        with self.assertQueryCount(admin=946):  # randomness
            start_time = time.time()
            payslips = self.env['hr.payslip'].with_context(allowed_company_ids=self.company.ids).create(payslips_values)
            # --- 0.11892914772033691 seconds ---
            _logger.info("Payslips Creation: --- %s seconds ---", time.time() - start_time)

        # Payslip Computation
        with self.assertQueryCount(admin=876):
            start_time = time.time()
            with self.profile():
                payslips.compute_sheet()
            # --- 2.032362699508667 seconds ---
            _logger.info("Payslips Computation: --- %s seconds ---", time.time() - start_time)

        # Payslip Validation
        with self.assertQueryCount(admin=370):  # l10n adds some queries
            start_time = time.time()
            payslips.action_payslip_done()
            # --- 0.3815627098083496 seconds ---
            _logger.info("Payslips Validation: --- %s seconds ---", time.time() - start_time)
