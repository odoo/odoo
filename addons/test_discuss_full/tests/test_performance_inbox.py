# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import HttpCase, tagged, warmup


@tagged("post_install", "-at_install", "is_query_count")
class TestInboxPerformance(HttpCase, MailCommon):
    @warmup
    def test_fetch_rating_stats(self):
        """
        Computation of rating_stats should run a single query per model with rating_stats enabled.
        """
        record_a1 = self.env["mail.test.rating"].create({"name": "Ticket A1"})
        record_b1 = self.env["slide.channel"].create({"name": "Course B1"})
        for record in [record_a1, record_b1]:
            record.message_post(
                body=f"<p>Test message for {record.name}</p>",
                message_type="comment",
                partner_ids=[self.user_employee.partner_id.id],
                rating_value="4",
            )
        self.authenticate(self.user_employee.login, self.user_employee.password)
        with self.assertQueryCount(28):
            self.make_jsonrpc_request("/mail/inbox/messages")
        record_a2 = self.env["mail.test.rating"].create({"name": "Ticket A2"})
        record_b2 = self.env["slide.channel"].create({"name": "Course B2"})
        for record in [record_a2, record_b2]:
            record.message_post(
                body=f"<p>Test message for {record.name}</p>",
                message_type="comment",
                partner_ids=[self.user_employee.partner_id.id],
                rating_value="4",
            )
        self.authenticate(self.user_employee.login, self.user_employee.password)
        with self.assertQueryCount(28):
            self.make_jsonrpc_request("/mail/inbox/messages")
