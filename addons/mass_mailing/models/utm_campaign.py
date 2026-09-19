from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.libs.numbers import float_round


class UtmCampaign(models.Model):
    _inherit = "utm.campaign"

    mailing_mail_ids = fields.One2many(
        comodel_name="mailing.mailing",
        inverse_name="campaign_id",
        string="Mass Mailings",
        domain=[("mailing_type", "=", "mail")],
        groups="mass_mailing.group_mass_mailing_user",
    )
    mailing_mail_count = fields.Integer(
        string="Number of Mass Mailing",
        compute="_compute_mailing_mail_count",
        groups="mass_mailing.group_mass_mailing_user",
    )
    is_mailing_campaign_activated = fields.Boolean(
        compute="_compute_is_mailing_campaign_activated"
    )

    # A/B Testing
    ab_testing_mailings_count = fields.Integer(
        string="A/B Test Mailings #",
        compute="_compute_mailing_mail_count",
    )
    ab_testing_completed = fields.Boolean(
        string="A/B Testing Campaign Finished",
        compute="_compute_ab_testing_completed",
        store=True,
        copy=False,
        readonly=True,
    )
    ab_testing_winner_mailing_id = fields.Many2one(
        comodel_name="mailing.mailing",
        string="A/B Campaign Winner Mailing",
        copy=False,
    )
    ab_testing_schedule_datetime = fields.Datetime(
        string="Send Final On",
        default=lambda self: fields.Datetime.now() + relativedelta(days=1),
        help="Date that will be used to know when to determine and send the winner mailing",
    )
    ab_testing_winner_selection = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("opened_ratio", "Highest Open Rate"),
            ("clicks_ratio", "Highest Click Rate"),
            ("replied_ratio", "Highest Reply Rate"),
        ],
        string="Winner Selection",
        default="opened_ratio",
        help="Selection to determine the winner mailing that will be sent.",
    )

    # stat fields
    received_ratio = fields.Float(compute="_compute_statistics")
    opened_ratio = fields.Float(compute="_compute_statistics")
    replied_ratio = fields.Float(compute="_compute_statistics")
    bounced_ratio = fields.Float(compute="_compute_statistics")

    @api.depends("ab_testing_winner_mailing_id")
    def _compute_ab_testing_completed(self):
        for campaign in self:
            campaign.ab_testing_completed = bool(self.ab_testing_winner_mailing_id)

    @api.depends("mailing_mail_ids")
    def _compute_mailing_mail_count(self):
        mailing_data = self.env["mailing.mailing"]._read_group(
            [("campaign_id", "in", self.ids), ("mailing_type", "=", "mail")],
            ["campaign_id", "ab_testing_enabled"],
            ["__count"],
        )
        ab_testing_mapped_data = defaultdict(list)
        mapped_data = defaultdict(list)
        for campaign, ab_testing_enabled, count in mailing_data:
            if ab_testing_enabled:
                ab_testing_mapped_data[campaign.id].append(count)
            mapped_data[campaign.id].append(count)
        for campaign in self:
            campaign.mailing_mail_count = sum(
                mapped_data[campaign._origin.id or campaign.id]
            )
            campaign.ab_testing_mailings_count = sum(
                ab_testing_mapped_data[campaign._origin.id or campaign.id]
            )

    def _compute_statistics(self):
        """Compute statistics of the mass mailing campaign"""
        default_vals = {
            "received_ratio": 0,
            "opened_ratio": 0,
            "replied_ratio": 0,
            "bounced_ratio": 0,
        }
        if not self.ids:
            self.update(default_vals)
            return
        self.env.cr.execute(
            """
            SELECT
                c.id as campaign_id,
                COUNT(s.id) AS expected,
                COUNT(s.sent_datetime) AS sent,
                COUNT(s.trace_status) FILTER (WHERE s.trace_status in ('sent', 'open', 'reply')) AS delivered,
                COUNT(s.trace_status) FILTER (WHERE s.trace_status in ('open', 'reply')) AS open,
                COUNT(s.trace_status) FILTER (WHERE s.trace_status = 'reply') AS reply,
                COUNT(s.trace_status) FILTER (WHERE s.trace_status = 'bounce') AS bounce,
                COUNT(s.trace_status) FILTER (WHERE s.trace_status = 'cancel') AS cancel
            FROM
                mailing_trace s
            JOIN
                mailing_mailing m
                ON (m.id = s.mass_mailing_id)
            RIGHT JOIN
                utm_campaign c
                ON (c.id = m.campaign_id)
            WHERE
                c.id = ANY(%s)
            GROUP BY
                c.id
        """,
            (list(self.ids),),
        )

        all_stats = self.env.cr.dictfetchall()
        stats_per_campaign = {stats["campaign_id"]: stats for stats in all_stats}

        for campaign in self:
            stats = stats_per_campaign.get(campaign.id)
            if not stats:
                vals = default_vals
            else:
                total = (stats["expected"] - stats["cancel"]) or 1
                delivered = stats["sent"] - stats["bounce"]
                vals = {
                    "received_ratio": float_round(
                        100.0 * delivered / total, precision_digits=2
                    ),
                    "opened_ratio": float_round(
                        100.0 * stats["open"] / total, precision_digits=2
                    ),
                    "replied_ratio": float_round(
                        100.0 * stats["reply"] / total, precision_digits=2
                    ),
                    "bounced_ratio": float_round(
                        100.0 * stats["bounce"] / total, precision_digits=2
                    ),
                }

            campaign.update(vals)

    def _compute_is_mailing_campaign_activated(self):
        self.is_mailing_campaign_activated = self.env.user.has_group(
            "mass_mailing.group_mass_mailing_campaign"
        )

    def _get_mailing_recipients(self, model=None):
        """Return the recipients of a mailing campaign. This is based on the statistics
        build for each mailing."""
        # Every id is assigned in the loop below, so no seeded default is
        # needed. It used to be dict.fromkeys(self.ids, {}), which both shared
        # one dict across all keys and seeded a dict where a set is stored.
        domain = [("campaign_id", "in", self.ids)]
        if model:
            domain += [("model", "=", model)]
        res = {campaign.id: set() for campaign in self}
        for campaign, res_ids in self.env["mailing.trace"]._read_group(
            domain, ["campaign_id"], ["res_id:array_agg"]
        ):
            res[campaign.id] = set(res_ids)
        return res

    @api.model
    def _cron_process_mass_mailing_ab_testing(self):
        """Cron that manages A/B testing and sends a winner mailing computed based on
        the value set on the A/B testing campaign.
        In case there is no mailing sent for an A/B testing campaign we ignore this campaign
        """
        ab_testing_campaign = self.search(
            [
                ("ab_testing_schedule_datetime", "<=", fields.Datetime.now()),
                ("ab_testing_winner_selection", "!=", "manual"),
                ("ab_testing_completed", "=", False),
            ]
        )
        for campaign in ab_testing_campaign:
            ab_testing_mailings = campaign.mailing_mail_ids.filtered(
                lambda m: m.ab_testing_enabled
            )
            if not ab_testing_mailings.filtered(lambda m: m.state == "done"):
                continue
            ab_testing_mailings.action_send_winner_mailing()
        return ab_testing_campaign
