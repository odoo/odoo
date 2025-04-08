from odoo.addons.hr.tests.common import TestHrCommon
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import tagged


@tagged('post_install', '-at_install', 'mail_flow')
class TestHrEmployeeMail(TestHrCommon, MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_template_employee = cls.env['mail.template'].with_user(cls.user_admin).create({
            'auto_delete': True,
            'body_html': '<p>Hello <t t-out="object.name"/></p>',
            'email_from': '{{ object.user_id.email_formatted or user.email_formatted or "" }}',
            'model_id': cls.env['ir.model']._get_id('hr.employee'),
            'name': 'Test Hr Template',
            'subject': 'Test {{ object.name }}',
            'use_default_to': True,
        })
        # note: email and phone are user related fields
        cls.test_employee = cls.env['hr.employee'].create([
            {
                'company_id': cls.company_admin.id,
                'country_id': cls.env.ref('base.be').id,
                'name': 'QuickEmployee',
                'work_email': 'quick.employee@test.example.com',
                'work_phone': '+32455001122',
            },
        ])

    def test_assert_initial_values(self):
        self.assertTrue(self.test_employee.work_contact_id)
        self.assertFalse(self.test_employee.message_partner_ids)
        self.assertFalse(self.test_employee.email)
        self.assertFalse(self.test_employee.phone)
        self.assertFalse(self.test_employee.user_id)

    def test_employee_get_default_recipients(self):
        employee = self.test_employee.with_user(self.res_users_hr_officer)
        defaults = employee._message_get_default_recipients()
        self.assertDictEqual(
            defaults[employee.id],
            {'email_cc': '', 'email_to': '', 'partner_ids': self.test_employee.work_contact_id.ids},
        )

    def test_employee_get_suggested_recipients(self):
        employee = self.test_employee.with_user(self.res_users_hr_officer)
        suggested = employee._message_get_suggested_recipients()
        self.assertListEqual(suggested, [
            {
                'create_values': {},
                'email': self.test_employee.work_contact_id.email_normalized,
                'name': self.test_employee.work_contact_id.name,
                'partner_id': self.test_employee.work_contact_id.id,
            },
        ])

    def test_employee_template(self):
        employee, template = self.test_employee.with_user(self.res_users_hr_officer), self.test_template_employee.with_user(self.res_users_hr_officer)
        message = employee.message_post_with_source(
            template,
            message_type='comment',
            subtype_id=self.env.ref('mail.mt_comment').id,
        )
        self.assertEqual(
            message.notified_partner_ids, self.test_employee.work_contact_id,
            'Matches suggested recipients',
        )
