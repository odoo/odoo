from odoo import _, api, exceptions, fields, models


# Unlike challenges (which are flat lists of independent goals), quests
# are *ordered sequences* of steps with prerequisites, narrative context,
# and a sense of progression.  They map to Octalysis drives 1 (Epic
# Meaning) and 3 (Empowerment of Creativity) by giving users a story
# and choices.
class GamificationQuest(models.Model):
    """Multi-step narrative journey wrapping goal definitions."""

    _name = "gamification.quest"
    _description = "Gamification Quest"
    _inherit = ["mixin.mail.thread"]
    _order = "sequence, name"

    name = fields.Char(
        string="Quest Name",
        translate=True,
        required=True,
        tracking=True,
    )
    description = fields.Html(
        string="Story",
        translate=True,
        sanitize_attributes=False,
        help="Narrative framing for the quest (e.g., 'The Data Quality Crusade').",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    icon = fields.Image(
        max_width=128,
        max_height=128,
    )

    # Steps
    step_ids = fields.One2many(
        comodel_name="gamification.quest.step",
        inverse_name="quest_id",
        string="Steps",
        copy=True,
    )
    step_count = fields.Count(
        count_of="step_ids",
        string="# Steps",
    )

    # Rewards for completing the entire quest
    reward_badge_id = fields.Many2one(
        comodel_name="gamification.badge",
        string="Completion Badge",
        help="Badge granted when all steps are completed.",
    )
    reward_karma = fields.Integer(
        string="Completion Karma",
        default=0,
        help="Bonus karma granted on quest completion (on top of step rewards).",
    )

    # Targeting
    quest_mode = fields.Selection(
        selection=[("solo", "Solo"), ("team", "Team")],
        string="Mode",
        default="solo",
        required=True,
    )
    difficulty = fields.Selection(
        selection=[
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
            ("expert", "Expert"),
        ],
        default="intermediate",
        required=True,
    )

    # Enrollment tracking
    enrollment_ids = fields.One2many(
        comodel_name="gamification.quest.enrollment",
        inverse_name="quest_id",
        string="Enrollments",
    )
    enrollment_count = fields.Count(
        count_of="enrollment_ids",
        string="# Enrolled",
    )
    completion_count = fields.Integer(
        string="# Completed",
        compute="_compute_completion_count",
    )

    @api.depends("enrollment_ids.state")
    def _compute_completion_count(self):
        """Count the enrolments that reached the end of the quest."""
        counts = {}
        if self.ids:
            counts = {
                quest.id: count
                for quest, count in self.env[
                    "gamification.quest.enrollment"
                ]._read_group(
                    [("quest_id", "in", self.ids), ("state", "=", "completed")],
                    groupby=["quest_id"],
                    aggregates=["__count"],
                )
            }
        for quest in self:
            quest.completion_count = counts.get(quest.id, 0)


# Each step references a goal definition that must be met.  Steps are
# ordered by sequence and may have prerequisite steps that must be
# completed first.
class GamificationQuestStep(models.Model):
    """Individual step within a quest."""

    _name = "gamification.quest.step"
    _description = "Quest Step"
    _order = "sequence, id"

    quest_id = fields.Many2one(
        comodel_name="gamification.quest",
        index=True,
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(
        string="Step Name",
        translate=True,
        required=True,
    )
    description = fields.Text(
        translate=True,
        help="What the user needs to do for this step.",
    )
    sequence = fields.Integer(default=10)

    # What to accomplish
    definition_id = fields.Many2one(
        comodel_name="gamification.goal.definition",
        string="Goal Definition",
        help="The goal definition this step evaluates. "
        "Leave empty for manually-verified steps.",
    )
    target_goal = fields.Float(
        string="Target",
        default=1,
        help="Target value for the goal (e.g., 10 leads, 5 invoices).",
    )

    # Prerequisites (other steps in the same quest)
    prerequisite_ids = fields.Many2many(
        comodel_name="gamification.quest.step",
        relation="gamification_quest_step_prereq_rel",
        column1="step_id",
        column2="prereq_id",
        string="Prerequisites",
        domain="[('quest_id', '=', quest_id), ('id', '!=', id)]",
        help="Steps that must be completed before this one unlocks.",
    )

    # Rewards per step
    karma_reward = fields.Integer(
        string="Step Karma",
        default=0,
    )
    badge_id = fields.Many2one(
        comodel_name="gamification.badge",
        string="Step Badge",
        help="Optional badge for completing this step.",
    )

    # Skill tree link
    skill_node_id = fields.Many2one(
        comodel_name="gamification.skill.node",
        ondelete="set null",
        help="Skill tree node this step contributes to.",
    )

    @api.constrains("prerequisite_ids")
    def _check_no_self_prerequisite(self):
        """Prevent a step from being its own prerequisite."""
        for step in self:
            if step in step.prerequisite_ids:
                raise exceptions.ValidationError(
                    _("A step cannot be its own prerequisite.")
                )


# One enrollment per user per quest.  Each enrollment has step
# completion records that track which steps are done.
class GamificationQuestEnrollment(models.Model):
    """Tracks a user's progress through a quest."""

    _name = "gamification.quest.enrollment"
    _description = "Quest Enrollment"
    _order = "create_date desc"
    _rec_name = "quest_id"

    quest_id = fields.Many2one(
        comodel_name="gamification.quest",
        index=True,
        required=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.uid,
        index=True,
        required=True,
        ondelete="cascade",
    )
    state = fields.Selection(
        selection=[
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("abandoned", "Abandoned"),
        ],
        default="in_progress",
        index=True,
        required=True,
    )
    progress_percent = fields.Float(
        string="Progress %",
        compute="_compute_progress_percent",
        store=True,
    )

    # Step completions
    completion_ids = fields.One2many(
        comodel_name="gamification.quest.step.completion",
        inverse_name="enrollment_id",
        string="Step Completions",
    )

    _user_quest_uniq = models.UniqueIndex(
        "(user_id, quest_id)",
        "A user can only enroll in a quest once.",
    )

    def write(self, vals):
        """Block direct `state` writes; force transitions through
        `complete_step`/`_complete_quest`/`action_abandon`.

        `state` carried no `readonly`/`groups=`, so an employee could write
        `state="completed"` directly, bypassing every step/prerequisite
        check -- granting no karma/badge (those only fire from the methods
        above) but corrupting `progress_percent` and `quest.completion_count`
        (a count of `state='completed'` enrollments) with a quest never
        actually done. `sudo()` (the methods above, imports/migrations)
        still bypasses this.

        Scoped to the enrollment's own user, same as `gamification.kudos`'s
        equivalent guard: a third party has no business writing `state`
        either, but that case is already denied by `quest_enrollment_own_only`
        raising its own `AccessError` -- this only adds a stricter rule for
        the one path that record rule *does* allow, the owner editing their
        own enrollment directly instead of through the methods above.
        """
        if (
            "state" in vals
            and not self.env.su
            and any(enrollment.user_id == self.env.user for enrollment in self)
        ):
            raise exceptions.UserError(
                _("Complete the quest's steps instead of changing the status directly.")
            )
        return super().write(vals)

    @api.depends("completion_ids", "quest_id.step_ids")
    def _compute_progress_percent(self):
        for enrollment in self:
            total = len(enrollment.quest_id.step_ids)
            done = len(enrollment.completion_ids)
            enrollment.progress_percent = round(100.0 * done / total, 1) if total else 0

    def complete_step(self, step):
        """Mark a step as completed for this enrollment.

        Validates prerequisites, creates the completion record, grants
        step rewards, and checks if the quest is now complete.

        :param step: ``gamification.quest.step`` record.
        :return: created ``gamification.quest.step.completion`` or False.
        """
        self.check_singleton()
        if self.state != "in_progress":
            return False

        # A step belongs to exactly one quest; completing a foreign quest's
        # step through this enrollment would grant that step's reward without
        # ever enrolling in its quest, and could push this enrollment's own
        # completion count past its quest's step count -- auto-completing a
        # quest never actually done.
        if step.quest_id != self.quest_id:
            raise exceptions.UserError(
                _(
                    "'%(step)s' belongs to quest '%(other_quest)s', not '%(quest)s'.",
                    step=step.name,
                    other_quest=step.quest_id.name,
                    quest=self.quest_id.name,
                )
            )

        # Check not already completed
        if step.id in self.completion_ids.mapped("step_id").ids:
            return False

        # Check prerequisites
        completed_step_ids = set(self.completion_ids.mapped("step_id").ids)
        for prereq in step.prerequisite_ids:
            if prereq.id not in completed_step_ids:
                raise exceptions.UserError(
                    _(
                        "Cannot complete '%(step)s': prerequisite '%(prereq)s' not yet done.",
                        step=step.name,
                        prereq=prereq.name,
                    )
                )

        # sudo: employees have read-only access to the completion table now.
        # It used to be employee-writable with no record rule, so anyone could
        # INSERT a row on someone else's enrolment and skip the prerequisite
        # check above -- the only place prerequisites are enforced.  Recording a
        # completion is a system act; deciding to is what this method guards.
        completion = (
            self.env["gamification.quest.step.completion"]
            .sudo()
            .create(
                {
                    "enrollment_id": self.id,
                    "step_id": step.id,
                }
            )
        )

        # Grant step rewards
        user = self.user_id
        if step.karma_reward:
            user.sudo()._add_karma(
                step.karma_reward,
                source=self,
                reason=_("Quest step: %s", step.name),
            )
        if step.badge_id:
            self.env["gamification.badge.user"].sudo().create(
                {
                    "user_id": user.id,
                    "badge_id": step.badge_id.id,
                }
            )._send_badge()

        # Check if quest is now complete
        total_steps = len(self.quest_id.step_ids)
        completed_steps = len(self.completion_ids)
        if completed_steps >= total_steps:
            self._complete_quest()

        return completion

    def _complete_quest(self):
        """Mark the quest as completed and grant quest-level rewards."""
        self.check_singleton()
        self.sudo().state = "completed"
        user = self.user_id
        quest = self.quest_id

        # Grant quest completion rewards
        if quest.reward_karma:
            user.sudo()._add_karma(
                quest.reward_karma,
                source=self,
                reason=_("Quest completed: %s", quest.name),
            )
        if quest.reward_badge_id:
            self.env["gamification.badge.user"].sudo().create(
                {
                    "user_id": user.id,
                    "badge_id": quest.reward_badge_id.id,
                }
            )._send_badge()

        self.env["gamification.activity"]._log_quest_completed(
            user, quest, quest.reward_karma
        )

        # Unlock any skill-tree nodes gated on this quest.  This is the link
        # (node.quest_id) that previously left the skill tree inert.
        self.env["gamification.skill.node"].sudo()._unlock_nodes_for_quest(self)

    def action_abandon(self):
        """Abandon the quest. sudo() only bypasses write()'s state-change
        guard above; the `quest_enrollment_own_only` record rule already
        scopes this to the enrollment's own user.
        """
        self.filtered(lambda e: e.state == "in_progress").sudo().write(
            {
                "state": "abandoned",
            }
        )


class GamificationQuestStepCompletion(models.Model):
    """Record of completing a single quest step."""

    _name = "gamification.quest.step.completion"
    _description = "Quest Step Completion"
    _order = "completion_date desc"

    enrollment_id = fields.Many2one(
        comodel_name="gamification.quest.enrollment",
        index=True,
        required=True,
        ondelete="cascade",
    )
    step_id = fields.Many2one(
        comodel_name="gamification.quest.step",
        required=True,
        ondelete="cascade",
    )
    completion_date = fields.Datetime(
        default=fields.Datetime.now,
        readonly=True,
    )

    _enrollment_step_uniq = models.UniqueIndex(
        "(enrollment_id, step_id)",
        "A step can only be completed once per enrollment.",
    )
