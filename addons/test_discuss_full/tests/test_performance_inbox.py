# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import chain

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import HttpCase, tagged, warmup


@tagged("post_install", "-at_install", "is_query_count")
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
        #   - insert res_device_log
        #   - _xmlid_lookup (_get_public_users)
        #   - fetch website (_get_cached_values)
        #   - get_param ir_config_parameter (_pre_dispatch website_sale)
        #   4 _message_fetch:
        #       2 _search_needaction:
        #           - fetch res_users (current user)
        #           - search ir_rule (_get_rules for mail.notification)
        #       - search ir_rule (_get_rules)
        #       - search mail_message
        #   30 message _to_store:
        #       - search mail_message_schedule
        #       - fetch mail_message
        #       - search mail_followers
        #       2 thread _to_store:
        #           - fetch slide_channel
        #           - fetch product_template
        #       - search mail_message_res_partner_starred_rel (_compute_starred)
        #       - search message_attachment_rel
        #       - search mail_link_preview
        #       - search mail_message_reaction
        #       - search mail_message_res_partner_rel
        #       - fetch mail_message_subtype
        #       - search mail_notification
        #       7 _filtered_for_web_client:
        #           - fetch mail_notification
        #           4 _compute_domain:
        #               - search ir_rule (_get_rules for res.partner)
        #               - search res_groups_users_rel
        #               - search rule_group_rel
        #               - fetch ir_rule
        #           - fetch res_company
        #           - fetch res_partner
        #       2 _compute_rating_id:
        #           - search rating_rating
        #           - fetch rating_rating
        #       - search mail_tracking_value
        #       3 _author_to_store:
        #           - fetch res_partner
        #           - search res_users
        #           - fetch res_users
        #       - search ir_rule (_get_rules for rating.rating)
        #       - read group rating_rating (_rating_get_stats_per_record for slide.channel)
        #       - read group rating_rating (_compute_rating_stats for slide.channel)
        #       - read group rating_rating (_rating_get_stats_per_record for product.template)
        #       - read group rating_rating (_compute_rating_stats for product.template)
        #   - get_param ir_config_parameter (_save_session)
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
        with self.assertQueryCount(42):
            self.make_jsonrpc_request("/mail/inbox/messages")
