from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.sms.tools.sms_api import SmsApi


@tagged("post_install", "-at_install")
class TestSmsProcessQueue(TransactionCase):
    """`_process_queue` (the SMS queue cron) must not crash when the fetched
    batch spans more than one company.
    """

    def test_process_queue_multi_company_batch(self):
        company_a = self.env["res.company"].create({"name": "Audit Company A"})
        company_b = self.env["res.company"].create({"name": "Audit Company B"})
        message_a = self.env["mail.message"].create(
            {"body": "test a", "record_company_id": company_a.id}
        )
        message_b = self.env["mail.message"].create(
            {"body": "test b", "record_company_id": company_b.id}
        )
        sms_a = self.env["sms.sms"].create(
            {
                "number": "+32456010203",
                "body": "hello a",
                "mail_message_id": message_a.id,
                "state": "outgoing",
            }
        )
        sms_b = self.env["sms.sms"].create(
            {
                "number": "+32456070809",
                "body": "hello b",
                "mail_message_id": message_b.id,
                "state": "outgoing",
            }
        )

        def _send_sms_batch(sms_api, messages, delivery_reports_url=False):
            return [
                {"uuid": number["uuid"], "state": "success"}
                for message in messages
                for number in message["numbers"]
            ]

        with (
            patch.object(
                SmsApi, "_send_sms_batch", autospec=True, side_effect=_send_sms_batch
            ),
            # _commit_progress calls cr.commit(), forbidden on a test cursor:
            # stub the cron bookkeeping, the behavior under test is the send.
            patch.object(
                type(self.env["ir.cron"]),
                "_commit_progress",
                return_value=float("inf"),
            ),
        ):
            self.env["sms.sms"]._process_queue()

        self.assertEqual(
            (sms_a + sms_b).mapped("state"),
            ["pending", "pending"],
            "a batch spanning two companies must still be sent, not crash the cron",
        )

    def test_split_by_api_groups_by_company_scoped_iap_account(self):
        """A batch spanning companies with distinctly-scoped `iap.account`
        records must resolve each company's SMS against its own account, not
        collapse into a single group that silently uses one company's
        account for another company's messages.
        """
        company_a = self.env["res.company"].create({"name": "Audit Company A"})
        company_b = self.env["res.company"].create({"name": "Audit Company B"})
        sms_service = self.env["iap.service"].search(
            [("technical_name", "=", "sms")], limit=1
        ) or self.env["iap.service"].create(
            {"technical_name": "sms", "name": "SMS", "unit_name": "credits"}
        )
        account_a = self.env["iap.account"].create(
            {
                "service_id": sms_service.id,
                "account_token": "token-company-a",
                "company_ids": [(6, 0, [company_a.id])],
            }
        )
        account_b = self.env["iap.account"].create(
            {
                "service_id": sms_service.id,
                "account_token": "token-company-b",
                "company_ids": [(6, 0, [company_b.id])],
            }
        )
        message_a = self.env["mail.message"].create(
            {"body": "test a", "record_company_id": company_a.id}
        )
        message_b = self.env["mail.message"].create(
            {"body": "test b", "record_company_id": company_b.id}
        )
        sms_a = self.env["sms.sms"].create(
            {
                "number": "+32456010203",
                "body": "hello a",
                "mail_message_id": message_a.id,
                "state": "outgoing",
            }
        )
        sms_b = self.env["sms.sms"].create(
            {
                "number": "+32456070809",
                "body": "hello b",
                "mail_message_id": message_b.id,
                "state": "outgoing",
            }
        )

        batch = (sms_a + sms_b).with_context(
            allowed_company_ids=[company_a.id, company_b.id]
        )
        groups = list(batch._split_by_api())

        self.assertEqual(
            len(groups),
            2,
            "each company's SMS must be split into its own group",
        )
        tokens_by_company = {}
        for sms_api, recs in groups:
            for rec in recs:
                tokens_by_company[rec._get_sms_company()] = (
                    sms_api.account.sudo().account_token
                )
        self.assertEqual(tokens_by_company[company_a], account_a.sudo().account_token)
        self.assertEqual(tokens_by_company[company_b], account_b.sudo().account_token)
