# pylint: disable=C0326

from odoo import fields
from odoo.tests import tagged
from odoo.tools import html2plaintext

from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged("post_install", "-at_install")
class TestAccountReportsTours(AccountTestInvoicingHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.report = cls.env.ref("account.balance_sheet")
        cls.report.column_ids.sortable = True

        # Test the root reports. We don't want to choose US variants if some are installed.
        cls.env["account.report"].search([]).variant_report_ids.active = False

        cls.account_101401 = cls.env["account.account"].search(
            [
                ("company_ids", "=", cls.company_data["company"].id),
                ("code", "=", 101401),
            ]
        )

        cls.bank_suspense_account = cls.company_data[
            "company"
        ].account_config_id.account_journal_suspense_account_id

        cls.account_101404 = cls.env["account.account"].search(
            [
                ("company_ids", "=", cls.company_data["company"].id),
                ("code", "=", 101404),
            ]
        )
        if not cls.account_101404:
            # additional outstanding accounts are created when accounting is not installed
            cls.account_101404 = cls.env["account.account"].search(
                [
                    ("company_ids", "=", cls.company_data["company"].id),
                    ("code", "=", "OSTR00"),
                ]
            )
            cls.account_101404.code = "101404"

        cls.account_121000 = cls.env["account.account"].search(
            [
                ("company_ids", "=", cls.company_data["company"].id),
                ("code", "=", 121000),
            ]
        )

        cls.account_251000 = cls.env["account.account"].search(
            [
                ("company_ids", "=", cls.company_data["company"].id),
                ("code", "=", 251000),
            ]
        )

        move = cls.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2022-06-01",
                "journal_id": cls.company_data["default_journal_cash"].id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "debit": 75.0,
                            "credit": 0.0,
                            "account_id": cls.account_101401.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 100.0,
                            "credit": 0.0,
                            "account_id": cls.bank_suspense_account.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 50.0,
                            "credit": 0.0,
                            "account_id": cls.account_101404.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 25.0,
                            "credit": 0.0,
                            "account_id": cls.account_121000.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 250.0,
                            "account_id": cls.account_251000.id,
                        },
                    ),
                ],
            }
        )

        move.action_post()

    def test_account_reports_tours(self):
        self.start_tour("/odoo", "account_reports", login=self.env.user.login)

    def test_account_reports_annotations_tours(self):
        date = fields.Date.today().strftime("%Y-%m-%d")
        message_101401 = self.env["mail.message"].create(
            {
                "model": "account.account",
                "res_id": self.account_101401.id,
                "body": "Annotation 101401",
                "date": date,
                "author_id": self.env.user.partner_id.id,
                "message_type": "comment",
                "subtype_id": self.env.ref("mail.mt_note").id,
            }
        )
        annotation_101401 = self.env["account.report.annotation"].create(
            {
                "date": date,
                "message_id": message_101401.id,
            }
        )
        message_101404 = self.env["mail.message"].create(
            {
                "model": "account.account",
                "res_id": self.account_101404.id,
                "body": "Annotation 101404",
                "date": date,
                "author_id": self.env.user.partner_id.id,
                "message_type": "comment",
                "subtype_id": self.env.ref("mail.mt_note").id,
            }
        )
        annotation_101404 = self.env["account.report.annotation"].create(
            {
                "date": date,
                "message_id": message_101404.id,
            }
        )

        self.start_tour(
            "/odoo", "account_reports_annotations", login=self.env.user.login
        )

        annotations = self.env["account.report.annotation"].search([])

        self.assertEqual(len(annotations), 2, "There should be two annotations")

        self.assertTrue(
            annotation_101401 in annotations,
            "The annotation on account 101401 should still exist",
        )
        self.assertTrue(
            annotation_101404 not in annotations,
            "The annotation on account 101404 should have been deleted",
        )

        new_message = (annotations - annotation_101401).message_id
        self.assertEqual(
            new_message.model,
            "account.account",
            "The new message should be linked to an account",
        )
        self.assertEqual(
            new_message.res_id,
            self.account_121000.id,
            "The new message should be linked to account 121000",
        )

    def test_account_reports_audit_tours(self):
        self.start_tour(
            "/odoo/action-account.action_view_account_audit",
            "account_reports_audit",
            login=self.env.user.login,
        )

        messages = self.env["mail.message"].search([("model", "=", "account.account")])
        annotations = self.env["account.report.annotation"].search(
            [("message_id", "in", messages.ids)]
        )

        self.assertEqual(
            len(messages), 1, "There should be one message created by the tour"
        )
        self.assertEqual(
            len(annotations), 1, "There should be one annotation created by the tour"
        )
        self.assertEqual(
            bool(annotations.date), True, "The message should be an annotation (pinned)"
        )
        self.assertEqual(
            html2plaintext(messages.body),
            "Annotation from the audit",
            "The message body should match the expected annotation text",
        )
