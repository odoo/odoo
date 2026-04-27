# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import HelpdeskCommon
from odoo.addons.mail.tests.common import mail_new_test_user


class TestHelpdeskTeamPrivacyVisibility(HelpdeskCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.portal_user = mail_new_test_user(
            cls.env,
            name='helpdesk_portal',
            login='helpdesk_portal',
            email='helpdesk@portal.com',
            notification_type='email',
            groups='base.group_portal',
        )
        cls.user_partner = cls.env['res.partner'].with_context({'mail_create_nolog': True}).create({
            'name': 'helpdesk_user',
            'email': 'helpdesk@user.com',
            'company_id': False,
            'user_ids': [cls.helpdesk_user.id],
        })
        cls.portal_partner = cls.env['res.partner'].with_context({'mail_create_nolog': True}).create({
            'name': 'helpdesk_portal',
            'email': 'helpdesk@portal.com',
            'company_id': False,
            'user_ids': [cls.portal_user.id],
        })

        cls.ticket = cls.env['helpdesk.ticket'].create({
                'name': 'Test Ticket',
                'team_id': cls.test_team.id,
                'stage_id': cls.stage_new.id,
                'user_id': None,
        })

    def search_test_team_with_user(self, user):
        return self.env['helpdesk.team'].with_user(user).search([('id', '=', self.test_team.id)])

    def search_test_ticket_with_user(self, user):
        return self.env['helpdesk.ticket'].with_user(user).search([('id', '=', self.ticket.id)])

    def test_helpdesk_team_visibility_invited_internal(self):
        self.test_team.privacy_visibility = 'invited_internal'

        self.assertTrue(self.search_test_team_with_user(self.helpdesk_manager), "A Helpdesk > Admin should see the team.")
        self.assertFalse(self.search_test_team_with_user(self.helpdesk_user), "An uninvited Helpdesk > User should not see the team.")
        self.assertFalse(self.search_test_ticket_with_user(self.portal_user), "A Portal User should not see the team's tickets.")

        self.test_team.message_subscribe(partner_ids=[self.user_partner.id])

        self.assertTrue(self.search_test_team_with_user(self.helpdesk_user), "A Helpdesk > User following the team should see it.")
        self.assertTrue(self.search_test_ticket_with_user(self.helpdesk_user), "A Helpdesk > User following the team should see its tickets.")

        self.test_team.message_unsubscribe([self.user_partner.id])
        self.ticket.message_subscribe([self.user_partner.id])

        self.assertTrue(self.search_test_ticket_with_user(self.helpdesk_user), "A Helpdesk > User following the ticket should see it.")

    def test_helpdesk_team_visibility_internal(self):
        self.test_team.privacy_visibility = 'internal'

        self.assertTrue(self.search_test_team_with_user(self.helpdesk_manager), "A Helpdesk > Admin should see the team.")
        self.assertTrue(self.search_test_team_with_user(self.helpdesk_user), "A Helpdesk > User should see the team.")
        self.assertFalse(self.search_test_ticket_with_user(self.portal_user), "A Portal User should not see the team's tickets.")

        self.test_team.message_subscribe(partner_ids=[self.portal_partner.id])

        self.assertFalse(self.search_test_ticket_with_user(self.portal_user), "A Portal User following a team without the portal visibility should not see its tickets.")

        self.test_team.message_unsubscribe([self.portal_partner.id])
        self.ticket.message_subscribe([self.portal_partner.id])

        self.assertFalse(self.search_test_ticket_with_user(self.portal_user), "A Portal User following a ticket in a team without the portal visibility should not see it.")

    def test_helpdesk_team_visibility_portal(self):
        self.test_team.privacy_visibility = 'portal'

        self.assertTrue(self.search_test_team_with_user(self.helpdesk_manager), "A Helpdesk > Admin should see the team.")
        self.assertTrue(self.search_test_team_with_user(self.helpdesk_user), "A Helpdesk > User should see the team.")
        self.assertFalse(self.search_test_ticket_with_user(self.portal_user), "An uninvited Portal User should not see the team's tickets.")

        self.test_team.message_subscribe(partner_ids=[self.portal_partner.id])

        self.assertTrue(self.search_test_ticket_with_user(self.portal_user), "A Portal User following the team should see its tickets.")

        self.test_team.message_unsubscribe([self.portal_partner.id])
        self.ticket.message_subscribe([self.portal_partner.id])

        self.assertTrue(self.search_test_ticket_with_user(self.portal_user), "A Portal User following the ticket should see it.")
