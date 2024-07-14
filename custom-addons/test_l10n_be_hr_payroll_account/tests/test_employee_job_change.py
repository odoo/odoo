# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from freezegun import freeze_time

from odoo import fields
import odoo.tests
from . import common


@odoo.tests.tagged('-at_install', 'post_install', 'salary')
class TestEmployeeJobChange(common.TestPayrollAccountCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['hr.job'].create({
            'name': 'Senior Developer BE',
            'company_id': cls.company_id.id,
            'default_contract_id': cls.senior_dev_contract.id,
            'l10n_be_contract_ip': True,
        })
        partner = cls.env['res.partner'].create({
            'name': 'Jean Jasse',
            'street': 'La rue, 15',
            'city': 'Brussels',
            'country_id': cls.env.ref('base.be').id,
            'zip': '0348',
            'lang': 'en_US',
            'phone': '+32 2 290 34 90',
            'email': 'jeanjasse@doublehelice.be',
        })
        work_contact = cls.env['res.partner'].sudo().create({
            'email': 'jeanjasse@doublehelice.be',
            'mobile': '+32 2 290 34 90',
            'name': 'Jean Jasse',
            'company_id': cls.company_id.id,
        })
        bank_ing = cls.env['res.bank'].create({
            'name': 'ING',
            'bic': 'BBRUBEBB'
        })
        account = cls.env['res.partner.bank'].create({
            'acc_number': 'BE02151804051200',
            'bank_id': bank_ing.id,
            'partner_id': partner.id,
            'company_id': cls.company_id.id,
        })
        employee = cls.env['hr.employee'].create({
            'name': 'Jean Jasse',
            'company_id': cls.company_id.id,
            'country_id': cls.env.ref('base.be').id,
            'bank_account_id': account.id,
            'gender': 'male',
            'children': 0,
            'km_home_work': 0,
            'place_of_birth': 'Charleroi',
            'country_of_birth': cls.env.ref('base.be').id,
            'birthday': fields.Date.from_string('1988-05-10'),
            'identification_id': '11.11.11-111.11',
            'certificate': 'master',
            'study_school': 'UCL',
            'study_field': 'Civil Engineering',
            'work_contact_id': work_contact.id,
            'work_email': 'jeanjasse@doublehelice.be',
            'l10n_be_scale_seniority': 1,
            'emergency_contact': 'Caballero',
            'emergency_phone': '+32 2 290 34 90',
            'private_street': 'La rue, 15',
            'private_city': 'Brussels',
            'private_country_id': cls.env.ref('base.be').id,
            'private_zip': '0348',
            'private_phone': '+32 2 290 34 90',
            'private_email': 'jeanjasse@doublehelice.be',
            'lang': 'en_US',
            'id_card': cls.pdf_content,
        })
        cls.env['res.users'].create({
            'create_employee_id': employee.id,
            'employee_id': employee.id,
            'name': employee.name,
            'email': 'jeanjasse@doublehelice.be',
            'login': 'jeanjasse',
            'password': 'jeanjasse',
            'company_id': cls.company_id.id,
            'company_ids': cls.company_id.ids,
        })
        contract = cls.env['hr.contract'].create({
            'name': "Jean Jasse's old contract",
            'employee_id': employee.id,
            'company_id': cls.company_id.id,
            'wage': 3000,
            'hr_responsible_id': cls.env.ref('base.user_admin').id,
            'default_contract_id': cls.new_dev_contract.id,
            'sign_template_id': cls.template.id,
            'ip_wage_rate': 25,
            'internet': 0,
            'date_start': datetime.date(2015, 1, 1),
        })
        contract.write({'state': 'open'})
        cls.env.flush_all()

    def test_employee_job_change(self):
        # This test checks if an employee changing jobs while staying in the company correctly gets
        # the values of the new job instead of the values of the old one.
        # This test also ensure that every required values that can be prefilled using the
        # employee's data is indeed prefilled.
        with freeze_time("2022-01-01"):
            self.start_tour("/", 'hr_contract_salary_tour_job_change', login='admin')
        job_changing_employee = self.env['hr.employee'].search([('name', '=', 'Jean Jasse')])
        new_contract = self.env['hr.contract'].search([
            ('employee_id', '=', job_changing_employee.id),
            ('state', '=', 'draft'),
        ])
        self.assertTrue(job_changing_employee.active, 'Employee is active')
        self.assertTrue(new_contract.ip, 'The new contract should have an IP')
        self.assertEqual(new_contract.ip_wage_rate, 50, 'The new contract should have an ip_wage_rate of 50')
