# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from unittest.mock import patch

from odoo.tests import Form, HttpCase, freeze_time, tagged
from odoo.tests.common import TransactionCase

from odoo.addons.hr.models.hr_version import HrVersion
from odoo.addons.mail.tests.common import mail_new_test_user


class TestEmployeeCompanyChangeCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a, cls.company_b = cls.env['res.company'].create([
            {'name': 'Company A', 'tz': 'Europe/Brussels'},
            {'name': 'Company B', 'tz': 'America/New_York'},
        ])
        cls.calendar_b = cls.env['resource.calendar'].create({
            'name': 'Company B Calendar',
            'company_id': cls.company_b.id,
        })
        cls.company_b.resource_calendar_id = cls.calendar_b
        cls.department_a = cls.env['hr.department'].create({'name': 'Department A', 'company_id': cls.company_a.id})
        cls.job_a = cls.env['hr.job'].create({'name': 'Developer', 'company_id': cls.company_a.id})
        cls.hr_officer = mail_new_test_user(
            cls.env,
            login='company_change_hr_officer',
            groups='base.group_user,hr.group_hr_user',
            company_id=cls.company_a.id,
            company_ids=(cls.company_a | cls.company_b).ids,
        )
        cls.employee = cls.env['hr.employee'].with_company(cls.company_a).create({
            'name': 'Moving Employee',
            'company_id': cls.company_a.id,
            'date_version': date(2024, 1, 1),
            'contract_date_start': date(2024, 1, 1),
            'department_id': cls.department_a.id,
            'job_id': cls.job_a.id,
            'tz': 'Europe/Brussels',
        })
        cls.version_a = cls.employee.version_id


