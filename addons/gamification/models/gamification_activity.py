from odoo import _, api, fields, models


# Aggregates all notable gamification events into a single, time-ordered
# stream.  This powers the company-wide social feed on the dashboard
# and provides the visibility that drives Socializer player types.
#
# Activities are auto-created by source models (badges, kudos,
# achievements, streaks, rank-ups) via helper methods -- never manually.
# Inherits mixin.mail.thread so users can react to or discuss activities.
class GamificationActivity(models.Model):
    """Centralized social activity feed for gamification events."""

    _name = "gamification.activity"
    _description = "Gamification Activity Feed"
    _inherit = ["mixin.mail.thread"]
    _order = "activity_date desc, id desc"
    _rec_name = "summary"

    activity_type = fields.Selection(
        selection=[
            ("badge", "Badge Earned"),
            ("kudos", "Kudos Sent"),
            ("achievement", "Achievement Unlocked"),
            ("streak_milestone", "Streak Milestone"),
            ("level_up", "Level Up"),
            ("challenge_completed", "Challenge Completed"),
            ("quest_completed", "Quest Completed"),
            ("skill_unlocked", "Skill Unlocked"),
        ],
        string="Type",
        index=True,
        readonly=True,
        required=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        index=True,
        readonly=True,
        required=True,
        ondelete="cascade",
    )
    target_user_id = fields.Many2one(
        comodel_name="res.users",
        index=True,
        readonly=True,
        ondelete="set null",
        help="Secondary user (e.g. kudos recipient).",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="user_id.company_id",
        string="Company",
    )
    summary = fields.Char(
        readonly=True,
        required=True,
    )
    icon = fields.Char(
        string="Icon CSS",
        readonly=True,
    )
    activity_date = fields.Datetime(
        string="Date",
        default=fields.Datetime.now,
        index=True,
        readonly=True,
    )

    # Optional references to source records
    badge_id = fields.Many2one(
        comodel_name="gamification.badge",
        readonly=True,
        ondelete="set null",
    )
    achievement_id = fields.Many2one(
        comodel_name="gamification.achievement",
        readonly=True,
        ondelete="set null",
    )
    challenge_id = fields.Many2one(
        comodel_name="gamification.challenge",
        readonly=True,
        ondelete="set null",
    )
    karma_gained = fields.Integer(readonly=True)

    # ── Factory methods (called by source models) ───────────────────
    #
    # One `_log` and one `_log_batch`, not ten near-identical `sudo().create()`
    # calls.  The eight `_log_*` helpers differed only in `activity_type`, `icon`
    # and a sentence, and two more callers (quest completion, skill unlock)
    # open-coded the same create and bypassed the helpers entirely.

    #: activity_type -> default icon. The summary itself is rendered at READ
    #: time from the row's own fields by ``_render_summary``, never stored: a
    #: stored sentence is frozen in the language of whoever triggered the
    #: event and goes stale the moment a user, badge or quest is renamed.
    ACTIVITY_KINDS = {
        "badge": "fa fa-certificate",
        "kudos": "fa fa-heart",
        "achievement": "fa fa-trophy",
        "streak_milestone": "fa fa-fire",
        "level_up": "fa fa-arrow-up",
        "challenge_completed": "fa fa-flag-checkered",
        "quest_completed": "fa fa-flag-checkered",
        "skill_unlocked": "fa fa-puzzle-piece",
    }

    @api.model
    def _log_batch(self, entries: list[dict]) -> GamificationActivity:
        """Record several activities in one INSERT.

        :param entries: dicts with ``activity_type``, ``user_id`` and any of
            ``target_user_id``, ``badge_id``, ``achievement_id``,
            ``challenge_id``, ``karma_gained``, ``icon``, ``summary_args``.
        :return: the created records.
        """
        if not entries:
            return self.browse()

        # Warm the caches the summaries read from, in one query per model rather
        # than one per entry: `_render_summary` reaches for user, badge,
        # achievement and challenge names, and a batch of level-ups otherwise
        # paid a SELECT per row.
        Users = self.env["res.users"]
        Users.browse(
            {
                uid
                for entry in entries
                for uid in (entry.get("user_id"), entry.get("target_user_id"))
                if uid
            }
        ).mapped("name")
        for model, key in (
            ("gamification.badge", "badge_id"),
            ("gamification.achievement", "achievement_id"),
            ("gamification.challenge", "challenge_id"),
        ):
            if ids := {e[key] for e in entries if e.get(key)}:
                self.env[model].browse(ids).mapped("name")

        vals_list = []
        for entry in entries:
            entry = dict(entry)
            kind = entry["activity_type"]
            summary_args = entry.pop("summary_args", {})
            entry.setdefault("icon", self.ACTIVITY_KINDS.get(kind, "fa fa-star"))
            entry.setdefault("summary", self._render_summary(kind, entry, summary_args))
            vals_list.append(entry)
        return self.sudo().create(vals_list)

    @api.model
    def _log(self, activity_type: str, user, **kwargs) -> GamificationActivity:
        """Record one activity.  Thin wrapper over :meth:`_log_batch`."""
        return self._log_batch(
            [{"activity_type": activity_type, "user_id": user.id, **kwargs}]
        )

    @api.model
    def _render_summary(self, kind: str, vals: dict, args: dict) -> str:
        """Build the display sentence for an activity.

        Called on write to fill the stored ``summary`` (which the list view and
        every existing row still use) and available for a future read-time
        render.  Kept in one place so the ten call sites cannot drift.
        """
        Users = self.env["res.users"]
        user = Users.browse(vals["user_id"])
        target = Users.browse(vals.get("target_user_id") or ())
        if kind == "badge":
            badge = self.env["gamification.badge"].browse(vals["badge_id"])
            if target:
                return _(
                    "%(sender)s awarded %(badge)s to %(user)s",
                    sender=target.name,
                    badge=badge.name,
                    user=user.name,
                )
            return _(
                "%(user)s earned the %(badge)s badge", user=user.name, badge=badge.name
            )
        if kind == "kudos":
            return _(
                "%(sender)s recognized %(recipient)s for %(category)s",
                sender=user.name,
                recipient=target.name,
                category=args["category"],
            )
        if kind == "achievement":
            ach = self.env["gamification.achievement"].browse(vals["achievement_id"])
            return _(
                "%(user)s unlocked '%(achievement)s' (%(rarity)s)",
                user=user.name,
                achievement=ach.name,
                rarity=ach.rarity,
            )
        if kind == "streak_milestone":
            return _(
                "%(user)s reached %(days)s days on %(streak)s!",
                user=user.name,
                days=args["days"],
                streak=args["streak"],
            )
        if kind == "level_up":
            return _("%(user)s reached %(rank)s!", user=user.name, rank=args["rank"])
        if kind == "challenge_completed":
            challenge = self.env["gamification.challenge"].browse(vals["challenge_id"])
            return _(
                "%(user)s completed the '%(challenge)s' challenge",
                user=user.name,
                challenge=challenge.name,
            )
        if kind == "quest_completed":
            return _(
                "%(user)s completed the '%(quest)s' quest!",
                user=user.name,
                quest=args["quest"],
            )
        if kind == "skill_unlocked":
            return _(
                "%(user)s unlocked skill '%(skill)s'",
                user=user.name,
                skill=args["skill"],
            )
        return _("%(user)s earned an achievement", user=user.name)

    # -- named wrappers, kept so source models read as prose ---------------

    @api.model
    def _log_badge(self, user, badge, sender=None):
        """Record a badge-earned activity."""
        return self._log(
            "badge",
            user,
            target_user_id=sender.id if sender else False,
            badge_id=badge.id,
        )

    @api.model
    def _log_kudos(self, sender, recipient, category, karma):
        """Record a kudos-sent activity."""
        return self._log(
            "kudos",
            sender,
            target_user_id=recipient.id,
            icon=category.icon or "fa fa-heart",
            karma_gained=karma,
            summary_args={"category": category.name},
        )

    @api.model
    def _log_achievement(self, user, achievement, karma):
        """Record an achievement-unlocked activity."""
        return self._log(
            "achievement",
            user,
            achievement_id=achievement.id,
            karma_gained=karma,
        )

    @api.model
    def _log_streak_milestone(self, user, streak_type, day_count, karma):
        """Record a streak milestone activity."""
        return self._log(
            "streak_milestone",
            user,
            karma_gained=karma,
            summary_args={"days": day_count, "streak": streak_type.name},
        )

    @api.model
    def _log_level_up(self, user, rank):
        """Record a level-up activity."""
        return self._log("level_up", user, summary_args={"rank": rank.name})

    @api.model
    def _log_challenge_completed(self, user, challenge):
        """Record a challenge-completed activity."""
        return self._log("challenge_completed", user, challenge_id=challenge.id)

    @api.model
    def _log_quest_completed(self, user, quest, karma):
        """Record a quest-completed activity."""
        return self._log(
            "quest_completed",
            user,
            karma_gained=karma,
            summary_args={"quest": quest.name},
        )

    @api.model
    def _log_skill_unlocked(self, user, node, karma):
        """Record a skill-node-unlocked activity."""
        return self._log(
            "skill_unlocked",
            user,
            karma_gained=karma,
            summary_args={"skill": node.name},
        )

    # ── Feed API ────────────────────────────────────────────────────

    def _get_display_summary(self) -> str:
        """Re-render this activity's sentence in the reader's language.

        Falls back to the stored ``summary`` when the row does not carry enough
        structure to rebuild -- rows written before a source record was deleted,
        and any type a future module adds without teaching ``_render_summary``.
        """
        self.check_singleton()
        args = {}
        if self.activity_type == "streak_milestone":
            # The streak's name and day count are not columns on this model, so
            # the stored sentence is the only record of them.
            return self.summary
        if self.activity_type == "kudos" or self.activity_type in (
            "quest_completed",
            "skill_unlocked",
        ):
            return self.summary
        if self.activity_type == "level_up":
            if not self.user_id.rank_id:
                return self.summary
            args = {"rank": self.user_id.rank_id.name}
        # The source m2os are all `ondelete="set null"`, so a deleted badge or
        # challenge leaves the row intact with a blank reference. Rendering that
        # produces a sentence with `False` where the name was -- worse than the
        # stored one, and it does not raise, so a try/except cannot catch it.
        # Check the reference this type needs is still there.
        required = {
            "badge": self.badge_id,
            "achievement": self.achievement_id,
            "challenge_completed": self.challenge_id,
        }.get(self.activity_type)
        if required is not None and not required:
            return self.summary

        vals = {
            "user_id": self.user_id.id,
            "target_user_id": self.target_user_id.id,
            "badge_id": self.badge_id.id,
            "achievement_id": self.achievement_id.id,
            "challenge_id": self.challenge_id.id,
        }
        try:
            return self._render_summary(self.activity_type, vals, args)
        except KeyError, ValueError:
            return self.summary

    @api.model
    def get_activity_feed(self, limit=30):
        """Return the latest activities for the dashboard social feed.

        Filters by the current user's company.  Respects users'
        ``gamification_visibility`` setting — activities from users
        with 'private' visibility are excluded.

        :param int limit: max entries.
        :return: list of dicts for the OWL component.
        """
        # An activity is two-party (e.g. kudos sender ↔ recipient, badge awarder
        # ↔ earner) and its ``summary`` bakes in both names.  Exclude the row if
        # *either* party is private, otherwise a private user still surfaces as
        # the counterparty of a public user's event.
        activities = self.search(
            [
                ("company_id", "=", self.env.company.id),
                ("user_id.gamification_visibility", "!=", "private"),
                "|",
                ("target_user_id", "=", False),
                ("target_user_id.gamification_visibility", "!=", "private"),
            ],
            limit=self.env["res.users"]._gamification_clamp_limit(limit, default=30),
        )
        # Render the sentence NOW rather than serving the stored one. `summary`
        # is written once, in the language of whoever triggered the event and
        # with the names as they read that day, so a French reader saw English
        # and a renamed badge stayed renamed only in the future. The stored
        # column is kept: it is this model's `_rec_name` and what the list view
        # and every existing row use.
        return [
            {
                "id": a.id,
                "activity_type": a.activity_type,
                "user_name": a.user_id.name,
                "target_user_name": a.target_user_id.name
                if a.target_user_id
                else False,
                "summary": a._get_display_summary(),
                "icon": a.icon,
                "karma_gained": a.karma_gained,
                "date": a.activity_date.date().isoformat()
                if a.activity_date
                else False,
            }
            for a in activities
        ]
