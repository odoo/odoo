import logging
from datetime import UTC, date, datetime, time, timedelta
from typing import Self

from psycopg import IntegrityError

from odoo import _, api, exceptions, fields, models
from odoo.libs.datetime import timezone
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

# Milestone days and their karma bonus multipliers.
# At day 7 the user gets base_karma * 2, at day 30 base_karma * 5, etc.
STREAK_MILESTONES = {
    7: 2,
    30: 5,
    100: 10,
    365: 25,
}


# Each streak type specifies an ORM domain evaluated daily per user.
# If the domain matches at least one record created/modified on the
# previous day, the streak continues; otherwise it breaks.
class GamificationStreakType(models.Model):
    """Configurable streak type defining what activity sustains the streak."""

    _name = "gamification.streak.type"
    _description = "Gamification Streak Type"
    _order = "sequence, name"

    name = fields.Char(
        string="Streak Name",
        translate=True,
        required=True,
    )
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    icon = fields.Image(
        max_width=128,
        max_height=128,
    )

    # What counts as "activity" for this streak
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Target Model",
        required=True,
        ondelete="cascade",
        help="The model where activity is tracked (e.g. crm.lead, account.move).",
    )
    model_name = fields.Char(related="model_id.model")
    domain = fields.Char(
        string="Activity Domain",
        default="[]",
        required=True,
        help="Domain to filter records.  May reference 'user' (current user) "
        "and 'date_from' / 'date_to' (the day being checked).\n"
        "Every candidate user whose domain evaluates to the same text shares "
        "one query and its answer: if the domain does not reference 'user' "
        "at all, that is every candidate, so a single day's activity (or "
        "lack of it) is credited -- or the streak broken -- for the whole "
        "population at once, not per person. That is a deliberate, "
        "supported shape for a company-wide/shared streak (e.g. 'did "
        "anyone log a sale today'); it is a misconfiguration if a per-user "
        "streak was intended.",
    )
    date_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        required=True,
        ondelete="cascade",
        help="The date/datetime field used to check daily activity.",
    )

    # Rewards
    karma_bonus = fields.Integer(
        string="Daily Karma Bonus",
        default=0,
        help="Karma granted each day the streak is maintained.  "
        "Milestone days (7, 30, 100, 365) multiply this value.",
    )
    freeze_allowance = fields.Integer(
        string="Freeze Days per Month",
        default=2,
        help="Number of days per month a user can skip without breaking the streak.",
    )

    streak_ids = fields.One2many(
        comodel_name="gamification.streak",
        inverse_name="streak_type_id",
        string="User Streaks",
    )
    user_count = fields.Integer(
        string="# Active Streaks",
        compute="_compute_user_count",
    )

    @api.depends("streak_ids.state")
    def _compute_user_count(self) -> None:
        """Count active streaks per type."""
        if not self.ids:
            for rec in self:
                rec.user_count = 0
            return
        data = self.env["gamification.streak"]._read_group(
            [("streak_type_id", "in", self.ids), ("state", "=", "active")],
            groupby=["streak_type_id"],
            aggregates=["__count"],
        )
        count_map = {st.id: count for st, count in data}
        for rec in self:
            rec.user_count = count_map.get(rec.id, 0)

    def _check_user_activity(self, user: models.Model, check_date: date) -> bool:
        """Check if *user* performed the required activity on *check_date*.

        :param user: ``res.users`` record.
        :param check_date: ``date`` to check.
        :return: ``True`` if the domain matches at least one record.
        """
        self.check_singleton()
        return user.id in self._check_user_activity_batch(user, check_date)

    def _check_user_activity_batch(
        self, users: models.Model, check_date: date
    ) -> set[int]:
        """Check activity for many users at once, returning the active user IDs.

        One query per *distinct evaluated domain*, not one per user.

        The previous shape sampled ``users[0]`` against ``users[1]`` to guess
        whether the domain referenced ``user``, and took a single global query if
        they matched.  Two things were wrong with it.  It compared the
        date-augmented first domain against the bare second one, so the guess was
        always "user-specific" and the fast path was unreachable -- the batch ran
        one query per user regardless.  And repairing only that comparison would
        have introduced a real defect: a two-user sample cannot speak for a third
        user whose domain differs, so everyone in the batch would have been judged
        by ``users[0]``'s domain.  Grouping by the domain each user actually
        evaluates to needs no sampling, is correct for every domain shape, and
        still collapses the common cases (a constant domain, or one keyed on a
        handful of companies) to one or two queries.

        :param users: ``res.users`` recordset to check.
        :param check_date: ``date`` to check.
        :return: set of user IDs that had qualifying activity.
        """
        self.check_singleton()
        if not users:
            return set()

        # "Did you show up on day D?" is a calendar-day question, so the window
        # is built in the *user's* timezone and only then converted to UTC for
        # the query.  Storage stays UTC throughout -- this mirrors
        # ``lunch.supplier._compute_available_today`` and
        # ``hr.employee._get_schedule_tz``, which resolve the relevant record's tz in
        # backend/cron code for exactly this reason.
        #
        # Note ``fields.Date.context_today`` is deliberately *not* used: it
        # reads ``env.tz``, which in a cron is the cron user's timezone, not
        # the streak owner's.
        Obj = self.env[self.model_id.model].sudo()
        date_field = self.date_field_id.name

        # (tz, evaluated domain) -> user ids sharing it
        buckets: dict[tuple[str, str], tuple[list, list[int]]] = {}
        for user in users:
            tz_name = self._get_streak_tz_name(user)
            date_from, date_to = self._get_day_bounds_utc(check_date, tz_name)
            domain = safe_eval(
                self.domain,
                {"user": user, "date_from": date_from, "date_to": date_to},
            )
            domain += [
                (date_field, ">=", date_from),
                (date_field, "<=", date_to),
            ]
            key = (tz_name, repr(domain))
            buckets.setdefault(key, (domain, []))[1].append(user.id)

        active_ids: set[int] = set()
        for domain, user_ids in buckets.values():
            if Obj.search_count(domain, limit=1):  # noqa: E8507 - one query per distinct domain; users sharing one were merged above
                active_ids.update(user_ids)
        return active_ids

    def _get_streak_tz_name(self, user) -> str:
        """Return the timezone whose calendar day defines this user's streak.

        Falls back the same way ``hr.employee._get_schedule_tz`` does, ending in UTC so
        the behaviour is unchanged for users with no timezone set.
        """
        return user.tz or user.company_id.partner_id.tz or "UTC"

    def _get_day_bounds_utc(self, check_date: date, tz_name: str) -> tuple[str, str]:
        """Return the naive-UTC ``[start, end]`` strings bounding ``check_date``
        as that day is experienced in ``tz_name``.
        """
        tz = timezone(tz_name)
        start_local = datetime.combine(check_date, time.min).replace(tzinfo=tz)
        end_local = datetime.combine(check_date, time.max).replace(tzinfo=tz)
        return (
            fields.Datetime.to_string(start_local.astimezone(UTC).replace(tzinfo=None)),
            fields.Datetime.to_string(end_local.astimezone(UTC).replace(tzinfo=None)),
        )