@tagged('post_install', '-at_install')
@freeze_time('2026-11-24')
class TestEmployeeCompanyChange(TestEmployeeCompanyChangeCommon):

    def test_change_company_moves_all_versions(self):
        version_2025 = self.employee.create_version({'date_version': date(2025, 1, 1)})
        self.assertFalse(self.employee.action_change_company(self.company_b.id))

        self.employee.write({'company_id': self.company_b.id})

        self.assertEqual(self.employee.company_id, self.company_b)
        self.assertEqual(self.employee.resource_id.company_id, self.company_b)
        self.assertEqual(version_2025.company_id, self.company_b)
        self.assertFalse(version_2025.department_id)
        self.assertFalse(version_2025.job_id)
        self.assertEqual(version_2025.resource_calendar_id, self.calendar_b)
        self.assertEqual(version_2025.tz, 'America/New_York')
        self.assertEqual(version_2025.address_id, self.company_b.partner_id, "The address of the old company is replaced by the one of the new company")
        self.assertEqual(self.version_a.company_id, self.company_b, "Without payslips, all the versions are moved")
        self.assertFalse(self.version_a.department_id)

    def test_change_company_in_old_company_context(self):
        # the employee is moved while the context still only allows the old company
        employee = self.employee.with_context(allowed_company_ids=self.company_a.ids)
        version_2025 = employee.create_version({'date_version': date(2025, 1, 1)})
        employee.write({'company_id': self.company_b.id})
        self.assertEqual(employee.version_id, version_2025)
        self.assertEqual(employee.company_id, self.company_b)

    def test_change_company_with_company_dependent_values(self):
        department_b = self.env['hr.department'].create({'name': 'Department B', 'company_id': self.company_b.id})
        self.employee.write({'company_id': self.company_b.id, 'department_id': department_b.id})
        self.assertEqual(self.employee.version_id.department_id, department_b)

    def test_move_to_company_in_the_future(self):
        version_b = self.employee._move_to_company(self.company_b, date(2026, 12, 1))

        self.assertEqual(self.version_a.contract_date_end, date(2026, 11, 30))
        self.assertEqual(version_b.date_version, date(2026, 12, 1))
        self.assertEqual(version_b.company_id, self.company_b)
        self.assertEqual(version_b.contract_date_start, date(2026, 12, 1))
        self.assertFalse(version_b.contract_date_end)
        self.assertFalse(version_b.department_id)
        self.assertEqual(version_b.resource_calendar_id, self.calendar_b)
        self.assertEqual(self.employee.current_version_id, self.version_a)
        self.assertEqual(self.employee.company_id, self.company_a)

        with freeze_time('2026-12-01'):
            self.env['hr.employee']._cron_update_current_version_id()
            self.assertEqual(self.employee.current_version_id, version_b)
            self.assertEqual(self.employee.company_id, self.company_b)
            self.assertEqual(self.employee.resource_id.company_id, self.company_b)

    def test_move_to_company_with_work_location(self):
        address_b = self.env['res.partner'].create({'name': 'Office B Address', 'company_id': self.company_b.id})
        office_b = self.env['hr.work.location'].create({
            'name': 'Office B',
            'company_id': self.company_b.id,
            'address_id': address_b.id,
            'location_type': 'office',
        })
        version_b = self.employee._move_to_company(self.company_b, date(2026, 12, 1))
        self.assertEqual(version_b.work_location_id, office_b)
        self.assertEqual(version_b.address_id, address_b)
        self.assertEqual(self.version_a.address_id, self.company_a.partner_id)

    def test_move_to_company_in_the_past(self):
        version_b = self.employee._move_to_company(self.company_b, date(2026, 11, 1))
        self.assertEqual(self.employee.current_version_id, version_b)
        self.assertEqual(self.employee.company_id, self.company_b)
        self.assertEqual(self.version_a.contract_date_end, date(2026, 10, 31))

    def test_move_to_company_wizard(self):
        self.version_a.contract_date_end = date(2026, 12, 31)
        wizard = Form(self.env['hr.employee.company.change.wizard'].with_context(
            default_version_id=self.version_a.id,
            default_company_id=self.company_b.id,
        ))
        self.assertEqual(wizard.date_version, date(2027, 1, 1), "The default date is the day after the contract end")
        wizard.save().action_confirm()

        version_b = self.employee.version_ids.filtered(lambda v: v.company_id == self.company_b)
        self.assertEqual(version_b.date_version, date(2027, 1, 1))
        self.assertEqual(version_b.contract_date_start, date(2027, 1, 1))
        self.assertEqual(self.version_a.contract_date_end, date(2026, 12, 31))

    def test_moved_employee_visibility(self):
        version_b = self.employee._move_to_company(self.company_b, date(2026, 11, 1))
        employees_a = self.env['hr.employee'].with_user(self.hr_officer).with_context(allowed_company_ids=self.company_a.ids)
        employees_b = self.env['hr.employee'].with_user(self.hr_officer).with_context(allowed_company_ids=self.company_b.ids)
        action_domain = [
            '|', ('company_id', 'in', self.company_a.ids), ('version_company_ids', 'in', self.company_a.ids),
        ]

        self.assertEqual(employees_a.search(action_domain), self.employee, "The old company still sees the employee")
        employee_a = employees_a.browse(self.employee.id)
        self.assertEqual(employee_a.version_id, self.version_a)
        self.assertEqual(employee_a.department_id, self.department_a)
        self.assertEqual(employee_a.version_ids, self.version_a, "Only the versions of company A are visible")

        employee_b = employees_b.browse(self.employee.id)
        self.assertEqual(employee_b.version_id, version_b)
        self.assertEqual(employee_b.version_ids, version_b)

    def test_moved_employee_resource_access(self):
        employee_b = self.env['hr.employee'].create({'name': 'Employee B', 'company_id': self.company_b.id})
        self.employee._move_to_company(self.company_b, date(2026, 12, 1))
        self.assertEqual(self.employee.resource_id.company_id, self.company_a)

        resources_b = self.env['resource.resource'].with_user(self.hr_officer).with_context(allowed_company_ids=self.company_b.ids)
        resources_b.browse(self.employee.resource_id.id).check_access('read')
        self.assertIn(self.employee.resource_id, resources_b.search([]))

        resources_a = self.env['resource.resource'].with_user(self.hr_officer).with_context(allowed_company_ids=self.company_a.ids)
        self.assertNotIn(employee_b.resource_id, resources_a.search([]))

    def test_moved_employee_public_visibility(self):
        self.employee._move_to_company(self.company_b, date(2026, 11, 1))
        internal_user = mail_new_test_user(
            self.env,
            login='company_change_internal_user',
            groups='base.group_user',
            company_id=self.company_a.id,
            company_ids=(self.company_a | self.company_b).ids,
        )
        action_domain = [
            '|', ('company_id', 'in', self.company_a.ids), ('version_company_ids', 'in', self.company_a.ids),
        ]
        employees = self.env['hr.employee'].with_user(internal_user).with_context(allowed_company_ids=self.company_a.ids)
        self.assertNotIn(self.employee, employees.search(action_domain),
            "The directory only shows the employees of their current company")


@tagged('post_install', '-at_install')
class TestEmployeeCompanyChangeUi(TestEmployeeCompanyChangeCommon, HttpCase):

    def _start_company_change_tour(self, tour):
        # admin: moving an employee may write payroll fields of the localizations (e.g. Belgian Dimona)
        admin = self.env.ref('base.user_admin')
        admin.company_ids = [(4, self.company_a.id), (4, self.company_b.id)]
        self.start_tour(
            f"/odoo/employees/{self.employee.id}",
            tour,
            login=admin.login,
            cookies={'cids': f"{self.company_a.id}-{self.company_b.id}"},
        )

    def test_change_company_tour(self):
        self._start_company_change_tour('hr_employee_company_change_tour')
        self.assertEqual(self.employee.company_id, self.company_b)
        self.assertEqual(len(self.employee.version_ids), 1)

    def test_move_to_company_tour(self):
        # payslips until the end of October 2026
        def _get_company_change_date(version):
            return date(2026, 11, 1) if version.date_version < date(2026, 11, 1) else False

        with patch.object(HrVersion, '_get_company_change_date', _get_company_change_date):
            self._start_company_change_tour('hr_employee_company_move_tour')
        version_b = self.employee.version_ids.filtered(lambda v: v.company_id == self.company_b)
        self.assertEqual(version_b.date_version, date(2026, 11, 1))
        self.assertEqual(self.version_a.company_id, self.company_a)
