from datetime import date, timedelta
from typing import Any, Literal, Self

from odoo import _, api, fields, models
from odoo.models import ValuesType
from odoo.tools import SQL


class ResUsers(models.Model):
    _inherit = "res.users"

    karma = fields.Integer(
        compute="_compute_karma",
        store=True,
        readonly=False,
    )
    karma_tracking_ids = fields.One2many(
        comodel_name="gamification.karma.tracking",
        inverse_name="user_id",
        string="Karma Changes",
        groups="base.group_system",
    )
    badge_ids = fields.One2many(
        comodel_name="gamification.badge.user",
        inverse_name="user_id",
        string="Badges",
        copy=False,
    )
    gold_badge = fields.Integer(
        string="Gold badges count",
        compute="_compute_badge_level_counts",
    )
    silver_badge = fields.Integer(
        string="Silver badges count",
        compute="_compute_badge_level_counts",
    )
    bronze_badge = fields.Integer(
        string="Bronze badges count",
        compute="_compute_badge_level_counts",
    )
    rank_id = fields.Many2one(
        comodel_name="gamification.karma.rank",
        index="btree_not_null",
    )
    next_rank_id = fields.Many2one(comodel_name="gamification.karma.rank")

    # XP progress fields for UI display
    xp_to_next_rank = fields.Integer(
        string="XP to Next Rank",
        compute="_compute_xp_progress",
    )
    xp_progress_percent = fields.Float(
        string="XP Progress %",
        compute="_compute_xp_progress",
    )
    streak_ids = fields.One2many(
        comodel_name="gamification.streak",
        inverse_name="user_id",
        string="Streaks",
    )

    # Profile enhancements
    featured_badge_ids = fields.Many2many(
        comodel_name="gamification.badge.user",
        relation="gamification_featured_badge_rel",
        string="Featured Badges",
        help="Up to 3 badges showcased on the user's gamification profile.",
    )
    gamification_visibility = fields.Selection(
        selection=[
            ("private", "Private"),
            ("team", "Team Only"),
            ("public", "Public"),
        ],
        string="Profile Visibility",
        default="public",
        help="Keeps you out of the leaderboards, the activity feed, the mentor "
        "suggestions and other people's badge and achievement lists. It does "
        "not hide your karma or rank from someone who opens your user record.",
    )
    last_gamification_nudge_date = fields.Date(
        string="Last Nudge Date",
        help="Last date a gamification nudge was sent to this user.  "
        "Used to rate-limit nudges to at most once per week.",
    )

    @property
    def SELF_WRITEABLE_FIELDS(self) -> list[str]:
        """Let users control their own gamification privacy setting.

        Without this the field is rendered on the user's own profile form but
        rejected on write, so the only person who could not make a profile
        private was its owner.
        """
        return super().SELF_WRITEABLE_FIELDS + ["gamification_visibility"]

    @api.depends("karma_tracking_ids.new_value", "karma_tracking_ids.old_value")
    def _compute_karma(self) -> None:
        """Karma is the sum of every recorded gain.

        This deliberately sums ``new_value - old_value`` rather than taking the
        most recent row's ``new_value``.  "Latest row wins" silently dropped
        karma in two reachable cases: a row inserted with an older
        ``tracking_date`` never became the winner, and several rows created in
        one batch all chained from the same pre-batch value so only the last
        one counted.  Summing gains is also what every other consumer of this
        table already does (``_get_tracking_karma_gain_position``, the season
        leaderboard, the engagement snapshots), so the whole module now agrees
        on a single definition of karma.

        Consolidation is karma-neutral under this definition: collapsing a
        month of rows into one whose gain equals their total leaves the sum
        unchanged, which is why no "skip computation" escape hatch is needed.

        This computes karma and nothing else.  Re-ranking used to hang off the
        end of it, which put ``_rank_changed`` -- outbound mail, badge creation,
        activity rows and mentor payouts -- behind an ORM flush, reached through
        a stack of five recompute frames.  It now hangs off
        ``gamification.karma.tracking`` writes instead: that is the one table
        every karma change goes through, including the technical view, so the
        coverage is the same and the trigger is a place a reader can find.
        """
        self.env["gamification.karma.tracking"].flush_model()

        select_query = """
            SELECT user_id, COALESCE(SUM(new_value - COALESCE(old_value, 0)), 0)
              FROM gamification_karma_tracking
             WHERE user_id = ANY(%(user_ids)s)
          GROUP BY user_id
        """
        self.env.cr.execute(select_query, {"user_ids": self.ids})

        user_karma_map = dict(self.env.cr.fetchall())

        for user in self:
            user.karma = user_karma_map.get(user.id, 0)

    # `badge_ids` alone missed the level: re-grading a badge from bronze to gold
    # left every holder's counters on the old split until some unrelated grant
    # moved them.
    @api.depends("badge_ids", "badge_ids.badge_id.level")
    def _compute_badge_level_counts(self) -> None:
        """Count each user's badges per level (gold, silver, bronze)."""
        for user in self:
            user.gold_badge = 0
            user.silver_badge = 0
            user.bronze_badge = 0

        self.env.cr.execute(
            """
            SELECT bu.user_id, b.level, count(1)
            FROM gamification_badge_user bu, gamification_badge b
            WHERE bu.user_id = ANY(%s)
              AND bu.badge_id = b.id
              AND b.level IS NOT NULL
            GROUP BY bu.user_id, b.level
        """,
            [list(self.ids)],
        )

        for user_id, level, count in self.env.cr.fetchall():
            # levels are gold, silver, bronze but fields have _badge postfix
            self.browse(user_id)[f"{level}_badge"] = count

    @api.depends("karma", "rank_id", "next_rank_id")
    def _compute_xp_progress(self) -> None:
        """Compute XP progress toward the next rank for progress bar display."""
        for user in self:
            next_rank = user.next_rank_id or user._get_next_rank()
            if not next_rank or not user.rank_id:
                user.xp_to_next_rank = next_rank.karma_min if next_rank else 0
                user.xp_progress_percent = 0.0
                continue
            current_min = user.rank_id.karma_min
            next_min = next_rank.karma_min
            span = next_min - current_min
            if span <= 0:
                user.xp_to_next_rank = 0
                user.xp_progress_percent = 100.0
            else:
                user.xp_to_next_rank = max(next_min - user.karma, 0)
                user.xp_progress_percent = min(
                    100.0,
                    round(100.0 * (user.karma - current_min) / span, 1),
                )

    #: Upper bound for the ``limit`` of any gamification list a client can ask
    #: for over RPC.  These endpoints are public, so the parameter is attacker
    #: controlled and ``limit=10**9`` was a valid call.
    GAMIFICATION_MAX_LIMIT = 100

    @api.model
    def _gamification_clamp_limit(self, limit: int, default: int = 10) -> int:
        """Return a sane ``limit`` for a public gamification endpoint."""
        try:
            limit = int(limit)
        except TypeError, ValueError:
            return default
        return max(1, min(limit, self.GAMIFICATION_MAX_LIMIT))

    @api.model
    def _get_domain_gamification_listable(self) -> list[Any]:
        """Domain for users who may appear in a gamification list.

        One definition, four call sites.  It used to be four hand-written
        domains -- the leaderboard, the activity feed and the season board each
        filtered ``gamification_visibility``, and the mentor suggestions did
        not.  Three agreeing implementations of a rule is three chances for the
        fourth to disagree, and it did.
        """
        return [
            ("active", "=", True),
            ("share", "=", False),
            ("gamification_visibility", "!=", "private"),
        ]

    def _send_gamification_notification(
        self, notif_type: str, data: dict[str, Any]
    ) -> None:
        """Send a real-time bus notification for gamification events.

        :param notif_type: one of 'badge', 'streak', 'level_up', 'achievement'.
        :param data: notification payload (title, message, etc.).
        """
        bus = self.env["bus.bus"]
        for user in self:
            bus._sendone(
                user.partner_id,
                "gamification/notification",
                {
                    "type": notif_type,
                    **data,
                },
            )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        res = super().create(vals_list)

        self._add_karma_batch(
            {
                user: {
                    "gain": int(vals["karma"]),
                    "old_value": 0,
                    "reason": _("User Creation"),
                }
                for user, vals in zip(res, vals_list, strict=True)
                if vals.get("karma")
            }
        )

        return res

    def write(self, vals: ValuesType) -> Literal[True]:
        if "karma" in vals:
            # Record the change as a tracking entry and let ``_compute_karma``
            # (and the ``_recompute_rank`` it triggers) set the karma value.
            # Writing ``karma`` directly in ``vals`` would protect the stored
            # computed field from recomputation for these records, so the
            # tracking would be created but ``rank_id`` / ``next_rank_id`` would
            # stay stale until some later karma event.
            target = int(vals.pop("karma"))
            self._add_karma_batch(
                {
                    user: {"gain": target - user.karma}
                    for user in self
                    if target != user.karma
                }
            )
        return super().write(vals)

    def _add_karma(
        self, gain: int, source=None, reason: str | None = None
    ) -> bool | None:
        self.check_singleton()
        values = {"gain": gain, "source": source, "reason": reason}
        return self._add_karma_batch({self: values})

    def _add_karma_batch(
        self, values_per_user: dict[Any, dict[str, Any]]
    ) -> bool | None:
        if not values_per_user:
            return None

        create_values = []
        for user, values in values_per_user.items():
            origin = values.get("source") or self.env.user
            reason = values.get("reason") or _("Add Manually")
            origin_description = f"{origin.display_name} #{origin.id}"
            old_value = values.get("old_value", user.karma)

            create_values.append(
                {
                    "new_value": old_value + values["gain"],
                    "old_value": old_value,
                    "origin_ref": f"{origin._name},{origin.id}",
                    "reason": f"{reason} ({origin_description})",
                    "user_id": user.id,
                }
            )

        self.env["gamification.karma.tracking"].sudo().create(create_values)
        return True

    def _get_tracking_karma_gain_position(
        self,
        user_domain: list[Any],
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Get absolute position in term of gained karma for users. First a ranking
        of all users is done given a user_domain; then the position of each user
        belonging to the current record set is extracted.

        Example: in website profile, search users with name containing Norbert. Their
        positions should not be 1 to 4 (assuming 4 results), but their actual position
        in the karma gain ranking (with example user_domain being karma > 1,
        website published True).

        :param user_domain: general domain (i.e. active, karma > 1, website, ...)
          to compute the absolute position of the current record set
        :param from_date: compute karma gained after this date (included) or from
          beginning of time;
        :param to_date: compute karma gained before this date (included) or until
          end of time;

        :rtype: list[dict]
        :return:
          ::

            [{
                'user_id': user_id (belonging to current record set),
                'karma_gain_total': integer, karma gained in the given timeframe,
                'karma_position': integer, ranking position
            }, {..}]

          ordered by descending karma position
        """
        if not self:
            return []

        where_query = self.env["res.users"]._search(user_domain, bypass_access=True)

        sql = SQL(
            """
SELECT final.user_id, final.karma_gain_total, final.karma_position
FROM (
    SELECT intermediate.user_id, intermediate.karma_gain_total, row_number() OVER (ORDER BY intermediate.karma_gain_total DESC) AS karma_position
    FROM (
        SELECT "res_users".id as user_id, COALESCE(SUM("tracking".new_value - "tracking".old_value), 0) as karma_gain_total
        FROM %s
        LEFT JOIN "gamification_karma_tracking" as "tracking"
        ON "res_users".id = "tracking".user_id AND "res_users"."active" IS TRUE
        WHERE %s %s %s
        GROUP BY "res_users".id
        ORDER BY karma_gain_total DESC
    ) intermediate
) final
WHERE final.user_id = ANY(%s)""",
            where_query.from_clause,
            where_query.where_clause or SQL("TRUE"),
            SQL("AND tracking.tracking_date::DATE >= %s::DATE", from_date)
            if from_date
            else SQL(),
            SQL("AND tracking.tracking_date::DATE <= %s::DATE", to_date)
            if to_date
            else SQL(),
            list(self.ids),
        )

        self.env.cr.execute(sql)
        return self.env.cr.dictfetchall()

    def _get_karma_position(self, user_domain: list[Any]) -> list[dict[str, Any]]:
        """Get absolute position in term of total karma for users. First a ranking
        of all users is done given a user_domain; then the position of each user
        belonging to the current record set is extracted.

        Example: in website profile, search users with name containing Norbert. Their
        positions should not be 1 to 4 (assuming 4 results), but their actual position
        in the total karma ranking (with example user_domain being karma > 1,
        website published True).

        :param user_domain: general domain (i.e. active, karma > 1, website, ...)
          to compute the absolute position of the current record set

        :rtype: list[dict]
        :return:

            ::

                [{
                    'user_id': user_id (belonging to current record set),
                    'karma_position': integer, ranking position
                }, {..}] ordered by karma_position desc
        """
        if not self:
            return []

        where_query = self.env["res.users"]._search(user_domain, bypass_access=True)

        # we search on every user in the DB to get the real positioning (not the one inside the subset)
        # then, we filter to get only the subset.
        sql = SQL(
            """
SELECT sub.user_id, sub.karma_position
FROM (
    SELECT "res_users"."id" as user_id, row_number() OVER (ORDER BY res_users.karma DESC) AS karma_position
    FROM %s
    WHERE %s
) sub
WHERE sub.user_id = ANY(%s)""",
            where_query.from_clause,
            where_query.where_clause or SQL("TRUE"),
            list(self.ids),
        )
        self.env.cr.execute(sql)
        return self.env.cr.dictfetchall()

    def _rank_changed(self) -> None:
        """Notify users of a rank change and auto-grant the rank's badges.

        Batched throughout: one search for the already-granted badges, one
        ``create`` for the missing ones, one activity insert and one mentorship
        pass for the whole set.  The per-user shape cost a search, a create and
        a ``send_mail`` each, which is what a bulk re-rank multiplies.

        Skipped during module installation to avoid spamming.
        """
        if self.env.context.get("install_mode", False):
            return

        ranked = self.filtered("rank_id")
        if not ranked:
            return

        # --- badges the new ranks unlock, in two queries rather than 2N ---
        BadgeUser = self.env["gamification.badge.user"].sudo()
        wanted = {
            (user.id, badge.id)
            for user in ranked
            for badge in user.rank_id.unlock_badge_ids
        }
        if wanted:
            already = {
                (bu.user_id.id, bu.badge_id.id)
                for bu in BadgeUser.search(
                    [
                        ("user_id", "in", ranked.ids),
                        ("badge_id", "in", [badge_id for _uid, badge_id in wanted]),
                    ]
                )
            }
            if missing := wanted - already:
                BadgeUser.create(
                    [
                        {"user_id": user_id, "badge_id": badge_id}
                        for user_id, badge_id in sorted(missing)
                    ]
                )._send_badge()

        # --- bus notification: inherently per user, it targets their own feed ---
        for user in ranked:
            user._send_gamification_notification(
                "level_up",
                {
                    "title": _("Level Up!"),
                    "message": _("You reached %s!", user.rank_id.name),
                },
            )

        self.env["gamification.activity"]._log_batch(
            [
                {
                    "activity_type": "level_up",
                    "user_id": user.id,
                    "summary_args": {"rank": user.rank_id.name},
                }
                for user in ranked
            ]
        )

        self.env["gamification.mentorship"]._on_mentee_rank_up(ranked)

        template = self.env.ref(
            "gamification.mail_template_data_new_rank_reached", raise_if_not_found=False
        )
        if template:
            for user in ranked.filtered(lambda u: u.rank_id.karma_min > 0):
                template.send_mail(
                    user.id,
                    force_send=False,
                    email_layout_xmlid="mail.mail_notification_light",
                )

    def _recompute_rank_if_relevant(self) -> None:
        """Re-rank only the users a rank change could actually move.

        A user with no karma and no rank is already where they belong, and the
        callers of this are write hooks that fire on every karma event, so the
        filter is what keeps a bulk import from walking the whole user table.
        """
        # Filter in the caller's environment and only then sudo: `self.sudo()`
        # first hands back records in a *different* env, whose cache is empty, so
        # the filter re-reads karma and rank that the caller had already loaded.
        movable = self.filtered(lambda u: u.karma > 0 or u.rank_id)
        if movable:
            movable.sudo()._recompute_rank()

    def _recompute_rank(self) -> None:
        """Set rank_id and next_rank_id from karma, for the whole recordset.

        One query for the ranks and at most one write per distinct target rank,
        however many users are being re-ranked.

        What that does NOT do is make re-ranking flat: `_rank_changed` sends one
        bus message and queues one email per user who actually moved, and those
        are per recipient by nature. Re-ranking 60 users with every rank
        changing measured 385 queries here against 429 for the second
        implementation this replaces -- the saving is the writes and the badge
        search, not the notifications, and it is about 10%.

        That second implementation, ``_recompute_rank_bulk``, was dispatched to
        above ``len(ranks) * 3`` users because the original loop wrote once per
        user. Grouping by target rank removed its reason to exist, and it is
        deleted rather than left unreachable: it also skipped ``_rank_changed``
        for users dropping below the lowest rank, so the two paths did not agree
        on behaviour either.

        Callers should still pre-filter to users who can move; see
        ``_recompute_rank_if_relevant``.
        """
        ranks = [
            {"rank": rank, "karma_min": rank.karma_min}
            for rank in self.env["gamification.karma.rank"].search(
                [], order="karma_min DESC, id"
            )
        ]

        if not ranks:
            return

        # Group by the (rank, next_rank) pair each user lands on, so the whole
        # set costs one write and one _rank_changed per distinct rank rather
        # than one of each per user.
        by_target: dict[tuple[int | bool, int | bool], list[int]] = {}
        changed_ids: list[int] = []
        for user in self:
            for i, r in enumerate(ranks):
                if user.karma >= r["karma_min"]:
                    target = (
                        r["rank"].id,
                        ranks[i - 1]["rank"].id if i > 0 else False,
                    )
                    break
            else:
                # Karma below every rank — clear the rank, point at the lowest.
                target = (False, ranks[-1]["rank"].id)
            if (user.rank_id.id or False) != target[0]:
                changed_ids.append(user.id)
            by_target.setdefault(target, []).append(user.id)

        for (rank_id, next_rank_id), user_ids in by_target.items():
            self.browse(user_ids).write(
                {"rank_id": rank_id, "next_rank_id": next_rank_id}
            )

        if changed_ids:
            self.browse(changed_ids)._rank_changed()

    def _get_next_rank(self) -> models.Model:
        """Return the next karma rank for this user.

        For fresh users with 0 karma that don't yet have ``rank_id`` /
        ``next_rank_id``, returns the lowest-karma rank as a default.
        """
        if self.next_rank_id:
            return self.next_rank_id
        domain = [("karma_min", ">", self.rank_id.karma_min)] if self.rank_id else []
        return self.env["gamification.karma.rank"].search(
            domain, order="karma_min ASC", limit=1
        )

    def prepare_rank_email_links(self) -> list[dict[str, str]]:
        """Hook for other modules to add redirect buttons in the rank-reached email.

        :return: list of dicts with 'url' and 'label' keys,
            e.g. ``[{'url': '/forum', 'label': 'Go to Forum'}]``
        """
        self.check_singleton()
        return []

    def action_karma_report(self) -> dict[str, Any]:
        """Open the karma tracking history for this user."""
        self.check_singleton()
        return {
            "name": _("Karma Updates"),
            "res_model": "gamification.karma.tracking",
            "target": "current",
            "type": "ir.actions.act_window",
            "view_mode": "list",
            "context": {
                "default_user_id": self.id,
                "search_default_user_id": self.id,
            },
        }

    @api.model
    def get_gamification_dashboard_data(self) -> dict[str, Any]:
        """Aggregate all gamification data for the current user's dashboard.

        Returns a single dict consumed by the OWL dashboard component.
        Designed for one RPC round-trip.
        """
        user = self.env.user
        Streak = self.env["gamification.streak"]
        BadgeUser = self.env["gamification.badge.user"]
        AchUnlock = self.env["gamification.achievement.unlock"]
        Goal = self.env["gamification.goal"]

        # Creates any missing streak rows and hands back the whole set, so the
        # section below does not search for what we just built.
        user_streaks = Streak._get_user_streaks(user)

        # Profile
        next_rank = user.next_rank_id or user._get_next_rank()
        featured = [
            {
                "id": bu.id,
                "badge_name": bu.badge_id.name,
                "level": bu.level,
            }
            for bu in user.featured_badge_ids[:3]
        ]
        profile = {
            "user_name": user.name,
            "karma": user.karma,
            "rank_name": user.rank_id.name or _("Unranked"),
            "rank_image": user.rank_id.image_128 if user.rank_id else False,
            "next_rank_name": next_rank.name if next_rank else False,
            "xp_progress_percent": user.xp_progress_percent,
            "xp_to_next_rank": user.xp_to_next_rank,
            "gold_badge": user.gold_badge,
            "silver_badge": user.silver_badge,
            "bronze_badge": user.bronze_badge,
            "featured_badges": featured,
            "visibility": user.gamification_visibility,
        }

        # Active streaks
        streaks = [
            {
                "id": s.id,
                "name": s.streak_type_id.name,
                "current_count": s.current_count,
                "longest_count": s.longest_count,
                "state": s.state,
                "freeze_remaining": s.freeze_remaining,
            }
            for s in user_streaks
        ]

        # Active challenge goals
        goals = [
            {
                "id": g.id,
                "challenge_name": g.challenge_id.name or _("Personal Goal"),
                "definition_name": g.definition_id.name,
                "current": g.current,
                "target": g.target_goal,
                "completeness": g.completeness,
                "state": g.state,
                "end_date": g.end_date.isoformat() if g.end_date else False,
            }
            for g in Goal.search(
                [
                    ("user_id", "=", user.id),
                    ("state", "in", ["inprogress", "reached"]),
                    ("closed", "=", False),
                ],
                order="current desc",
                limit=10,
            )
        ]

        # Recent badges (last 10)
        badges = [
            {
                "id": bu.id,
                "badge_name": bu.badge_id.name,
                "level": bu.level,
                "date": bu.create_date.date().isoformat(),
                "sender_name": bu.sender_id.name if bu.sender_id else False,
            }
            for bu in BadgeUser.search(
                [
                    ("user_id", "=", user.id),
                ],
                order="create_date desc",
                limit=10,
            )
        ]

        # Unified activity feed (replaces kudos-only feed)
        activity_feed = self.env["gamification.activity"].get_activity_feed(limit=20)

        # Recent achievement unlocks
        achievements = [
            {
                "id": u.id,
                "name": u.achievement_id.name,
                "description": u.achievement_id.description,
                "rarity": u.rarity,
                "date": u.unlock_date.date().isoformat() if u.unlock_date else False,
            }
            for u in AchUnlock.search(
                [
                    ("user_id", "=", user.id),
                ],
                order="unlock_date desc",
                limit=10,
            )
        ]

        # Karma leaderboard (top 10 in same company)
        leaderboard = self._get_karma_leaderboard(limit=10)

        return {
            "profile": profile,
            "streaks": streaks,
            "goals": goals,
            "badges": badges,
            "activity_feed": activity_feed,
            "achievements": achievements,
            "leaderboard": leaderboard,
        }

    @api.model
    def _get_karma_leaderboard(self, limit=10):
        """Return top karma users in the current user's company.

        Respects ``gamification_visibility`` — private users are excluded.

        :param int limit: max entries to return.
        :return: list of dicts with user_id, user_name, karma, rank_name.
        """
        users = self.search(
            [
                ("company_id", "=", self.env.company.id),
                ("karma", ">", 0),
                *self._get_domain_gamification_listable(),
            ],
            order="karma desc",
            limit=self._gamification_clamp_limit(limit),
        )
        current_uid = self.env.uid
        return [
            {
                "user_id": u.id,
                "user_name": u.name,
                "karma": u.karma,
                "rank_name": u.rank_id.name or "",
                "is_current_user": u.id == current_uid,
            }
            for u in users
        ]

    @api.model
    def send_kudos_from_dashboard(self, recipient_id, category_id, message):
        """Create a kudos record directly from the dashboard.

        :param int recipient_id: target user id.
        :param int category_id: kudos category id.
        :param str message: recognition message.
        :return: dict with the created kudos summary.
        """
        kudos = self.env["gamification.kudos"].create(
            {
                "sender_id": self.env.uid,
                "recipient_id": recipient_id,
                "category_id": category_id,
                "message": message,
            }
        )
        return {
            "id": kudos.id,
            "sender_name": kudos.sender_id.name,
            "recipient_name": kudos.recipient_id.name,
            "category_name": kudos.category_id.name,
            "category_icon": kudos.category_id.icon,
            "message": kudos.message,
            "karma_granted": kudos.karma_granted,
        }

    # ── Engagement Nudges ───────────────────────────────────────────

    NUDGE_COOLDOWN_DAYS = 7

    def _mark_eligible_users_nudged(self) -> Self:
        """Return the subset of users eligible for a nudge (not nudged within cooldown).

        Also marks the returned users as nudged today so subsequent
        nudge methods in the same cron run won't double-send.
        """
        cutoff = fields.Date.today() - timedelta(days=self.NUDGE_COOLDOWN_DAYS)
        eligible = self.filtered(
            lambda u: (
                not u.last_gamification_nudge_date
                or u.last_gamification_nudge_date <= cutoff
            )
        )
        if eligible:
            eligible.sudo().write({"last_gamification_nudge_date": fields.Date.today()})
        return eligible

    @api.model
    def _cron_engagement_nudges(self):
        """Detect engagement patterns and send targeted nudges.

        Runs daily.  Checks for:
        - Streaks about to expire (1 freeze day left, no activity yesterday)
        - Users close to next rank (within 10% of karma threshold)
        - Goals close to completion (>80% but not reached)
        - Users inactive for 7+ days (had karma activity before)

        Each user receives at most one nudge per ``NUDGE_COOLDOWN_DAYS`` period.
        """
        self._nudge_streak_warning()
        self._nudge_close_to_rank()
        self._nudge_goals_almost_done()
        self._nudge_inactive_users()

    @api.model
    def _nudge_streak_warning(self):
        """Warn users whose streaks have 0 freeze days left."""
        streaks = self.env["gamification.streak"].search(
            [
                ("state", "=", "active"),
                ("freeze_remaining", "=", 0),
                ("current_count", ">=", 3),
            ]
        )
        eligible_users = streaks.mapped("user_id")._mark_eligible_users_nudged()
        if not eligible_users:
            return
        for streak in streaks.filtered(lambda s: s.user_id in eligible_users):
            streak.user_id._send_gamification_notification(
                "streak",
                {
                    "title": _("Streak at Risk!"),
                    "message": _(
                        "Your %(streak)s streak (%(days)s days) has no freeze days left!",
                        streak=streak.streak_type_id.name,
                        days=streak.current_count,
                    ),
                },
            )

    @api.model
    def _nudge_close_to_rank(self):
        """Notify users within 10% of their next rank."""
        # Push arithmetic filter to SQL instead of loading all users into Python
        self.env["res.users"].flush_model()
        self.env.cr.execute(
            """
            SELECT u.id
            FROM res_users u
            JOIN gamification_karma_rank r ON r.id = u.next_rank_id
            WHERE u.active IS TRUE
              AND u.share IS NOT TRUE
              AND u.karma > 0
              AND (r.karma_min - u.karma) BETWEEN 1 AND CEIL(r.karma_min * 0.10)
            """,
        )
        candidate_ids = [row[0] for row in self.env.cr.fetchall()]
        if not candidate_ids:
            return
        candidates = self.browse(candidate_ids)
        for user in candidates._mark_eligible_users_nudged():
            threshold = user.next_rank_id.karma_min
            distance = threshold - user.karma
            user._send_gamification_notification(
                "level_up",
                {
                    "title": _("Almost There!"),
                    "message": _(
                        "Only %(xp)s XP to reach %(rank)s!",
                        xp=distance,
                        rank=user.next_rank_id.name,
                    ),
                },
            )

    @api.model
    def _nudge_goals_almost_done(self):
        """Notify users with goals >80% complete (handles both 'higher' and 'lower' conditions)."""
        goals = self.env["gamification.goal"].search(
            [
                ("state", "=", "inprogress"),
                ("closed", "=", False),
                ("target_goal", ">", 0),
            ]
        )
        # Narrow to goals that actually warrant a nudge *before* asking who is
        # eligible: ``_mark_eligible_users_nudged`` marks the users it returns as nudged, so
        # calling it on every goal owner burned the weekly nudge budget of
        # users who were nowhere near completion and never got a message —
        # which also blocked them from the other three nudge types.
        almost_done = goals.filtered(lambda g: 80 <= g.completeness < 100)
        if not almost_done:
            return
        candidate_users = almost_done.mapped("user_id")._mark_eligible_users_nudged()
        if not candidate_users:
            return
        for goal in almost_done.filtered(lambda g: g.user_id in candidate_users):
            goal.user_id._send_gamification_notification(
                "badge",
                {
                    "title": _("So Close!"),
                    "message": _(
                        "%(goal)s is %(pct)s%% complete!",
                        goal=goal.definition_id.name,
                        pct=round(goal.completeness),
                    ),
                },
            )

    @api.model
    def _nudge_inactive_users(self):
        """Re-engage users who were active but haven't earned karma in 7+ days."""
        cutoff = fields.Date.today() - timedelta(days=7)
        cr = self.env.cr

        cr.execute(
            """
            SELECT DISTINCT t.user_id
            FROM gamification_karma_tracking t
            JOIN res_users u ON u.id = t.user_id
            WHERE u.active IS TRUE AND u.share IS NOT TRUE
              AND t.user_id NOT IN (
                  SELECT DISTINCT user_id
                  FROM gamification_karma_tracking
                  WHERE tracking_date >= %(cutoff)s
              )
              AND t.tracking_date >= %(older_cutoff)s
        """,
            {
                "cutoff": cutoff,
                "older_cutoff": cutoff - timedelta(days=23),
            },
        )

        user_ids = [row[0] for row in cr.fetchall()]
        if not user_ids:
            return

        for user in self.browse(user_ids)._mark_eligible_users_nudged():
            user._send_gamification_notification(
                "badge",
                {
                    "title": _("We Miss You!"),
                    "message": _(
                        "Your team is earning karma — come back and join the action!"
                    ),
                },
            )
