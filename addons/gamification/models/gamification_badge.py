import logging
from datetime import date

from odoo import _, api, exceptions, fields, models
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


class GamificationBadge(models.Model):
    """Badge object that users can send and receive"""

    CAN_GRANT = 1
    NOBODY_CAN_GRANT = 2
    USER_NOT_VIP = 3
    BADGE_REQUIRED = 4
    TOO_MANY = 5

    _name = "gamification.badge"
    _description = "Gamification Badge"
    _inherit = ["mixin.mail.thread", "mixin.image"]

    name = fields.Char(
        string="Badge",
        translate=True,
        required=True,
    )
    active = fields.Boolean(default=True)
    description = fields.Html(
        translate=True,
        sanitize_attributes=False,
    )
    level = fields.Selection(
        selection=[("bronze", "Bronze"), ("silver", "Silver"), ("gold", "Gold")],
        string="Forum Badge Level",
        default="bronze",
    )

    rule_auth = fields.Selection(
        selection=[
            ("everyone", "Everyone"),
            ("users", "A selected list of users"),
            ("having", "People having some badges"),
            ("nobody", "No one, assigned through challenges"),
        ],
        string="Allowance to Grant",
        default="everyone",
        required=True,
        help="Who can grant this badge",
    )
    rule_auth_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="rel_badge_auth_users",
        string="Authorized Users",
        help="Only these people can give this badge",
    )
    rule_auth_badge_ids = fields.Many2many(
        comodel_name="gamification.badge",
        relation="gamification_badge_rule_badge_rel",
        column1="badge1_id",
        column2="badge2_id",
        string="Required Badges",
        help="Only the people having these badges can give this badge",
    )

    rule_max = fields.Boolean(
        string="Monthly Limited Sending",
        help="Check to set a monthly limit per person of sending this badge",
    )
    rule_max_number = fields.Integer(
        string="Limitation Number",
        help="The maximum number of time this badge can be sent per month per person.",
    )
    challenge_ids = fields.One2many(
        comodel_name="gamification.challenge",
        inverse_name="reward_id",
        string="Reward of Challenges",
    )

    goal_definition_ids = fields.Many2many(
        comodel_name="gamification.goal.definition",
        relation="badge_unlocked_definition_rel",
        string="Rewarded by",
        help="The users that have succeeded these goals will receive automatically the badge.",
    )

    owner_ids = fields.One2many(
        comodel_name="gamification.badge.user",
        inverse_name="badge_id",
        string="Owners",
        help="The list of instances of this badge granted to users",
    )

    granted_count = fields.Integer(
        string="Total",
        compute="_compute_owner_stats",
        help="The number of time this badge has been received.",
    )
    granted_users_count = fields.Integer(
        string="Number of users",
        compute="_compute_owner_stats",
        help="The number of time this badge has been received by unique users.",
    )
    unique_owner_ids = fields.Many2many(
        comodel_name="res.users",
        string="Unique Owners",
        compute="_compute_owner_stats",
        help="The list of unique users having received this badge.",
    )

    stat_this_month = fields.Integer(
        string="Monthly total",
        compute="_compute_owner_stats",
        help="The number of time this badge has been received this month.",
    )
    stat_my = fields.Integer(
        string="My Total",
        compute="_compute_owner_stats",
        help="The number of time the current user has received this badge.",
    )
    stat_my_this_month = fields.Integer(
        string="My Monthly Total",
        compute="_compute_owner_stats",
        help="The number of time the current user has received this badge this month.",
    )
    stat_my_monthly_sending = fields.Integer(
        string="My Monthly Sending Total",
        compute="_compute_owner_stats",
        help="The number of time the current user has sent this badge this month.",
    )

    remaining_sending = fields.Integer(
        string="Remaining Sending Allowed",
        compute="_compute_remaining_sending",
        help="If a maximum is set",
    )

    # Every column here is "as seen by the acting user": the four stat_* ones
    # count that user's own sending and receiving, and the owner ones go through
    # res.users._search, so record rules decide which owners are visible. Merging
    # the two passes made that one compute, and it has to say so or the cache
    # serves one user's numbers to the next.
    @api.depends_context("uid")
    @api.depends("owner_ids")
    def _compute_owner_stats(self) -> None:
        """Fill every per-badge statistic from a single aggregation.

        This was two passes over ``gamification_badge_user`` carrying the same
        ``@api.depends``, so they always recomputed together and always cost two
        round-trips to answer one question about one table.

        The owner columns go through ``res.users._search`` so that who you are
        still decides which owners you can see; the four ``stat_*`` columns are
        about the acting user's own sending and receiving and need no such
        scoping.
        """
        defaults = {
            "granted_count": 0,
            "granted_users_count": 0,
            "unique_owner_ids": [],
            "stat_my": 0,
            "stat_this_month": 0,
            "stat_my_this_month": 0,
            "stat_my_monthly_sending": 0,
        }
        if not self.ids:
            self.update(defaults)
            return

        query = self.env["res.users"]._search([])
        badge_alias = query.join(
            "res_users", "id", "gamification_badge_user", "user_id", "badges"
        )
        rows = self.env.execute_query_dict(
            SQL(
                """
              SELECT %(badge_alias)s.badge_id AS badge_id,
                     count(res_users.id) AS granted_count,
                     count(distinct res_users.id) AS granted_users_count,
                     array_agg(distinct res_users.id) AS unique_owner_ids,
                     count(*) FILTER (
                         WHERE %(badge_alias)s.user_id = %(uid)s
                     ) AS stat_my,
                     count(*) FILTER (
                         WHERE %(badge_alias)s.create_date >= %(month)s
                     ) AS stat_this_month,
                     count(*) FILTER (
                         WHERE %(badge_alias)s.user_id = %(uid)s
                           AND %(badge_alias)s.create_date >= %(month)s
                     ) AS stat_my_this_month,
                     count(*) FILTER (
                         WHERE %(badge_alias)s.create_uid = %(uid)s
                           AND %(badge_alias)s.create_date >= %(month)s
                     ) AS stat_my_monthly_sending
                FROM %(from_clause)s
               WHERE %(where_clause)s
                 AND %(badge_alias)s.badge_id IN %(ids)s
            GROUP BY %(badge_alias)s.badge_id
            """,
                from_clause=query.from_clause,
                where_clause=query.where_clause or SQL("TRUE"),
                badge_alias=SQL.identifier(badge_alias),
                ids=tuple(self.ids),
                uid=self.env.uid,
                month=date.today().replace(day=1),
            )
        )
        mapping = {row.pop("badge_id"): row for row in rows}
        for badge in self:
            badge.update(mapping.get(badge.id, defaults))

    @api.depends(
        "rule_auth",
        "rule_auth_user_ids",
        "rule_auth_badge_ids",
        "rule_max",
        "rule_max_number",
        "stat_my_monthly_sending",
    )
    def _compute_remaining_sending(self) -> None:
        """Computes the number of badges remaining the user can send

        0 if not allowed or no remaining
        integer if limited sending
        -1 if infinite (should not be displayed)
        """
        for badge in self:
            if badge._can_grant_badge() != self.CAN_GRANT:
                # if the user cannot grant this badge at all, result is 0
                badge.remaining_sending = 0
            elif not badge.rule_max:
                # if there is no limitation, -1 is returned which means 'infinite'
                badge.remaining_sending = -1
            else:
                badge.remaining_sending = (
                    badge.rule_max_number - badge.stat_my_monthly_sending
                )

    def check_granting(self) -> bool:
        """Check the user 'uid' can grant the badge 'badge_id' and raise the appropriate exception
        if not

        Do not check for SUPERUSER_ID
        """
        status_code = self._can_grant_badge()
        if status_code == self.CAN_GRANT:
            return True
        elif status_code == self.NOBODY_CAN_GRANT:
            raise exceptions.UserError(_("This badge can not be sent by users."))
        elif status_code == self.USER_NOT_VIP:
            raise exceptions.UserError(_("You are not in the user allowed list."))
        elif status_code == self.BADGE_REQUIRED:
            raise exceptions.UserError(_("You do not have the required badges."))
        elif status_code == self.TOO_MANY:
            raise exceptions.UserError(
                _("You have already sent this badge too many time this month.")
            )
        else:
            _logger.error("Unknown badge status code: %s", status_code)
        return False

    def _can_grant_badge(self) -> int:
        """Check if a user can grant a badge to another user

        :return: integer representing the permission.
        """
        if self.env.is_admin():
            return self.CAN_GRANT

        if self.rule_auth == "nobody":
            return self.NOBODY_CAN_GRANT
        elif self.rule_auth == "users" and self.env.user not in self.rule_auth_user_ids:
            return self.USER_NOT_VIP
        elif self.rule_auth == "having":
            # Ask only about the badges this rule names, instead of loading every
            # badge the user owns to intersect in Python.
            held = self.env["gamification.badge.user"].search_fetch(
                [
                    ("user_id", "=", self.env.uid),
                    ("badge_id", "in", self.rule_auth_badge_ids.ids),
                ],
                ["badge_id"],
            )
            if self.rule_auth_badge_ids - held.badge_id:
                return self.BADGE_REQUIRED

        if self.rule_max and self.stat_my_monthly_sending >= self.rule_max_number:
            return self.TOO_MANY

        # badge.rule_auth == 'everyone' -> no check
        return self.CAN_GRANT
