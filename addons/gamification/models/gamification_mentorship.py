from typing import Any

from odoo import _, api, exceptions, fields, models


# Creates a structured relationship where experienced users guide
# newcomers.  Mentors earn karma when their mentee hits milestones,
# creating a win-win dynamic (Octalysis drives 1 + 5: Epic Meaning
# + Social Influence).
class GamificationMentorship(models.Model):
    """Mentor-mentee pairing for guided gamification progression."""

    _name = "gamification.mentorship"
    _description = "Gamification Mentorship"
    _inherit = ["mixin.mail.thread"]
    _order = "create_date desc"
    _rec_name = "display_name"

    mentor_id = fields.Many2one(
        comodel_name="res.users",
        index=True,
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    mentee_id = fields.Many2one(
        comodel_name="res.users",
        index=True,
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("pending", "Awaiting Confirmation"),
            ("active", "Active"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="pending",
        index=True,
        required=True,
        tracking=True,
    )
    start_date = fields.Date(
        default=fields.Date.today,
        readonly=True,
    )
    end_date = fields.Date(tracking=True)
    description = fields.Text(
        string="Goals",
        help="What the mentor and mentee aim to achieve together.",
    )

    # Karma rewards.
    #
    # These decide how much karma the mentor is paid, and the payout runs
    # through ``sudo()``.  They are therefore manager-only: were they writable
    # by ``base.group_user``, any employee could name themselves mentor over an
    # arbitrary mentee, set an arbitrary payout and call ``action_complete()``
    # to mint unbounded karma.  ``groups=`` is enforced by the ORM on both read
    # and write, so the reward amounts can never come from the acting user.
    #
    # ``groups=`` does not stop the ORM applying the *default*, though, so a
    # self-appointed mentor still collected 25 karma per mentee rank-up without
    # the mentee doing or agreeing to anything.  Consent is what closes that:
    # a mentorship starts ``pending`` and pays nothing until the counterparty
    # confirms it -- see ``_check_may_accept``.
    mentor_karma_per_milestone = fields.Integer(
        string="Mentor Karma per Milestone",
        default=25,
        groups="base.group_erp_manager",
        help="Karma granted to the mentor when the mentee reaches a new rank.",
    )
    mentor_karma_on_completion = fields.Integer(
        string="Mentor Karma on Completion",
        default=100,
        groups="base.group_erp_manager",
        help="Karma bonus for the mentor when the mentorship is completed.",
    )
    mentee_milestones_reached = fields.Integer(
        string="Milestones Reached",
        default=0,
        readonly=True,
        help="Number of rank-ups the mentee achieved during this mentorship.",
    )
    total_mentor_karma = fields.Integer(
        string="Total Mentor Karma Earned",
        default=0,
        readonly=True,
    )

    # Completion.  Manager-only for the same reason as the karma rewards: the
    # badge is granted via ``sudo()``, which bypasses the badge model's own
    # "you can not grant a badge to yourself" guard.
    completion_badge_id = fields.Many2one(
        comodel_name="gamification.badge",
        groups="base.group_erp_manager",
        help="Badge granted to both mentor and mentee on completion.",
    )

    # One mentorship per (mentor, mentee) pair that is not cancelled.  Scoping
    # this to ``state = 'active'`` alone would let a pair be completed and
    # immediately re-created, turning the completion payout into an unbounded
    # karma loop.
    _mentor_mentee_uniq = models.UniqueIndex(
        "(mentor_id, mentee_id) WHERE state != 'cancelled'",
        "A user can only have one mentorship with the same partner.",
    )

    @api.depends("mentor_id", "mentee_id")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = _(
                "%(mentor)s mentoring %(mentee)s",
                mentor=rec.mentor_id.name or "",
                mentee=rec.mentee_id.name or "",
            )

    @api.constrains("mentor_id", "mentee_id", "state")
    def _check_not_self_mentoring(self):
        """Reject a pairing that pays a user for their own progression.

        Direct self-mentoring is the obvious case.  The reciprocal pair is the
        same thing spread over two records: with A mentoring B *and* B mentoring
        A, every rank-up on either side pays the other, and each payout can push
        the payee over their own next threshold.  It terminates -- karma is
        monotone and ranks are finite -- but it is an amplification loop between
        two colluding users, so it is refused rather than bounded.
        """
        for rec in self:
            if rec.mentor_id == rec.mentee_id:
                raise exceptions.ValidationError(_("A user cannot mentor themselves."))

        live = self.filtered(lambda r: r.state in ("pending", "active"))
        if not live:
            return
        # One search for the whole recordset: the reciprocal of every live
        # pairing at once, then matched in memory.
        reciprocals = {
            (other.mentor_id.id, other.mentee_id.id)
            for other in self.sudo().search(
                [
                    ("mentor_id", "in", live.mentee_id.ids),
                    ("mentee_id", "in", live.mentor_id.ids),
                    ("state", "in", ("pending", "active")),
                    ("id", "not in", live.ids),
                ]
            )
        }
        for rec in live:
            if (rec.mentee_id.id, rec.mentor_id.id) in reciprocals:
                raise exceptions.ValidationError(
                    _(
                        "%(a)s and %(b)s cannot mentor each other: a reciprocal "
                        "pairing pays both sides for the same progression.",
                        a=rec.mentor_id.name,
                        b=rec.mentee_id.name,
                    )
                )

    @api.constrains("mentor_karma_per_milestone", "mentor_karma_on_completion")
    def _check_karma_rewards_positive(self):
        """Reject negative payouts, which would silently drain the mentor."""
        for rec in self.sudo():
            if rec.mentor_karma_per_milestone < 0 or rec.mentor_karma_on_completion < 0:
                raise exceptions.ValidationError(
                    _("Mentorship karma rewards cannot be negative.")
                )

    def write(self, vals: Any) -> bool:
        """Block direct `state` writes; force transitions through the
        `action_*` methods.

        `state` carried no `readonly`/`groups=` of its own, so nothing at the
        ORM layer stopped a caller from skipping `_check_may_accept()` /
        `_check_may_complete()` entirely and writing `state` directly (e.g. a
        self-proposed mentor confirming their own pending mentorship via RPC
        or the statusbar widget) -- exactly the consent bypass those checks
        exist to prevent. `sudo()` (the `action_*` methods themselves, plus
        imports/migrations) still bypasses this, same pattern as
        `gamification.kudos.write()`'s value-field freeze.

        Scoped to the mentorship's own mentor/mentee: a third party has no
        business writing `state` either, but that case is already denied by
        `mentorship_own_only` raising its own `AccessError` -- this only adds
        a stricter rule for the one path that record rule *does* allow, a
        party editing their own mentorship directly instead of through the
        `action_*` methods.
        """
        if (
            "state" in vals
            and not self.env.su
            and any(self.env.user in (rec.mentor_id, rec.mentee_id) for rec in self)
        ):
            raise exceptions.UserError(
                _(
                    "Use Accept/Decline/Complete/Cancel instead of changing"
                    " the status directly."
                )
            )
        return super().write(vals)

    def _check_may_accept(self):
        """Ensure the caller is the party who did *not* propose the mentorship.

        A mentorship is a two-sided arrangement that pays one side, so the side
        that proposed it cannot also confirm it.  Whoever created the record has
        already said yes by creating it; the counterparty is the one whose
        agreement is still missing.

        :raises AccessError: if the current user is neither the counterparty nor
            a gamification manager.
        """
        if self.env.su or self.env.user.has_group("base.group_erp_manager"):
            return
        for rec in self:
            proposer = rec.create_uid
            counterparty = rec.mentor_id if proposer == rec.mentee_id else rec.mentee_id
            if counterparty != self.env.user:
                raise exceptions.AccessError(
                    _(
                        "Only %(who)s or a gamification manager can confirm this "
                        "mentorship. The person who proposed it cannot also "
                        "accept it.",
                        who=counterparty.name,
                    )
                )

    def action_accept(self):
        """Confirm a proposed mentorship, making its rewards live.

        Callable by the counterparty or a manager only -- see
        ``_check_may_accept``.  Until this runs the pairing exists but
        ``_on_mentee_rank_up`` ignores it, so no karma moves.
        """
        self._check_may_accept()
        self.filtered(lambda r: r.state == "pending").sudo().write({"state": "active"})

    def action_decline(self):
        """Refuse a proposed mentorship.  Same audience as ``action_accept``."""
        self._check_may_accept()
        self.filtered(lambda r: r.state == "pending").sudo().write(
            {"state": "cancelled", "end_date": fields.Date.today()}
        )

    def _check_may_complete(self):
        """Ensure the caller is allowed to close the mentorship.

        Completion pays the *mentor*, so the mentor may not trigger it: that
        would be self-awarding.  Only the counterparty (the mentee) or a
        gamification manager can confirm that the mentorship actually happened.

        :raises AccessError: if the current user is neither the mentee nor a
            manager.
        """
        if self.env.su or self.env.user.has_group("base.group_erp_manager"):
            return
        for rec in self:
            if rec.mentee_id != self.env.user:
                raise exceptions.AccessError(
                    _(
                        "Only %(mentee)s or a gamification manager can complete "
                        "this mentorship. A mentor cannot award their own "
                        "completion rewards.",
                        mentee=rec.mentee_id.name,
                    )
                )

    def action_complete(self):
        """Mark the mentorship as completed and grant rewards.

        Callable by the mentee or a manager only — see ``_check_may_complete``.
        """
        self._check_may_complete()
        for rec in self.filtered(lambda r: r.state == "active"):
            # sudo: the reward fields are manager-only (see their definition),
            # so a mentee legitimately completing the mentorship cannot read
            # them under their own rights.
            rec_sudo = rec.sudo()
            rec_sudo.state = "completed"
            rec_sudo.end_date = fields.Date.today()

            # Grant completion karma to mentor
            if rec_sudo.mentor_karma_on_completion:
                rec_sudo.mentor_id._add_karma(
                    rec_sudo.mentor_karma_on_completion,
                    source=rec,
                    reason=_("Mentorship completed with %s", rec_sudo.mentee_id.name),
                )
                rec_sudo.total_mentor_karma += rec_sudo.mentor_karma_on_completion

            # Grant completion badge to both
            if rec_sudo.completion_badge_id:
                BadgeUser = self.env["gamification.badge.user"].sudo()
                for user in (rec_sudo.mentor_id, rec_sudo.mentee_id):
                    BadgeUser.create(
                        {
                            "user_id": user.id,
                            "badge_id": rec_sudo.completion_badge_id.id,
                        }
                    )._send_badge()

    def action_cancel(self):
        """Cancel the mentorship. Either party may cancel their own active
        mentorship; the `mentorship_own_only` record rule already scopes
        that. sudo() only bypasses `write()`'s state-change guard above.
        """
        self.filtered(lambda r: r.state == "active").sudo().write(
            {
                "state": "cancelled",
                "end_date": fields.Date.today(),
            }
        )

    def _on_mentee_rank_up(self, mentees):
        """Pay the mentors of every mentee in ``mentees`` that just ranked up.

        Takes a recordset: ``_rank_changed`` now hands over a whole batch, and
        one search plus one ``_add_karma_batch`` covers it instead of a search
        and a karma write cycle per user.

        Only ``active`` pairings pay.  A mentorship starts ``pending`` until the
        counterparty confirms it, which is what stops an employee naming
        themselves mentor over a colleague and collecting on their progress.

        :param mentees: ``res.users`` recordset that reached a new rank.
        """
        if not mentees:
            return
        # sudo: a rank-up is a system event.  The mentee triggering it has no
        # rights on their mentor's mentorship record (record rule) nor on the
        # manager-only reward fields, but the mentor must still be paid.
        pairings = self.sudo().search(
            [
                ("mentee_id", "in", mentees.ids),
                ("state", "=", "active"),
                ("mentor_karma_per_milestone", ">", 0),
            ]
        )
        if not pairings:
            return

        karma_per_mentor: dict[Any, dict[str, Any]] = {}
        for rec in pairings:
            mentee = rec.mentee_id
            gain = rec.mentor_karma_per_milestone
            entry = karma_per_mentor.setdefault(
                rec.mentor_id,
                {
                    "gain": 0,
                    "source": rec,
                    "reason": _(
                        "Mentee %(mentee)s reached %(rank)s",
                        mentee=mentee.name,
                        rank=mentee.rank_id.name or "a new rank",
                    ),
                },
            )
            entry["gain"] += gain
            rec.mentee_milestones_reached += 1
            rec.total_mentor_karma += gain

        self.env["res.users"].sudo()._add_karma_batch(karma_per_mentor)

    @api.model
    def get_suggested_mentors(self, limit=5):
        """Suggest potential mentors for the current user.

        Returns users with higher karma who are not already mentoring
        the current user.

        :param int limit: max suggestions.
        :return: list of dicts with user_id, user_name, karma, rank_name.
        """
        user = self.env.user
        # Exclude users already mentoring this user, and users this user is
        # already mentoring -- _check_not_self_mentoring's reciprocal-pair
        # check would reject that pairing anyway if the caller acted on the
        # suggestion, since the two are already paired in the other direction.
        existing_pairings = self.search(
            [
                ("state", "in", ("pending", "active")),
                "|",
                ("mentee_id", "=", user.id),
                ("mentor_id", "=", user.id),
            ]
        )
        existing_pairing_ids = (
            existing_pairings.mentor_id | existing_pairings.mentee_id
        ).ids

        Users = self.env["res.users"]
        mentors = Users.search(
            [
                ("karma", ">", user.karma),
                ("id", "!=", user.id),
                ("id", "not in", existing_pairing_ids),
                ("company_id", "=", user.company_id.id),
                *Users._get_domain_gamification_listable(),
            ],
            order="karma desc",
            limit=Users._gamification_clamp_limit(limit),
        )
        return [
            {
                "user_id": m.id,
                "user_name": m.name,
                "karma": m.karma,
                "rank_name": m.rank_id.name or "",
            }
            for m in mentors
        ]
