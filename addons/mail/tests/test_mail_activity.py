from freezegun import freeze_time

from odoo.tests import tagged, HttpCase
from odoo import fields


@tagged("mail_activity", "-at_install", "post_install")
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

    def test_activity_schedule_on_invoice(self):
        partner = self.env['res.partner'].create({'name': 'Activity Test Partner'})

        account = self.env['account.account'].create({
                'name': 'Test Income Account',
                'code': 'T1000',
                'account_type': 'income',
                'reconcile': True,
            })

        journal = self.env['account.journal'].create({
            'name': 'Test Sales Journal',
            'type': 'sale',
            'code': 'TSA',
            'autocheck_on_post': False,
        })

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'journal_id': journal.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': 'Product A',
                'quantity': 1,
                'price_unit': 100,
                'account_id': account.id,
            })],
        })

        move.action_post()
