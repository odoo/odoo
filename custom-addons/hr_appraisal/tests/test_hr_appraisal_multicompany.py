# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, new_test_user


class TestHrAppraisal(TransactionCase):
    """ Test used to check that appraisal works in multicompany."""

    @classmethod
    def setUpClass(cls):
        super(TestHrAppraisal, cls).setUpClass()
        cls.HrEmployee = cls.env['hr.employee']
        cls.HrAppraisal = cls.env['hr.appraisal']
        cls.main_company = cls.env['res.company'].create({'name': 'main'})
        cls.other_company = cls.env['res.company'].create({'name': 'other'})

        cls.env['ir.config_parameter'].sudo().set_param("hr_appraisal.appraisal_create_in_advance_days", 8)

        cls.user = new_test_user(cls.env, login='My super login', groups='hr_appraisal.group_hr_appraisal_user',
                                  company_ids=[(6, 0, (cls.main_company | cls.other_company).ids)], company_id=cls.main_company.id)

        cls.hr_employee = cls.HrEmployee.create(dict(
            name="Michael Hawkins",
            user_id=cls.user.id,
            create_date=date.today() - relativedelta(months=3),
            last_appraisal_date=date.today() - relativedelta(months=3),
            company_id=cls.main_company.id,
        ))

        cls.hr_employee2 = cls.HrEmployee.create(dict(
            user_id=cls.user.id,
            company_id=cls.other_company.id,
            create_date=date.today() - relativedelta(months=6, days=6),
            last_appraisal_date=date.today() - relativedelta(months=6, days=6),
        ))

    def test_hr_appraisal(self):
        # I create a new Employee with appraisal configuration.
        appraisal_count = self.env['hr.appraisal'].search_count
        self.assertEqual(appraisal_count([('employee_id', '=', self.hr_employee.id)]), 0)
        self.assertEqual(appraisal_count([('employee_id', '=', self.hr_employee2.id)]), 0)

        self.hr_employee2.next_appraisal_date = date.today()
        self.env['res.company']._run_employee_appraisal_plans()
        self.assertEqual(appraisal_count([('employee_id', '=', self.hr_employee.id)]), 0)
        self.assertEqual(appraisal_count([('employee_id', '=', self.hr_employee2.id)]), 1)

        self.assertEqual(self.env['hr.appraisal'].search([('employee_id', '=', self.hr_employee2.id)]).company_id.id, self.other_company.id)
        self.assertEqual(self.user.with_company(company=self.other_company.id).next_appraisal_date, self.hr_employee2.next_appraisal_date)
