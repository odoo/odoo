from odoo import fields, models


class DigestDigest(models.Model):
    _inherit = "digest.digest"

    kpi_livechat_rating = fields.Boolean(string="% of Happiness")
    kpi_livechat_rating_value = fields.Float(
        digits=(16, 2),
        compute="_compute_kpi_livechat_rating_value",
    )
    kpi_livechat_conversations = fields.Boolean(string="Conversations handled")
    kpi_livechat_conversations_value = fields.Integer(
        compute="_compute_kpi_livechat_conversations_value"
    )
    kpi_livechat_response = fields.Boolean(string="Time to answer (sec)")
    kpi_livechat_response_value = fields.Float(
        digits=(16, 2),
        compute="_compute_kpi_livechat_response_value",
    )

    def _compute_kpi_livechat_rating_value(self):
        start, end, __ = self._get_kpi_compute_parameters()
        Channel = self.env["discuss.channel"]
        # `_search`, not `search`: the id list this used to build had no bound
        # other than "every livechat session this database has ever held", and
        # it was rebuilt and re-sent to Postgres on every read -- six per
        # recipient. A Query stays a subquery over the indexed `res_id`, and
        # selects exactly the same ratings.
        livechat_channels = Channel._search([("channel_type", "=", "livechat")])
        ratings = Channel.rating_get_grades(
            [("create_date", ">=", start), ("create_date", "<", end)],
            record_ids=livechat_channels,
        )
        rated = sum(ratings.values())
        self.kpi_livechat_rating_value = ratings["great"] * 100 / rated if rated else 0

    def _compute_kpi_livechat_conversations_value(self):
        start, end, __ = self._get_kpi_compute_parameters()
        self.kpi_livechat_conversations_value = self.env[
            "discuss.channel"
        ].search_count(
            [
                ("channel_type", "=", "livechat"),
                ("create_date", ">=", start),
                ("create_date", "<", end),
            ]
        )

    def _compute_kpi_livechat_response_value(self):
        start, end, __ = self._get_kpi_compute_parameters()
        response_time = (
            self.env["im_livechat.report.channel"]
            .sudo()
            ._read_group(
                [
                    ("start_date", ">=", start),
                    ("start_date", "<", end),
                ],
                [],
                ["time_to_answer:avg"],
            )
        )
        self.kpi_livechat_response_value = response_time[0][0]

    def _get_kpi_actions(self, company, user):
        res = super()._get_kpi_actions(company, user)
        res["kpi_livechat_conversations"] = (
            "im_livechat.im_livechat_report_operator_action"
        )
        res["kpi_livechat_response"] = (
            "im_livechat.im_livechat_report_channel_time_to_answer_action"
        )
        return res
