import logging

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import new_test_user, tagged

from odoo.addons.account.tests.common import (
    AccountTestInvoicingCommon,
    AccountTestInvoicingHttpCommon,
)

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestAuditTrail(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = (
            cls.env["base"]
            .with_context(
                tracking_disable=False,
                mail_create_nolog=False,
                mail_notrack=False,
            )
            .env
        )
        cls.env.company.account_config_id.restrictive_audit_trail = False
        cls.move = cls.create_move()

    @classmethod
    def create_move(cls):
        return cls.env["account.move"].create(
            {
                "date": "2021-04-01",
                "line_ids": [
                    Command.create(
                        {
                            "balance": 100,
                            "account_id": cls.company_data[
                                "default_account_revenue"
                            ].id,
                        }
                    ),
                    Command.create(
                        {
                            "balance": -100,
                            "account_id": cls.company_data[
                                "default_account_revenue"
                            ].id,
                        }
                    ),
                ],
            }
        )

    def get_trail(self, record):
        self.env.cr.precommit.run()
        return self.env["mail.message"].search(
            [
                ("model", "=", record._name),
                ("res_id", "=", record.id),
            ]
        )

    def assertTrail(self, trail, expected):
        self.assertEqual(len(trail), len(expected))
        for message, expected_needle in zip(trail, expected[::-1], strict=False):
            self.assertIn(expected_needle, message.account_audit_log_preview)

    def test_can_unlink_draft(self):
        self.env.company.account_config_id.restrictive_audit_trail = True
        self.move.unlink()

    def test_cant_unlink_posted(self):
        self.env.company.account_config_id.restrictive_audit_trail = True
        self.move.action_post()
        self.move.action_draft()
        with self.assertRaisesRegex(
            UserError, "remove parts of a restricted audit trail"
        ):
            self.move.unlink()

    def test_cant_unlink_message(self):
        self.env.company.account_config_id.restrictive_audit_trail = True
        self.move.action_post()
        self.env.cr.flush()
        audit_trail = self.get_trail(self.move)
        with self.assertRaisesRegex(
            UserError, "remove parts of a restricted audit trail"
        ):
            audit_trail.unlink()

    def test_cant_unown_message(self):
        self.env.company.account_config_id.restrictive_audit_trail = True
        self.move.action_post()
        self.env.cr.flush()
        audit_trail = self.get_trail(self.move)
        with self.assertRaisesRegex(
            UserError, "remove parts of a restricted audit trail"
        ):
            audit_trail.res_id = 0

    def test_cant_unlink_tracking_value(self):
        self.env.company.account_config_id.restrictive_audit_trail = True
        self.move.action_post()
        self.env.cr.precommit.run()
        self.move.name = "track this!"
        audit_trail = self.get_trail(self.move)
        trackings = audit_trail.tracking_value_ids.sudo()
        self.assertTrue(trackings)
        with self.assertRaisesRegex(
            UserError, "remove parts of a restricted audit trail"
        ):
            trackings.unlink()

    def test_content(self):
        messages = ["Journal Entry created"]
        self.assertTrail(self.get_trail(self.move), messages)

        self.move.action_post()
        messages.append(
            "Updated\nFalse ⇨ True (Reviewed)\nFalse ⇨ MISC/2021/04/0001 (Number)\nDraft ⇨ Posted (Status)"
        )
        self.assertTrail(self.get_trail(self.move), messages)

        self.move.action_draft()
        messages.append("Updated\nTrue ⇨ False (Reviewed)\nPosted ⇨ Draft (Status)")
        self.assertTrail(self.get_trail(self.move), messages)

        self.move.name = "nawak"
        messages.append("Updated\nMISC/2021/04/0001 ⇨ nawak (Number)")
        self.assertTrail(self.get_trail(self.move), messages)

        self.move.line_ids = [
            Command.update(self.move.line_ids[0].id, {"balance": 300}),
            Command.update(self.move.line_ids[1].id, {"credit": 200}),
            Command.create(
                {
                    "balance": -100,
                    "account_id": self.company_data["default_account_revenue"].id,
                }
            ),
        ]
        messages.extend(
            [
                "updated\n100.0 ⇨ 300.0",
                "updated\n-100.0 ⇨ -200.0",
                "created\n ⇨ 400000 Product Sales (Account)\n0.0 ⇨ -100.0 (Balance)",
            ]
        )
        self.assertTrail(self.get_trail(self.move), messages)

        self.move.line_ids[
            0
        ].tax_ids = self.env.company.account_config_id.account_purchase_tax_id
        suspense_account_code = (
            self.env.company.account_config_id.account_journal_suspense_account_id.code
        )
        messages.extend(
            [
                "updated\n ⇨ 15% (Taxes)",
                "created\n ⇨ 131000 Tax Paid (Account)\n0.0 ⇨ 45.0 (Balance)\nFalse ⇨ 15% (Label)",
                f"created\n ⇨ {suspense_account_code} Bank Suspense Account (Account)\n0.0 ⇨ -45.0 (Balance)\nFalse ⇨ Automatic Balancing Line (Label)",
            ]
        )
        self.assertTrail(self.get_trail(self.move), messages)
        self.move.with_context(dynamic_unlink=True).line_ids.unlink()
        messages.extend(
            [
                "deleted\n400000 Product Sales ⇨  (Account)\n300.0 ⇨ 0.0 (Balance)\n15% ⇨  (Taxes)",
                "deleted\n400000 Product Sales ⇨  (Account)\n-200.0 ⇨ 0.0 (Balance)",
                "deleted\n400000 Product Sales ⇨  (Account)\n-100.0 ⇨ 0.0 (Balance)",
                "deleted\n131000 Tax Paid ⇨  (Account)\n45.0 ⇨ 0.0 (Balance)\n15% ⇨ False (Label)",
                f"deleted\n{suspense_account_code} Bank Suspense Account ⇨  (Account)\n-45.0 ⇨ 0.0 (Balance)\nAutomatic Balancing Line ⇨ False (Label)",
            ]
        )
        self.assertTrail(self.get_trail(self.move), messages)

        self.env.company.account_config_id.restrictive_audit_trail = True
        messages_company = ["Updated\nFalse ⇨ True (Restrictive Audit Trail)"]
        self.assertTrail(
            self.get_trail(self.company.account_config_id), messages_company
        )

    def test_partner_notif(self):
        user = new_test_user(
            self.env,
            "test-user-notif",
            groups="base.group_portal",
            notification_type="email",
        )
        user.partner_id.sudo().customer_rank += 1
        self.assertGreater(user.partner_id.customer_rank, 0)
        user.partner_id.message_post(body="Test", partner_ids=user.partner_id.ids)

    def test_partner_unlink(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Test",
                "customer_rank": 1,
            }
        )
        partner.unlink()


