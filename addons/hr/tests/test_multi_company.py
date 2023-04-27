# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.addons.hr.tests.common import TestHrCommon
from odoo.addons.base.models.qweb import QWebException


class TestMultiCompany(TestHrCommon):

    def setUp(self):
        super().setUp()
        self.company_1 = self.env['res.company'].create({'name': 'Opoo'})
        self.company_2 = self.env['res.company'].create({'name': 'Otoo'})
        self.employees = self.env['hr.employee'].create([
            {'name': 'Bidule', 'company_id': self.company_1.id},
            {'name': 'Machin', 'company_id': self.company_2.id},
        ])
        self.res_users_hr_officer.company_ids = [
            (4, self.company_1.id),
            (4, self.company_2.id),
        ]
        self.res_users_hr_officer.company_id = self.company_1.id

    def test_multi_company_report(self):
        content, content_type = self.env.ref('hr.hr_employee_print_badge').with_user(self.res_users_hr_officer).with_context(
            allowed_company_ids=[self.company_1.id, self.company_2.id]
        )._render_qweb_pdf(res_ids=self.employees.ids)
        self.assertIn(b'Bidule', content)
        self.assertIn(b'Machin', content)

    def test_single_company_report(self):
        with self.assertRaises(QWebException):  # CacheMiss followed by AccessError
            content, content_type = self.env.ref('hr.hr_employee_print_badge').with_user(self.res_users_hr_officer).with_company(
                self.company_1
            )._render_qweb_pdf(res_ids=self.employees.ids)
