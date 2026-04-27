# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from freezegun import freeze_time

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo.tests import HttpCase, tagged, TransactionCase
from odoo.tools import file_open

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged('-at_install', 'post_install', 'payroll_dashboard_ui')
class TestDashboardUi(HttpCase):

    def test_dashboard_ui(self):
        # This test is meant to test the basic features of the dashboard
        company = self.env['res.company'].create({
            'name': 'Payroll Dashboard Company',
        })
        user = mail_new_test_user(
            self.env, name="Laurie Poiret", login="dashboarder",
            groups="base.group_user,hr_payroll.group_hr_payroll_manager",
            company_id=company.id)
        if self.env.ref('sign.group_sign_manager', raise_if_not_found=False):
            user.groups_id += self.env.ref('sign.group_sign_manager', raise_if_not_found=False)
        department = self.env['hr.department'].create({
            'name': 'Payroll',
            'company_id': company.id,
        })
        # this will make one of the action box non empty
        employee = self.env['hr.employee'].create({
            'user_id': user.id,
            'company_id': company.id,
            'department_id': department.id,
            'resource_calendar_id': company.resource_calendar_id.id,
        })
        # The test will break if sign is installed
        if self.env['ir.module.module'].search([('name', '=', 'sign'), ('state', '=', 'installed')]):
            user.groups_id += self.env.ref('sign.group_sign_manager', raise_if_not_found=False)
            with file_open('sign/static/demo/employment.pdf', "rb") as f:
                pdf_content = base64.b64encode(f.read())

            attachment = self.env['ir.attachment'].with_user(user).create({
                'type': 'binary',
                'datas': pdf_content,
                'name': 'Employment Contract.pdf',
            })
            self.env['sign.template'].with_user(user).create({
                'attachment_id': attachment.id,
                'sign_item_ids': [(6, 0, [])],
            })

        warnings = self.env['hr.payslip'].get_dashboard_warnings()
        emp_wo_contract_warn = {}
        for warning in warnings:
            if warning['string'] == "Employees Without Running Contracts":
                emp_wo_contract_warn = warning
                break
        self.assertTrue(emp_wo_contract_warn, "There should be a warning for employees without contracts")
        emp_wo_contract = self.env['hr.employee'].search(emp_wo_contract_warn['action']['domain'])
        self.assertTrue(
            employee in emp_wo_contract,
            "Laurie Poiret should appear in the list of employees without contract")

        self.env['hr.contract'].create([{
            'name': "Laurie's contract",
            'employee_id': employee.id,
            'state': 'open',
            'hr_responsible_id': self.env.user.id,
            'wage': 2000,
        }])

        warnings = self.env['hr.payslip'].get_dashboard_warnings()
        emp_wo_contract_warn = {}
        for warning in warnings:
            if warning['string'] == "Employees Without Running Contracts":
                emp_wo_contract_warn = warning
                break
        # Conditional checking as the warning might not be there depending on how other data are handled
        if warning:
            emp_wo_contract = self.env['hr.employee'].search(emp_wo_contract_warn['action']['domain'])
            self.assertFalse(
                employee in emp_wo_contract,
                "Laurie Poiret should not appear in the list of employees without contract")

        self.start_tour("/web", "payroll_dashboard_ui_tour", login='dashboarder', timeout=300)

