# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import chain

from odoo.addons.mail.tests.common import MailCommon
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
        #   - search website_rewrite (_get_rewrites) sometimes occurs depending on the routing cache
        #   - _get ir_config_parameter (web.max_file_upload_size) sometimes occurs depending on the routing cache
        #   - fetch ir_attachment (res.lang flag_image) sometimes occurs depending on the routing cache
        #   4 _message_fetch:
        #       2 _search_needaction:
        #           - fetch res_users (current user)
        #           - search ir_rule (_get_rules for mail.notification)
        #       - search ir_rule (_get_rules)
        #       - search mail_message
        #   - fetch bus_bus (_bus_last_id)
        #   30 store add message:
        #       - search mail_message
        #       - fetch mail_message
        #       - search mail_message_schedule
        #       - search mail_followers
        #       - search ir_rule (_get_rules for rating.rating)
        #       - read group rating_rating (_rating_get_stats_per_record for slide.channel)
        #       - read group rating_rating (_rating_get_stats_per_record for product.template)
        #       2 thread:
        #           - fetch slide_channel
        #           - fetch product_template
        #       - search mail_message_res_partner_bookmarked_rel (_compute_is_bookmarked)
        #       - search message_attachment_rel
        #       - search mail_message_res_partner_rel
        #       - search mail_message_reaction
        #       - search mail_poll (start_message_id)
        #       - search mail_poll (end_message_id)
        #       - search mail_message_link_preview
        #       - search mail_notification
        #       - fetch mail_notification
        #       - search mail_tracking_value
        #       2 _compute_rating_id:
        #           - search rating_rating
        #           - fetch rating_rating
        #       4 author:
        #           - fetch res_partner
        #           - search res_users
        #           - fetch res_users
        #           - fetch res_partner
        #       - fetch mail_message_subtype
        #       6 rating stats computation:
        #           - read group rating_rating (_rating_get_stats_per_record for slide.channel)
        #           - read group rating_rating (_rating_get_stats_per_record for product.template)
        #           - compute message_needaction for slide.channel
        #           - compute message_needaction for product.template
        #       - select current db snapshot
        first_model_records = self.env["product.template"].create(
            [{"name": "Product A1"}, {"name": "Product A2"}]
        )
        second_model_records = self.env["slide.channel"].create(
            [{"name": "Course B1"}, {"name": "Course B2"}]
        )
        for record in chain(first_model_records, second_model_records):
            record.message_post(
                body=f"<p>Test message for {record.name}</p>",
                message_type="comment",
                partner_ids=[self.user_employee.partner_id.id],
                rating_value="4",
            )
        self.authenticate(self.user_employee.login, self.user_employee.password)
        with self.assertQueryCount(41):
            self.make_jsonrpc_request("/mail/data", {"fetch_params": ["/mail/inbox/messages"]})