@tagged("post_install", "-at_install")
class TestAuditTrailAttachment(AccountTestInvoicingHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.account_config_id.restrictive_audit_trail = True
        cls.document_installed = (
            "documents_account"
            in cls.env["ir.module.module"]._get_installed_module_ids()
        )
        if cls.document_installed:
            folder_test = cls.env["document.document"].create(
                {
                    "name": "folder_test",
                    "type": "folder",
                }
            )
            existing_setting = (
                cls.env["document.account.folder.setting"]
                .sudo()
                .search(
                    [("journal_id", "=", cls.company_data["default_journal_sale"].id)]
                )
            )
            if existing_setting:
                existing_setting.folder_id = folder_test
            else:
                cls.env["document.account.folder.setting"].sudo().create(
                    {
                        "folder_id": folder_test.id,
                        "journal_id": cls.company_data["default_journal_sale"].id,
                    }
                )

    def _send_and_print(self, invoice):
        return (
            self.env["mixin.account.move.send"]
            .with_context(
                force_report_rendering=True,
            )
            ._generate_and_send_invoices(invoice)
        )

    def test_audit_trail_attachment(self):
        invoice = self.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_a.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "product",
                                "quantity": 1,
                                "price_unit": 100,
                            }
                        )
                    ],
                }
            ]
        )
        invoice.action_post()
        self.assertFalse(invoice.message_main_attachment_id)

        first_attachment = self._send_and_print(invoice)
        self.assertTrue(first_attachment)

        first_attachment.unlink()
        self.assertTrue(first_attachment.exists())
        with self.assertRaisesRegex(
            UserError, "remove parts of a restricted audit trail."
        ):
            first_attachment.unlink()

        invoice.invalidate_recordset()
        second_attachment = self._send_and_print(invoice)
        self.assertNotEqual(first_attachment, second_attachment)

        first_attachment.register_as_main_attachment()
        self.assertEqual(invoice.message_main_attachment_id, first_attachment)
        second_attachment.register_as_main_attachment()
        self.assertEqual(invoice.message_main_attachment_id, second_attachment)

        if self.document_installed:
            document = self.env["document.document"].search(
                [
                    ("res_model", "=", "account.move"),
                    ("res_id", "=", invoice.id),
                    ("name", "=ilike", "%.pdf"),
                ]
            )
            self.assertTrue(document)
            document.attachment_id = first_attachment
            document.attachment_id = second_attachment
        else:
            _logger.runbot(
                "Documents module is not installed, skipping part of the test"
            )

    def test_audit_trail_write_attachment(self):
        invoice = self.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_a.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "product",
                                "quantity": 1,
                                "price_unit": 100,
                            }
                        )
                    ],
                }
            ]
        )
        invoice.action_post()
        self.assertFalse(invoice.message_main_attachment_id)

        self._send_and_print(invoice)
        attachment = invoice.message_main_attachment_id

        with self.assertRaisesRegex(
            UserError, "remove parts of a restricted audit trail."
        ):
            attachment.write(
                {
                    "res_id": self.env.user.id,
                    "res_model": self.env.user._name,
                }
            )

        with self.assertRaisesRegex(
            UserError, "remove parts of a restricted audit trail."
        ):
            attachment.datas = b"new data"

        another_attachment = self.env["ir.attachment"].create(
            {
                "name": "doc.pdf",
                "res_model": "mail.compose.message",
                "datas": attachment.datas,
            }
        )
        invoice.message_post(
            message_type="comment", attachment_ids=another_attachment.ids
        )