@tagged('-at_install', 'post_install', 'payroll_dashboard')
class TestDashboard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'Dashboard Company',
        })
        cls.user = mail_new_test_user(
            cls.env, name="Laurie Poiret", login="dashboarder",
            groups="base.group_user,hr_payroll.group_hr_payroll_manager",
            company_id=cls.company.id,
        )

    def test_multi_sections(self):
        # Test that the dashboard function returns a dict with all keys, regardless of emptyness
        Payslip = self.env['hr.payslip']

        all_sections = Payslip._get_dashboard_default_sections()
        dashboard = Payslip.get_payroll_dashboard_data(all_sections)
        self.assertTrue(all(section in dashboard for section in all_sections))

        sub_sections = all_sections[1:3]
        dashboard = Payslip.get_payroll_dashboard_data(sub_sections)
        self.assertEqual(len(sub_sections), len(dashboard))
        self.assertTrue(all(section in dashboard for section in sub_sections))

    def test_dashboard_batches(self):
        # Tests the dates for batches, by default it should return
        # the batches for the last 3 'active' months ignoring
        # any month that has been skipped
        payslip_runs = self.env['hr.payslip.run'].create([
            {
                'name': 'Batch 1 - Oct',
                'date_start': '2021-10-01',
                'date_end': '2021-10-31',
                'company_id': self.company.id,
            },
            {
                'name': 'Batch 1 - Sept',
                'date_start': '2021-09-01',
                'date_end': '2021-09-30',
                'company_id': self.company.id,
            },
            {
                'name': 'Batch 2 - Sept',
                'date_start': '2021-09-01',
                'date_end': '2021-09-30',
                'company_id': self.company.id,
            },
            {
                'name': 'Batch 1 - June',
                'date_start': '2021-06-01',
                'date_end': '2021-06-30',
                'company_id': self.company.id,
            },
            {
                'name': 'Batch 1 - May',
                'date_start': '2021-05-01',
                'date_end': '2021-05-31',
                'company_id': self.company.id,
            },
        ])
        with freeze_time(date(2021, 12, 31)):
            batches_to_return = payslip_runs.filtered(lambda r: r.date_start.month >= 6)
            dashboard = self.env['hr.payslip'].with_user(self.user).get_payroll_dashboard_data(sections=['batches'])
            self.assertTrue('batches' in dashboard)
            self.assertEqual(len(dashboard['batches']), len(batches_to_return))
            self.assertEqual(set(read['id'] for read in dashboard['batches']), set(batches_to_return.ids))

    def test_dashboard_empty_stats(self):
        # Tests that when stats are empty they are tagged as sample
        dashboard = self.env['hr.payslip'].with_user(self.user).get_payroll_dashboard_data(sections=['stats'])
        self.assertTrue(all(stats['is_sample'] is True for stats in dashboard['stats']))

    def _test_dashboard_stats(self):
        # Tests that the result inside of the stats dashboard is somewhat coherent
        emp_1, emp_2, emp_3 = self.env['hr.employee'].create([
            {'name': 'Employee 1', 'company_id': self.company.id},
            {'name': 'Employee 2', 'company_id': self.company.id},
            {'name': 'Employee 3', 'company_id': self.company.id}
        ])
        today = date.today()
        self.env['hr.contract'].create([
            {
                'name': 'Contract 1',
                'employee_id': emp_1.id,
                'date_start': today - relativedelta(months=1, day=1),
                'state': 'open',
                'wage': 1000,
                'company_id': self.company.id,
            },
            {
                'name': 'Contract 2',
                'employee_id': emp_2.id,
                'date_start': today - relativedelta(day=1),
                'state': 'open',
                'wage': 2000,
                'company_id': self.company.id,
            },
            {
                'name': 'Contract 3',
                'employee_id': emp_3.id,
                'date_start': today + relativedelta(months=1, day=1),
                'state': 'open',
                'wage': 4500,
                'company_id': self.company.id,
            }
        ])
        self.env['hr.employee'].flush_model()
        self.env['hr.contract'].flush_model()

        dashboard = self.env['hr.payslip'].with_user(self.user).get_payroll_dashboard_data(sections=['stats'])
        # Identify the different sections
        employer_cost = employees = None
        for section in dashboard['stats']:
            if section['id'] == 'employer_cost':
                employer_cost = section
            elif section['id'] == 'employees':
                employees = section
        self.assertTrue(all([employer_cost, employees]))

        # Check employees monthly
        # Employees contains the number of unique employees that worked on that period
        employees_stat = employees['data']['monthly']
        self.assertEqual(employees_stat[0]['value'], 1)
        self.assertEqual(employees_stat[1]['value'], 2)
        self.assertEqual(employees_stat[2]['value'], 3)

        # Check yearly employees outside the function as the assertions are dependent on the freeze time date
        return employees['data']['yearly']

    def test_dashboard_stat_end_of_year(self):
        # Tests the dashboard at the end of a year
        with freeze_time(date(2021, 12, 1)):
            employees_stat = self._test_dashboard_stats()
            self.assertEqual(employees_stat[0]['value'], 0)
            self.assertEqual(employees_stat[1]['value'], 2)
            self.assertEqual(employees_stat[2]['value'], 3)

    def test_dashboard_stat_start_of_year(self):
        # Tests the dashboard again but at the start of a year
        with freeze_time(date(2021, 1, 1)):
            employees_stat = self._test_dashboard_stats()
            self.assertEqual(employees_stat[0]['value'], 1)
            self.assertEqual(employees_stat[1]['value'], 3)
            self.assertEqual(employees_stat[2]['value'], 3)

    def test_dashboard_stat_middle_of_year(self):
        # Tests the dashboard again but at the middle of the year
        with freeze_time(date(2021, 6, 1)):
            employees_stat = self._test_dashboard_stats()
            self.assertEqual(employees_stat[0]['value'], 0)
            self.assertEqual(employees_stat[1]['value'], 3)
            self.assertEqual(employees_stat[2]['value'], 3)

    def test_dashboard_no_english_language_access(self):
        # Tests that we can access the dashboard when we don't have english language active
        Payslip = self.env['hr.payslip']
        # We remove english from every model of the app that needed it to get french as main and unique language
        self.env['res.lang']._activate_lang('fr_FR')
        fr_lang = self.env['res.lang'].search([['code', '=', 'fr_FR']])
        if 'website' in self.env:
            self.env['website'].search([]).write({'language_ids': fr_lang.ids, 'default_lang_id': fr_lang.id})
        self.env['res.users'].with_context(active_test=False).search([]).write({'lang' : 'fr_FR'})
        self.env['res.partner'].search([]).write({'lang' : 'fr_FR'})

        self.env['res.lang'].search([['code', '=', 'en_US']]).active = False

        # We only test that we won't receive a traceback when we don't have access to the english language
        # The normal flow of the functions are tested above
        Payslip.get_payroll_dashboard_data()
        Payslip.get_dashboard_warnings()
