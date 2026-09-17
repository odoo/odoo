# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.hr.tests.common import TestHrCommon
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.fields import Command
from odoo.tests import tagged

from odoo.exceptions import AccessError


class TestMultiCompanyReport(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_1 = cls.env['res.company'].create({'name': 'Opoo'})
        cls.company_2 = cls.env['res.company'].create({'name': 'Otoo'})
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

        cls.company_a = cls.env['res.company'].create({'name': 'Company A'})
        cls.company_b = cls.env['res.company'].create({'name': 'Company B'})

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

    def test_read_no_manager_company(self):
        self.employee_b.parent_id = False

        with self.assertRaises(AccessError):
            self.employee_a.with_user(self.user_b).name

    def test_manager_cannot_access_employee_from_inactive_company(self):
        """
        A manager cannot have access to their subordinate if they are in a
        different company. Otherwise bugs may appear when accessing
        company-limited fields of the employee (e.g.: their resource)
        """
        current_company = self.env['res.company'].create({'name': 'Scenic company'})
        other_company = self.env['res.company'].create({'name': 'Cringe company'})

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
            'account_number': 'BE12345678901234',
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
            'account_number': 'BE99999999999999',
            'partner_id': partner.id,
            'company_id': self.company_b.id,
        })

        ctx = {'allowed_company_ids': [self.company_a.id, self.company_b.id]}
        account_unlinked = account_unlinked.with_context(ctx)

        # Fallback must pick the candidate of the matching company (company_b)
        self.assertEqual(account_unlinked.employee_id, employee_b)

    def test_user_can_access_own_employee_from_inactive_company(self):
        """
        A user must be able to read their own employee record even if it belongs
        to a company that is not currently active in their session (e.g., for avatars).
        """
        self.user_a.write({'group_ids': [Command.link(self.env.ref('hr.group_hr_user').id)]})
        emp_a_comp_b = self.employee_a.with_user(self.user_a).with_context(allowed_company_ids=[self.company_b.id])
        emp_other_comp_b = self.employee_other_a.with_user(self.user_a).with_context(allowed_company_ids=[self.company_b.id])

        try:
            emp_a_comp_b.check_access('read')
        except AccessError:
            self.fail("User should be able to read their own employee record across companies.")

        with self.assertRaises(
                AccessError, msg="A user cannot access other employees if they are not in a selected company"
        ):
            emp_other_comp_b.check_access('read')
