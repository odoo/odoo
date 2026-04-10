# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import chain

from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError
from odoo.tests.common import HttpCase, tagged, warmup


@tagged("is_query_count")
class TestInboxPerformance(HttpCase, MailCommon):
    @warmup
    def test_fetch_with_rating_stats_enabled(self):
        """
        Computation of rating_stats should run a single query per model with rating_stats enabled.
        """
        # Queries (in order):
        #   - search website (get_current_website by domain)
        #   - search website (get_current_website default)
        #   - sometimes could occur depending on the routing cache (website_rewrite, ir_config_parameter, res.lang flag_image)
        #   - _xmlid_lookup (_get_public_users)
        #   - user authentication(_get_lock_timeouts)
        #   4 _message_fetch:
        #       2 _search_needaction:
        #           - fetch res_users (current user)
        #           - search ir_rule (_get_rules for mail.notification)
        #       - search ir_rule (_get_rules)
        #       - search mail_message
        #   - search bus_bus (_bus_last_id in bus.py)
        #   33 store add message:
        #       - fetch mail_message
        #       - search mail_message_schedule
        #       - search mail_followers
        #       - search ir_rule (_get_rules for rating.rating)
        #       - read group rating_rating (_rating_get_stats_per_record for slide.channel)
        #       - read group rating_rating (_rating_get_stats_per_record for product.template)
        #       3 thread :
        #           - fetch hr_employee
        #           - fetch slide_channel
        #           - fetch product_template
        #       - search mail_message_res_partner_starred_rel (_compute_starred)
        #       - search message_attachment_rel
        #       - search mail_message_res_partner_rel
        #       - search mail_message_reaction
        #       - search mail_poll (start_message_id)
        #       - search mail_poll (end_message_id)
        #       - search mail_message_link_preview
        #       4 _filtered_for_web_client:
        #           - search mail_notification
        #           - fetch mail_notification
        #           - fetch res_partner
        #           - fetch mail_message_subtype
        #       - search mail_tracking_value
        #       2 _compute_rating_id:
        #           - search rating_rating
        #           - fetch rating_rating
        #       3 author:
        #           - fetch res_partner
        #           - search res_users
        #           - fetch res_users
        #       - compute message_needaction for hr.employee
        #       2 compute message_needaction for slide.channel (one query per record due to the lack of batching)
        #       2 compute message_needaction for product.template (one query per record due to the lack of batching)
        #       - read group rating_rating (_compute_rating_stats for slide.channel)
        #       - read group rating_rating (_compute_rating_stats for product.template)

        # rating stats enabled
        first_model_records = self.env["product.template"].create(
            [{"name": "Product A1"}, {"name": "Product A2"}]
        )
        second_model_records = self.env["slide.channel"].create(
            [{"name": "Course B1"}, {"name": "Course B2"}]
        )
        # group restricted fields
        third_model_record = self.env["hr.employee"].create({"name": "Employee"})
        with self.assertRaises(AccessError):
            third_model_record.with_user(self.user_employee).read("message_needaction_counter")
        for record in chain(first_model_records, second_model_records, third_model_record):
            record.message_post(
                body=f"<p>Test message for {record.name}</p>",
                message_type="comment",
                partner_ids=[self.user_employee.partner_id.id],
                rating_value="4",
            )
        self.authenticate(self.user_employee.login, self.user_employee.password)
        with self.assertQueryCount(43):
            self.make_jsonrpc_request("/mail/inbox/messages")
