# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged, HttpCase


@tagged("-at_install", "post_install")
class TestMailActivityChatter(HttpCase):

    def test_chatter_activity_tour(self):
        testuser = self.env['res.users'].create({
            'email': 'testuser@testuser.com',
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
        })
        self.start_tour(
            f"/web#id={testuser.partner_id.id}&model=res.partner",
            "mail_activity_schedule_from_chatter",
            login="admin",
        )
