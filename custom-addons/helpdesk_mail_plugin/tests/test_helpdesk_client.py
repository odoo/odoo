# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.addons.mail_plugin.tests.common import TestMailPluginControllerCommon, mock_auth_method_outlook
from odoo.addons.mail.tests.common import MailCase


class TestHelpdeskClient(TestMailPluginControllerCommon, MailCase):
    @mock_auth_method_outlook('employee')
    def test_ticket_creation_notification(self):
        """Test the ticket creation using the mail plugin endpoint.

        Test that the ticket is created, with the
        - name set with the email subject
        - description set with the email body
        - user set with the current logged user

        Check also that the acknowledgement email has been sent.
        """
        self.user_test.groups_id |= self.env.ref('helpdesk.group_helpdesk_user')
        customer = self.env['res.partner'].create({'name': 'Customer', 'email': 'customer@example.com'})

        email_body = 'Test email body'
        email_subject = 'Test email subject'

        messages_info = [{
            'content': 'The reference for your ticket is',
            'message_type': 'auto_comment',
            'subtype': 'mail.mt_note',
            'email_values': {
                'email_from': self.env.company.email_formatted,
            },
            'notif': [{'partner': customer, 'type': 'email', 'status': 'sent'}],
        }, {
            'content': '',
            'message_type': 'notification',
            'email_values': {
                'email_from': self.env.company.email_formatted,
            },
            'subtype': 'helpdesk.mt_ticket_new',
            'notif': [],
        }]

        with self.assertPostNotifications(messages_info):
            ticket_id = self.make_jsonrpc_request('/mail_plugin/ticket/create', {
                'email_body': email_body,
                'email_subject': email_subject,
                'partner_id': customer.id,
            }).get('ticket_id')
            self.env['mail.mail'].process_email_queue()

        self.assertTrue(bool(ticket_id))

        ticket = self.env['helpdesk.ticket'].browse(ticket_id)

        self.assertTrue(bool(ticket))
        self.assertIn(email_body, ticket.description)
        self.assertEqual(ticket.name, email_subject)
        self.assertEqual(ticket.user_id, self.user_test)
