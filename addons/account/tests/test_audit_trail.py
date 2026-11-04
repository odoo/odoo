from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged, new_test_user


@tagged('post_install', '-at_install')
class TestAuditTrail(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env['base'].with_context(
            tracking_disable=False,
            mail_create_nolog=False,
            mail_notrack=False,
        ).env
        cls.env.company.check_account_audit_trail = True
        cls.move = cls.create_move()

    @classmethod
    def create_move(cls):
        return cls.env['account.move'].create({
            'date': '2021-04-01',
            'line_ids': [
                Command.create({
                    'balance': 100,
                    'account_id': cls.company_data['default_account_revenue'].id
                }),
                Command.create({
                    'balance': -100,
                    'account_id': cls.company_data['default_account_revenue'].id
                }),
            ],
        })

    def get_trail(self, move):
        self.env.cr.precommit.run()
        return self.env['mail.message'].search([
            ('model', '=', 'account.move'),
            ('res_id', '=', move.id),
        ])

    def assertTrail(self, trail, expected):
        self.assertEqual(len(trail), len(expected))
        for message, expected in zip(trail, expected[::-1]):
            self.assertIn(expected, message.account_audit_log_preview)

    def test_can_unlink_draft(self):
        self.move.unlink()

    def test_cant_unlink_posted(self):
        self.move.action_post()
        self.move.button_draft()
        with self.assertRaisesRegex(UserError, "remove parts of the audit trail"):
            self.move.unlink()

    def test_cant_unlink_message(self):
        self.move.action_post()
        audit_trail = self.get_trail(self.move)
        with self.assertRaisesRegex(UserError, "remove parts of the audit trail"):
            audit_trail.unlink()

    def test_cant_unown_message(self):
        self.move.action_post()
        audit_trail = self.get_trail(self.move)
        with self.assertRaisesRegex(UserError, "remove parts of the audit trail"):
            audit_trail.res_id = 0

    def test_cant_unlink_tracking_value(self):
        self.move.action_post()
        self.env.cr.precommit.run()
        self.move.name = 'track this!'
        audit_trail = self.get_trail(self.move)
        trackings = audit_trail.tracking_value_ids.sudo()
        self.assertTrue(trackings)
        with self.assertRaisesRegex(UserError, "remove parts of the audit trail"):
            trackings.unlink()

    def test_content(self):
        messages = ["Journal Entry created"]
        self.assertTrail(self.get_trail(self.move), messages)

        self.move.action_post()
        messages.append("Updated\nFalse ⇨ True (Checked)\nFalse ⇨ MISC/2021/04/0001 (Number)\nDraft ⇨ Posted (Status)")
        self.assertTrail(self.get_trail(self.move), messages)

        self.move.button_draft()
        messages.append("Updated\nPosted ⇨ Draft (Status)")
        self.assertTrail(self.get_trail(self.move), messages)

        self.move.name = "nawak"
        messages.append("Updated\nMISC/2021/04/0001 ⇨ nawak (Number)")
        self.assertTrail(self.get_trail(self.move), messages)

        self.move.line_ids = [
            Command.update(self.move.line_ids[0].id, {'balance': 300}),
            Command.update(self.move.line_ids[1].id, {'credit': 200}),  # writing on debit/credit or balance both log
            Command.create({
                'balance': -100,
                'account_id': self.company_data['default_account_revenue'].id,
            })
        ]
        messages.extend([
            "updated\n100.0 ⇨ 300.0",
            "updated\n-100.0 ⇨ -200.0",
            "created\n ⇨ 400000 Product Sales (Account)\n0.0 ⇨ -100.0 (Balance)",
        ])
        self.assertTrail(self.get_trail(self.move), messages)

        self.move.line_ids[0].tax_ids = self.env.company.account_purchase_tax_id
        messages.extend([
            "updated\n ⇨ 15% (Taxes)",
            "created\n ⇨ 131000 Tax Paid (Account)\n0.0 ⇨ 45.0 (Balance)\nFalse ⇨ 15% (Label)",
            "created\n ⇨ 101402 Bank Suspense Account (Account)\n0.0 ⇨ -45.0 (Balance)\nFalse ⇨ Automatic Balancing Line (Label)",
        ])
        self.assertTrail(self.get_trail(self.move), messages)
        self.move.with_context(dynamic_unlink=True).line_ids.unlink()
        messages.extend([
            "deleted\n400000 Product Sales ⇨  (Account)\n300.0 ⇨ 0.0 (Balance)\n15% ⇨  (Taxes)",
            "deleted\n400000 Product Sales ⇨  (Account)\n-200.0 ⇨ 0.0 (Balance)",
            "deleted\n400000 Product Sales ⇨  (Account)\n-100.0 ⇨ 0.0 (Balance)",
            "deleted\n131000 Tax Paid ⇨  (Account)\n45.0 ⇨ 0.0 (Balance)\n15% ⇨ False (Label)",
            "deleted\n101402 Bank Suspense Account ⇨  (Account)\n-45.0 ⇨ 0.0 (Balance)\nAutomatic Balancing Line ⇨ False (Label)",
        ])
        self.assertTrail(self.get_trail(self.move), messages)

    def test_partner_notif(self):
        """Audit trail should not block partner notification."""
        user = new_test_user(
            self.env, 'test-user-notif', groups="base.group_portal",
            notification_type='email',
        )
        # identify that user as being a customer
        user.partner_id._increase_rank('customer_rank', 1)
        user.partner_id.message_post(body='Test', partner_ids=user.partner_id.ids)

    def test_partner_unlink(self):
        """Audit trail should not block partner unlink if they didn't create moves"""
        partner = self.env['res.partner'].create({
            'name': 'Test',
            'customer_rank': 1,
        })
        partner.unlink()
