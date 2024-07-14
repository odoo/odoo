# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user


class TestHrAppraisalRequest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.manager_user = new_test_user(cls.env, login='Lucky Luke', name='Manager Tiranique')
        cls.manager = cls.env['hr.employee'].create({
            'name': 'Manager Tiranique',
            'user_id': cls.manager_user.id,
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
