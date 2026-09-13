import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


# Recorded once per day by a cron job.  Stores aggregate statistics
# that would be expensive to compute on the fly.  Enables trend
# analysis: is gamification adoption growing?  Which mechanics are
# sticky?  Where do users drop off?
class GamificationEngagementSnapshot(models.Model):
    """Daily snapshot of gamification engagement metrics."""

    _name = "gamification.engagement.snapshot"
    _description = "Gamification Engagement Snapshot"
    _order = "snapshot_date desc"
    _rec_name = "snapshot_date"

    snapshot_date = fields.Date(
        string="Date",
        default=fields.Date.today,
        index=True,
        readonly=True,
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    # ── User Activity ───────────────────────────────────────────────
    total_users = fields.Integer(
        string="Total Internal Users",
        readonly=True,
    )
    users_with_karma = fields.Integer(
        string="Users with Karma > 0",
        readonly=True,
    )
    active_users_7d = fields.Integer(
        string="Active Users (7 days)",
        readonly=True,
        help="Users who earned karma in the last 7 days.",
    )
    active_users_30d = fields.Integer(
        string="Active Users (30 days)",
        readonly=True,
        help="Users who earned karma in the last 30 days.",
    )

    # ── Challenge & Goals ───────────────────────────────────────────
    active_challenges = fields.Integer(readonly=True)
    goals_in_progress = fields.Integer(readonly=True)
    goals_reached_7d = fields.Integer(
        string="Goals Reached (7 days)",
        readonly=True,
        help="Goals that reached their target in the last 7 days.",
    )
    goal_completion_rate = fields.Float(
        string="Goal Completion Rate %",
        readonly=True,
        help="Percentage of non-draft, non-canceled goals that are reached.",
    )

    # ── Badges ──────────────────────────────────────────────────────
    total_badges_granted = fields.Integer(readonly=True)
    badges_granted_7d = fields.Integer(
        string="Badges Granted (7 days)",
        readonly=True,
    )
    unique_badge_holders = fields.Integer(readonly=True)

    # ── Kudos ───────────────────────────────────────────────────────
    total_kudos = fields.Integer(
        string="Total Kudos Sent",
        readonly=True,
    )
    kudos_7d = fields.Integer(
        string="Kudos Sent (7 days)",
        readonly=True,
    )
    unique_kudos_senders_7d = fields.Integer(
        string="Unique Kudos Senders (7 days)",
        readonly=True,
    )
    unique_kudos_recipients_7d = fields.Integer(
        string="Unique Kudos Recipients (7 days)",
        readonly=True,
    )

    # ── Streaks ─────────────────────────────────────────────────────
    active_streaks = fields.Integer(readonly=True)
    broken_streaks = fields.Integer(readonly=True)
    avg_streak_length = fields.Float(
        string="Avg Active Streak Length (days)",
        readonly=True,
    )
    streaks_past_7d = fields.Integer(
        string="Streaks >= 7 days",
        readonly=True,
        help="Active streaks that have survived at least 7 days.",
    )
    streaks_past_30d = fields.Integer(
        string="Streaks >= 30 days",
        readonly=True,
        help="Active streaks that have survived at least 30 days.",
    )

    # ── Achievements ────────────────────────────────────────────────
    total_unlocks = fields.Integer(
        string="Total Achievement Unlocks",
        readonly=True,
    )
    unlocks_7d = fields.Integer(
        string="Achievement Unlocks (7 days)",
        readonly=True,
    )

    # ── Karma ───────────────────────────────────────────────────────
    total_karma_granted = fields.Integer(readonly=True)
    karma_granted_7d = fields.Integer(
        string="Karma Granted (7 days)",
        readonly=True,
    )
    avg_user_karma = fields.Float(readonly=True)

    _snapshot_date_company_uniq = models.UniqueIndex(
        "(snapshot_date, company_id) WHERE company_id IS NOT NULL",
        "Only one snapshot per company per day.",
    )

    @api.model
    def _cron_record_snapshot(self):
        """Record a daily engagement snapshot for each company."""
        companies = self.env["res.company"].search([])
        for company in companies:
            self._record_snapshot(company)

    def _record_snapshot(self, company):
        """Compute and store engagement metrics for a single company.

        :param company: ``res.company`` record.
        :return: created ``gamification.engagement.snapshot`` record.
        """
        today = fields.Date.today()

        # Skip if already recorded today
        existing = self.search(
            [
                ("snapshot_date", "=", today),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        if existing:
            return existing

        # Every query below reads through `cr.execute`, which does not flush.
        # `res_users.karma` in particular is a stored compute, so a snapshot
        # taken in the same transaction as a karma grant read the pre-grant
        # column. The cron runs after the streak and achievement crons by
        # design, which is exactly when there is pending work to miss.
        self.env.flush_all()

        cr = self.env.cr
        d7 = today - timedelta(days=7)
        d30 = today - timedelta(days=30)

        # ── User metrics ────────────────────────────────────────────
        cr.execute(
            """
            SELECT
                COUNT(*) AS total_users,
                COUNT(*) FILTER (WHERE karma > 0) AS users_with_karma,
                COALESCE(AVG(karma) FILTER (WHERE karma > 0), 0) AS avg_user_karma
            FROM res_users
            WHERE active IS TRUE AND share IS NOT TRUE
              AND company_id = %(company_id)s
        """,
            {"company_id": company.id},
        )
        user_row = cr.dictfetchone()

        # Active users: those with karma tracking entries in the period
        cr.execute(
            """
            SELECT
                COUNT(DISTINCT user_id) FILTER (
                    WHERE tracking_date >= %(d7)s
                ) AS active_7d,
                COUNT(DISTINCT user_id) FILTER (
                    WHERE tracking_date >= %(d30)s
                ) AS active_30d
            FROM gamification_karma_tracking t
            JOIN res_users u ON u.id = t.user_id
            WHERE u.company_id = %(company_id)s
              AND u.active IS TRUE AND u.share IS NOT TRUE
        """,
            {"company_id": company.id, "d7": d7, "d30": d30},
        )
        activity_row = cr.dictfetchone()

        # ── Challenge & Goal metrics ────────────────────────────────
        cr.execute(
            """
            SELECT COUNT(DISTINCT gc.id) AS active_challenges
            FROM gamification_challenge gc
            JOIN gamification_challenge_users_rel rel
                ON rel.gamification_challenge_id = gc.id
            JOIN res_users u ON u.id = rel.res_users_id
            WHERE gc.state = 'inprogress'
              AND u.company_id = %(company_id)s
        """,
            {"company_id": company.id},
        )
        challenge_row = cr.dictfetchone()

        cr.execute(
            """
            SELECT
                COUNT(*) FILTER (
                    WHERE state = 'inprogress'
                ) AS goals_in_progress,
                COUNT(*) FILTER (
                    WHERE state = 'reached'
                    AND last_update >= %(d7)s
                ) AS goals_reached_7d,
                CASE
                    WHEN COUNT(*) FILTER (
                        WHERE state IN ('inprogress', 'reached', 'failed')
                    ) > 0
                    THEN 100.0 * COUNT(*) FILTER (WHERE state = 'reached')
                        / COUNT(*) FILTER (
                            WHERE state IN ('inprogress', 'reached', 'failed')
                        )
                    ELSE 0
                END AS goal_completion_rate
            FROM gamification_goal g
            JOIN res_users u ON u.id = g.user_id
            WHERE u.company_id = %(company_id)s
        """,
            {"company_id": company.id, "d7": d7},
        )
        goal_row = cr.dictfetchone()

        # ── Badge metrics ───────────────────────────────────────────
        cr.execute(
            """
            SELECT
                COUNT(*) AS total_badges_granted,
                COUNT(*) FILTER (
                    WHERE bu.create_date::date >= %(d7)s
                ) AS badges_granted_7d,
                COUNT(DISTINCT bu.user_id) AS unique_badge_holders
            FROM gamification_badge_user bu
            JOIN res_users u ON u.id = bu.user_id
            WHERE u.company_id = %(company_id)s
        """,
            {"company_id": company.id, "d7": d7},
        )
        badge_row = cr.dictfetchone()

        # ── Kudos metrics ───────────────────────────────────────────
        cr.execute(
            """
            SELECT
                COUNT(*) AS total_kudos,
                COUNT(*) FILTER (
                    WHERE k.create_date::date >= %(d7)s
                ) AS kudos_7d,
                COUNT(DISTINCT k.sender_id) FILTER (
                    WHERE k.create_date::date >= %(d7)s
                ) AS unique_senders_7d,
                COUNT(DISTINCT k.recipient_id) FILTER (
                    WHERE k.create_date::date >= %(d7)s
                ) AS unique_recipients_7d
            FROM gamification_kudos k
            JOIN res_users u ON u.id = k.sender_id
            WHERE u.company_id = %(company_id)s
        """,
            {"company_id": company.id, "d7": d7},
        )
        kudos_row = cr.dictfetchone()

        # ── Streak metrics ──────────────────────────────────────────
        cr.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE s.state = 'active') AS active_streaks,
                COUNT(*) FILTER (WHERE s.state = 'broken') AS broken_streaks,
                COALESCE(AVG(s.current_count) FILTER (
                    WHERE s.state = 'active'
                ), 0) AS avg_streak_length,
                COUNT(*) FILTER (
                    WHERE s.state = 'active' AND s.current_count >= 7
                ) AS streaks_past_7d,
                COUNT(*) FILTER (
                    WHERE s.state = 'active' AND s.current_count >= 30
                ) AS streaks_past_30d
            FROM gamification_streak s
            JOIN res_users u ON u.id = s.user_id
            WHERE u.company_id = %(company_id)s
        """,
            {"company_id": company.id},
        )
        streak_row = cr.dictfetchone()

        # ── Achievement metrics ─────────────────────────────────────
        cr.execute(
            """
            SELECT
                COUNT(*) AS total_unlocks,
                COUNT(*) FILTER (
                    WHERE au.unlock_date::date >= %(d7)s
                ) AS unlocks_7d
            FROM gamification_achievement_unlock au
            JOIN res_users u ON u.id = au.user_id
            WHERE u.company_id = %(company_id)s
        """,
            {"company_id": company.id, "d7": d7},
        )
        unlock_row = cr.dictfetchone()

        # ── Karma aggregate ─────────────────────────────────────────
        cr.execute(
            """
            SELECT
                COALESCE(SUM(GREATEST(new_value - old_value, 0)), 0) AS total_karma,
                COALESCE(SUM(GREATEST(new_value - old_value, 0)) FILTER (
                    WHERE tracking_date >= %(d7)s
                ), 0) AS karma_7d
            FROM gamification_karma_tracking t
            JOIN res_users u ON u.id = t.user_id
            WHERE u.company_id = %(company_id)s
        """,
            {"company_id": company.id, "d7": d7},
        )
        karma_row = cr.dictfetchone()

        return self.sudo().create(
            {
                "snapshot_date": today,
                "company_id": company.id,
                # Users
                "total_users": user_row["total_users"],
                "users_with_karma": user_row["users_with_karma"],
                "avg_user_karma": round(user_row["avg_user_karma"], 1),
                "active_users_7d": activity_row["active_7d"],
                "active_users_30d": activity_row["active_30d"],
                # Challenges & Goals
                "active_challenges": challenge_row["active_challenges"],
                "goals_in_progress": goal_row["goals_in_progress"],
                "goals_reached_7d": goal_row["goals_reached_7d"],
                "goal_completion_rate": round(goal_row["goal_completion_rate"], 1),
                # Badges
                "total_badges_granted": badge_row["total_badges_granted"],
                "badges_granted_7d": badge_row["badges_granted_7d"],
                "unique_badge_holders": badge_row["unique_badge_holders"],
                # Kudos
                "total_kudos": kudos_row["total_kudos"],
                "kudos_7d": kudos_row["kudos_7d"],
                "unique_kudos_senders_7d": kudos_row["unique_senders_7d"],
                "unique_kudos_recipients_7d": kudos_row["unique_recipients_7d"],
                # Streaks
                "active_streaks": streak_row["active_streaks"],
                "broken_streaks": streak_row["broken_streaks"],
                "avg_streak_length": round(streak_row["avg_streak_length"], 1),
                "streaks_past_7d": streak_row["streaks_past_7d"],
                "streaks_past_30d": streak_row["streaks_past_30d"],
                # Achievements
                "total_unlocks": unlock_row["total_unlocks"],
                "unlocks_7d": unlock_row["unlocks_7d"],
                # Karma
                "total_karma_granted": karma_row["total_karma"],
                "karma_granted_7d": karma_row["karma_7d"],
            }
        )

    @api.model
    def get_analytics_summary(self):
        """Return the latest snapshot + trend data for the dashboard.

        Compares the most recent snapshot with the one from 7 days ago
        to produce directional trends (up/down/flat).

        :return: dict with 'current' snapshot data and 'trends' dict.
        """
        today = fields.Date.today()
        company_id = self.env.company.id

        current = self.search(
            [
                ("company_id", "=", company_id),
            ],
            limit=1,
            order="snapshot_date desc",
        )

        previous = self.search(
            [
                ("company_id", "=", company_id),
                ("snapshot_date", "<=", today - timedelta(days=7)),
            ],
            limit=1,
            order="snapshot_date desc",
        )

        if not current:
            return {"current": {}, "trends": {}}

        trend_fields = [
            "active_users_7d",
            "goals_reached_7d",
            "badges_granted_7d",
            "kudos_7d",
            "active_streaks",
            "unlocks_7d",
            "karma_granted_7d",
            "goal_completion_rate",
        ]
        trends = {}
        for field_name in trend_fields:
            cur_val = current[field_name] or 0
            prev_val = (previous[field_name] or 0) if previous else 0
            if prev_val == 0:
                trends[field_name] = "new" if cur_val > 0 else "flat"
            elif cur_val > prev_val:
                trends[field_name] = "up"
            elif cur_val < prev_val:
                trends[field_name] = "down"
            else:
                trends[field_name] = "flat"

        return {
            "current": {
                "snapshot_date": current.snapshot_date.isoformat(),
                "total_users": current.total_users,
                "users_with_karma": current.users_with_karma,
                "active_users_7d": current.active_users_7d,
                "active_users_30d": current.active_users_30d,
                "active_challenges": current.active_challenges,
                "goals_in_progress": current.goals_in_progress,
                "goals_reached_7d": current.goals_reached_7d,
                "goal_completion_rate": current.goal_completion_rate,
                "total_badges_granted": current.total_badges_granted,
                "badges_granted_7d": current.badges_granted_7d,
                "unique_badge_holders": current.unique_badge_holders,
                "total_kudos": current.total_kudos,
                "kudos_7d": current.kudos_7d,
                "unique_kudos_senders_7d": current.unique_kudos_senders_7d,
                "active_streaks": current.active_streaks,
                "avg_streak_length": current.avg_streak_length,
                "streaks_past_7d": current.streaks_past_7d,
                "streaks_past_30d": current.streaks_past_30d,
                "total_unlocks": current.total_unlocks,
                "unlocks_7d": current.unlocks_7d,
                "total_karma_granted": current.total_karma_granted,
                "karma_granted_7d": current.karma_granted_7d,
                "avg_user_karma": current.avg_user_karma,
            },
            "trends": trends,
        }
