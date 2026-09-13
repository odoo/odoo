import logging
import operator as op
import re
import uuid
from typing import Any, Self

import requests
from dateutil.relativedelta import relativedelta
from markupsafe import Markup, escape

from odoo import Command, _, api, fields, models, modules
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.guarded_http import RefusedDestination
from odoo.libs.json import dumps as json_dumps
from odoo.models import ValuesType
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

_SCORE_COMPARATORS = {
    "=": op.eq,
    "!=": op.ne,
    "<": op.lt,
    "<=": op.le,
    ">": op.gt,
    ">=": op.ge,
}


_WEBHOOK_RESPONSE_MAX_BYTES = 64 * 1024


class SurveyUser_Input(models.Model):
    _name = "survey.user_input"
    _description = "Survey User Input"
    _rec_name = "survey_id"
    _order = "create_date desc"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity"]

    survey_id = fields.Many2one(
        comodel_name="survey.survey",
        index=True,
        readonly=True,
        ondelete="cascade",
    )
    scoring_type = fields.Selection(
        related="survey_id.scoring_type",
        string="Scoring",
    )
    start_datetime = fields.Datetime(
        string="Start date and time",
        readonly=True,
    )
    end_datetime = fields.Datetime(
        string="End date and time",
        readonly=True,
    )
    deadline = fields.Datetime(
        help="Datetime until customer can open the survey and submit answers"
    )
    lang_id = fields.Many2one(
        comodel_name="res.lang",
        string="Language",
    )
    state = fields.Selection(
        selection=[
            ("new", "New"),
            ("in_progress", "In Progress"),
            ("done", "Completed"),
        ],
        string="Status",
        default="new",
        readonly=True,
    )
    test_entry = fields.Boolean(readonly=True)
    last_displayed_page_id = fields.Many2one(
        comodel_name="survey.question",
        string="Last displayed question/page",
    )
    is_attempts_limited = fields.Boolean(
        related="survey_id.is_attempts_limited",
        string="Limited number of attempts",
    )
    attempts_limit = fields.Integer(
        related="survey_id.attempts_limit",
        string="Number of attempts",
    )
    attempts_count = fields.Integer(compute="_compute_attempts_info")
    attempts_number = fields.Integer(
        string="Attempt n°",
        compute="_compute_attempts_info",
    )
    survey_time_limit_reached = fields.Boolean(
        compute="_compute_survey_time_limit_reached"
    )
    access_token = fields.Char(
        string="Identification token",
        default=lambda self: str(uuid.uuid4()),
        copy=False,
        readonly=True,
        required=True,
    )
    invite_token = fields.Char(
        string="Invite token",
        copy=False,
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
        index="btree_not_null",
        readonly=True,
    )
    email = fields.Char(readonly=True)
    nickname = fields.Char(
        help="Attendee nickname, mainly used to identify them in the survey session leaderboard."
    )
    ip_address = fields.Char(
        string="IP Address",
        readonly=True,
        help="Respondent's IP address. Not stored if survey has 'Anonymize IP' enabled.",
    )
    save_later_datetime = fields.Datetime(
        string="Resume Link Sent",
        copy=False,
        readonly=True,
        help="When the 'continue later' link was last emailed for this attempt.",
    )
    user_input_line_ids = fields.One2many(
        comodel_name="survey.user_input.line",
        inverse_name="user_input_id",
        string="Answers",
        copy=True,
    )
    predefined_question_ids = fields.Many2many(
        comodel_name="survey.question",
        string="Predefined Questions",
        readonly=True,
        context={"active_test": False},
    )
    scoring_percentage = fields.Float(
        string="Score (%)",
        compute="_compute_scoring_values",
        compute_sudo=True,
        store=True,
    )
    scoring_total = fields.Float(
        string="Total Score",
        digits=(10, 2),
        compute="_compute_scoring_values",
        compute_sudo=True,
        store=True,
    )
    scoring_success = fields.Boolean(
        string="Quiz Passed",
        compute="_compute_scoring_success",
        compute_sudo=True,
        store=True,
    )
    survey_first_submitted = fields.Boolean()
    is_speeder = fields.Boolean(
        string="Speeder",
        compute="_compute_is_speeder",
        search="_search_is_speeder",
        help="Respondent completed the survey in less than a third of this survey's "
        "median duration, compared against every response as it stands now.",
    )
    is_straight_liner = fields.Boolean(
        string="Straight-liner",
        compute="_compute_is_straight_liner",
        store=True,
        help="Respondent selected the same answer for every choice/matrix question.",
    )
    quality_score = fields.Integer(
        compute="_compute_quality_score",
        search="_search_quality_score",
        help="Response quality from 0 (worst) to 100 (best). Based on speed and answer variety.",
    )
    is_session_answer = fields.Boolean(
        string="Is in a Session",
        help="Is that user input part of a survey session or not.",
    )
    question_time_limit_reached = fields.Boolean(
        compute="_compute_question_time_limit_reached"
    )

    _unique_token = models.Constraint(
        "UNIQUE (access_token)",
        "An access token must be unique!",
    )

    @api.depends(
        "user_input_line_ids.answer_score",
        "user_input_line_ids.question_id",
        "predefined_question_ids.answer_score",
        "predefined_question_ids.question_type",
        "predefined_question_ids.is_scored_question",
        "predefined_question_ids.suggested_answer_ids.answer_score",
    )
    def _compute_scoring_values(self) -> None:
        for user_input in self:
            total_possible_score = (
                user_input.predefined_question_ids._get_max_obtainable_score()
            )

            if total_possible_score == 0:
                user_input.scoring_percentage = 0
                user_input.scoring_total = 0
            else:
                score_total = sum(user_input.user_input_line_ids.mapped("answer_score"))
                user_input.scoring_total = score_total
                score_percentage = (score_total / total_possible_score) * 100
                user_input.scoring_percentage = (
                    round(score_percentage, 2) if score_percentage > 0 else 0
                )

    @api.depends("scoring_percentage", "survey_id")
    def _compute_scoring_success(self) -> None:
        for user_input in self:
            user_input.scoring_success = (
                bool(user_input.survey_id)
                and user_input.scoring_percentage
                >= user_input.survey_id.scoring_success_min
            )

    SPEEDER_MEDIAN_FRACTION = 3
    STRAIGHT_LINER_MIN_CHOICES = 3

    @api.depends("state", "start_datetime", "end_datetime", "survey_id")
    def _compute_is_speeder(self) -> None:
        """Derived, not stored: this compares a response against all of its siblings.

        `@api.depends` cannot express "depends on the aggregate of my siblings", so a
        stored column is right only at the instant it is written and silently wrong
        from the next completion onwards -- while backing a saved filter and a
        decorated list column.
        """
        finished = self.filtered(
            lambda ui: ui.state == "done" and ui.start_datetime and ui.end_datetime
        )
        (self - finished).is_speeder = False
        medians = finished.survey_id._get_median_answer_durations()
        for user_input in finished:
            median = medians.get(user_input.survey_id.id, 0)
            duration = (
                user_input.end_datetime - user_input.start_datetime
            ).total_seconds()
            user_input.is_speeder = bool(
                median and duration < median / self.SPEEDER_MEDIAN_FRACTION
            )

    @api.depends("state", "user_input_line_ids.suggested_answer_id")
    def _compute_is_straight_liner(self) -> None:
        for user_input in self:
            choice_lines = user_input.user_input_line_ids.filtered(
                lambda ln: (
                    ln.suggested_answer_id and not ln.skipped and not ln.matrix_row_id
                )
            )
            user_input.is_straight_liner = (
                user_input.state == "done"
                and len(choice_lines) >= self.STRAIGHT_LINER_MIN_CHOICES
                and len(set(choice_lines.suggested_answer_id.ids)) == 1
            )

    @api.depends("is_speeder", "is_straight_liner")
    def _compute_quality_score(self) -> None:
        for user_input in self:
            penalty = 50 * user_input.is_speeder + 50 * user_input.is_straight_liner
            user_input.quality_score = max(100 - penalty, 0)

    _SCORE_SQL = """
        WITH medians AS (
            SELECT survey_id,
                   percentile_cont(0.5) WITHIN GROUP (
                       ORDER BY extract(epoch FROM end_datetime - start_datetime)
                   ) AS median
              FROM survey_user_input
             WHERE state = 'done'
                   AND test_entry IS NOT TRUE
                   AND start_datetime IS NOT NULL
                   AND end_datetime IS NOT NULL
             GROUP BY survey_id
        ), scored AS (
            SELECT ui.id,
                   (m.median > 0
                    AND ui.state = 'done'
                    AND ui.start_datetime IS NOT NULL
                    AND ui.end_datetime IS NOT NULL
                    AND extract(epoch FROM ui.end_datetime - ui.start_datetime)
                        < m.median / %s) AS speeder,
                   COALESCE(ui.is_straight_liner, FALSE) AS straight_liner
              FROM survey_user_input ui
              LEFT JOIN medians m ON m.survey_id = ui.survey_id
        )
        SELECT id,
               GREATEST(100 - 50 * speeder::int - 50 * straight_liner::int, 0) AS score,
               speeder
          FROM scored
    """

    def _scored_rows(self) -> list[tuple[int, int, bool]]:
        self.env["survey.user_input"].flush_model(
            [
                "survey_id",
                "state",
                "test_entry",
                "start_datetime",
                "end_datetime",
                "is_straight_liner",
            ]
        )
        self.env.cr.execute(self._SCORE_SQL, [self.SPEEDER_MEDIAN_FRACTION])
        return self.env.cr.fetchall()

    @api.model
    def _search_is_speeder(self, comparator: str, value: Any) -> list[Any]:
        if comparator not in ("=", "!="):
            raise NotImplementedError(comparator)
        speeders = [row[0] for row in self._scored_rows() if row[2]]
        wanted = bool(value) == (comparator == "=")
        return [("id", "in" if wanted else "not in", speeders)]

    @api.model
    def _search_quality_score(self, comparator: str, value: Any) -> list[Any]:
        compare = _SCORE_COMPARATORS.get(comparator)
        if compare is None:
            raise NotImplementedError(comparator)
        matching = [row[0] for row in self._scored_rows() if compare(row[1], value)]
        return [("id", "in", matching)]

    @api.depends("start_datetime", "survey_id.is_time_limited", "survey_id.time_limit")
    def _compute_survey_time_limit_reached(self) -> None:
        for user_input in self:
            if not user_input.is_session_answer and user_input.start_datetime:
                start_time = user_input.start_datetime
                time_limit = user_input.survey_id.time_limit
                user_input.survey_time_limit_reached = (
                    user_input.survey_id.is_time_limited
                    and fields.Datetime.now()
                    >= start_time + relativedelta(minutes=time_limit)
                )
            else:
                user_input.survey_time_limit_reached = False

    @api.depends(
        "survey_id.session_question_id.time_limit",
        "survey_id.session_question_id.is_time_limited",
        "survey_id.session_question_start_time",
    )
    def _compute_question_time_limit_reached(self) -> None:
        for user_input in self:
            if (
                user_input.is_session_answer
                and user_input.survey_id.session_question_start_time
            ):
                start_time = user_input.survey_id.session_question_start_time
                time_limit = user_input.survey_id.session_question_id.time_limit
                user_input.question_time_limit_reached = (
                    user_input.survey_id.session_question_id.is_time_limited
                    and fields.Datetime.now()
                    >= start_time + relativedelta(seconds=time_limit)
                )
            else:
                user_input.question_time_limit_reached = False

    @api.depends(
        "state",
        "test_entry",
        "survey_id.is_attempts_limited",
        "partner_id",
        "email",
        "invite_token",
    )
    def _compute_attempts_info(self) -> None:
        attempts_to_compute = self.filtered(
            lambda user_input: (
                user_input.state == "done"
                and not user_input.test_entry
                and user_input.survey_id.is_attempts_limited
            )
        )

        for user_input in self - attempts_to_compute:
            user_input.attempts_count = 1
            user_input.attempts_number = 1

        if attempts_to_compute:
            self.flush_model(
                [
                    "email",
                    "invite_token",
                    "partner_id",
                    "state",
                    "survey_id",
                    "test_entry",
                ]
            )

            self.env.cr.execute(
                """
                SELECT user_input.id,
                       COUNT(all_attempts_user_input.id) AS attempts_count,
                       COUNT(CASE WHEN all_attempts_user_input.id < user_input.id THEN all_attempts_user_input.id END) + 1 AS attempts_number
                FROM survey_user_input user_input
                LEFT OUTER JOIN survey_user_input all_attempts_user_input
                ON user_input.survey_id = all_attempts_user_input.survey_id
                AND all_attempts_user_input.state = 'done'
                AND all_attempts_user_input.test_entry IS NOT TRUE
                AND (user_input.invite_token IS NULL OR user_input.invite_token = all_attempts_user_input.invite_token)
                AND (user_input.partner_id = all_attempts_user_input.partner_id OR user_input.email = all_attempts_user_input.email)
                WHERE user_input.id = ANY(%s)
                GROUP BY user_input.id;
            """,
                (list(attempts_to_compute.ids),),
            )

            attempts_number_results = self.env.cr.dictfetchall()

            attempts_number_results = {
                attempts_number_result["id"]: {
                    "attempts_number": attempts_number_result["attempts_number"],
                    "attempts_count": attempts_number_result["attempts_count"],
                }
                for attempts_number_result in attempts_number_results
            }

            for user_input in attempts_to_compute:
                attempts_number_result = attempts_number_results.get(user_input.id, {})
                user_input.attempts_number = attempts_number_result.get(
                    "attempts_number", 1
                )
                user_input.attempts_count = attempts_number_result.get(
                    "attempts_count", 1
                )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        pending_lines = []
        for vals in vals_list:
            detached = not vals.get(
                "survey_id", self.env.context.get("default_survey_id")
            )
            pending_lines.append(
                vals.pop("user_input_line_ids", []) if detached else []
            )
            if "predefined_question_ids" not in vals:
                survey_id = vals.get(
                    "survey_id", self.env.context.get("default_survey_id")
                )
                survey = self.env["survey.survey"].browse(survey_id)
                vals["predefined_question_ids"] = [
                    Command.set(
                        survey._prepare_user_input_predefined_questions().ids
                        if survey
                        else []
                    )
                ]
        responses = super().create(vals_list)
        for response, lines in zip(responses, pending_lines, strict=True):
            if lines:
                response.user_input_line_ids = lines
        return responses

    @api.depends("survey_id", "nickname", "partner_id")
    def _compute_display_name(self):
        super()._compute_display_name()
        for response in self.filtered(lambda response: not response.survey_id):
            response.display_name = (
                response.nickname
                or response.partner_id.display_name
                or self.env._("Response")
            )

    @api.constrains("survey_id", "predefined_question_ids")
    def _check_response_questions(self):
        for response in self:
            for line in response.user_input_line_ids:
                if line.question_id.survey_id != response.survey_id or (
                    not response.survey_id
                    and line.question_id not in response.predefined_question_ids
                ):
                    raise ValidationError(
                        self.env._("Keep answered questions in their response.")
                    )

    def _submit_answers(self, answers):
        self.check_singleton()
        self._lock()
        self.invalidate_recordset(["state"])
        if self.state == "done":
            raise UserError(self.env._("This response has already been submitted."))
        questions = self.predefined_question_ids
        if set(answers) - set(questions.ids):
            raise ValidationError(
                self.env._("An answer does not belong to this response.")
            )
        errors = {}
        for question in questions:
            errors.update(question._check_answer(answers.get(question.id)))
        if errors:
            raise ValidationError("\n".join(dict.fromkeys(errors.values())))
        for question in questions:
            answer = answers.get(question.id)
            if not question._is_unanswered(answer):
                self._save_lines(question, answer)
        self._mark_done()

    def action_resend(self) -> dict[str, Any]:
        partners = self.env["res.partner"]
        emails = []
        for user_answer in self:
            if user_answer.partner_id:
                partners |= user_answer.partner_id
            elif user_answer.email:
                emails.append(user_answer.email)

        return self.survey_id.with_context(
            default_existing_mode="resend",
            default_partner_ids=partners.ids,
            default_emails=",".join(emails),
        ).action_send_survey()

    def action_print_answers(self) -> dict[str, Any]:
        self.check_singleton()
        url = self.env["ir.http"]._url_for(
            f"/survey/print/{self.survey_id.access_token}?answer_token={self.access_token}",
            self.lang_id.code or None,
        )
        return {
            "type": "ir.actions.act_url",
            "name": "View Answers",
            "target": "self",
            "url": url,
        }

    def action_redirect_to_attempts(self) -> dict[str, Any]:
        self.check_singleton()

        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "survey.action_survey_user_input"
        )
        context = dict(self.env.context or {})

        context["create"] = False
        context["search_default_survey_id"] = self.survey_id.id
        context["search_default_group_by_survey"] = False
        if self.partner_id:
            context["search_default_partner_id"] = self.partner_id.id
        elif self.email:
            context["search_default_email"] = self.email

        action["context"] = context
        return action

    @api.model
    def _generate_invite_token(self) -> str:
        return str(uuid.uuid4())

    SAVE_LATER_COOLDOWN_MINUTES = 5

    def _consume_save_later_allowance(self) -> bool:
        self.check_singleton()
        self.env.cr.execute(
            "SELECT save_later_datetime FROM survey_user_input WHERE id = %s FOR UPDATE",
            [self.id],
        )
        [(last_sent,)] = self.env.cr.fetchall()
        now = fields.Datetime.now()
        if last_sent and now < last_sent + relativedelta(
            minutes=self.SAVE_LATER_COOLDOWN_MINUTES
        ):
            return False
        self.sudo().write({"save_later_datetime": now})
        return True

    def _lock(self) -> None:
        """Serialise concurrent work on one participation.

        The client's own guard cannot cover this: two requests carrying the same answer
        token both read state != 'done' and both run to completion, which is a second
        certification email, a second badge award and a second webhook. Postgres decides
        the order instead.
        """
        if not self.ids:
            return
        self.flush_recordset()
        self.env.cr.execute(
            "SELECT id FROM survey_user_input WHERE id = ANY(%s) FOR UPDATE", [self.ids]
        )

    def _mark_in_progress(self) -> None:
        self.write({"start_datetime": fields.Datetime.now(), "state": "in_progress"})
        for user_input in self:
            user_input._fire_webhook("survey_started")

    def _mark_done(self) -> None:
        self._evaluate_calculated_fields()
        self.write(
            {
                "end_datetime": fields.Datetime.now(),
                "state": "done",
            }
        )

        challenge_sudo = self.env["gamification.challenge"].sudo()
        badge_ids = []
        self.filtered("survey_id")._notify_new_participation_subscribers()
        for user_input in self.filtered("survey_id"):
            if user_input.survey_id.certification and user_input.scoring_success:
                if (
                    user_input.survey_id.certification_mail_template_id
                    and not user_input.test_entry
                ):
                    user_input.survey_id.certification_mail_template_id.send_mail(
                        user_input.id, email_layout_xmlid="mail.mail_notification_light"
                    )
                if user_input.survey_id.certification_give_badge:
                    badge_ids.append(user_input.survey_id.certification_badge_id.id)

            user_input.predefined_question_ids -= (
                user_input._get_inactive_conditional_questions()
            )

        if badge_ids:
            challenges = challenge_sudo.search([("reward_id", "in", badge_ids)])
            if challenges:
                challenge_sudo._cron_update(ids=challenges.ids, commit=False)

        for user_input in self:
            user_input._fire_webhook("survey_completed")

        for user_input in self.filtered(lambda ui: not ui.test_entry):
            # followup_rule_ids already excludes archived rules (active_test).
            for rule in user_input.survey_id.followup_rule_ids:
                rule._execute(user_input)

    def _fire_webhook(self, event: str) -> None:
        """Every guard lives here, so no call site has to remember them."""
        self.check_singleton()
        survey = self.survey_id
        webhook_url = survey.webhook_url
        if not webhook_url or self.test_entry:
            return

        if survey.webhook_events == "completed" and event != "survey_completed":
            return

        payload = self._prepare_webhook_payload(event)
        json_payload = json_dumps(payload)
        input_id = self.id
        session = self.env["ir.egress"].session(
            purpose="survey_webhook", max_bytes=_WEBHOOK_RESPONSE_MAX_BYTES
        )

        def do_post():
            try:
                with session:
                    session.post(
                        webhook_url,
                        data=json_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=5,
                        allow_redirects=False,
                    )
            except RefusedDestination as refusal:
                _logger.warning(
                    "Survey webhook (%s) refused for input %s: %s",
                    event,
                    input_id,
                    refusal,
                )
            except requests.RequestException:
                _logger.warning(
                    "Survey webhook (%s) failed for input %s to %s",
                    event,
                    input_id,
                    webhook_url,
                    exc_info=True,
                )

        self.env.cr.postcommit.add(do_post)

    def _prepare_webhook_payload(
        self, event: str = "survey_completed"
    ) -> dict[str, Any]:
        self.check_singleton()
        answers = []
        for line in self.user_input_line_ids:
            if line.skipped:
                continue
            answers.append(
                {
                    "question_id": line.question_id.id,
                    "question_title": line.question_id.title,
                    "question_type": line.question_id.question_type,
                    "answer_value": line._get_answer_value(),
                }
            )
        return {
            "event": event,
            "survey_id": self.survey_id.id,
            "survey_title": self.survey_id.title,
            "user_input_id": self.id,
            "respondent": {
                "email": self.email or "",
                "nickname": self.nickname or "",
                "partner_id": self.partner_id.id if self.partner_id else None,
            },
            "score_percentage": self.scoring_percentage,
            "scoring_success": self.scoring_success,
            "completed_at": str(self.end_datetime),
            "answers": answers,
        }

    def get_start_url(self) -> str:
        self.check_singleton()
        return f"{self.survey_id.get_start_url()}?answer_token={self.access_token}"

    def get_print_url(self) -> str:
        self.check_singleton()
        return f"{self.survey_id.get_print_url()}?answer_token={self.access_token}"

    _CALC_REF_RE = re.compile(r"\bQ(\d+)\b")

    _CALC_ALLOWED_NAMES = {
        "min": min,
        "max": max,
        "abs": abs,
        "round": round,
        "sum": sum,
        "len": len,
        "int": int,
        "float": float,
        "True": True,
        "False": False,
        "None": None,
    }

    def _evaluate_calculated_fields(self) -> None:
        for user_input in self:
            calculated_questions = user_input.survey_id.question_ids.filtered(
                lambda q: q.question_type == "calculated" and q.calculated_expression
            )
            if not calculated_questions:
                continue

            answer_values = {}
            for line in user_input.user_input_line_ids.filtered(
                lambda ln: not ln.skipped
            ):
                qid = line.question_id.id
                if line.answer_type == "numerical_box":
                    answer_values[qid] = line.value_numerical_box
                elif line.answer_type == "scale":
                    answer_values[qid] = float(line.value_scale)
                elif line.answer_type == "suggestion" and line.suggested_answer_id:
                    answer_values[qid] = line.suggested_answer_id.answer_score

            for question in calculated_questions:
                expr = question.calculated_expression
                local_vars = dict(self._CALC_ALLOWED_NAMES)
                for match in self._CALC_REF_RE.finditer(expr):
                    ref_id = int(match.group(1))
                    local_vars[f"Q{ref_id}"] = answer_values.get(ref_id, 0)

                try:
                    result = float(safe_eval(expr, local_vars))
                except Exception:
                    _logger.warning(
                        "Failed to evaluate calculated field %s (expression: %s)",
                        question.id,
                        expr,
                    )
                    continue

                existing = user_input.user_input_line_ids.filtered(
                    lambda ln, q=question: ln.question_id == q
                )
                vals = {
                    "user_input_id": user_input.id,
                    "question_id": question.id,
                    "skipped": False,
                    "answer_type": "numerical_box",
                    "value_numerical_box": result,
                }
                try:
                    with self.env.cr.savepoint():
                        if existing:
                            existing.write(vals)
                        else:
                            self.env["survey.user_input.line"].create(vals)
                except Exception:
                    _logger.warning(
                        "Could not store calculated field %s for input %s",
                        question.id,
                        user_input.id,
                        exc_info=True,
                    )

    _PIPING_RE = re.compile(r"\{\{Q(\d+)\}\}")

    def _resolve_piping(self, text: str | Markup) -> str | Markup:
        """Substitute {{Q<id>}} with this respondent's answer to that question.

        The number is a question **id**, the same reference
        `survey.question.calculated_expression` documents for its own `Q<id>`
        syntax. It used to fall back to a 1-based position when no question
        carried that id, which meant {{Q3}} named the third question in one survey
        and the question whose id is 3 in another -- and flipped meaning the moment
        such a question was added. A position also moves when questions are
        reordered, which a stored reference must not.
        """
        if not text or "{{Q" not in text:
            return text
        self.check_singleton()

        is_markup = isinstance(text, Markup)
        answered = self.user_input_line_ids.filtered(lambda line: not line.skipped)
        lines_by_question = answered.grouped("question_id")

        answer_by_id: dict[int, str] = {}
        for question, lines in lines_by_question.items():
            if question not in self.survey_id.question_ids:
                continue
            values = [
                value
                for value in (line._get_answer_value() for line in lines)
                if value is not None
            ]
            if not values:
                continue
            raw_value = (
                ", ".join(str(value) for value in values)
                if question.question_type == "multiple_choice"
                else str(values[0])
            )
            answer_by_id[question.id] = escape(raw_value) if is_markup else raw_value

        result = self._PIPING_RE.sub(
            lambda match: answer_by_id.get(int(match.group(1)), ""), text
        )
        return Markup(result) if is_markup else result

    def _save_lines(
        self,
        question: Any,
        answer: Any,
        comment: str | None = None,
        overwrite_existing: bool = True,
    ) -> None:
        if question.question_type in ("statement", "calculated"):
            return

        self.check_singleton()
        if not self.survey_id and (
            question.survey_id or question not in self.predefined_question_ids
        ):
            raise ValidationError(
                self.env._("This question does not belong to the response.")
            )
        old_answers = self.env["survey.user_input.line"].search(
            [("user_input_id", "=", self.id), ("question_id", "=", question.id)]
        )
        if old_answers and not overwrite_existing:
            raise UserError(_("This answer cannot be overwritten."))

        if question.question_type in [
            "char_box",
            "text_box",
            "scale",
            "nps",
            "numerical_box",
            "slider",
            "rating",
            "date",
            "datetime",
        ]:
            self._save_line_simple_answer(question, old_answers, answer)
            if question.save_as_email and answer:
                self.write({"email": answer})
            if question.save_as_nickname and answer:
                self.write({"nickname": answer})

        elif question.question_type in ["simple_choice", "dropdown", "multiple_choice"]:
            self._save_line_choice(question, old_answers, answer, comment)
        elif question.question_type in ("matrix", "likert"):
            self._save_line_matrix(question, old_answers, answer, comment)
        elif question.question_type in ("ranking", "constant_sum"):
            self._save_line_per_answer(question, old_answers, answer)
        elif question.question_type == "file_upload":
            self._save_line_file_upload(question, old_answers, answer)
        else:
            raise ValueError(
                f"{question.question_type}: This type of question has no saving function"
            )

    def _save_line_simple_answer(
        self, question: Any, old_answers: Any, answer: Any
    ) -> Any:
        vals = self._get_line_answer_values(question, answer, question.question_type)
        if old_answers:
            old_answers.write(vals)
            return old_answers
        else:
            return self.env["survey.user_input.line"].create(vals)

    def _save_line_choice(
        self, question: Any, old_answers: Any, answers: Any, comment: str | None
    ) -> Any:
        if not (isinstance(answers, list)):
            answers = [answers]

        if not answers and not (comment and question.comment_count_as_answer):
            answers = [False]

        vals_list = [
            self._get_line_answer_values(question, answer, "suggestion")
            for answer in answers
        ]

        if comment:
            vals_list.append(self._get_line_comment_values(question, comment))

        old_answers.sudo().unlink()
        return self.env["survey.user_input.line"].create(vals_list)

    def _save_line_matrix(
        self, question: Any, old_answers: Any, answers: dict | None, comment: str | None
    ) -> Any:
        vals_list = []

        if not answers and question.matrix_row_ids:
            answers = {question.matrix_row_ids[0].id: [False]}

        if answers:
            if question._filter_foreign_answer_ids(
                answers.keys(), field="matrix_row_ids"
            ):
                raise ValidationError(
                    _("This answer is not a valid choice for this question.")
                )
            for row_key, row_answer in answers.items():
                for answer in row_answer:
                    vals = self._get_line_answer_values(question, answer, "suggestion")
                    vals["matrix_row_id"] = int(row_key)
                    vals_list.append(vals.copy())

        if comment:
            vals_list.append(self._get_line_comment_values(question, comment))

        old_answers.sudo().unlink()
        return self.env["survey.user_input.line"].create(vals_list)

    def _save_line_per_answer(
        self, question: Any, old_answers: Any, answers: dict | None
    ) -> Any:
        vals_list = []
        if not answers:
            vals_list.append(
                {
                    "user_input_id": self.id,
                    "question_id": question.id,
                    "skipped": True,
                    "answer_type": None,
                }
            )
        else:
            if question._filter_foreign_answer_ids(answers.keys()):
                raise ValidationError(
                    _("This answer is not a valid choice for this question.")
                )
            for answer_id, value in answers.items():
                vals_list.append(
                    {
                        "user_input_id": self.id,
                        "question_id": question.id,
                        "skipped": False,
                        "answer_type": "numerical_box",
                        "suggested_answer_id": int(answer_id),
                        "value_numerical_box": float(value),
                    }
                )
        old_answers.sudo().unlink()
        return self.env["survey.user_input.line"].create(vals_list)

    def _save_line_file_upload(
        self, question: Any, old_answers: Any, answer: Any
    ) -> Any:
        vals = {
            "user_input_id": self.id,
            "question_id": question.id,
            "skipped": not answer,
            "answer_type": "char_box" if answer else None,
            "value_char_box": str(answer) if answer else False,
        }
        if old_answers:
            old_answers.write(vals)
            return old_answers
        return self.env["survey.user_input.line"].create(vals)

    def _get_line_answer_values(
        self, question: Any, answer: Any, answer_type: str
    ) -> dict[str, Any]:
        vals = {
            "user_input_id": self.id,
            "question_id": question.id,
            "skipped": False,
            "answer_type": answer_type,
        }
        if question._is_unanswered(answer):
            vals.update(answer_type=None, skipped=True)
            return vals

        if answer_type == "suggestion":
            if question._filter_foreign_answer_ids([answer]):
                raise ValidationError(
                    _("This answer is not a valid choice for this question.")
                )
            vals["suggested_answer_id"] = int(answer)
        elif answer_type in ("numerical_box", "slider"):
            vals["answer_type"] = "numerical_box"
            vals["value_numerical_box"] = float(answer)
        elif answer_type in ("scale", "nps", "rating"):
            vals["answer_type"] = "scale"
            vals["value_scale"] = int(answer)
        else:
            vals[f"value_{answer_type}"] = answer
        return vals

    def _get_line_comment_values(self, question: Any, comment: str) -> dict[str, Any]:
        return {
            "user_input_id": self.id,
            "question_id": question.id,
            "skipped": False,
            "answer_type": "char_box",
            "value_char_box": comment,
        }

    def _prepare_answer_statistics(self) -> dict[Any, dict[str, Any]]:
        res = {user_input: {"by_section": {}} for user_input in self}

        scored_questions = self.mapped("predefined_question_ids").filtered(
            lambda question: question.is_scored_question
        )

        for question in scored_questions:
            question_incorrect_scored_answers = self.env["survey.question.answer"]
            question_correct_suggested_answers = self.env["survey.question.answer"]
            if question.question_type in ("simple_choice", "dropdown"):
                question_incorrect_scored_answers = (
                    question.suggested_answer_ids.filtered(
                        lambda answer: not answer.is_correct and answer.answer_score > 0
                    )
                )
            if question.question_type in [
                "simple_choice",
                "dropdown",
                "multiple_choice",
            ]:
                question_correct_suggested_answers = (
                    question.suggested_answer_ids.filtered(
                        lambda answer: answer.is_correct
                    )
                )

            question_section = question.page_id.title or _("Uncategorized")
            for user_input in self:
                user_input_lines = user_input.user_input_line_ids.filtered(
                    lambda line, q=question: (
                        line.question_id == q
                        and (
                            line.answer_type != "char_box" or q.comment_count_as_answer
                        )
                    )
                )
                if question.question_type in ("simple_choice", "dropdown"):
                    answer_result_key = self._simple_choice_question_answer_result(
                        user_input_lines,
                        question_correct_suggested_answers,
                        question_incorrect_scored_answers,
                    )
                elif question.question_type == "multiple_choice":
                    answer_result_key = self._multiple_choice_question_answer_result(
                        user_input_lines, question_correct_suggested_answers
                    )
                else:
                    answer_result_key = self._simple_question_answer_result(
                        user_input_lines
                    )

                if question_section not in res[user_input]["by_section"]:
                    res[user_input]["by_section"][question_section] = {
                        "question_count": 0,
                        "correct": 0,
                        "partial": 0,
                        "incorrect": 0,
                        "skipped": 0,
                    }

                res[user_input]["by_section"][question_section]["question_count"] += 1
                res[user_input]["by_section"][question_section][answer_result_key] += 1

        for user_input in self:
            res[user_input]["totals"] = self._aggregate_section_totals(
                res[user_input]["by_section"]
            )

        return res

    def _aggregate_section_totals(
        self,
        by_section: dict[str, dict[str, int]],
    ) -> list[dict[str, Any]]:
        correct = partial = incorrect = skipped = 0
        for section_counts in by_section.values():
            correct += section_counts.get("correct", 0)
            partial += section_counts.get("partial", 0)
            incorrect += section_counts.get("incorrect", 0)
            skipped += section_counts.get("skipped", 0)
        return [
            {"text": _("Correct"), "count": correct},
            {"text": _("Partially"), "count": partial},
            {"text": _("Incorrect"), "count": incorrect},
            {"text": _("Unanswered"), "count": skipped},
        ]

    def _multiple_choice_question_answer_result(
        self, user_input_lines: Any, question_correct_suggested_answers: Any
    ) -> str:
        correct_user_input_lines = user_input_lines.filtered(
            lambda line: line.answer_is_correct and not line.skipped
        ).mapped("suggested_answer_id")
        incorrect_user_input_lines = user_input_lines.filtered(
            lambda line: not line.answer_is_correct and not line.skipped
        )
        if (
            question_correct_suggested_answers
            and correct_user_input_lines == question_correct_suggested_answers
            and not incorrect_user_input_lines
        ):
            return "correct"
        elif correct_user_input_lines:
            return "partial"
        elif incorrect_user_input_lines:
            return "incorrect"
        else:
            return "skipped"

    def _simple_choice_question_answer_result(
        self,
        user_input_line: Any,
        question_correct_suggested_answers: Any,
        question_incorrect_scored_answers: Any,
    ) -> str:
        user_answer = (
            user_input_line.suggested_answer_id
            if not user_input_line.skipped
            else self.env["survey.question.answer"]
        )
        if user_answer in question_correct_suggested_answers:
            return "correct"
        elif user_answer in question_incorrect_scored_answers:
            return "partial"
        elif user_answer:
            return "incorrect"
        else:
            return "skipped"

    def _simple_question_answer_result(self, user_input_line: Any) -> str:
        if user_input_line.skipped:
            return "skipped"
        elif user_input_line.answer_is_correct:
            return "correct"
        else:
            return "incorrect"

    def _get_conditional_values(self) -> tuple[dict, dict, Any]:
        triggering_answers_by_question = {}
        triggered_questions_by_answer = {}
        if self.survey_id and self.survey_id.questions_selection != "random":
            triggering_answers_by_question, triggered_questions_by_answer = (
                self.survey_id._get_conditional_maps()
            )
        selected_answers = self._get_selected_suggested_answers()

        return (
            triggering_answers_by_question,
            triggered_questions_by_answer,
            selected_answers,
        )

    def _get_selected_suggested_answers(self) -> Any:
        return self.mapped("user_input_line_ids.suggested_answer_id")

    def _clear_inactive_conditional_answers(self) -> None:
        inactive_questions = self._get_inactive_conditional_questions()

        answers_to_delete = self.user_input_line_ids.filtered(
            lambda answer: answer.question_id in inactive_questions
        )
        answers_to_delete.unlink()

    def _get_inactive_conditional_questions(self) -> Any:
        _dummy_triggering_answers, _dummy_triggered_questions, selected_answers = (
            self._get_conditional_values()
        )

        inactive_questions = self.env["survey.question"]
        for question in self.sudo().survey_id.question_ids:
            has_answer_trigger = bool(question.triggering_answer_ids)
            has_value_trigger = bool(question.triggering_question_id)

            if not has_answer_trigger and not has_value_trigger:
                continue

            answer_trigger_met = has_answer_trigger and bool(
                question.triggering_answer_ids & selected_answers
            )
            value_trigger_met = has_value_trigger and self._evaluate_value_trigger(
                question
            )

            if not answer_trigger_met and not value_trigger_met:
                inactive_questions |= question

        return inactive_questions

    def _evaluate_value_trigger(self, question: Any) -> bool:
        trigger_q = question.triggering_question_id
        op = question.triggering_operator
        threshold = question.triggering_value or ""

        answer_line = self.user_input_line_ids.filtered(
            lambda ln, q=trigger_q: ln.question_id == q and not ln.skipped
        )
        if not answer_line:
            return op == "is_not_answered"
        if op == "is_answered":
            return True
        if op == "is_not_answered":
            return False

        answer_value = answer_line[0]._get_answer_value()
        if answer_value is None:
            return op == "is_not_answered"

        if trigger_q.question_type in (
            "numerical_box",
            "slider",
            "scale",
            "nps",
            "rating",
        ):
            try:
                num_val = float(answer_value)
                num_threshold = float(threshold)
            except ValueError, TypeError:
                return False
            return self._compare(op, num_val, num_threshold)

        str_val = str(answer_value).strip().lower()
        str_threshold = threshold.strip().lower()
        if op == "contains":
            return str_threshold in str_val
        return self._compare(op, str_val, str_threshold)

    @staticmethod
    def _compare(operator: str, value: Any, threshold: Any) -> bool:
        match operator:
            case "eq":
                return value == threshold
            case "neq":
                return value != threshold
            case "gt":
                return value > threshold
            case "gte":
                return value >= threshold
            case "lt":
                return value < threshold
            case "lte":
                return value <= threshold
        return False

    def _get_print_questions(self) -> Any:
        survey = self.survey_id
        if self.is_session_answer:
            most_voted_answers = survey._get_session_most_voted_answers()
            inactive_questions = (
                most_voted_answers._get_inactive_conditional_questions()
            )
        else:
            inactive_questions = self._get_inactive_conditional_questions()
        return (
            survey.question_ids if survey else self.predefined_question_ids
        ) - inactive_questions

    def _get_next_skipped_page_or_question(self) -> Any:
        self.check_singleton()
        skipped_mandatory_answer_ids = self.user_input_line_ids.filtered(
            lambda answer: answer.skipped and answer.question_id.constr_mandatory
        )

        if not skipped_mandatory_answer_ids:
            return self.env["survey.question"]

        page_or_question_key = (
            "page_id"
            if self.survey_id.questions_layout_effective == "page_per_section"
            else "question_id"
        )
        page_or_question_ids = skipped_mandatory_answer_ids.mapped(
            page_or_question_key
        ).sorted()

        if (
            self.last_displayed_page_id not in page_or_question_ids
            or self.last_displayed_page_id == page_or_question_ids[-1]
        ):
            return page_or_question_ids[0]

        current_page_index = page_or_question_ids.ids.index(
            self.last_displayed_page_id.id
        )
        return page_or_question_ids[current_page_index + 1]

    def _get_skipped_questions(self) -> Any:
        self.check_singleton()

        return self.user_input_line_ids.filtered(
            lambda answer: answer.skipped and answer.question_id.constr_mandatory
        ).question_id

    def _is_last_skipped_page_or_question(self, page_or_question: Any) -> bool:
        if self.survey_id.questions_layout_effective == "one_page":
            return True
        skipped = self._get_skipped_questions()
        if not skipped:
            return True
        if self.survey_id.questions_layout_effective == "page_per_section":
            skipped = skipped.page_id
        return skipped[-1:] == page_or_question

    def _notify_new_participation_subscribers(self) -> None:
        subtype_id = self.env.ref(
            "survey.mt_survey_survey_user_input_completed", raise_if_not_found=False
        )
        if not self.ids or not subtype_id:
            return
        author_id = (
            self.env.ref("base.partner_root").id
            if self.env.user.is_public
            else self.env.user.partner_id.id
        )
        recipients_data = self.env["mail.followers"]._get_recipient_data(
            self.survey_id, "notification", subtype_id.id
        )
        followed_survey_ids = [
            survey_id for survey_id, followers in recipients_data.items() if followers
        ]
        for user_input in self.filtered(
            lambda user_input_: user_input_.survey_id.id in followed_survey_ids
        ):
            survey_title = user_input.survey_id.title
            if user_input.partner_id:
                body = _(
                    '%(participant)s just participated in "%(survey_title)s".',
                    participant=user_input.partner_id.display_name,
                    survey_title=survey_title,
                )
            else:
                body = _(
                    'Someone just participated in "%(survey_title)s".',
                    survey_title=survey_title,
                )

            user_input.message_post(
                author_id=author_id,
                body=body,
                subtype_xmlid="survey.mt_survey_user_input_completed",
            )

    RETENTION_BATCH_SIZE = 1000

    @api.model
    def _cron_cleanup_expired_responses(self) -> None:
        """One domain for every survey, and a bounded unlink.

        The per-survey loop issued one search each, then deleted the whole expired set
        in a single transaction -- unbounded by construction, since the first run
        against a survey with a year of history is the largest one.
        """
        now = fields.Datetime.now()
        surveys = self.env["survey.survey"].search([("data_retention_days", ">", 0)])
        if not surveys:
            return

        expired_domain = (
            Domain("state", "=", "done")
            & Domain("test_entry", "=", False)
            & Domain.OR(
                Domain("survey_id", "=", survey.id)
                & Domain(
                    "end_datetime",
                    "<",
                    now - relativedelta(days=survey.data_retention_days),
                )
                for survey in surveys
            )
        )

        auto_commit = not modules.module.current_test
        while expired := self.search(expired_domain, limit=self.RETENTION_BATCH_SIZE):
            _logger.info(
                "Data retention: deleting %s expired response(s)", len(expired)
            )
            expired.sudo().unlink()
            if auto_commit:
                self.env.cr.commit()
