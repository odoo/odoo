from datetime import datetime
from typing import Literal, Self

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.models import ValuesType
from odoo.tools import date_utils

#: Writing any of these changes a recorded gain, and therefore someone's karma.
KARMA_VALUE_FIELDS = frozenset({"gain", "new_value", "old_value", "user_id"})


# Each record represents a single karma change event.  The ``new_value``
# field is the user's karma *after* the change; ``gain`` is computed as
# ``new_value - old_value``.  Monthly consolidation compresses old records
# into one-per-user-per-month summaries.
class GamificationKarmaTracking(models.Model):
    """Audit log of all karma changes with source attribution."""

    _name = "gamification.karma.tracking"
    _description = "Track Karma Changes"
    _rec_name = "user_id"
    _order = "tracking_date desc, id desc"

    def _selection_origin_models(self) -> list[tuple[str, str]]:
        return [
            ("res.users", _("User")),
            ("gamification.streak", _("Streak")),
            ("gamification.kudos", _("Kudos")),
            ("gamification.achievement.unlock", _("Achievement")),
            ("gamification.quest.enrollment", _("Quest")),
            ("gamification.skill.node.unlock", _("Skill")),
            ("gamification.mentorship", _("Mentorship")),
        ]

    user_id = fields.Many2one(
        comodel_name="res.users",
        index=True,
        required=True,
        ondelete="cascade",
    )
    old_value = fields.Integer(
        string="Old Karma Value",
        readonly=True,
    )
    new_value = fields.Integer(
        string="New Karma Value",
        required=True,
    )
    gain = fields.Integer(
        compute="_compute_gain",
        readonly=False,
    )
    consolidated = fields.Boolean()

    tracking_date = fields.Datetime(
        default=fields.Datetime.now,
        index=True,
        readonly=True,
    )
    reason = fields.Text(
        string="Description",
        default=lambda self: _("Add Manually"),
    )
    origin_ref = fields.Reference(
        selection=lambda self: self._selection_origin_models(),
        string="Source",
        default=lambda self: f"res.users,{self.env.user.id}",
    )
    origin_ref_model_name = fields.Selection(
        selection=lambda self: self._selection_origin_models(),
        string="Source Type",
        compute="_compute_origin_ref_model_name",
        # Derivable from origin_ref before the row exists, so compute it into
        # the INSERT.  Without this every batch of tracking rows paid a second
        # statement -- an UPDATE settling this one column -- right after its own
        # INSERT.
        precompute=True,
        store=True,
    )

    # The monthly consolidation cron scans, three times over,
    # ``tracking_date BETWEEN <month> AND consolidated IS NOT TRUE``.  A plain
    # index on ``tracking_date`` matches every row in the month and then
    # filters ``consolidated`` from the heap; this partial index covers only
    # the un-consolidated rows the cron actually touches, so it stays small and
    # its selectivity does not decay as consolidated history accumulates.
    # (A covering ``(user_id) INCLUDE (old_value, new_value)`` index for the
    # per-user karma SUM was measured with EXPLAIN and rejected — the planner
    # keeps a bitmap heap scan, so it added write cost for no read benefit.)
    _unconsolidated_date_idx = models.Index(
        "(tracking_date) WHERE consolidated IS NOT TRUE"
    )

    @api.depends("old_value", "new_value")
    def _compute_gain(self) -> None:
        for karma in self:
            karma.gain = karma.new_value - (karma.old_value or 0)

    @api.depends("origin_ref")
    def _compute_origin_ref_model_name(self) -> None:
        for karma in self:
            if not karma.origin_ref:
                karma.origin_ref_model_name = False
                continue

            karma.origin_ref_model_name = karma.origin_ref._name

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        # fill missing old value with current user karma
        users = self.env["res.users"].browse(
            [
                values["user_id"]
                for values in vals_list
                if "old_value" not in values and values.get("user_id")
            ]
        )
        # Running karma per user, advanced as rows are built.  Snapshotting
        # once before the loop made every row of a batch chain from the same
        # pre-batch value, so two +10/+5 rows for one user both started at the
        # old karma and only the last one counted.
        karma_per_users = {user.id: user.karma for user in users}

        for values in vals_list:
            user_id = values.get("user_id")
            if "old_value" not in values and user_id:
                values["old_value"] = karma_per_users[user_id]

            if "gain" in values and "old_value" in values:
                values["new_value"] = values["old_value"] + values["gain"]
                del values["gain"]

            if user_id and "new_value" in values:
                karma_per_users[user_id] = values["new_value"]

        records = super().create(vals_list)
        records._recompute_user_ranks()
        return records

    def write(self, vals: ValuesType) -> Literal[True]:
        res = super().write(vals)
        if not KARMA_VALUE_FIELDS.isdisjoint(vals):
            self._recompute_user_ranks()
        return res

    def unlink(self) -> Literal[True]:
        users = self.user_id
        res = super().unlink()
        users._recompute_rank_if_relevant()
        return res

    def _recompute_user_ranks(self) -> None:
        """Re-evaluate the rank of every user these rows touch.

        This is the hook ``_compute_karma`` used to carry.  Putting it on the
        table rather than on the compute means the trigger is a write a reader
        can point at, and it still covers every path that changes karma --
        ``_add_karma_batch`` goes through ``create`` and the technical view goes
        through ``create``/``write``/``unlink``.
        """
        self.user_id._recompute_rank_if_relevant()

    @api.model
    def _consolidate_cron(self) -> bool:
        """Consolidate the trackings 2 months ago. Used by a cron to cleanup tracking records."""
        from_date = date_utils.start_of(
            fields.Datetime.today(), "month"
        ) - relativedelta(months=2)
        return self._process_consolidate(from_date)

    def _process_consolidate(
        self, from_date: datetime, end_date: datetime | None = None
    ) -> bool:
        """Consolidate the karma trackings.

        The consolidation keeps, for each user, the oldest "old_value" and the most recent
        "new_value", creates a new karma tracking with those values and removes all karma
        trackings between those dates. The origin / reason is changed on the consolidated
        records, so this information is lost in the process.
        """
        self.env["gamification.karma.tracking"].flush_model()

        if not end_date:
            end_date = date_utils.end_of(date_utils.end_of(from_date, "month"), "day")

        # The consolidated row carries the SUM of the gains it replaces, not the
        # newest row's ``new_value``.
        #
        # Taking the newest ``new_value`` assumed the rows telescope -- every
        # row's ``old_value`` equal to the previous row's ``new_value``.  Nothing
        # declares or checks that, and two ordinary administrative acts break it:
        # editing ``old_value`` in the technical view (the list is editable and
        # the field is exposed) and deleting a row.  Consolidation then moved
        # karma in whichever direction the break went -- a probe measured it both
        # losing 10 and *restoring* 20 an admin had deliberately deleted -- from a
        # cron, up to two months later, with no log line.
        #
        # Summing is the same single statement and cannot do that: the row it
        # writes has, by construction, the gain of the rows it replaces, so this
        # operation is karma-neutral whatever shape the chain is in.
        select_query = """
        WITH window_rows AS (
            SELECT user_id,
                   MIN(tracking_date) AS from_date,
                   SUM(new_value - COALESCE(old_value, 0)) AS total_gain,
                   (ARRAY_AGG(COALESCE(old_value, 0)
                              ORDER BY tracking_date ASC, id ASC))[1] AS first_old
              FROM gamification_karma_tracking
             WHERE tracking_date BETWEEN %(from_date)s AND %(end_date)s
               AND consolidated IS NOT TRUE
          GROUP BY user_id
        )
            INSERT INTO gamification_karma_tracking (
                            user_id,
                            old_value,
                            new_value,
                            tracking_date,
                            origin_ref,
                            origin_ref_model_name,
                            consolidated,
                            reason)
            SELECT          user_id,
                            first_old,
                            first_old + total_gain,
                            from_date,
                            %(origin_ref)s,
                            'res.users',
                            TRUE,
                            %(reason)s
              FROM window_rows
        """

        self.env.cr.execute(
            select_query,
            {
                "from_date": from_date,
                "end_date": end_date,
                "origin_ref": f"res.users,{self.env.user.id}",
                "reason": _(
                    "Consolidation from %(from_date)s to %(end_date)s",
                    from_date=from_date.date(),
                    end_date=end_date.date(),
                ),
            },
        )

        # Delete the collapsed rows in SQL, in the same statement style as the
        # INSERT above.
        #
        # This previously went through the ORM under a
        # ``skip_karma_computation`` context flag, whose ``_compute_karma``
        # early-return did not merely skip the computation: Odoo clears a
        # field's to-compute flag *before* invoking the compute, so returning
        # without assigning consumed any pending karma recompute and left
        # ``res_users.karma`` permanently out of sync with this table.  Because
        # the flush was ``flush_all()``, it destroyed unrelated pending
        # recomputes across the whole transaction, not just this one's.
        #
        # No flag is needed now: the consolidated row's gain equals the total
        # gain of the rows it replaces, so under the sum-of-gains definition of
        # karma this operation cannot change any user's karma.
        self.env.cr.execute(
            """
            DELETE FROM gamification_karma_tracking
             WHERE tracking_date BETWEEN %(from_date)s AND %(end_date)s
               AND consolidated IS NOT TRUE
            """,
            {"from_date": from_date, "end_date": end_date},
        )
        self.env["gamification.karma.tracking"].invalidate_model()
        # Karma is a *stored* compute over this table.  Rewriting the table in
        # raw SQL leaves the column and the cache holding the pre-consolidation
        # value, so drop both and let the next read recompute.  The one2many
        # id list on `res.users` is a separate cache entry from the field
        # values above it: a caller that already read `karma_tracking_ids` in
        # this same transaction before consolidating would otherwise recompute
        # `karma` from a stale id list (referencing rows this method just
        # deleted). Not reachable through the only production caller today
        # (`_consolidate_cron` runs in a fresh cron env with an empty cache),
        # but nothing here should depend on every future caller remembering to
        # invalidate on our behalf.
        self.env["res.users"].invalidate_model(["karma", "karma_tracking_ids"])
        return True
