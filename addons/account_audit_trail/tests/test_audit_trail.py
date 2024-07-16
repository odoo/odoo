from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged, new_test_user
from odoo.tools.mail import html2plaintext


@tagged('post_install', '-at_install')
class TestAuditTrail(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.check_account_audit_trail = True
        cls.move = cls.create_move()

    @classmethod
    def create_move(cls):
        return cls.env['account.move'].create({
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
            self.assertRegex(
                html2plaintext(message.account_audit_log_preview),
                expected
            )

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
        messages.append(r"Updated Draft Posted \(Status\)")
        self.assertTrail(self.get_trail(self.move), messages)

        self.move.button_draft()
        messages.append(r"Updated Posted Draft \(Status\)")
        self.assertTrail(self.get_trail(self.move), messages)

        self.move.name = "nawak"
        messages.append(r"Updated MISC/\d+/\d+/0001 nawak \(Number\)")
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
            r"updated 100.0 300.0",
            r"updated -100.0 -200.0",
            r"created  400000 Product Sales \(Account\) 0.0 -100.0 \(Balance\)",
        ])
        self.assertTrail(self.get_trail(self.move), messages)

        self.move.line_ids[0].tax_ids = self.env.company.account_purchase_tax_id
        messages.extend([
            r"updated  15% \(Taxes\)",
            r"created  131000 Tax Paid \(Account\) 0.0 45.0 \(Balance\) False 15% \(Label\)",
            r"created  101402 Bank Suspense Account \(Account\) 0.0 -45.0 \(Balance\) False Automatic Balancing Line \(Label\)",
        ])
        self.assertTrail(self.get_trail(self.move), messages)
        self.move.with_context(dynamic_unlink=True).line_ids.unlink()
        messages.extend([
            r"deleted 400000 Product Sales  \(Account\) 300.0 0.0 \(Balance\) 15%  \(Taxes\)",
            r"deleted 400000 Product Sales  \(Account\) -200.0 0.0 \(Balance\)",
            r"deleted 400000 Product Sales  \(Account\) -100.0 0.0 \(Balance\)",
            r"deleted 131000 Tax Paid  \(Account\) 45.0 0.0 \(Balance\) 15% False \(Label\)",
            r"deleted 101402 Bank Suspense Account  \(Account\) -45.0 0.0 \(Balance\) Automatic Balancing Line False \(Label\)",
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
