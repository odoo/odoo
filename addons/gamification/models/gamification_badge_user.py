import logging
from typing import Any, Self

from odoo import _, api, exceptions, fields, models
from odoo.models import ValuesType

_logger = logging.getLogger(__name__)


class GamificationBadgeUser(models.Model):
    """User having received a badge"""

    _name = "gamification.badge.user"
    _description = "Gamification User Badge"
    _inherit = ["mixin.mail.thread"]
    _order = "create_date desc"
    _rec_name = "badge_name"
    _mail_partner_fields = ("user_partner_id",)

    user_id = fields.Many2one(
        comodel_name="res.users",
        index=True,
        required=True,
        ondelete="cascade",
    )
    user_partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="user_id.partner_id",
    )
    sender_id = fields.Many2one(comodel_name="res.users")
    badge_id = fields.Many2one(
        comodel_name="gamification.badge",
        index=True,
        required=True,
        ondelete="cascade",
    )
    challenge_id = fields.Many2one(comodel_name="gamification.challenge")
    comment = fields.Text()
    badge_name = fields.Char(
        related="badge_id.name",
        string="Badge Name",
    )
    level = fields.Selection(
        related="badge_id.level",
        string="Badge Level",
        readonly=True,
    )

    def _send_badge(self) -> bool:
        """Send a notification to each user for receiving a badge.

        Does not verify constraints on badge granting — the caller
        (typically ``create``) is responsible for that.
        """
        template = self.env.ref(
            "gamification.email_template_badge_received", raise_if_not_found=False
        )
        if not template:
            # A missing template is a broken mail setup, not a reason to fail the
            # grant: the badge, its bus notification and its feed entry all still
            # happen.  `_rank_changed` already guarded the same ref this way.
            _logger.warning(
                "gamification.email_template_badge_received is missing; "
                "granting %s badge(s) without the notification email.",
                len(self),
            )
            rendered = dict.fromkeys(self.ids, "")
        else:
            rendered = template._render_field("body_html", self.ids)
        for badge_user in self:
            badge_user.message_notify(
                model=badge_user._name,
                res_id=badge_user.id,
                body=rendered[badge_user.id],
                partner_ids=[badge_user.user_partner_id.id],
                subject=_(
                    "You've earned the %(badge)s badge!", badge=badge_user.badge_name
                ),
                subtype_xmlid="mail.mt_comment",
                email_layout_xmlid="mail.mail_notification_layout",
            )
            # Real-time bus notification
            badge_user.user_id._send_gamification_notification(
                "badge",
                {
                    "title": _("Badge Earned!"),
                    "message": badge_user.badge_name,
                },
            )
            # Log to unified activity feed
            self.env["gamification.activity"]._log_badge(
                badge_user.user_id,
                badge_user.badge_id,
                badge_user.sender_id,
            )

        return True

    def _notify_get_recipients_groups(
        self, message, model_description, msg_vals=False
    ) -> list[list[Any]]:
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals
        )
        self.check_singleton()
        for group in groups:
            if group[0] == "user":
                group[2]["has_button_access"] = False
        return groups

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        Badge = self.env["gamification.badge"]
        # System grants (challenge rewards, achievement/rank badges) run under
        # sudo and are exempt from the peer-granting guards below.
        if not self.env.su:
            uid = self.env.uid
            grants_per_badge: dict[int, int] = {}
            for vals in vals_list:
                if vals.get("user_id") == uid:
                    raise exceptions.UserError(
                        _("You can not grant a badge to yourself.")
                    )
                grants_per_badge[vals["badge_id"]] = (
                    grants_per_badge.get(vals["badge_id"], 0) + 1
                )
            # Enforce the monthly cap over the whole batch: check_granting()
            # only sees the pre-batch count, so N grants of a limited badge in
            # a single create would otherwise slip past a per-record limit.
            if not self.env.is_admin():
                for badge_id, count in grants_per_badge.items():
                    badge = Badge.browse(badge_id)
                    if (
                        badge.rule_max
                        and badge.stat_my_monthly_sending + count
                        > badge.rule_max_number
                    ):
                        raise exceptions.UserError(
                            _(
                                "You have already sent this badge too many time"
                                " this month."
                            )
                        )
        # Per-badge granting rules (auth list, required badges, current limit)
        checked_badge_ids: set[int] = set()
        for vals in vals_list:
            badge_id = vals["badge_id"]
            if badge_id not in checked_badge_ids:
                Badge.browse(badge_id).check_granting()
                checked_badge_ids.add(badge_id)
        return super().create(vals_list)
