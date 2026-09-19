import ast
import logging
from datetime import date, datetime, timedelta
from typing import Any, Literal, Self

from odoo import _, api, exceptions, fields, models
from odoo.models import ValuesType
from odoo.tools.safe_eval import safe_eval, time

_logger = logging.getLogger(__name__)


class GamificationGoal(models.Model):
    """Individual goal instance for a user on a specific time period."""

    _name = "gamification.goal"
    _description = "Gamification Goal"
    _inherit = ["mixin.mail.thread"]
    _rec_name = "definition_id"
    _order = "start_date desc, end_date desc, definition_id, id"
    _mail_partner_fields = ("user_partner_id",)

    definition_id = fields.Many2one(
        comodel_name="gamification.goal.definition",
        string="Goal Definition",
        required=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        index=True,
        required=True,
        ondelete="cascade",
        bypass_search_access=True,
    )
    user_partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="user_id.partner_id",
    )
    line_id = fields.Many2one(
        comodel_name="gamification.challenge.line",
        string="Challenge Line",
        ondelete="cascade",
    )
    challenge_id = fields.Many2one(
        related="line_id.challenge_id",
        readonly=True,
        help="Challenge that generated the goal, assign challenge to users "
        "to generate goals with a value in this field.",
    )
    start_date = fields.Date(default=fields.Date.today)
    end_date = fields.Date()  # no start and end = always active
    target_goal = fields.Float(
        string="To Reach",
        required=True,
    )
    # no goal = global index
    current = fields.Float(
        string="Current Value",
        default=0,
        required=True,
    )
    completeness = fields.Float(compute="_compute_completeness")
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("inprogress", "In progress"),
            ("reached", "Reached"),
            ("failed", "Failed"),
            ("canceled", "Cancelled"),
        ],
        default="draft",
        index=True,
        required=True,
    )
    to_update = fields.Boolean(string="To update")
    closed = fields.Boolean(
        string="Closed goal",
        index=True,
    )

    computation_mode = fields.Selection(related="definition_id.computation_mode")
    color = fields.Integer(
        string="Color Index",
        compute="_compute_color",
    )
    remind_update_delay = fields.Integer(
        string="Remind delay",
        help="The number of days after which the user "
        "assigned to a manual goal will be reminded. "
        "Never reminded if no value is specified.",
    )
    last_update = fields.Date(
        help="In case of manual goal, reminders are sent if the goal as not "
        "been updated for a while (defined in challenge). Ignored in "
        "case of non-manual goal or goal not linked to a challenge."
    )

    definition_description = fields.Text(
        related="definition_id.description",
        string="Definition Description",
        readonly=True,
    )
    definition_condition = fields.Selection(
        related="definition_id.condition",
        string="Definition Condition",
        readonly=True,
    )
    definition_suffix = fields.Char(
        related="definition_id.full_suffix",
        string="Suffix",
        readonly=True,
    )
    definition_display = fields.Selection(
        related="definition_id.display_mode",
        string="Display Mode",
        readonly=True,
    )

    #: Fields that decide whether a goal counts as reached, and therefore whether
    #: its challenge pays out.  Writing any of them is a manager act.
    OUTCOME_FIELDS = frozenset(
        {"closed", "current", "end_date", "start_date", "state", "target_goal"}
    )

    @api.depends("end_date", "last_update", "state")
    def _compute_color(self) -> None:
        """Set the color based on the goal's state and completion"""
        for goal in self:
            goal.color = 0
            if goal.end_date and goal.last_update:
                if (goal.end_date < goal.last_update) and (goal.state == "failed"):
                    goal.color = 2
                elif (goal.end_date < goal.last_update) and (goal.state == "reached"):
                    goal.color = 5

    @api.depends("current", "target_goal", "definition_id.condition")
    def _compute_completeness(self) -> None:
        """Return the percentage of completeness of the goal, between 0 and 100"""
        for goal in self:
            if goal.definition_condition == "higher":
                if goal.current >= goal.target_goal:
                    goal.completeness = 100.0
                else:
                    goal.completeness = (
                        round(100.0 * goal.current / goal.target_goal, 2)
                        if goal.target_goal
                        else 0
                    )
            elif goal.current < goal.target_goal:
                # a goal 'lower than' has only two values possible: 0 or 100%
                goal.completeness = 100.0
            else:
                goal.completeness = 0.0

    def _check_remind_delay(self) -> dict[str, Any]:
        """Verify if a goal has not been updated for some time and send a
        reminder message of needed.

        :return: data to write on the goal object
        """
        self.check_singleton()
        if not (self.remind_update_delay and self.last_update):
            return {}

        delta_max = timedelta(days=self.remind_update_delay)
        if date.today() - self.last_update < delta_max:
            return {}

        # generate a reminder report
        body_html = self.env.ref(
            "gamification.email_template_goal_reminder"
        )._render_field("body_html", self.ids, compute_lang=True)[self.id]
        self.message_notify(
            body=body_html,
            partner_ids=[self.user_id.partner_id.id],
            subtype_xmlid="mail.mt_comment",
            email_layout_xmlid="mail.mail_notification_light",
        )

        return {"to_update": True}

    def _get_write_values(self, new_value: float) -> dict[Any, ValuesType]:
        """Generate values to write after recomputation of a goal score.

        State is evaluated from the goal's current situation, *not* from
        whether the measured value happened to move.  Skipping the whole method
        when ``new_value == self.current`` meant a goal whose metric was simply
        flat could never change state: an expired, unmet goal stayed
        ``inprogress`` and un-``closed`` for ever, was re-evaluated by the cron
        on every run, and permanently blocked resetting its challenge to draft.

        Draft goals have not started and closed ones (failed/cancelled) were
        frozen on purpose; neither should be moved by an automatic
        recomputation -- including ``current`` itself.  This check used to run
        only after ``current`` was already staged for writing, so the
        always-visible "refresh" button (which calls this via ``sudo()``, see
        ``_write_goal_values``) could silently re-measure and overwrite a
        closed goal's ``current``, corrupting the frozen history
        ``_get_adaptive_targets`` reads back from it.
        """
        if self.state not in ("inprogress", "reached"):
            return {}

        result = {}
        if new_value != self.current:
            result["current"] = new_value

        condition = self.definition_id.condition
        reached = (condition == "higher" and new_value >= self.target_goal) or (
            condition == "lower" and new_value <= self.target_goal
        )

        if reached:
            # success, do not set closed as it can still change
            if self.state != "reached":
                result["state"] = "reached"
        elif self.end_date and fields.Date.today() > self.end_date:
            # deadline passed without the target being met
            result["state"] = "failed"
            result["closed"] = True
        elif self.state == "reached":
            # the value fell back below the target before the deadline, so the
            # goal is in progress again — matching what ``action_reach``
            # documents ("will be reset to In Progress at the next goal update
            # until the end date").
            result["state"] = "inprogress"

        return {self: result} if result else {}

    def update_goal(self) -> bool:
        """Recompute every goal's value and settle its state.

        Split by computation mode: each ``_measure_*`` returns
        ``{goal: values}`` for its own batch and this method owns the ordering,
        the batched write and the optional intermediate commit.  It used to do
        all four inline, which made it both the module's longest function and
        its only C901 offender.

        If a manual goal is not updated for enough time, the user will be
        reminded to do so (done only once, in 'inprogress' state).
        If a goal reaches the target value, the status is set to reached.
        If the end date is passed (at least +1 day, time not considered) without
        the target value being reached, the goal is set as failed.
        """
        goals_by_definition = {}
        for goal in self.with_context(prefetch_fields=False):
            goals_by_definition.setdefault(goal.definition_id, []).append(goal)

        measure = {
            "manually": self._measure_manual_goals,
            "python": self._measure_python_goals,
            "count": self._measure_aggregate_goals,
            "sum": self._measure_aggregate_goals,
        }
        for definition, goals in goals_by_definition.items():
            handler = measure.get(definition.computation_mode)
            if handler is None:
                _logger.error(
                    "Invalid computation mode '%s' in definition %s",
                    definition.computation_mode,
                    definition.name,
                )
                continue
            self._write_goal_values(handler(definition, goals))
            if self.env.context.get("commit_gamification"):
                self.env.cr.commit()
        return True

    def _write_goal_values(self, goals_to_write: dict) -> None:
        """Write ``{goal: values}`` in one statement per distinct value set.

        The values are computed server-side and never user-supplied, so this
        writes as sudo: the refresh button must keep working for non-manager
        users without tripping the outcome-field guard in ``write``, which only
        targets direct user writes.
        """
        by_values: dict[frozenset, list[int]] = {}
        for goal, values in goals_to_write.items():
            if not values:
                continue
            by_values.setdefault(frozenset(values.items()), []).append(goal.id)
        Goal = self.env["gamification.goal"].sudo()
        for vals_key, goal_ids in by_values.items():
            Goal.browse(goal_ids).write(dict(vals_key))

    def _measure_manual_goals(self, definition, goals) -> dict:
        """Manual goals hold whatever the user last entered; only remind."""
        return {goal: goal._check_remind_delay() for goal in goals}

    def _measure_python_goals(self, definition, goals) -> dict:
        """Run the definition's Python snippet once per goal."""
        # TODO batch execution
        goals_to_write = {}
        code = definition.compute_code.strip()
        for goal in goals:
            cxt = {
                "object": goal,
                "env": self.env,
                "date": date,
                "datetime": datetime,
                "timedelta": timedelta,
                "time": time,
            }
            safe_eval(code, cxt, mode="exec")
            # the result of the evaluated code is put in the 'result' local
            # variable, propagated to the context
            result = cxt.get("result")
            if isinstance(result, (float, int)):
                goals_to_write.update(goal._get_write_values(result))
            else:
                _logger.error(
                    "Invalid return content '%r' from the evaluation "
                    "of code for definition %s, expected a number",
                    result,
                    definition.name,
                )
        return goals_to_write

    def _measure_aggregate_goals(self, definition, goals) -> dict:
        """Count or sum records for count/sum definitions."""
        # sudo: a count/sum goal measures an objective metric; under the
        # caller's record rules the stored value would depend on who triggered
        # the refresh (and pair badly with the sudo write). Scoping still comes
        # from the goal's own domain/batch_user_expression, not from the actor.
        Obj = self.env[definition.model_id.model].sudo()
        if definition.batch_mode:
            return self._measure_batched_goals(definition, goals, Obj)
        return self._measure_per_goal(definition, goals, Obj)

    def _measure_batched_goals(self, definition, goals, Obj) -> dict:
        """Batch mode: one aggregate per (start_date, end_date) window."""
        goals_to_write = {}
        field_date_name = definition.field_date_id.name
        general_domain = ast.literal_eval(definition.domain)
        field_name = definition.batch_distinctive_field.name

        subqueries = {}
        for goal in goals:
            start_date = (field_date_name and goal.start_date) or False
            end_date = (field_date_name and goal.end_date) or False
            subqueries.setdefault((start_date, end_date), {})[goal.id] = safe_eval(
                definition.batch_user_expression, {"user": goal.user_id}
            )

        # the global query should be split by time periods (especially for
        # recurrent goals)
        for (start_date, end_date), query_goals in subqueries.items():
            subquery_domain = list(general_domain)
            subquery_domain.append((field_name, "in", list(set(query_goals.values()))))
            if start_date:
                subquery_domain.append((field_date_name, ">=", start_date))
            if end_date:
                subquery_domain.append((field_date_name, "<=", end_date))

            if definition.computation_mode == "count":
                aggregate = "__count"
            else:
                aggregate = f"{definition.field_id.name}:sum"
            user_values = Obj._read_group(  # noqa: E8507 - one query per distinct period; goals sharing one were merged above
                subquery_domain, groupby=[field_name], aggregates=[aggregate]
            )

            # _read_group emits no row for a key with zero matches, so build a
            # lookup and default missing goals to 0 -- otherwise a goal whose
            # value dropped to 0 would keep its stale (possibly still 'reached')
            # value.
            value_by_key = {
                (
                    field_value.id
                    if isinstance(field_value, models.Model)
                    else field_value
                ): value
                for field_value, value in user_values
            }
            for goal in (g for g in goals if g.id in query_goals):
                new_value = value_by_key.get(query_goals[goal.id], 0)
                goals_to_write.update(goal._get_write_values(new_value))
        return goals_to_write

    def _measure_per_goal(self, definition, goals, Obj) -> dict:
        """Non-batch mode: evaluate the domain once per goal."""
        goals_to_write = {}
        field_date_name = definition.field_date_id.name
        field_name = definition.field_id.name
        field = Obj._fields.get(field_name)
        sum_supported = bool(field) and field.type in {"integer", "float", "monetary"}
        if definition.computation_mode == "sum" and not sum_supported:
            # Deliberate, upstream-tested behaviour: summing a non-numeric field
            # degrades to counting matching rows (see
            # test_40_create_challenge_with_sum_goal, which asserts the field is
            # non-numeric on purpose).  Logged because it is surprising when hit
            # by accident.
            _logger.info(
                "Goal definition %s sums %r on %s, which is not numeric "
                "(type %r): counting rows instead.",
                definition.name,
                field_name,
                definition.model_id.model,
                field.type if field else None,
            )

        # Goals sharing a domain share an answer.  A definition whose domain
        # does not mention `user` gives every goal of the same period the same
        # number, and used to pay a search_count each to find that out.
        by_domain: dict[str, tuple[list, list]] = {}
        for goal in goals:
            domain = safe_eval(definition.domain, {"user": goal.user_id})
            if field_date_name:
                if goal.start_date:
                    domain.append((field_date_name, ">=", goal.start_date))
                if goal.end_date:
                    domain.append((field_date_name, "<=", goal.end_date))
            by_domain.setdefault(repr(domain), (domain, []))[1].append(goal)

        for domain, domain_goals in by_domain.values():
            if definition.computation_mode == "sum" and sum_supported:
                res = Obj._read_group(domain, [], [f"{field_name}:sum"])  # noqa: E8507 - one query per distinct domain; goals sharing one were merged above
                new_value = res[0][0] or 0.0
            else:
                new_value = Obj.search_count(domain)  # noqa: E8507 - one query per distinct domain; goals sharing one were merged above
            for goal in domain_goals:
                goals_to_write.update(goal._get_write_values(new_value))
        return goals_to_write

    def action_start(self) -> bool:
        """Mark a goal as started.

        This should only be used when creating goals manually (in draft state)
        """
        self.write({"state": "inprogress"})
        return self.update_goal()

    def action_reach(self) -> bool:
        """Mark a goal as reached.

        If the target goal condition is not met, the state will be reset to In
        Progress at the next goal update until the end date.
        """
        return self.write({"state": "reached"})

    def action_fail(self) -> bool:
        """Set the state of the goal to failed.

        A failed goal will be ignored in future checks.
        """
        return self.write({"state": "failed"})

    def action_cancel(self) -> bool:
        """Reset the completion after setting a goal as reached or failed.

        This is only the current state, if the date and/or target criteria
        match the conditions for a change of state, this will be applied at the
        next goal update.
        """
        return self.write({"state": "inprogress"})

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        return super(GamificationGoal, self.with_context(no_remind_goal=True)).create(
            vals_list
        )

    def write(self, vals: ValuesType) -> Literal[True]:
        """Update goals and trigger on-change reports.

        Sets ``last_update`` to today.  If ``current`` changed and the
        challenge's report frequency is 'onchange', a single progress report
        is generated per challenge (batched, not per-goal).

        :raises UserError: if ``definition_id`` or ``user_id`` is modified on
            a non-draft goal (prevents drag-and-drop reordering accidents).
        """
        if "definition_id" in vals or "user_id" in vals:
            if any(g.state != "draft" for g in self):
                raise exceptions.UserError(
                    _("Can not modify the configuration of a started goal")
                )

        # Guarding `current` and `state` alone was not enough: every field in
        # OUTCOME_FIELDS feeds the reached/failed decision, so lowering your own
        # `target_goal` is exactly as good as writing your own `current`.  An
        # employee could set it to 0 on an automatic goal, wait one night, and
        # collect the challenge's reward badge -- including a `rule_auth='nobody'`
        # badge that exists precisely so users cannot grant it.
        #
        # `current` stays writable by the goal's owner because moving the value of
        # a *manual* goal is the whole point of one; the wizard is that path.
        # Declaring the outcome by hand is not, on either kind of goal, which is
        # why `state` is manager-only now rather than manual-goals-only.
        protected = self.OUTCOME_FIELDS.intersection(vals)
        if protected and not (
            self.env.su or self.env.user.has_group("base.group_erp_manager")
        ):
            if self.filtered(lambda g: g.definition_id.computation_mode != "manually"):
                raise exceptions.UserError(
                    _(
                        "Automatic goals are computed by the system and can not be"
                        " updated manually."
                    )
                )
            if forbidden := protected - {"current"}:
                raise exceptions.UserError(
                    _(
                        "On your own goal you may update the value, not %(fields)s.",
                        fields=", ".join(sorted(forbidden)),
                    )
                )
            # `goal_user_visibility`'s ranking clause grants read *and write* to
            # any fellow participant of a ranking-visibility challenge, not just
            # the goal's own owner -- it exists so a leaderboard can be seen, not
            # edited. Without this check a co-participant could overwrite another
            # user's manual `current` value through the ORM.
            if self.filtered(lambda g: g.user_id != self.env.user):
                raise exceptions.UserError(
                    _("You can only update the value of your own goals.")
                )

        # `last_update` dates the last change to the goal's *value*, and
        # `_check_remind_delay` measures the manual-goal reminder from it.
        # Stamping it on every write let the cron's own `state` / `closed` writes
        # reset that clock, so a goal nobody had touched in months never became
        # due for a reminder.
        if "current" in vals:
            vals = {**vals, "last_update": fields.Date.context_today(self)}
        result = super().write(vals)

        # Batch on-change reports: one report per (challenge, user) pair
        if "current" in vals and "no_remind_goal" not in self.env.context:
            reports_to_send: dict = {}  # {challenge_id: set of user recordsets}
            for goal in self:
                challenge = goal.challenge_id
                if challenge and challenge.report_message_frequency == "onchange":
                    reports_to_send.setdefault(challenge.id, (challenge, set()))
                    reports_to_send[challenge.id][1].add(goal.user_id.id)
            for challenge, user_ids in reports_to_send.values():
                users = self.env["res.users"].browse(user_ids)
                challenge.sudo().report_progress(users=users)

        return result

    def get_action(self) -> dict[str, Any] | Literal[False]:
        """Get the ir.action related to update the goal

        In case of a manual goal, should return a wizard to update the value
        :return: action description in a dictionary
        """
        self.check_singleton()
        if self.definition_id.action_id:
            # open the action linked to the goal
            action = self.definition_id.action_id.read()[0]

            if self.definition_id.res_id_field:
                action["res_id"] = safe_eval(
                    self.definition_id.res_id_field, {"user": self.env.user}
                )

                # if one element to display, should see it in form mode if possible
                action["views"] = [
                    (view_id, mode)
                    for (view_id, mode) in action["views"]
                    if mode == "form"
                ] or action["views"]
            return action

        if self.computation_mode == "manually":
            # open a wizard window to update the value manually
            return {
                "name": _("Update %s", self.definition_id.name),
                "id": self.id,
                "type": "ir.actions.act_window",
                "views": [[False, "form"]],
                "target": "new",
                "context": {
                    "default_goal_id": self.id,
                    "default_current": self.current,
                },
                "res_model": "gamification.goal.wizard",
            }

        return False