class GamificationStreak(models.Model):
    """Per-user streak instance tracking consecutive daily activity."""

    _name = "gamification.streak"
    _description = "User Activity Streak"
    _order = "current_count desc, id"
    _rec_name = "streak_type_id"

    user_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.uid,
        index=True,
        required=True,
        ondelete="cascade",
    )
    streak_type_id = fields.Many2one(
        comodel_name="gamification.streak.type",
        index=True,
        required=True,
        ondelete="cascade",
    )
    current_count = fields.Integer(
        string="Current Streak",
        default=0,
        readonly=True,
    )
    longest_count = fields.Integer(
        string="Longest Streak",
        default=0,
        readonly=True,
    )
    last_activity_date = fields.Date(
        string="Last Activity",
        readonly=True,
    )
    last_checked_date = fields.Date(
        string="Last Checked",
        index=True,
        readonly=True,
        help="Day the streak cron last evaluated this streak, whatever the "
        "outcome. Used to make the cron idempotent.",
    )
    freeze_remaining = fields.Integer(
        string="Freeze Days Left",
        default=0,
        help="Days remaining this month where the streak won't break.",
    )
    state = fields.Selection(
        selection=[("active", "Active"), ("broken", "Broken")],
        default="active",
        index=True,
        readonly=True,
        required=True,
    )
    total_karma_earned = fields.Integer(
        default=0,
        readonly=True,
    )

    _user_streak_type_uniq = models.UniqueIndex(
        "(user_id, streak_type_id)",
        "A user can only have one streak per type.",
    )

    @api.depends("streak_type_id", "current_count")
    def _compute_display_name(self) -> None:
        """Display as 'Streak Name — 42 days'."""
        for rec in self:
            rec.display_name = f"{rec.streak_type_id.name} — {rec.current_count} days"

    def _record_activity(self) -> None:
        """Credit today's activity to every streak in the recordset.

        Batched: one karma write cycle and one activity insert for the whole
        set, not one per streak.  The cron calls this with every streak of a
        type that qualified today, so the per-streak shape multiplied a tracking
        INSERT, a karma recompute and a rank re-evaluation by the number of
        people holding the streak.
        """
        today = fields.Date.today()
        due = self.filtered(lambda s: s.last_activity_date != today)
        if not due:
            return

        # karma_per_user below is keyed by user_id alone: only the first
        # streak processed for a given user supplies `source`/`reason`, so
        # this method silently misattributes if `due` ever holds two
        # different-type streaks for the same user. The sole caller
        # (`_cron_update_streaks`) groups by streak_type_id before calling
        # this, and `_user_streak_type_uniq` caps one streak per user per
        # type, so today this can't happen -- guard it explicitly so a
        # future caller can't silently reintroduce the collision.
        if len(due) != len(due.user_id):
            raise exceptions.UserError(
                _(
                    "_record_activity() received more than one streak for the"
                    " same user in a single call; karma attribution would be"
                    " ambiguous."
                )
            )

        karma_per_user: dict = {}
        feed_entries = []
        for streak in due:
            streak.current_count += 1
            streak.last_activity_date = today
            streak.longest_count = max(streak.longest_count, streak.current_count)
            if streak.state == "broken":
                streak.state = "active"

            karma = streak.streak_type_id.karma_bonus
            if not karma:
                continue
            total = karma * STREAK_MILESTONES.get(streak.current_count, 1)
            entry = karma_per_user.setdefault(
                streak.user_id,
                {
                    "gain": 0,
                    "source": streak,
                    "reason": _(
                        "Streak day %(day)s: %(streak)s",
                        day=streak.current_count,
                        streak=streak.streak_type_id.name,
                    ),
                },
            )
            entry["gain"] += total
            streak.total_karma_earned += total

            if streak.current_count in STREAK_MILESTONES:
                streak.user_id._send_gamification_notification(
                    "streak",
                    {
                        "title": _("Streak Milestone!"),
                        "message": _(
                            "%(streak)s — %(days)s days!",
                            streak=streak.streak_type_id.name,
                            days=streak.current_count,
                        ),
                    },
                )
                feed_entries.append(
                    {
                        "activity_type": "streak_milestone",
                        "user_id": streak.user_id.id,
                        "karma_gained": total,
                        "summary_args": {
                            "days": streak.current_count,
                            "streak": streak.streak_type_id.name,
                        },
                    }
                )

        if karma_per_user:
            self.env["res.users"].sudo()._add_karma_batch(karma_per_user)
        if feed_entries:
            self.env["gamification.activity"]._log_batch(feed_entries)

    def _break_streak(self) -> None:
        """Break the streak — reset current count but preserve longest."""
        self.write(
            {
                "state": "broken",
                "current_count": 0,
            }
        )

    @api.model
    def _cron_update_streaks(self) -> None:
        """Daily cron: check all active streaks and break those without activity.

        For each active streak, checks if the user had qualifying activity
        yesterday.  If not, uses a freeze day or breaks the streak.
        Also resets freeze allowance on the 1st of each month.
        """
        today = fields.Date.today()
        yesterday = today - timedelta(days=1)

        # Reset freeze allowance on 1st of month — batch by type.
        #
        # Includes 'broken' streaks, not just 'active' ones: a streak that
        # revives later in *this same run* (see the activity check below)
        # would otherwise skip this month's freeze allowance entirely --
        # the reset ran before the revival and there is no second pass.
        if today.day == 1:
            streaks_to_reset = self.search([("state", "in", ["active", "broken"])])
            # Group by streak type for batch writes
            by_type: dict[int, list[int]] = {}
            for streak in streaks_to_reset:
                by_type.setdefault(streak.streak_type_id.id, []).append(streak.id)
            for type_id, streak_ids in by_type.items():
                stype = self.env["gamification.streak.type"].browse(type_id)
                self.browse(streak_ids).write(
                    {"freeze_remaining": stype.freeze_allowance}
                )

        # Check active and broken streaks — broken ones can revive if the
        # user performed qualifying activity yesterday.
        #
        # The re-entry guard is ``last_checked_date``, not
        # ``last_activity_date``: the latter only advances when activity is
        # *found*, so the freeze and break branches were not idempotent.  A
        # second run on the same day (an admin using "Run Manually", or a cron
        # retry) burned another freeze day, and a third broke a streak the user
        # had never actually missed.
        active_streaks = self.search(
            [
                ("state", "in", ["active", "broken"]),
                "|",
                ("last_checked_date", "<", today),
                ("last_checked_date", "=", False),
            ]
        )

        # Resolve activity once per streak TYPE over all its users.  The per-
        # streak call this replaces cost a measured 4.2 queries for every extra
        # streak, on a workload whose correct marginal cost is zero: one streak
        # type with a constant domain is one question, however many people hold
        # a streak of it.
        for streak_type, streaks in active_streaks.grouped("streak_type_id").items():
            try:
                with self.env.cr.savepoint():
                    active_user_ids = streak_type._check_user_activity_batch(
                        streaks.user_id, yesterday
                    )
            except Exception:
                _logger.exception(
                    "Streak type %r (id %s) failed to evaluate activity for %s "
                    "streak(s); skipping it and continuing the run.",
                    streak_type.name,
                    streak_type.id,
                    len(streaks),
                )
                continue

            qualified = streaks.filtered(
                lambda s, ok=active_user_ids: s.user_id.id in ok
            )
            # One savepoint for the whole type, not one per streak: the karma
            # grant and the feed insert are batched below, so a failure inside
            # them is not attributable to a single streak anyway.
            try:
                with self.env.cr.savepoint():
                    qualified._record_activity()
                    for streak in streaks - qualified:
                        self._process_missed_day(streak)
                    streaks.last_checked_date = today
            except Exception:
                _logger.exception(
                    "Streak run failed for type %r (id %s) over %s streak(s); "
                    "skipping it and continuing the run.",
                    streak_type.name,
                    streak_type.id,
                    len(streaks),
                )

    def _process_missed_day(self, streak) -> None:
        """Freeze or break one streak whose owner did not qualify.

        :param streak: the ``gamification.streak`` to freeze or break.
        """
        if streak.state == "broken":
            # Already broken — nothing to freeze or break further
            return
        if streak.freeze_remaining > 0:
            streak.freeze_remaining -= 1
            _logger.info(
                "Streak freeze used: %s for user %s (%s remaining)",
                streak.streak_type_id.name,
                streak.user_id.login,
                streak.freeze_remaining,
            )
            return
        _logger.info(
            "Streak broken: %s for user %s (was %s days)",
            streak.streak_type_id.name,
            streak.user_id.login,
            streak.current_count,
        )
        streak._break_streak()

    @api.model
    def _get_user_streaks(self, user: models.Model | None = None) -> Self:
        """Return this user's streaks, creating any that do not exist yet.

        Called when a user first accesses gamification features.  A single query
        finds the active streak types the user has no row for.

        :param user: the owner; defaults to the current user.
        :return: every ``gamification.streak`` the user now holds.
        """
        user = user or self.env.user
        self.env.cr.execute(
            """
            SELECT st.id, st.freeze_allowance
            FROM gamification_streak_type st
            WHERE st.active IS TRUE
              AND NOT EXISTS (
                  SELECT 1 FROM gamification_streak gs
                  WHERE gs.streak_type_id = st.id AND gs.user_id = %s
              )
            """,
            [user.id],
        )
        missing = self.env.cr.fetchall()
        if missing:
            # Two concurrent first-visits (two tabs, a double-click) can both
            # see the same "missing" list and both try to create it: the
            # second insert hits `_user_streak_type_uniq` and would otherwise
            # raise instead of just returning the streak the first insert
            # already made. One savepoint for the whole batch, matching the
            # per-batch savepoint style already used by the streak cron above.
            try:
                with self.env.cr.savepoint():
                    self.sudo().create(
                        [
                            {
                                "user_id": user.id,
                                "streak_type_id": type_id,
                                "freeze_remaining": freeze_allowance,
                            }
                            for type_id, freeze_allowance in missing
                        ]
                    )
            except IntegrityError:
                pass
        return self.search([("user_id", "=", user.id)], order="current_count desc")
