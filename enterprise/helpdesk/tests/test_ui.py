# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

import odoo.tests
from .common import HelpdeskCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase, HelpdeskCommon):
    def test_ui(self):
        self.start_tour("/odoo", 'helpdesk_tour', login="admin")

    def test_helpdesk_ticket_on_portal_ui(self):
        self.test_team.privacy_visibility = 'portal'
        self.test_team.message_subscribe(partner_ids=[self.helpdesk_portal.partner_id.id])
        self.env['helpdesk.ticket'].create({
            'name': 'lamp stand',
            'team_id': self.test_team.id,
        })
        self.start_tour('/odoo', 'helpdesk_search_ticket_on_portal_tour', login=self.helpdesk_portal.login)
