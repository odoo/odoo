# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import Command
from odoo.tests import HttpCase, freeze_time, tagged

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged('post_install', '-at_install')
@freeze_time('2026-10-22')
class TestCompanyTransfer(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env['res.company'].create({'name': 'Company A'})
        cls.company_b = cls.env['res.company'].create({'name': 'Company B'})
        cls.calendar_b = cls.env['resource.calendar'].create({
            'name': 'Company B Calendar',
            'company_id': cls.company_b.id,
        })
        cls.company_b.resource_calendar_id = cls.calendar_b
        cls.company_a.tz = 'Europe/Brussels'
        cls.company_b.tz = 'America/New_York'
        cls.user = mail_new_test_user(
            cls.env,
            login='transferred_user',
            company_id=cls.company_a.id,
            company_ids=cls.company_a.ids,
        )

    def _create_employee(self, **vals):
        return self.env['hr.employee'].with_company(self.company_a).create({
            'name': 'Transferred Employee',
            'company_id': self.company_a.id,
            **vals,
        })

    def _get_new_employee(self, action):
        return self.env['hr.employee'].browse(action['res_id'])

    def test_duplicate_employee(self):
        job = self.env['hr.job'].create({'name': 'Developer', 'company_id': self.company_a.id})
        employee = self._create_employee(
            user_id=self.user.id,
            contract_date_start=date(2024, 1, 1),
            job_id=job.id,
            tz='Europe/Brussels',
        )
        new_employee = self._get_new_employee(employee.action_duplicate_employee(self.company_b.id))

        self.assertEqual(new_employee.name, employee.name)
        self.assertEqual(new_employee.company_id, self.company_b)
        self.assertEqual(new_employee.resource_calendar_id, self.calendar_b)
        self.assertFalse(new_employee.job_title)
        self.assertEqual(new_employee.tz, 'America/New_York')
        self.assertEqual(new_employee.resource_id.tz, 'America/New_York')
        self.assertEqual(new_employee.contract_date_start, date(2026, 10, 22))
        self.assertFalse(new_employee.user_id, "The user should only be moved when archiving")
        self.assertTrue(employee.active)
        self.assertEqual(employee.user_id, self.user)

    def test_duplicate_employee_without_contract(self):
        employee = self._create_employee()
        new_employee = self._get_new_employee(employee.action_duplicate_employee(self.company_b.id))
        self.assertFalse(new_employee.contract_date_start)
        self.assertFalse(new_employee.is_in_contract)

    def test_duplicate_and_archive_employee_moves_user(self):
        employee = self._create_employee(user_id=self.user.id)
        new_employee = self._get_new_employee(
            employee.action_duplicate_and_archive_employee(self.company_b.id))

        self.assertFalse(employee.active)
        self.assertFalse(employee.user_id)
        self.assertEqual(new_employee.user_id, self.user)
        self.assertTrue(self.user.active)
        self.assertIn(self.company_b, self.user.company_ids)

    def test_duplicate_and_archive_employee_in_contract(self):
        employee = self._create_employee(
            user_id=self.user.id,
            contract_date_start=date(2024, 1, 1),
        )
        new_employee = self._get_new_employee(
            employee.action_duplicate_and_archive_employee(self.company_b.id))

        self.assertFalse(employee.active)
        self.assertTrue(employee.departure_id)
        self.assertEqual(new_employee.user_id, self.user)
        self.assertTrue(self.user.active, "The user is still linked to an active employee")
        self.assertTrue(new_employee.is_in_contract)


@tagged('post_install', '-at_install')
class TestCompanyTransferUi(HttpCase):

    def test_company_transfer_tour(self):
        company_a, company_b = self.env['res.company'].create([
            {'name': 'Transfer Company A'},
            {'name': 'Transfer Company B'},
        ])
        admin = self.env.ref('base.user_admin')
        admin.company_ids = [Command.link(company_a.id), Command.link(company_b.id)]
        admin.company_id = company_a
        employee = self.env['hr.employee'].create({
            'name': 'Tour Transferred Employee',
            'company_id': company_a.id,
        })

        self.start_tour(
            f"/odoo/employees/{employee.id}",
            'hr_employee_company_transfer_tour',
            login='admin',
            cookies={'cids': f"{company_a.id}-{company_b.id}"},
        )

        self.assertFalse(employee.active)
        new_employee = self.env['hr.employee'].search([
            ('name', '=', 'Tour Transferred Employee'),
            ('company_id', '=', company_b.id),
        ])
        self.assertEqual(len(new_employee), 1)
