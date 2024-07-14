# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from freezegun import freeze_time
from dateutil.relativedelta import relativedelta

from odoo.addons.mail.tests.common import mail_new_test_user

from odoo.tests.common import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestLinkExpirationDate(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.offer_date = datetime.date(2022, 1, 14)
        cls.validity_period = 7
        cls.fail_text = 'This link is invalid. Please contact the HR Responsible to get a new one...'

        cls.structure_type = cls.env['hr.payroll.structure.type'].create({'name': 'struct'})
        cls.job = cls.env['hr.job'].create({
            'name': 'Familiar job',
        })

    def test_link_for_applicant(self):
        """
        Applicant should be able to access salary configurator before the link Expires.
        After the link expiration date, applicant should be redirected to the invalid link page.
        """
        offer_template = self.env['hr.contract'].create({
            'name': "Contract",
            'wage': 6500,
            'structure_type_id': self.structure_type.id,
            'job_id': self.job.id,
        })
        applicant = self.env['hr.applicant'].create({'name': 'Guillermo De La Cruz, wanna be a Vampire', 'partner_name': 'Guillermo De La Cruz'})
        applicant_wizard = self.env['generate.simulation.link'].with_context(default_applicant_id=applicant).new({
            'validity': self.validity_period,
            'contract_id': offer_template.id,
        })

        with freeze_time(self.offer_date):
            applicant_wizard.action_send_offer()
            offer = applicant.salary_offer_ids
            url = f'/salary_package/simulation/offer/{offer.id}?token={offer.access_token}'
            res = self.url_open(url)
        self.assertTrue(self.fail_text not in str(res.content), "The applicant should not be redirected to the invalid link page")

        with freeze_time(self.offer_date + relativedelta(days=(self.validity_period + 1))):
            late_res = self.url_open(url)
        self.assertTrue(self.fail_text in str(late_res.content), 'The applicant should be redirected to the invalid link page')

    def test_link_for_employee(self):
        simple_user = mail_new_test_user(
            self.env,
            name='Nandor Relentless',
            login='Al Qolnidar',
            email='Nandor@odoo.com',
            groups='base.group_user',
        )
        employee = self.env['hr.employee'].create({'name': "Nandor", 'user_id': simple_user.id})
        employee_contract = self.env['hr.contract'].create({
            'name': "Contract",
            'employee_id': employee.id,
            'wage': 6500,
            'structure_type_id': self.structure_type.id,
            'job_id': self.job.id,
        })
        employee_wizard = self.env['generate.simulation.link'].with_context(default_employee_contract_id=employee_contract).new({
            'validity': self.validity_period,
            'contract_id': employee_contract.id,
        })

        with freeze_time(self.offer_date):
            employee_wizard.action_send_offer()
            offer = employee_contract.salary_offer_ids
            url = f'/salary_package/simulation/offer/{offer.id}'
            self.authenticate(simple_user.login, simple_user.login)
            res = self.url_open(url)
        self.assertTrue(self.fail_text not in str(res.content), "The Employee should not be redirected to the invalid link page")

        with freeze_time(self.offer_date + relativedelta(days=(self.validity_period + 1))):
            self.authenticate(simple_user.login, simple_user.login)
            late_res = self.url_open(url)
        self.assertTrue(self.fail_text in str(late_res.content), 'The Employee should be redirected to the invalid link page')

    def test_applicant_with_archived_contract(self):
        applicant = self.env['hr.applicant'].create({
            'name': 'demo',
            'partner_name': 'demo',
        })

        applicant_contract = self.env['hr.contract'].create({
            'name': "Contract",
            'applicant_id': applicant.id,
            'wage': 6500,
            'structure_type_id': self.structure_type.id,
            'job_id': self.job.id,
        })

        applicant_contract.copy({
            'active': False,
        })

        proposed_contract = applicant.action_show_proposed_contracts()

        self.assertEqual(applicant.proposed_contracts_count, 1)
        self.assertEqual(proposed_contract.get('views'), [[False, 'form']])
        self.assertEqual(proposed_contract.get('res_id'), applicant_contract.id)
