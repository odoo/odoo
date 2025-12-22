# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.addons.base.models.ir_qweb import QWebException

from odoo.addons.mail.tests.common import mail_new_test_user

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
        with self.assertRaises(QWebException):  # CacheMiss followed by AccessError
            self.env['ir.actions.report'].with_user(self.res_users_hr_officer).with_company(
                self.company_1
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

    def test_read_manager_employee(self):
        # UserB should be able to read its manager's record - without being connected
        # on company A
        self.employee_a.with_user(self.user_b).with_company(self.company_b).name

        self.employee_b.with_user(self.user_a).with_company(self.company_a).name

        # UserB should not be able to read other employees in that company
        with self.assertRaises(AccessError):
            self.employee_other_a.with_user(self.user_b).with_company(self.company_b).name

    def test_read_no_manager_company(self):
        self.employee_b.parent_id = False

        with self.assertRaises(AccessError):
            self.employee_a.with_user(self.user_b).name
