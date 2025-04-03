from freezegun import freeze_time

from odoo.tests import tagged, HttpCase


@tagged("-at_install", "post_install")
class TestMailActivityChatter(HttpCase):

    def test_mail_activity_schedule_from_chatter(self):
        testuser = self.env['res.users'].create({
            'email': 'testuser@testuser.com',
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
        })
        self.start_tour(
            f"/odoo/res.partner/{testuser.partner_id.id}",
            "mail_activity_schedule_from_chatter",
            login="admin",
        )

    def test_mail_activity_date_format(self):
        with freeze_time("2024-1-1 09:00:00 AM"):
            LANG_CODE = "en_US"
            self.env = self.env(context={"lang": LANG_CODE})
            testuser = self.env['res.users'].create({
                "email": "testuser@testuser.com",
                "name": "Test User",
                "login": "testuser",
                "password": "testuser",
            })
            lang = self.env["res.lang"].search([('code', '=', LANG_CODE)])
            lang.date_format = "%d/%b/%y"
            lang.time_format = "%I:%M:%S %p"

            self.start_tour(
                f"/web#id={testuser.partner_id.id}&model=res.partner",
                "mail_activity_date_format",
                login="admin",
            )
