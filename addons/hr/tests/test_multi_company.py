# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC, date, datetime
from unittest.mock import patch

from odoo.addons.hr.models.hr_version import HrVersion
from odoo.addons.hr.tests.common import TestHrCommon
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import Form, HttpCase, freeze_time, tagged
from odoo.tests.common import TransactionCase
from odoo.fields import Command
from odoo.exceptions import AccessError, ValidationError


class TestMultiCompanyReport(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_1 = cls.add_class_company('base.test_company', {'name': 'Opoo'})
        cls.company_2 = cls.add_class_company('base.test_company_with_branch', {'name': 'Otoo'})
        cls.employees = cls.env['hr.employee'].create([
            {'name': 'Bidule', 'company_id': cls.company_1.id},
            {'name': 'Machin', 'company_id': cls.company_2.id},
        ])
        cls.res_users_hr_officer.company_ids = [
            (4, cls.company_1.id),
            (4, cls.company_2.id),
        ]
        cls.res_users_hr_officer.company_id = cls.company_1.id
        # flush and invalidate the cache, otherwise a full cache may prevent
        # access rights to be checked
        cls.env.flush_all()
        cls.env.invalidate_all()

    def test_multi_company_report(self):
        content, _ = self.env['ir.actions.report'].with_user(self.res_users_hr_officer).with_context(
            allowed_company_ids=[self.company_1.id, self.company_2.id]
        )._render_qweb_pdf('hr.hr_employee_print_badge', res_ids=self.employees.ids)
        self.assertIn(b'Bidule', content)
        self.assertIn(b'Machin', content)

    def test_single_company_report(self):
        with self.assertRaises(AccessError):  # CacheMiss followed by AccessError
            self.env['ir.actions.report'].with_user(self.res_users_hr_officer).with_context(
                allowed_company_ids=self.company_1.ids,
            )._render_qweb_pdf('hr.hr_employee_print_badge', res_ids=self.employees.ids)


class TestMultiCompany(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_a = cls.add_class_company('base.test_company', {'name': 'Company A'})
        cls.company_b = cls.add_class_company('base.test_company_with_branch', {'name': 'Company B'})

        cls.user_a = mail_new_test_user(cls.env, login='user_a', company_id=cls.company_a.id, company_ids=(cls.company_a | cls.company_b).ids)
        cls.user_b = mail_new_test_user(cls.env, login='user_b', company_id=cls.company_b.id)

        cls.employee_a = cls.env['hr.employee'].create({
            'name': 'Employee A',
            'company_id': cls.company_a.id,
            'user_id': cls.user_a.id,
        })

        cls.employee_other_a = cls.env['hr.employee'].create({
            'name': 'Employee Other A',
            'company_id': cls.company_a.id,
        })

        cls.employee_b = cls.env['hr.employee'].create({
            'name': 'Employee B',
            'company_id': cls.company_b.id,
            'user_id': cls.user_b.id,
            'parent_id': cls.employee_a.id,
        })

        cls.employee_other_b = cls.env['hr.employee'].create({
            'name': 'Employee Other B',
            'company_id': cls.company_b.id,
        })

        cls.env.flush_all()
        cls.env.invalidate_all()

    def test_manager_cannot_access_employee_from_inactive_company(self):
        """
        A manager cannot have access to their subordinate if they are in a
        different company. Otherwise bugs may appear when accessing
        company-limited fields of the employee (e.g.: their resource)
        """
        current_company = self.add_company('base.test_company_template', {'name': 'Scenic company'})
        other_company = self.add_company('base.test_company_template2', {'name': 'Cringe company'})

        manager_user = mail_new_test_user(
            self.env, groups="hr.group_hr_user", login='manager_user',
            company_id=current_company.id, company_ids=current_company.ids,
        )

        manager_employee = self.env['hr.employee'].create({
            'name': 'Manager employee',
            'company_id': current_company.id,
            'user_id': manager_user.id,
        })
        employee_same_company, employee_other_company = self.env['hr.employee'].create([
            {
                'name': 'Employee same company',
                'company_id': current_company.id,
                'parent_id': manager_employee.id,
            },
            {
                'name': 'Employee other company',
                'company_id': other_company.id,
                'parent_id': manager_employee.id,
            },
        ])

        # employee managed by user and in the same company, we should have access
        employee_same_company.with_user(manager_user).check_access('read')

        with self.assertRaises(
            AccessError, msg="A manager cannot access their subordinates if they are not in a selected company",
        ):
            employee_other_company.with_user(manager_user).check_access('read')

    def test_unavailable_intervals_employee_from_inactive_company(self):
        """ The gantt views list the employees of all the companies of the user to users without
        access to the employees (they are read through hr.employee.public): their unavailability
        is computed whatever the active companies, without reading their resource as the user. """
        self.employee_other_b.contract_date_start = date(2026, 1, 1)
        self.env.flush_all()
        self.env.invalidate_all()

        start = datetime(2026, 11, 2, tzinfo=UTC)  # a Monday
        stop = datetime(2026, 11, 9, tzinfo=UTC)
        unavailabilities = self.env['hr.employee'].with_user(self.user_a).with_context(
            allowed_company_ids=self.company_a.ids,
        ).browse(self.employee_other_b.id)._get_employee_unavailable_intervals(start, stop)
        self.assertEqual(
            unavailabilities[self.employee_other_b.id],
            [{'start': datetime(2026, 11, 7, tzinfo=UTC), 'stop': stop}],
            "the working schedule of the employee is used: only the weekend is unavailable",
        )

    def test_bank_account_multi_company_linked_same_company(self):
        """
        Ensure bank.employee_id and employee_salary_amount resolve to the employee
        who has the account in bank_account_ids and belongs to the same company.
        """
        self.env.user.company_ids |= self.company_b

        # Shared partner between two employees across companies
        partner = self.env['res.partner'].create({'name': 'Shared Partner'})
        employee_a = self.env['hr.employee'].create({
            'name': 'Employee A',
            'company_id': self.company_a.id,
            'work_contact_id': partner.id,
        })
        employee_b = self.env['hr.employee'].create({
            'name': 'Employee B',
            'company_id': self.company_b.id,
            'work_contact_id': partner.id,
        })

        # Bank accounts matching each employee's company
        account_a = self.env['res.partner.bank'].create({
            'account_number': 'BE68539007547034',
            'partner_id': partner.id,
            'company_id': self.company_a.id,
        })
        account_b = self.env['res.partner.bank'].create({
            'account_number': 'BE71096123456769',
            'partner_id': partner.id,
            'company_id': self.company_b.id,
        })

        # Link each bank account to its respective employee
        employee_a.bank_account_ids = [Command.link(account_a.id)]
        employee_b.bank_account_ids = [Command.link(account_b.id)]

        # Simulate user having both companies active in the switcher
        ctx = {'allowed_company_ids': [self.company_a.id, self.company_b.id]}
        account_a = account_a.with_context(ctx)
        account_b = account_b.with_context(ctx)

        # Verify each account resolves to the correct employee and receives 100% allocation
        self.assertEqual(account_a.employee_id, employee_a)
        self.assertEqual(account_b.employee_id, employee_b)
        self.assertEqual(account_a.employee_salary_amount, 100)
        self.assertEqual(account_b.employee_salary_amount, 100)

    def test_bank_account_multi_company_linked_mismatched_company(self):
        """
        Ensure bank.employee_id still resolves to the linking employee even if
        the bank account has a mismatched historical company_id.
        """
        self.env.user.company_ids |= self.company_b

        partner = self.env['res.partner'].create({'name': 'Shared Partner'})
        employee_b = self.env['hr.employee'].create({
            'name': 'Employee B',
            'company_id': self.company_b.id,
            'work_contact_id': partner.id,
        })

        # Historical account created under company_a
        account_old = self.env['res.partner.bank'].create({
            'account_number': 'BE07345678901234',
            'partner_id': partner.id,
            'company_id': self.company_a.id,
        })

        # Account is explicitly linked to employee in company_b
        employee_b.bank_account_ids = [Command.link(account_old.id)]

        ctx = {'allowed_company_ids': [self.company_a.id, self.company_b.id]}
        account_old = account_old.with_context(ctx)

        # Best-effort resolution must prioritize the explicit link over company mismatch
        self.assertEqual(account_old.employee_id, employee_b)

    def test_bank_account_multi_company_unlinked_fallback(self):
        """
        Ensure bank.employee_id falls back to the employee matching the account company
        when the bank account is not yet linked to any employee's bank_account_ids.
        """
        self.env.user.company_ids |= self.company_b

        partner = self.env['res.partner'].create({'name': 'Shared Partner'})
        self.env['hr.employee'].create({
            'name': 'Employee A',
            'company_id': self.company_a.id,
            'work_contact_id': partner.id,
        })
        employee_b = self.env['hr.employee'].create({
            'name': 'Employee B',
            'company_id': self.company_b.id,
            'work_contact_id': partner.id,
        })

        # New account belonging to company_b, not yet linked in bank_account_ids
        account_unlinked = self.env['res.partner.bank'].create({
            'account_number': 'BE89999999999999',
            'partner_id': partner.id,
            'company_id': self.company_b.id,
        })

        ctx = {'allowed_company_ids': [self.company_a.id, self.company_b.id]}
        account_unlinked = account_unlinked.with_context(ctx)

        # Fallback must pick the candidate of the matching company (company_b)
        self.assertEqual(account_unlinked.employee_id, employee_b)

    def test_shared_calendar_write_other_company(self):
        """A working schedule used by employees of an unselected company cannot be edited."""
        calendar = self.env['resource.calendar'].create({'name': 'Shared calendar', 'company_id': False})
        (self.employee_a | self.employee_b).resource_calendar_id = calendar

        with self.assertRaises(ValidationError):
            calendar.with_context(allowed_company_ids=self.company_a.ids).write({'calendar_type': 'variable'})
        self.assertEqual(calendar.calendar_type, 'fixed')

        calendar.with_context(allowed_company_ids=(self.company_a | self.company_b).ids).write({'calendar_type': 'variable'})
        self.assertEqual(calendar.calendar_type, 'variable')

    def test_child_ids_multi_company(self):
        self.res_users_hr_officer.write({
            'company_ids': [(4, self.company_a.id), (4, self.company_b.id)],
            'company_id': self.company_a.id,
        })
        manager_as_officer = self.employee_a.with_user(self.res_users_hr_officer)
        self.assertFalse(
            manager_as_officer.with_context(allowed_company_ids=self.company_a.ids).child_ids,
            "Subordinates in companies the user cannot access should be hidden",
        )
        self.assertEqual(
            manager_as_officer.with_context(allowed_company_ids=(self.company_a | self.company_b).ids).child_ids,
            self.employee_b,
        )

    def test_search_child_ids_multi_company(self):
        self.res_users_hr_officer.write({
            'company_ids': [(4, self.company_a.id), (4, self.company_b.id)],
            'company_id': self.company_a.id,
        })
        Employee = self.env['hr.employee'].with_user(self.res_users_hr_officer)
        any_domain = [('child_ids', 'any', [('company_id', '=', self.company_b.id)])]
        in_domain = [('child_ids', 'in', self.employee_b.ids)]

        employee_company_a = Employee.with_context(allowed_company_ids=self.company_a.ids)
        self.assertFalse(
            employee_company_a.search(any_domain),
            "Subordinates in companies the user cannot access should not be searchable",
        )
        self.assertFalse(employee_company_a.search(in_domain))

        employee_all_companies = Employee.with_context(allowed_company_ids=(self.company_a | self.company_b).ids)
        self.assertEqual(employee_all_companies.search(any_domain), self.employee_a)
        self.assertEqual(employee_all_companies.search(in_domain), self.employee_a)


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
        self.assertFalse(self.employee.work_contact_id.company_id, "The work contact is shared between the companies")

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
        self.assertFalse(self.employee.work_contact_id.company_id, "The work contact is shared between both companies")

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

    def test_move_to_company_branch_of_the_same_employer(self):
        # a branch of the same legal employer (same root company): the contract goes on, only a new version of the
        # branch starts on the effective date
        branch_a = self.env['res.company'].create({'name': 'Branch A', 'parent_id': self.company_a.id})
        version_branch = self.employee._move_to_company(branch_a, date(2026, 12, 1))
        self.assertEqual(version_branch.date_version, date(2026, 12, 1))
        self.assertEqual(version_branch.company_id, branch_a)
        self.assertEqual(version_branch.contract_date_start, date(2024, 1, 1), "The contract goes on")
        self.assertFalse(version_branch.contract_date_end)
        self.assertFalse(self.version_a.contract_date_end, "The contract of the old company doesn't end")
        self.assertEqual(self.version_a.company_id, self.company_a)

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

    def test_move_to_company_user_conflict(self):
        user = mail_new_test_user(self.env, login='company_change_user', groups='base.group_user',
            company_id=self.company_a.id, company_ids=(self.company_a | self.company_b).ids)
        self.employee.user_id = user
        self.env['hr.employee'].create({'name': 'Same User B', 'company_id': self.company_b.id, 'user_id': user.id})
        with self.assertRaises(ValidationError):
            self.employee._move_to_company(self.company_b, date(2026, 12, 1))
        with self.assertRaises(ValidationError):
            self.employee.write({'company_id': self.company_b.id})

    def test_move_to_company_user_conflict_cron(self):
        # the conflict appears after the move is planned: the daily cron must not fail
        user = mail_new_test_user(self.env, login='company_change_user', groups='base.group_user',
            company_id=self.company_a.id, company_ids=(self.company_a | self.company_b).ids)
        self.employee.user_id = user
        self.employee._move_to_company(self.company_b, date(2026, 12, 1))
        self.env['hr.employee'].create({'name': 'Same User B', 'company_id': self.company_b.id, 'user_id': user.id})
        with freeze_time('2026-12-01'), self.assertLogs('odoo.addons.hr.models.hr_employee', level='WARNING') as logs:
            self.env['hr.employee']._cron_update_current_version_id()
            self.env.flush_all()
        self.assertEqual(self.employee.company_id, self.company_a)
        self.assertIn("its user is already linked to an employee there", logs.output[0])

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
        self.assertTrue(employee_b.work_contact_id.display_name, "The new company can read the work contact")

    def test_moved_employee_resource_access(self):
        employee_b = self.env['hr.employee'].create({'name': 'Employee B', 'company_id': self.company_b.id})
        self.employee._move_to_company(self.company_b, date(2026, 12, 1))
        self.assertEqual(self.employee.resource_id.company_id, self.company_a)

        resources_b = self.env['resource.resource'].with_user(self.hr_officer).with_context(allowed_company_ids=self.company_b.ids)
        resources_b.browse(self.employee.resource_id.id).check_access('read')
        self.assertTrue(resources_b.browse(self.employee.resource_id.id).calendar_id.name,
            "The working schedule of the resource is readable from the companies of the versions")
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
