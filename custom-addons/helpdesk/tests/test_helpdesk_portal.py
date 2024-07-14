# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests.common import HttpCase
from .common import HelpdeskCommon


class TestHelpdeskPortal(HttpCase, HelpdeskCommon):
    def test_customer_closure(self):
        self.test_team.allow_portal_ticket_closing = True
        self.test_team.privacy_visibility = 'portal'

        portal_user = mail_new_test_user(
            self.env,
            name='helpdesk_portal',
            login='helpdesk_portal',
            email='helpdesk@portal.com',
            groups='base.group_portal',
        )

        ticket = self.env['helpdesk.ticket'].create({
                'name': 'Test Ticket',
                'team_id': self.test_team.id,
                'stage_id': self.stage_new.id,
                'user_id': self.helpdesk_user.id,
        })

        self.assertFalse(ticket.closed_by_partner, 'The ticket should not be closed by the customer.')

        self.authenticate(portal_user.login, portal_user.login)
        response = self.url_open(f"/my/ticket/close/{ticket.id}/{ticket.access_token}")

        self.assertEqual(response.status_code, 200, 'The request should be successful.')
        self.assertTrue(ticket.closed_by_partner, 'The ticket should be closed by the customer.')
        self.assertEqual(ticket.stage_id, self.stage_done, 'The ticket should be moved to the Done stage.')
