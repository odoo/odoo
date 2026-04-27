# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user
from odoo.addons.mail.tests.common import MockEmail


class TestHrAppraisalRequest(TransactionCase, MockEmail):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.manager_2_user = new_test_user(cls.env, login='Averell Dalton', name='Averell Dalton')
        cls.manager_2 = cls.env['hr.employee'].create({
            'name': 'Averell Dalton',
            'user_id': cls.manager_2_user.id,
        })
        cls.manager_3_user = new_test_user(cls.env, login='Angus Dalton', name='Angus Dalton')
        cls.manager_3 = cls.env['hr.employee'].create({
            'name': 'Angus Dalton',
            'user_id': cls.manager_3_user.id,
        })
        cls.manager_user = new_test_user(cls.env, login='Lucky Luke', name='Manager Tiranique')
        cls.manager = cls.env['hr.employee'].create({
            'name': 'Manager Tiranique',
            'user_id': cls.manager_user.id,
            'parent_id': cls.manager_2.id,
        })
        cls.employee_user = new_test_user(cls.env, login='Rantanplan', name='Michaël Hawkins')
        cls.employee = cls.env['hr.employee'].create({
            'name': "Michaël Hawkins",
            'parent_id': cls.manager.id,
            'work_email': 'michael@odoo.com',
            'user_id': cls.employee_user.id,
        })
        cls.employee.work_email = 'chouxblanc@donc.com'

    def request_appraisal_from(self, record, user):
        """ An appraisal can be requested from appraisal form only """
        return self.env['request.appraisal'] \
            .with_user(user) \
            .with_context({'default_appraisal_id': record.id}) \
            .create({})

    def test_manager_simple_request(self):
        """ Manager requests an appraisal for one of his employee """
        appraisal = self.env['hr.appraisal'].create({'employee_id': self.employee.id, 'manager_ids': self.employee.parent_id})
        request = self.request_appraisal_from(appraisal, user=self.manager_user)
        self.assertEqual(request.employee_id, self.employee)
        self.assertEqual(request.recipient_ids, self.employee_user.partner_id, "It should be sent to the employee user's partner")
        request.action_invite()

    def test_manager_request_work_email(self):
        """ Send appraisal to work email """
        self.employee.user_id = False
        appraisal = self.env['hr.appraisal'].create({'employee_id': self.employee.id, 'manager_ids': self.employee.parent_id})
        request = self.request_appraisal_from(appraisal, user=self.manager_user)
        self.assertEqual(request.recipient_ids.email, self.employee.work_email)
        self.assertEqual(request.recipient_ids.name, self.employee.name)
        request.action_invite()

    def test_manager_request_work_email_2(self):
        """ Send appraisal to work email """
        self.employee.user_id = False
        self.employee.work_contact_id = False
        appraisal = self.env['hr.appraisal'].create({'employee_id': self.employee.id, 'manager_ids': self.employee.parent_id})
        request = self.request_appraisal_from(appraisal, user=self.manager_user)
        self.assertEqual(request.recipient_ids.email, self.employee.work_email)

    def test_manager_request_himself(self):
        """ Send appraisal to only manager if HR asks for himself
            Employee sends an appraisal request to it's manager
            For appraisal manager_ids needs to be explicitly set
        """
        appraisal = self.env['hr.appraisal'].create({'employee_id': self.employee.id, 'manager_ids': self.employee.parent_id})
        request = self.request_appraisal_from(appraisal, user=self.employee_user)
        self.assertEqual(request.recipient_ids, self.manager_user.partner_id)

    def test_manager_activity(self):
        """ Check that appraisal request mail is posted in chatter"""
        appraisal = self.env['hr.appraisal'].create({'employee_id': self.employee.id, 'manager_ids': self.employee.parent_id})
        rest_message_ids = appraisal.message_ids
        request = self.request_appraisal_from(appraisal, user=self.manager_user)
        request.body = "My awesome message"
        request.action_invite()
        message_ids = appraisal.message_ids - rest_message_ids
        self.assertEqual(len(message_ids), 1, "Request mail has not been posted")
        self.assertEqual(message_ids.email_from, self.manager_user.email_formatted, "The mail of a sender wrong")
        self.assertTrue("<p>My awesome message</p>" in message_ids.body)

    def test_employee_simple_request(self):
        """ Employee requests an appraisal from his manager """
        appraisal = self.env['hr.appraisal'].create({'employee_id': self.employee.id, 'manager_ids': self.employee.parent_id})
        request = self.request_appraisal_from(appraisal, user=self.employee_user)
        self.assertEqual(request.employee_id, self.employee)
        self.assertEqual(request.recipient_ids, self.manager_user.partner_id, "It should be sent to the manager's partner")
        request.action_invite()

    def test_custom_body(self):
        """ Custom body should be sent """
        appraisal = self.env['hr.appraisal'].create({'employee_id': self.employee.id, 'manager_ids': self.employee.parent_id})
        request = self.request_appraisal_from(appraisal, user=self.employee_user)
        request.body = "My awesome message"
        request.action_invite()
        notification = self.env['mail.message'].search([
            ('model', '=', appraisal._name),
            ('res_id', '=', appraisal.id),
            ('message_type', '=', 'comment'),
        ])
        self.assertTrue("<p>My awesome message</p>" in notification.body)

    def test_compute_can_request_appraisal(self):
        self.employee.with_user(self.manager_2_user)._compute_can_request_appraisal()
        # Check the appraisal request rights
        self.assertTrue(self.employee.can_request_appraisal)

        self.employee.with_user(self.manager_3_user)._compute_can_request_appraisal()
        # Check the appraisal request rights
        self.assertFalse(self.employee.can_request_appraisal)

    def test_user_body(self):
        """ user body should be sent """
        appraisal = self.env['hr.appraisal'].create({'employee_id': self.employee.id, 'manager_ids': self.employee.parent_id})
        request = self.request_appraisal_from(appraisal, user=self.employee_user)
        request.user_body = "Hello World !"
        request.action_invite()
        notification = self.env['mail.message'].search([
            ('model', '=', appraisal._name),
            ('res_id', '=', appraisal.id),
            ('message_type', '=', 'comment'),
        ])
        self.assertTrue("<p>Hello World !</p>" in notification.body)

    def test_user_mail_render_security(self):
        appraisal = self.env['hr.appraisal'].create({'employee_id': self.employee.id, 'manager_ids': self.employee.parent_id})
        request_as_employee = self.request_appraisal_from(appraisal, user=self.employee_user)
        request_as_template_editor = request_as_employee.with_env(self.env)

        # The employee can change the body of its appraisal
        request_as_employee.body = 'Hello'
        # As long as it doesn't contain sensitive placeholders
        with self.assertRaisesRegex(AccessError, 'Only members of Mail Template Editor'):
            request_as_employee.body = '<t t-out="object.sudo().name"/>'
        # The employee cannot change the template to an arbitrary template
        with self.assertRaisesRegex(ValidationError, 'Appraisal for Michaël Hawkins should be using'):
            with self.env.cr.savepoint():
                request_as_employee.template_id = self.env['mail.template'].search([], limit=1)

        # A mail template editor can put sensitive placeholders
        request_as_template_editor.body = '<t t-out="object.sudo().employee_id.name"/>'

        # The employee must be able to render the body even if the body contain sensible placeholders
        # put by the template or a template editor
        with self.mock_mail_gateway():
            request_as_employee.action_invite()

        self.assertMailMailWRecord(
            appraisal,
            [appraisal.manager_ids.user_partner_id],
            'sent',
            author=appraisal.employee_id.user_partner_id,
            email_values={'body_content': f"<p>{self.employee.name}</p>"},
        )
