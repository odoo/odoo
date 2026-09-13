import logging
import random
import re
import uuid
from collections import defaultdict
from typing import Any, Literal, Self
from urllib.parse import urlencode

from markupsafe import escape

from odoo import Command, _, api, exceptions, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.netguard import DestinationRefused
from odoo.libs.web import urljoin as url_join
from odoo.models import ValuesType
from odoo.tools import escape_psql, is_html_empty

_logger = logging.getLogger(__name__)


class SurveySurvey(models.Model):
    _name = "survey.survey"
    _description = "Survey"
    _order = "create_date DESC"
    _rec_name = "title"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity"]

    SHORT_TOKEN_LENGTH = 6

    @api.model
    def _default_access_token(self) -> str:
        return str(uuid.uuid4())

    @api.model
    def default_get(self, fields: list[str]) -> dict[str, Any]:
        result = super().default_get(fields)
        if (
            "title" in fields
            and not result.get("title")
            and self.env.context.get("default_name")
        ):
            result["title"] = self.env.context.get("default_name")
        return result

    survey_type = fields.Selection(
        selection=[
            ("survey", "Survey"),
            ("live_session", "Live session"),
            ("assessment", "Assessment"),
            ("custom", "Custom"),
        ],
        default="custom",
        required=True,
    )
    lang_ids = fields.Many2many(
        comodel_name="res.lang",
        string="Languages",
        default=lambda self: self.env["res.lang"]._get_lang_cached(
            self.env.context.get("lang") or self.env["res.lang"].get_installed()[0][0]
        ),
        domain=lambda self: [
            (
                "id",
                "in",
                [
                    lang.id
                    for lang in self.env["res.lang"]
                    ._get_active_by_field("code")
                    .values()
                ],
            )
        ],
        help="Leave the field empty to support all installed languages.",
    )
    allowed_survey_types = fields.Json(
        string="Allowed survey types",
        compute="_compute_allowed_survey_types",
    )
    title = fields.Char(
        string="Survey Title",
        translate=True,
        required=True,
    )
    color = fields.Integer(
        string="Color Index",
        default=0,
    )
    tag_ids = fields.Many2many(
        comodel_name="survey.tag",
        string="Tags",
    )
    category_id = fields.Many2one(
        comodel_name="survey.category",
        index="btree_not_null",
    )
    description = fields.Html(
        translate=True,
        sanitize=True,
        sanitize_overridable=True,
        help="The description will be displayed on the home page of the survey. You can use this to give the purpose and guidelines to your candidates before they start it.",
    )
    description_done = fields.Html(
        string="End Message",
        translate=True,
        help="This message will be displayed when survey is completed",
    )
    background_image = fields.Image()
    background_image_url = fields.Char(
        string="Background Url",
        compute="_compute_background_image_url",
    )
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        domain=[("share", "=", False)],
        tracking=1,
    )
    restrict_user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Restricted to",
        domain=[("share", "=", False)],
        tracking=2,
    )
    question_and_page_ids = fields.One2many(
        comodel_name="survey.question",
        inverse_name="survey_id",
        string="Sections and Questions",
        copy=True,
    )
    page_ids = fields.One2many(
        comodel_name="survey.question",
        string="Pages",
        compute="_compute_page_and_question_ids",
    )
    question_ids = fields.One2many(
        comodel_name="survey.question",
        string="Questions",
        compute="_compute_page_and_question_ids",
    )
    question_count = fields.Count(
        count_of="question_ids",
        string="# Questions",
    )
    questions_layout = fields.Selection(
        selection=[
            ("page_per_question", "One page per question"),
            ("page_per_section", "One page per section"),
            ("one_page", "One page with all the questions"),
            ("conversational", "Conversational"),
        ],
        string="Pagination",
        default="page_per_question",
        required=True,
    )
    questions_selection = fields.Selection(
        selection=[("all", "All questions"), ("random", "Randomized per Section")],
        string="Question Selection",
        default="all",
        required=True,
        help="If randomized is selected, you can configure the number of random questions by section. This mode is ignored in live session.",
    )
    progression_mode = fields.Selection(
        selection=[("percent", "Percentage left"), ("number", "Number")],
        string="Display Progress as",
        default="percent",
        help="If Number is selected, it will display the number of questions answered on the total number of question to answer.",
    )
    user_input_ids = fields.One2many(
        comodel_name="survey.user_input",
        inverse_name="survey_id",
        string="User responses",
        readonly=True,
    )
    quota_ids = fields.One2many(
        comodel_name="survey.quota",
        inverse_name="survey_id",
        string="Quotas",
        help="Response quotas per answer option. When a quota is full, new respondents cannot select that answer.",
    )
    access_mode = fields.Selection(
        selection=[
            ("public", "Anyone with the link"),
            ("token", "Invited people only"),
        ],
        default="public",
        required=True,
    )
    access_token = fields.Char(
        default=lambda self: self._default_access_token(),
        copy=False,
    )
    users_login_required = fields.Boolean(
        string="Require Login",
        help="If checked, users have to login before answering even with a valid token.",
    )
    users_can_go_back = fields.Boolean(
        string="Users can go back",
        help="If checked, users can go back to previous pages.",
    )
    users_can_signup = fields.Boolean(
        string="Users can signup",
        compute="_compute_users_can_signup",
    )
    data_retention_days = fields.Integer(
        string="Data Retention (days)",
        default=0,
        help="Automatically delete completed responses older than this many days. "
        "Set to 0 to keep responses indefinitely.",
    )
    anonymize_ip = fields.Boolean(
        string="Anonymize IP Addresses",
        help="If enabled, respondent IP addresses are not stored.",
    )
    webhook_url = fields.Char(
        string="Webhook URL",
        help="URL to POST survey event data to. The payload is a JSON object "
        "with event type, survey, respondent, and answer details.",
    )
    webhook_events = fields.Selection(
        selection=[
            ("completed", "On completion only"),
            ("all", "On start, page submit, and completion"),
        ],
        default="completed",
        help="Which events trigger the webhook. 'All' fires on survey_started, "
        "page_submitted, and survey_completed.",
    )
    survey_url = fields.Char(
        string="Survey URL",
        compute="_compute_survey_urls",
    )
    survey_qr_url = fields.Char(
        string="QR Code URL",
        compute="_compute_survey_urls",
    )
    survey_embed_code = fields.Text(
        string="Embed Code",
        compute="_compute_survey_embed_code",
        help="HTML iframe snippet for embedding this survey on an external website.",
    )
    followup_rule_ids = fields.One2many(
        comodel_name="survey.followup.rule",
        inverse_name="survey_id",
        string="Follow-up Rules",
        help="Automated emails sent after survey completion based on conditions.",
    )
    slug = fields.Char(
        string="Custom URL Slug",
        help="Vanity URL path for this survey (e.g. 'customer-feedback'). "
        "The survey will be accessible at /s/customer-feedback in addition to the token URL.",
    )
    date_open = fields.Datetime(
        string="Opens On",
        help="Survey automatically becomes active at this date and time. Leave empty for immediate.",
    )
    date_close = fields.Datetime(
        string="Closes On",
        help="Survey automatically becomes inactive at this date and time. Leave empty for no deadline.",
    )
    date_schedule_applied = fields.Datetime(
        string="Schedule Applied On",
        copy=False,
        readonly=True,
        help="When the Opens On schedule was last acted on — either the "
        "scheduler opened the survey, or someone archived it and overrode the "
        "schedule. Cleared when Opens On changes, which arms it again.",
    )
    theme_color = fields.Char(
        string="Primary Color",
        default="#714B67",
        help="Primary color for buttons and accents (hex code, e.g. #714B67).",
    )
    theme_font = fields.Selection(
        selection=[
            ("default", "Default (System)"),
            ("serif", "Serif"),
            ("sans-serif", "Sans-serif"),
            ("monospace", "Monospace"),
        ],
        string="Font Family",
        default="default",
    )
    theme_custom_css = fields.Text(
        string="Custom CSS",
        help="Additional CSS applied to the survey frontend. Use with caution.",
    )
    answer_count = fields.Integer(
        string="Registered",
        compute="_compute_survey_statistic",
    )
    answer_done_count = fields.Integer(
        string="Attempts",
        compute="_compute_survey_statistic",
    )
    answer_score_avg = fields.Float(
        string="Avg Score (%)",
        compute="_compute_survey_statistic",
    )
    answer_duration_avg = fields.Float(
        string="Average Duration",
        compute="_compute_answer_duration_avg",
        help="Average duration of the survey (in hours)",
    )
    success_count = fields.Integer(
        string="Success",
        compute="_compute_survey_statistic",
    )
    success_ratio = fields.Integer(
        string="Success Ratio (%)",
        compute="_compute_survey_statistic",
    )
    scoring_type = fields.Selection(
        selection=[
            ("no_scoring", "No scoring"),
            ("scoring_with_answers_after_page", "Scoring with answers after each page"),
            ("scoring_with_answers", "Scoring with answers at the end"),
            ("scoring_without_answers", "Scoring without answers"),
        ],
        string="Scoring",
        compute="_compute_scoring_type",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    scoring_success_min = fields.Float(
        string="Required Score (%)",
        default=80.0,
    )
    scoring_max_obtainable = fields.Float(
        string="Maximum obtainable score",
        compute="_compute_scoring_max_obtainable",
    )
    is_attempts_limited = fields.Boolean(
        string="Limited number of attempts",
        compute="_compute_is_attempts_limited",
        store=True,
        readonly=False,
        help="Check this option if you want to limit the number of attempts per user",
    )
    attempts_limit = fields.Integer(
        string="Number of attempts",
        default=1,
    )
    is_time_limited = fields.Boolean(string="The survey is limited in time")
    time_limit = fields.Float(
        string="Time limit (minutes)",
        default=10,
    )
    certification = fields.Boolean(
        string="Is a Certification",
        compute="_compute_certification",
        precompute=True,
        store=True,
        readonly=False,
    )
    certification_mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Certified Email Template",
        domain="[('model', '=', 'survey.user_input')]",
        help="Automated email sent to the user when they succeed the certification, containing their certification document.",
    )
    certification_report_layout = fields.Selection(
        selection=[
            ("modern_purple", "Modern Purple"),
            ("modern_blue", "Modern Blue"),
            ("modern_gold", "Modern Gold"),
            ("classic_purple", "Classic Purple"),
            ("classic_blue", "Classic Blue"),
            ("classic_gold", "Classic Gold"),
        ],
        string="Certification template",
        default="modern_purple",
    )
    certification_give_badge = fields.Boolean(
        string="Give Badge",
        compute="_compute_certification_give_badge",
        store=True,
        copy=False,
        readonly=False,
    )
    certification_badge_id = fields.Many2one(
        comodel_name="gamification.badge",
        index="btree_not_null",
        copy=False,
    )
    certification_badge_id_dummy = fields.Many2one(
        related="certification_badge_id",
        string="Certification Badge ",
    )
    session_available = fields.Boolean(
        string="Live session available",
        compute="_compute_session_available",
    )
    session_state = fields.Selection(
        selection=[
            ("ready", "Ready"),
            ("in_progress", "In Progress"),
        ],
        copy=False,
    )
    session_code = fields.Char(
        compute="_compute_session_code",
        precompute=True,
        store=True,
        copy=False,
        readonly=False,
        help="This code will be used by your attendees to reach your session. Feel free to customize it however you like!",
    )
    session_link = fields.Char(compute="_compute_session_link")
    session_question_id = fields.Many2one(
        comodel_name="survey.question",
        string="Current Question",
        copy=False,
        help="The current question of the survey session.",
    )
    session_start_time = fields.Datetime(
        string="Current Session Start Time",
        copy=False,
    )
    session_question_start_time = fields.Datetime(
        string="Current Question Start Time",
        copy=False,
        help="The time at which the current question has started, used to handle the timer for attendees.",
    )
    session_answer_count = fields.Integer(
        string="Answers Count",
        compute="_compute_session_answer_count",
    )
    session_question_answer_count = fields.Integer(
        string="Question Answers Count",
        compute="_compute_session_question_answer_count",
    )
    session_show_leaderboard = fields.Boolean(
        string="Show Session Leaderboard",
        compute="_compute_session_show_leaderboard",
        help="Whether or not we want to show the attendees leaderboard for this survey.",
    )
    session_speed_rating = fields.Boolean(
        string="Reward quick answers",
        help="Attendees get more points if they answer quickly",
    )
    session_speed_rating_time_limit = fields.Integer(
        string="Time limit (seconds)",
        help="Default time given to receive additional points for right answers",
    )
    has_conditional_questions = fields.Boolean(
        string="Contains conditional questions",
        compute="_compute_has_conditional_questions",
    )

    _access_token_unique = models.Constraint(
        "unique(access_token)",
        "Access token should be unique",
    )
    _session_code_unique = models.Constraint(
        "unique(session_code)",
        "Session code should be unique",
    )
    _slug_unique = models.Constraint(
        "unique(slug)",
        "Two surveys cannot share the same custom URL slug.",
    )
    _certification_check = models.Constraint(
        "CHECK( scoring_type!='no_scoring' OR certification=False )",
        "You can only create certifications for surveys that have a scoring mechanism.",
    )
    _scoring_success_min_check = models.Constraint(
        "CHECK( scoring_success_min IS NULL OR (scoring_success_min>=0 AND scoring_success_min<=100) )",
        "The percentage of success has to be defined between 0 and 100.",
    )
    _time_limit_check = models.Constraint(
        "CHECK( (is_time_limited=False) OR (time_limit is not null AND time_limit > 0) )",
        "The time limit needs to be a positive number if the survey is time limited.",
    )
    _attempts_limit_check = models.Constraint(
        "CHECK( (is_attempts_limited=False) OR (attempts_limit is not null AND attempts_limit > 0) )",
        "The attempts limit needs to be a positive number if the survey has a limited number of attempts.",
    )
    _badge_uniq = models.Constraint(
        "unique (certification_badge_id)",
        "The badge for each survey should be unique!",
    )
    _session_speed_rating_has_time_limit = models.Constraint(
        "CHECK (session_speed_rating != TRUE OR session_speed_rating_time_limit IS NOT NULL AND session_speed_rating_time_limit > 0)",
        "A positive default time limit is required when the session rewards quick answers.",
    )

    @api.depends("background_image", "access_token")
    def _compute_background_image_url(self) -> None:
        self.background_image_url = False
        for survey in self.filtered(lambda s: s.background_image and s.access_token):
            survey.background_image_url = (
                f"/survey/{survey.access_token}/get_background_image"
            )

    @api.depends(
        "question_and_page_ids",
        "question_and_page_ids.question_type",
        "question_and_page_ids.answer_score",
        "question_and_page_ids.is_scored_question",
        "question_and_page_ids.suggested_answer_ids",
        "question_and_page_ids.suggested_answer_ids.answer_score",
    )
    def _compute_scoring_max_obtainable(self) -> None:
        for survey in self:
            survey.scoring_max_obtainable = (
                survey.question_ids._get_max_obtainable_score()
            )

    def _compute_users_can_signup(self) -> None:
        signup_allowed = (
            self.env["res.users"].sudo()._get_signup_invitation_scope() == "b2c"
        )
        for survey in self:
            survey.users_can_signup = signup_allowed

    @api.depends("access_token")
    def _compute_survey_urls(self) -> None:
        for survey in self:
            base_url = survey.get_base_url()
            full_url = url_join(base_url, survey.get_start_url())
            survey.survey_url = full_url
            survey.survey_qr_url = f"/report/barcode/QR/{full_url}?width=256&height=256"

    @api.depends("access_token", "title")
    def _compute_survey_embed_code(self) -> None:
        for survey in self:
            url = url_join(survey.get_base_url(), survey.get_start_url())
            survey.survey_embed_code = (
                f'<iframe src="{escape(url)}" '
                f'style="width:100%;min-height:640px;border:none;" '
                f'title="{escape(survey.title or "")}" '
                f'allow="camera;microphone" '
                f'loading="lazy"></iframe>'
            )

    @api.depends(
        "user_input_ids.state",
        "user_input_ids.test_entry",
        "user_input_ids.scoring_percentage",
        "user_input_ids.scoring_success",
    )
    def _compute_survey_statistic(self) -> None:
        default_vals = {
            "answer_count": 0,
            "answer_done_count": 0,
            "success_count": 0,
            "answer_score_avg": 0.0,
            "success_ratio": 0.0,
        }
        stat = {cid: dict(default_vals, answer_score_avg_total=0.0) for cid in self.ids}
        UserInput = self.env["survey.user_input"]
        base_domain = [("survey_id", "in", self.ids), ("test_entry", "=", False)]

        read_group_res = UserInput._read_group(
            base_domain,
            ["survey_id", "state", "scoring_percentage", "scoring_success"],
            ["__count"],
        )
        for survey, state, scoring_percentage, scoring_success, count in read_group_res:
            stat[survey.id]["answer_count"] += count
            if state == "done":
                stat[survey.id]["answer_done_count"] += count
                stat[survey.id]["answer_score_avg_total"] += scoring_percentage * count
                if scoring_success:
                    stat[survey.id]["success_count"] += count

        for survey_stats in stat.values():
            avg_total = survey_stats.pop("answer_score_avg_total")
            done = survey_stats["answer_done_count"]
            survey_stats["answer_score_avg"] = avg_total / done if done else 0.0
            survey_stats["success_ratio"] = (
                (survey_stats["success_count"] / done) * 100 if done else 0.0
            )

        for survey in self:
            survey.update(stat.get(survey._origin.id, default_vals))

    @api.depends(
        "user_input_ids.survey_id",
        "user_input_ids.start_datetime",
        "user_input_ids.end_datetime",
    )
    def _compute_answer_duration_avg(self) -> None:
        result_per_survey_id = {}
        if self.ids:
            self.env.cr.execute(
                """SELECT survey_id,
                          avg((extract(epoch FROM end_datetime)) - (extract (epoch FROM start_datetime)))
                     FROM survey_user_input
                    WHERE survey_id = any(%s) AND state = 'done'
                          AND end_datetime IS NOT NULL
                          AND start_datetime IS NOT NULL
                 GROUP BY survey_id""",
                [self.ids],
            )
            result_per_survey_id = dict(self.env.cr.fetchall())

        for survey in self:
            survey.answer_duration_avg = (
                result_per_survey_id.get(survey.id) or 0
            ) / 3600

    @api.depends("question_and_page_ids")
    def _compute_page_and_question_ids(self) -> None:
        for survey in self:
            survey.page_ids = survey.question_and_page_ids.filtered(
                lambda question: question.is_page
            )
            survey.question_ids = survey.question_and_page_ids - survey.page_ids

    @api.depends(
        "question_and_page_ids.triggering_answer_ids",
        "users_login_required",
        "access_mode",
    )
    def _compute_is_attempts_limited(self) -> None:
        for survey in self:
            if (
                not survey.is_attempts_limited
                or (survey.access_mode == "public" and not survey.users_login_required)
                or any(
                    question.triggering_answer_ids
                    for question in survey.question_and_page_ids
                )
            ):
                survey.is_attempts_limited = False

    @api.depends("session_start_time", "user_input_ids")
    def _compute_session_answer_count(self) -> None:
        count_by_survey = {}
        if self:
            count_by_survey = dict(
                self.env["survey.user_input"]._read_group(
                    Domain("is_session_answer", "=", True)
                    & Domain("state", "!=", "done")
                    & Domain.OR(
                        Domain("survey_id", "=", survey.id)
                        & Domain("create_date", ">=", survey.session_start_time)
                        for survey in self
                    ),
                    ["survey_id"],
                    ["create_uid:count"],
                )
            )
        for survey in self:
            survey.session_answer_count = count_by_survey.get(survey, 0)

    @api.depends(
        "session_question_id",
        "session_start_time",
        "user_input_ids.user_input_line_ids",
    )
    def _compute_session_question_answer_count(self) -> None:
        count_by_survey = {}
        if self:
            count_by_survey = dict(
                self.env["survey.user_input.line"]._read_group(
                    Domain.OR(
                        Domain("question_id", "=", survey.session_question_id.id)
                        & Domain("survey_id", "=", survey.id)
                        & Domain("create_date", ">=", survey.session_start_time)
                        for survey in self
                    ),
                    ["survey_id"],
                    ["user_input_id:count_distinct"],
                )
            )
        for survey in self:
            survey.session_question_answer_count = count_by_survey.get(survey, 0)

    @api.depends("access_token")
    def _compute_session_code(self) -> None:
        survey_without_session_code = self.filtered(
            lambda survey: not survey.session_code
        )
        session_codes = self._generate_session_codes(
            code_count=len(survey_without_session_code),
            excluded_codes=set(
                (self - survey_without_session_code).mapped("session_code")
            ),
        )
        for survey, session_code in zip(
            survey_without_session_code, session_codes, strict=False
        ):
            survey.session_code = session_code

    @api.depends("session_code")
    def _compute_session_link(self) -> None:
        for survey in self:
            if survey.session_code:
                survey.session_link = url_join(
                    survey.get_base_url(), f"/s/{survey.session_code}"
                )
            else:
                survey.session_link = url_join(
                    survey.get_base_url(), survey.get_start_url()
                )

    @api.depends("scoring_type", "question_and_page_ids.save_as_nickname")
    def _compute_session_show_leaderboard(self) -> None:
        for survey in self:
            survey.session_show_leaderboard = (
                survey.scoring_type != "no_scoring"
                and any(
                    question.save_as_nickname
                    for question in survey.question_and_page_ids
                )
            )

    @api.depends("question_and_page_ids.triggering_answer_ids")
    def _compute_has_conditional_questions(self) -> None:
        for survey in self:
            survey.has_conditional_questions = any(
                question.triggering_answer_ids or question.triggering_question_id
                for question in survey.question_and_page_ids
            )

    @api.depends("scoring_type")
    def _compute_certification(self) -> None:
        for survey in self:
            if not survey.certification or survey.scoring_type == "no_scoring":
                survey.certification = False

    @api.depends("users_login_required", "certification")
    def _compute_certification_give_badge(self) -> None:
        for survey in self:
            if (
                not survey.certification_give_badge
                or not survey.users_login_required
                or not survey.certification
            ):
                survey.certification_give_badge = False

    @api.depends("certification")
    def _compute_scoring_type(self) -> None:
        for survey in self:
            if survey.certification and survey.scoring_type in {False, "no_scoring"}:
                survey.scoring_type = "scoring_without_answers"
            elif not survey.scoring_type:
                survey.scoring_type = "no_scoring"

    @api.depends("survey_type", "certification")
    def _compute_session_available(self) -> None:
        for survey in self:
            survey.session_available = (
                survey.survey_type in {"live_session", "custom"}
                and not survey.certification
            )

    @property
    def questions_layout_effective(self) -> str:
        self.check_singleton()
        if self.questions_layout == "conversational":
            return "page_per_question"
        return self.questions_layout

    @api.depends_context("uid")
    def _compute_allowed_survey_types(self) -> None:
        self.allowed_survey_types = (
            [
                "survey",
                "live_session",
                "assessment",
                "custom",
            ]
            if self.env.user.has_group("survey.group_survey_user")
            else False
        )

    @api.onchange("survey_type")
    def _onchange_survey_type(self) -> None:
        if self.survey_type == "survey":
            self.certification = False
            self.is_time_limited = False
            self.scoring_type = "no_scoring"
        elif self.survey_type == "live_session":
            self.access_mode = "public"
            self.is_attempts_limited = False
            self.is_time_limited = False
            self.progression_mode = "percent"
            self.questions_layout = "page_per_question"
            self.questions_selection = "all"
            self.scoring_type = "scoring_with_answers"
            self.users_can_go_back = False
        elif self.survey_type == "assessment":
            self.access_mode = "token"
            self.scoring_type = "scoring_with_answers"

    @api.onchange("session_speed_rating", "session_speed_rating_time_limit")
    def _onchange_session_speed_rating(self) -> None:
        for survey in self.filtered("question_ids"):
            survey.question_ids._update_time_limit_from_survey(
                is_time_limited=survey.session_speed_rating,
                time_limit=survey.session_speed_rating_time_limit,
            )

    @api.onchange("restrict_user_ids", "user_id")
    def _onchange_restrict_user_ids(self) -> None:
        surveys_to_check = self.filtered(
            lambda s: s.restrict_user_ids and bool(s.user_id - s.restrict_user_ids)
        )
        users_are_managers = surveys_to_check.user_id.filtered(
            lambda user: user.has_group("survey.group_survey_manager")
        )
        for survey in surveys_to_check.filtered(
            lambda s: s.user_id not in users_are_managers
        ):
            survey.restrict_user_ids += survey.user_id

    _SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    @api.constrains("slug")
    def _check_slug(self) -> None:
        for survey in self.filtered("slug"):
            if not self._SLUG_RE.match(survey.slug):
                raise ValidationError(
                    _(
                        "The custom URL slug '%(slug)s' may only contain lowercase "
                        "letters, digits and single hyphens.",
                        slug=survey.slug,
                    )
                )
            if len(
                survey.slug
            ) == self.SHORT_TOKEN_LENGTH and self._resolve_short_token(survey.slug):
                raise ValidationError(
                    _(
                        "The custom URL slug '%(slug)s' collides with another survey's "
                        "short link. Pick a different length or wording.",
                        slug=survey.slug,
                    )
                )

    @api.constrains("webhook_url")
    def _check_webhook_url(self) -> None:
        for survey in self.filtered("webhook_url"):
            problem = survey._webhook_url_problem(survey.webhook_url)
            if problem:
                raise ValidationError(problem)

    @api.model
    def _webhook_url_problem(self, url: str) -> str | None:
        try:
            self.env["ir.egress"].check_url((url or "").strip())
        except DestinationRefused as refusal:
            return _(
                "Webhook URL %(url)s may not be called: %(reason)s",
                url=url,
                reason=str(refusal),
            )
        return None

    @api.constrains("scoring_type", "users_can_go_back")
    def _check_scoring_after_page_availability(self) -> None:
        failing = self.filtered(
            lambda survey: (
                survey.scoring_type == "scoring_with_answers_after_page"
                and survey.users_can_go_back
            )
        )
        if failing:
            raise ValidationError(
                _(
                    'Combining roaming and "Scoring with answers after each page" is not possible; please update the following surveys:\n- %(survey_names)s',
                    survey_names="\n- ".join(failing.mapped("title")),
                )
            )

    @api.constrains("user_id", "restrict_user_ids")
    def _check_survey_responsible_access(self) -> None:
        for user_id, surveys in (
            self.filtered(lambda s: bool(s.user_id - s.restrict_user_ids))
            .grouped("user_id")
            .items()
        ):
            accessible = surveys.with_user(user_id)._filtered_access("write")
            if len(accessible) < len(surveys):
                failing_surveys_sudo = (self - accessible).sudo()
                raise ValidationError(
                    _(
                        "The access of the following surveys is restricted. Make sure their responsible still has access to it: \n%(survey_names)s\n",
                        survey_names="\n".join(
                            f"- {survey.title}: {survey.user_id.name}"
                            for survey in failing_surveys_sudo
                        ),
                    )
                )

    @staticmethod
    def _normalize_slug(slug: str | bool) -> str | Literal[False]:
        return (slug or "").strip().lower() or False

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        for vals in vals_list:
            if "slug" in vals:
                vals["slug"] = self._normalize_slug(vals["slug"])
        surveys = super().create(vals_list)
        for survey_sudo in surveys.filtered(
            lambda survey: survey.certification_give_badge
        ).sudo():
            survey_sudo._create_certification_badge_trigger()
        return surveys

    def write(self, vals: ValuesType) -> Literal[True]:
        speed_rating, speed_limit = (
            vals.get("session_speed_rating"),
            vals.get("session_speed_rating_time_limit"),
        )

        surveys_to_update = self.filtered(
            lambda s: (
                (speed_rating is not None and s.session_speed_rating != speed_rating)
                or (
                    speed_limit is not None
                    and s.session_speed_rating_time_limit != speed_limit
                )
            )
        )

        badge_flag = vals.get("certification_give_badge")
        surveys_changing_badge = (
            self.filtered(lambda s: s.certification_give_badge != badge_flag)
            if "certification_give_badge" in vals
            else self.browse()
        )
        surveys_opening_changed = self.browse()
        if "date_open" in vals and "date_schedule_applied" not in vals:
            new_date_open = fields.Datetime.to_datetime(vals["date_open"])
            surveys_opening_changed = self.filtered(
                lambda s: s.date_open != new_date_open
            )
        if "slug" in vals:
            vals = dict(vals, slug=self._normalize_slug(vals["slug"]))

        result = super().write(vals)
        if surveys_opening_changed:
            surveys_opening_changed.write({"date_schedule_applied": False})
        if surveys_changing_badge:
            surveys_changing_badge.sudo()._handle_certification_badges(vals)

        if questions_to_update := surveys_to_update.question_ids:
            questions_to_update._update_time_limit_from_survey(
                is_time_limited=speed_rating, time_limit=speed_limit
            )

        return result

    def copy(self, default: ValuesType | None = None) -> Self:
        new_surveys = super().copy(default)
        if default and "question_ids" in default:
            return new_surveys

        for old_survey, new_survey in zip(self, new_surveys, strict=False):
            cloned_question_ids = new_survey.question_ids.sorted()

            answers_map = {
                src_answer.id: dst_answer.id
                for src, dst in zip(
                    old_survey.question_ids, cloned_question_ids, strict=False
                )
                for src_answer, dst_answer in zip(
                    src.suggested_answer_ids,
                    dst.suggested_answer_ids.sorted(),
                    strict=False,
                )
            }
            for src, dst in zip(
                old_survey.question_ids, cloned_question_ids, strict=False
            ):
                if src.triggering_answer_ids:
                    dst.triggering_answer_ids = [
                        answers_map[src_answer_id.id]
                        for src_answer_id in src.triggering_answer_ids
                    ]
        return new_surveys

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        vals_list = super().copy_data(default=default)
        return [
            dict(vals, title=self.env._("%s (copy)", survey.title))
            for survey, vals in zip(self, vals_list, strict=False)
        ]

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "title"))
        self._copy_translations_of_renamed_field(
            new, "title", lambda record, term: record.env._("%s (copy)", term)
        )

    def action_archive(self) -> None:
        super().action_archive()
        self.filtered(
            lambda survey: survey.date_open and not survey.date_schedule_applied
        ).date_schedule_applied = fields.Datetime.now()
        self.certification_badge_id.action_archive()

    def action_unarchive(self) -> None:
        super().action_unarchive()
        self.certification_badge_id.action_unarchive()

    def _create_answer(
        self,
        user: Self | bool = False,
        partner: Self | bool = False,
        email: str | bool = False,
        test_entry: bool = False,
        check_attempts: bool = True,
        **additional_vals: Any,
    ) -> Self:
        self.check_access("read")

        invite_token = additional_vals.pop("invite_token", False)
        nickname = additional_vals.pop("nickname", False)

        if partner and not user and partner.user_ids:
            user = partner.user_ids[0]

        user_inputs = self.env["survey.user_input"]
        for survey in self:
            survey._check_answer_creation(
                user,
                partner,
                email,
                test_entry=test_entry,
                check_attempts=check_attempts,
                invite_token=invite_token,
            )
            answer_vals = {
                "survey_id": survey.id,
                "test_entry": test_entry,
                "is_session_answer": survey.session_state in ["ready", "in_progress"],
            }
            if survey.session_state == "in_progress":
                answer_vals.update(
                    {
                        "state": "in_progress",
                        "start_datetime": fields.Datetime.now(),
                    }
                )
            if user and not user._is_public():
                answer_vals["partner_id"] = user.partner_id.id
                answer_vals["email"] = user.email
                answer_vals["nickname"] = nickname or user.name
            elif partner:
                answer_vals["partner_id"] = partner.id
                answer_vals["email"] = partner.email
                answer_vals["nickname"] = nickname or partner.name
            else:
                answer_vals["email"] = email
                answer_vals["nickname"] = nickname

            if invite_token:
                answer_vals["invite_token"] = invite_token
            elif survey.is_attempts_limited and survey.access_mode != "public":
                answer_vals["invite_token"] = self.env[
                    "survey.user_input"
                ]._generate_invite_token()

            answer_vals.update(additional_vals)
            user_input = user_inputs.create(answer_vals)
            user_inputs += user_input
            survey._prefill_identity_questions(user_input)

        return user_inputs

    def _prefill_identity_questions(self, user_input: Self) -> None:
        self.check_singleton()
        for question in self.question_ids.filtered(
            lambda q: (
                q.question_type == "char_box"
                and (q.save_as_email or q.save_as_nickname)
            )
        ):
            if question.save_as_email and user_input.email:
                user_input._save_lines(question, user_input.email)
            if question.save_as_nickname and user_input.nickname:
                user_input._save_lines(question, user_input.nickname)

    def _check_answer_creation(
        self,
        user: Self | bool,
        partner: Self | bool,
        email: str | bool,
        test_entry: bool = False,
        check_attempts: bool = True,
        invite_token: str | bool = False,
    ) -> None:
        self.check_singleton()
        if test_entry:
            try:
                self.with_user(user).check_access("read")
            except AccessError as e:
                raise exceptions.UserError(
                    _("Creating test token is not allowed for you.")
                ) from e

        if not test_entry:
            if not self.active:
                raise exceptions.UserError(
                    _("Creating token for closed/archived surveys is not allowed.")
                )
            if check_attempts and not self._has_attempts_left(
                partner or (user and user.partner_id), email, invite_token
            ):
                raise exceptions.UserError(_("No attempts left."))

    def _prepare_user_input_predefined_questions(self) -> Self:
        self.check_singleton()

        questions = self.env["survey.question"]

        for question in self.question_ids:
            if not question.page_id:
                questions |= question

        for page in self.page_ids:
            if self.questions_selection == "all":
                questions |= page.question_ids
            elif 0 < page.random_questions_count < len(page.question_ids):
                questions = questions.concat(
                    *random.sample(page.question_ids, page.random_questions_count)
                )
            else:
                questions |= page.question_ids

        return questions

    def _can_go_back(self, answer: Self, page_or_question: Self) -> bool:
        self.check_singleton()
        layout = self.questions_layout_effective
        if layout == "one_page" or not self.users_can_go_back:
            return False
        if answer.state != "in_progress" or answer.is_session_answer:
            return False
        if self.page_ids and page_or_question == self.page_ids[0]:
            return False
        return (
            layout == "page_per_section"
            or page_or_question != answer.predefined_question_ids[0]
        )

    def _has_attempts_left(
        self, partner: Self | bool, email: str | bool, invite_token: str | bool
    ) -> bool:
        self.check_singleton()

        if (
            self.access_mode != "public" or self.users_login_required
        ) and self.is_attempts_limited:
            return self._get_number_of_attempts_lefts(partner, email, invite_token) > 0

        return True

    def _get_number_of_attempts_lefts(
        self, partner: Self | bool, email: str | bool, invite_token: str | bool
    ) -> int:
        self.check_singleton()

        domain = Domain(
            [
                ("survey_id", "=", self.id),
                ("test_entry", "=", False),
                ("state", "=", "done"),
            ]
        )

        if partner:
            domain &= Domain("partner_id", "=", partner.id)
        else:
            domain &= Domain("email", "=", email)

        if invite_token:
            domain &= Domain("invite_token", "=", invite_token)

        return self.attempts_limit - self.env["survey.user_input"].search_count(domain)

    def _get_pages_or_questions(self, user_input: Self) -> Self:
        self.check_singleton()
        result = self.env["survey.question"]
        if self.questions_layout_effective == "page_per_section":
            result = self.page_ids
        elif self.questions_layout_effective == "page_per_question":
            if self.questions_selection == "random" and not self.session_state:
                result = user_input.predefined_question_ids
            else:
                result = self._get_pages_and_questions_to_show()

        return result

    def _get_pages_and_questions_to_show(self) -> Self:
        self.check_singleton()
        invalid_questions = self.env["survey.question"]
        questions_and_valid_pages = self.question_and_page_ids.filtered(
            lambda question: (
                question.question_type != "calculated"
                and (not question.is_page or not is_html_empty(question.description))
            )
        )

        for question in questions_and_valid_pages.filtered(
            "triggering_answer_ids"
        ).sorted():
            if (
                question.triggering_question_id
                and question.triggering_question_id not in invalid_questions
            ):
                continue

            for trigger in question.triggering_question_ids:
                if (
                    trigger not in invalid_questions
                    and not trigger.is_page
                    and trigger.question_type
                    in ["simple_choice", "dropdown", "multiple_choice"]
                    and (
                        trigger.sequence < question.sequence
                        or (
                            trigger.sequence == question.sequence
                            and trigger.id < question.id
                        )
                    )
                ):
                    break
            else:
                invalid_questions |= question
        return questions_and_valid_pages - invalid_questions

    def _get_next_page_or_question(
        self, user_input: Self, page_or_question_id: int, go_back: bool = False
    ) -> Self:
        survey = user_input.survey_id
        pages_or_questions = survey._get_pages_or_questions(user_input)
        Question = self.env["survey.question"]

        if not go_back:
            if not pages_or_questions:
                return Question
            if page_or_question_id == 0:
                return pages_or_questions[0]

        current_page_index = pages_or_questions.ids.index(page_or_question_id)

        if (go_back and current_page_index == 0) or (
            not go_back and current_page_index == len(pages_or_questions) - 1
        ):
            return Question

        inactive_questions = user_input._get_inactive_conditional_questions()
        if survey.questions_layout_effective == "page_per_question":
            question_candidates = (
                pages_or_questions[0:current_page_index]
                if go_back
                else pages_or_questions[current_page_index + 1 :]
            )
            for question in question_candidates.sorted(reverse=go_back):
                if question.is_page:
                    contains_active_question = any(
                        sub_question not in inactive_questions
                        for sub_question in question.question_ids
                    )
                    is_description_section = (
                        not question.question_ids
                        and not is_html_empty(question.description)
                    )
                    if contains_active_question or is_description_section:
                        return question
                elif question not in inactive_questions:
                    return question
        elif survey.questions_layout_effective == "page_per_section":
            section_candidates = (
                pages_or_questions[0:current_page_index]
                if go_back
                else pages_or_questions[current_page_index + 1 :]
            )
            for section in section_candidates.sorted(reverse=go_back):
                contains_active_question = any(
                    question not in inactive_questions
                    for question in section.question_ids
                )
                is_description_section = not section.question_ids and not is_html_empty(
                    section.description
                )
                if contains_active_question or is_description_section:
                    return section
        return Question

    def _is_first_page_or_question(
        self, user_input: Self, page_or_question: Self
    ) -> bool:
        if self.questions_layout_effective == "one_page":
            return True
        pages_or_questions = self._get_pages_or_questions(user_input)
        if not pages_or_questions:
            return True
        return page_or_question.id == pages_or_questions[0].id

    def _is_last_page_or_question(
        self, user_input: Self, page_or_question: Self
    ) -> bool:
        if self.questions_layout_effective == "one_page":
            return True
        pages_or_questions = self._get_pages_or_questions(user_input)
        current_page_index = pages_or_questions.ids.index(page_or_question.id)
        next_page_or_question_candidates = pages_or_questions[current_page_index + 1 :]
        if not next_page_or_question_candidates:
            return True
        inactive_questions = user_input._get_inactive_conditional_questions()
        if self.questions_layout_effective == "page_per_question":
            return not (
                any(
                    next_question not in inactive_questions
                    for next_question in next_page_or_question_candidates
                )
            )
        elif self.questions_layout_effective == "page_per_section":
            for section in next_page_or_question_candidates:
                if any(
                    next_question not in inactive_questions
                    for next_question in section.question_ids
                ):
                    return False
        return True

    def _get_survey_questions(
        self,
        answer: Self | None = None,
        page_id: int | None = None,
        question_id: int | None = None,
    ) -> tuple[Self, int | None]:
        if answer and answer.is_session_answer:
            return self.session_question_id, self.session_question_id.id
        if self.questions_layout_effective == "page_per_section":
            if not page_id:
                raise ValueError(
                    "Page id is needed for question layout 'page_per_section'"
                )
            page_or_question_id = int(page_id)
            questions = (
                self.env["survey.question"]
                .sudo()
                .search(
                    Domain("survey_id", "=", self.id)
                    & Domain("page_id", "=", page_or_question_id)
                )
            )
        elif self.questions_layout_effective == "page_per_question":
            if not question_id:
                raise ValueError(
                    "Question id is needed for question layout 'page_per_question'"
                )
            page_or_question_id = int(question_id)
            questions = self.env["survey.question"].sudo().browse(page_or_question_id)
        else:
            page_or_question_id = None
            questions = self.question_ids

        if answer:
            questions &= answer.predefined_question_ids
        return questions, page_or_question_id

    def _get_conditional_maps(self) -> tuple[defaultdict, defaultdict]:
        triggering_answers_by_question = defaultdict(
            lambda: self.env["survey.question.answer"]
        )
        triggered_questions_by_answer = defaultdict(lambda: self.env["survey.question"])
        for question in self.question_ids:
            triggering_answers_by_question[question] |= question.triggering_answer_ids

            for triggering_answer_id in question.triggering_answer_ids:
                triggered_questions_by_answer[triggering_answer_id] |= question

        return triggering_answers_by_question, triggered_questions_by_answer

    def _session_open(self) -> None:
        if self.env.user.has_group("survey.group_survey_user"):
            self.sudo().write({"session_state": "in_progress"})
            self.sudo().flush_recordset(["session_state"])

    def _get_session_next_question(self, go_back: bool) -> Self | None:
        self.check_singleton()

        if not self.question_ids or not self.env.user.has_group(
            "survey.group_survey_user"
        ):
            return None

        most_voted_answers = self._get_session_most_voted_answers()
        return self._get_next_page_or_question(
            most_voted_answers,
            self.session_question_id.id if self.session_question_id else 0,
            go_back=go_back,
        )

    def _get_session_most_voted_answers(self) -> Self:
        current_user_inputs = self.user_input_ids.filtered(
            lambda ui: (
                self.session_start_time and ui.create_date > self.session_start_time
            )
        )
        current_user_input_lines = current_user_inputs.user_input_line_ids.filtered(
            "suggested_answer_id"
        )

        votes_by_answer = dict.fromkeys(
            current_user_input_lines.mapped("suggested_answer_id"), 0
        )
        for answer in current_user_input_lines:
            votes_by_answer[answer.suggested_answer_id] += 1

        most_voted_answer_by_questions = dict.fromkeys(
            current_user_input_lines.mapped("question_id")
        )
        for question in most_voted_answer_by_questions:
            for answer in votes_by_answer:
                if answer.question_id != question:
                    continue
                most_voted_answer = most_voted_answer_by_questions[question]
                if (
                    not most_voted_answer
                    or votes_by_answer[most_voted_answer] < votes_by_answer[answer]
                ):
                    most_voted_answer_by_questions[question] = answer

        fake_user_input = self.env["survey.user_input"].new(
            {
                "survey_id": self.id,
                "predefined_question_ids": [
                    Command.set(self._prepare_user_input_predefined_questions().ids)
                ],
            }
        )

        fake_user_input_lines = self.env["survey.user_input.line"]
        for question, answer in most_voted_answer_by_questions.items():
            fake_user_input_lines |= self.env["survey.user_input.line"].new(
                {
                    "question_id": question.id,
                    "suggested_answer_id": answer.id,
                    "survey_id": self.id,
                    "user_input_id": fake_user_input.id,
                }
            )

        return fake_user_input

    def _prepare_leaderboard_values(self) -> list[dict[str, Any]]:
        self.check_singleton()

        leaderboard = self.env["survey.user_input"].search_read(
            [
                ("survey_id", "=", self.id),
                ("create_date", ">=", self.session_start_time),
            ],
            [
                "id",
                "nickname",
                "scoring_total",
            ],
            limit=15,
            order="scoring_total desc",
        )

        if (
            leaderboard
            and self.session_state == "in_progress"
            and any(
                answer.answer_score
                for answer in self.session_question_id.suggested_answer_ids
            )
        ):
            question_scores = {}
            input_lines = self.env["survey.user_input.line"].search_read(
                [
                    ("user_input_id", "in", [score["id"] for score in leaderboard]),
                    ("question_id", "=", self.session_question_id.id),
                ],
                ["user_input_id", "answer_score"],
            )
            for input_line in input_lines:
                question_scores[input_line["user_input_id"][0]] = (
                    question_scores.get(input_line["user_input_id"][0], 0)
                    + input_line["answer_score"]
                )

            for score_position, leaderboard_item in enumerate(leaderboard):
                question_score = question_scores.get(leaderboard_item["id"], 0)
                leaderboard_item.update(
                    {
                        "updated_score": leaderboard_item["scoring_total"],
                        "scoring_total": leaderboard_item["scoring_total"]
                        - question_score,
                        "leaderboard_position": score_position,
                        "max_question_score": sum(
                            score
                            for score in self.session_question_id.suggested_answer_ids.mapped(
                                "answer_score"
                            )
                            if score > 0
                        )
                        or 1,
                        "question_score": question_score,
                    }
                )
            leaderboard = sorted(
                leaderboard, key=lambda score: score["scoring_total"], reverse=True
            )

        return leaderboard

    def check_validity(self) -> None:
        self.check_singleton()
        if not self.question_ids:
            raise UserError(
                _("You cannot send an invitation for a survey that has no questions.")
            )

        if self.scoring_type != "no_scoring" and self.scoring_max_obtainable <= 0:
            raise UserError(
                _(
                    "A scored survey needs at least one question that gives points.\n"
                    "Please check answers and their scores."
                )
            )

        if self.questions_layout_effective == "page_per_section":
            if not self.page_ids:
                raise UserError(
                    _(
                        'You cannot send an invitation for a "One page per section" survey if the survey has no sections.'
                    )
                )
            if not self.page_ids.mapped("question_ids"):
                raise UserError(
                    _(
                        'You cannot send an invitation for a "One page per section" survey if the survey only contains empty sections.'
                    )
                )

        if not self.active:
            raise exceptions.UserError(
                _("You cannot send invitations for closed surveys.")
            )

    def action_send_survey(self) -> dict[str, Any]:
        self.check_validity()

        template = self.env.ref(
            "survey.mail_template_user_input_invite", raise_if_not_found=False
        )

        local_context = dict(
            self.env.context,
            default_survey_id=self.id,
            default_template_id=(template and template.id) or False,
            default_email_layout_xmlid="mail.mail_notification_light",
            default_send_email=(self.access_mode != "public"),
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Share a Survey"),
            "view_mode": "form",
            "res_model": "survey.invite",
            "target": "new",
            "context": local_context,
        }

    def action_start_survey(self, answer: Self | None = None) -> dict[str, Any]:
        self.check_singleton()
        token_query = urlencode(
            {"answer_token": (answer and answer.access_token) or None}
        )
        url = f"{self.get_start_url()}?{token_query}"
        return {
            "type": "ir.actions.act_url",
            "name": "Start Survey",
            "target": "self",
            "url": url,
        }

    def action_print_survey(self, answer: Self | None = None) -> dict[str, Any]:
        self.check_singleton()
        token_query = urlencode(
            {"answer_token": (answer and answer.access_token) or None}
        )
        url = f"{self.get_print_url()}?{token_query}"
        return {
            "type": "ir.actions.act_url",
            "name": "Print Survey",
            "target": "new",
            "url": url,
        }

    def action_result_survey(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "type": "ir.actions.act_url",
            "name": "Results of the Survey",
            "target": "new",
            "url": f"/survey/results/{self.id}",
        }

    def action_test_survey(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "type": "ir.actions.act_url",
            "name": "Test Survey",
            "target": "new",
            "url": f"/survey/test/{self.access_token}",
        }

    def _action_survey_user_input(self, **search_defaults: Any) -> dict[str, Any]:
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "survey.action_survey_user_input"
        )
        action["context"] = dict(
            self.env.context, search_default_survey_id=self.ids[0], **search_defaults
        )
        return action

    def action_survey_user_input_completed(self) -> dict[str, Any]:
        return self._action_survey_user_input(search_default_completed=1)

    def action_survey_user_input_certified(self) -> dict[str, Any]:
        return self._action_survey_user_input(search_default_scoring_success=1)

    def action_survey_user_input(self) -> dict[str, Any]:
        return self._action_survey_user_input()

    def action_survey_preview_certification_template(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": f"/survey/{self.id}/certification_preview",
        }

    def action_start_session(self) -> dict[str, Any]:
        if not self.env.user.has_group("survey.group_survey_user"):
            raise AccessError(_("Only survey users can manage sessions."))

        self.check_singleton()
        self.sudo().write(
            {
                "questions_layout": "page_per_question",
                "session_start_time": self.env.cr.now(),
                "session_question_id": None,
                "session_state": "ready",
            }
        )
        return self.action_view_session_manager()

    def action_view_session_manager(self) -> dict[str, Any]:
        self.check_singleton()

        return {
            "type": "ir.actions.act_url",
            "name": "Open Session Manager",
            "target": "new",
            "url": f"/survey/session/manage/{self.access_token}",
        }

    def action_end_session(self) -> None:
        if not self.env.user.has_group("survey.group_survey_user"):
            raise AccessError(_("Only survey users can manage sessions."))

        self.sudo().write({"session_state": False})
        session_inputs = self.user_input_ids.sudo().filtered(
            lambda ui: (
                ui.is_session_answer
                and ui.state != "done"
                and (
                    not self.session_start_time
                    or ui.create_date >= self.session_start_time
                )
            )
        )
        if session_inputs:
            session_inputs._mark_done()
        self.env["bus.bus"]._sendone(self.access_token, "end_session", {})

    def get_start_url(self) -> str:
        return f"/survey/start/{self.access_token}"

    def _resolve_short_token(self, prefix: str) -> Self:
        if len(prefix) != self.SHORT_TOKEN_LENGTH:
            return self.browse()
        candidates = self.sudo().search(
            [
                ("access_token", "=like", f"{escape_psql(prefix)}%"),
                ("active", "=", True),
                ("access_mode", "=", "public"),
            ],
            limit=2,
        )
        if len(candidates) != 1:
            if candidates:
                _logger.warning(
                    "Short link /s/%s is ambiguous between surveys %s; refusing to guess.",
                    prefix,
                    candidates.ids,
                )
            return self.browse()
        return candidates

    def get_print_url(self) -> str:
        return f"/survey/print/{self.access_token}"

    @api.model
    def _cron_scheduled_open_close(self) -> None:
        now = fields.Datetime.now()
        to_open = self.search(
            [
                ("date_open", "<=", now),
                ("active", "=", False),
                ("date_schedule_applied", "=", False),
                "|",
                ("date_close", "=", False),
                ("date_close", ">", now),
            ]
        )
        if to_open:
            to_open.write({"active": True, "date_schedule_applied": now})
            _logger.info("Activated %d scheduled surveys", len(to_open))

        to_close = self.search(
            [
                ("date_close", "<=", now),
                ("active", "=", True),
            ]
        )
        if to_close:
            to_close.action_archive()
            _logger.info("Deactivated %d expired surveys", len(to_close))

    def _prepare_survey_statistics(
        self, user_input_lines: Self | None = None
    ) -> dict[str, Any]:
        if user_input_lines:
            user_input_domain = [
                ("survey_id", "in", self.ids),
                ("id", "in", user_input_lines.mapped("user_input_id").ids),
            ]
        else:
            user_input_domain = [
                ("survey_id", "in", self.ids),
                ("state", "=", "done"),
                ("test_entry", "=", False),
            ]
        counts = (
            self.env["survey.user_input"]
            .sudo()
            ._read_group(user_input_domain, ["scoring_success", "state"], ["__count"])
        )

        scoring_success_count = scoring_failed_count = completed_count = 0
        for scoring_success, state, count in counts:
            if scoring_success:
                scoring_success_count += count
            else:
                scoring_failed_count += count
            if state == "done":
                completed_count += count

        total = scoring_success_count + scoring_failed_count
        return {
            "global_success_rate": round((scoring_success_count / total) * 100, 1)
            if total
            else 0,
            "count_all": total,
            "count_finished": completed_count,
            "count_failed": scoring_failed_count,
            "count_passed": scoring_success_count,
        }

    def _prepare_cross_tabulation(
        self, question_row_id: int, question_col_id: int
    ) -> dict[str, Any]:
        self.check_singleton()
        Question = self.env["survey.question"]
        q_row = Question.browse(question_row_id)
        q_col = Question.browse(question_col_id)

        if q_row.survey_id != self or q_col.survey_id != self:
            return {}
        if q_row == q_col:
            return {}

        lines = (
            self.env["survey.user_input.line"]
            .sudo()
            .search(
                [
                    ("question_id", "in", [question_row_id, question_col_id]),
                    ("skipped", "=", False),
                    ("user_input_id.state", "=", "done"),
                    ("user_input_id.test_entry", "=", False),
                ]
            )
        )

        # A respondent may hold several answers to one question (multiple choice, and
        # one row each for a matrix), so these are sets: keeping a single value per
        # respondent silently dropped every answer but the last.
        row_values_by_input = defaultdict(list)
        col_values_by_input = defaultdict(list)
        for line in lines:
            val = line._get_answer_value()
            if val is None:
                continue
            label = str(val)
            if line.matrix_row_id:
                label = f"{line.matrix_row_id.value}: {label}"
            target = (
                row_values_by_input
                if line.question_id.id == question_row_id
                else col_values_by_input
            )
            if label not in target[line.user_input_id.id]:
                target[line.user_input_id.id].append(label)

        row_labels = list(
            dict.fromkeys(v for vs in row_values_by_input.values() for v in vs)
        )
        col_labels = list(
            dict.fromkeys(v for vs in col_values_by_input.values() for v in vs)
        )
        row_idx = {label: i for i, label in enumerate(row_labels)}
        col_idx = {label: i for i, label in enumerate(col_labels)}

        matrix = [[0] * len(col_labels) for _ in row_labels]
        for ui_id, row_vals in row_values_by_input.items():
            for row_val in row_vals:
                for col_val in col_values_by_input.get(ui_id, ()):
                    matrix[row_idx[row_val]][col_idx[col_val]] += 1

        row_totals = [sum(row) for row in matrix]
        col_totals = [
            sum(matrix[r][c] for r in range(len(row_labels)))
            for c in range(len(col_labels))
        ]

        return {
            "question_row": {"id": q_row.id, "title": q_row.title},
            "question_col": {"id": q_col.id, "title": q_col.title},
            "row_labels": row_labels,
            "col_labels": col_labels,
            "matrix": matrix,
            "row_totals": row_totals,
            "col_totals": col_totals,
            "grand_total": sum(row_totals),
        }

    def _prepare_challenge_category(self) -> str:
        return "certification"

    def _create_certification_badge_trigger(self) -> None:
        self.check_singleton()
        if not self.certification_badge_id:
            raise UserError(
                _(
                    "Certification Badge is not configured for the survey %(survey_name)s",
                    survey_name=self.title,
                )
            )
        if self.env["gamification.challenge"].search_count(
            [("reward_id", "=", self.certification_badge_id.id)], limit=1
        ):
            return

        goal = self.env["gamification.goal.definition"].create(
            {
                "name": self.title,
                "description": _("%s certification passed", self.title),
                "domain": "['&', ('survey_id', '=', %s), ('scoring_success', '=', True)]"
                % self.id,
                "computation_mode": "count",
                "display_mode": "boolean",
                "model_id": self.env.ref("survey.model_survey_user_input").id,
                "condition": "higher",
                "batch_mode": True,
                "batch_distinctive_field": self.env.ref(
                    "survey.field_survey_user_input__partner_id"
                ).id,
                "batch_user_expression": "user.partner_id.id",
            }
        )
        challenge = self.env["gamification.challenge"].create(
            {
                "name": _("%s challenge certification", self.title),
                "reward_id": self.certification_badge_id.id,
                "state": "inprogress",
                "period": "once",
                "challenge_category": self._prepare_challenge_category(),
                "reward_realtime": True,
                "report_message_frequency": "never",
                "user_domain": [("karma", ">", 0)],
                "visibility_mode": "personal",
            }
        )
        self.env["gamification.challenge.line"].create(
            {"definition_id": goal.id, "challenge_id": challenge.id, "target_goal": 1}
        )

    def _handle_certification_badges(self, vals: dict[str, Any]) -> None:
        if vals.get("certification_give_badge"):
            self.certification_badge_id.action_unarchive()
            for survey in self:
                survey._create_certification_badge_trigger()
        else:
            badges = self.mapped("certification_badge_id")
            challenges_to_delete = self.env["gamification.challenge"].search(
                [("reward_id", "in", badges.ids)]
            )
            goals_to_delete = challenges_to_delete.mapped("line_ids").mapped(
                "definition_id"
            )
            badges.action_archive()
            challenges_to_delete.unlink()
            goals_to_delete.unlink()

    def _generate_session_codes(
        self, code_count: int = 1, excluded_codes: set[str] | bool = False
    ) -> list[str | bool]:
        self.flush_model(["session_code"])

        session_codes = set()
        excluded_codes = excluded_codes or set()
        existing_codes = (
            self.sudo()
            .with_context(active_test=False)
            .search_read([("session_code", "!=", False)], ["session_code"])
        )
        unavailable_codes = excluded_codes | {
            existing_code["session_code"] for existing_code in existing_codes
        }
        for digits_count in range(4, 10):
            range_lower_bound = 10 ** (digits_count - 1)
            range_upper_bound = (range_lower_bound * 10) - 1
            code_candidates = {
                str(random.randint(range_lower_bound, range_upper_bound))
                for _ in range(code_count + 20)
            }
            session_codes |= code_candidates - unavailable_codes
            if len(session_codes) >= code_count:
                return list(session_codes)[:code_count]

        return list(session_codes) + [False] * (code_count - len(session_codes))

    def _get_median_answer_durations(self) -> dict[int, float]:
        if not self.ids:
            return {}
        self.env["survey.user_input"].flush_model(
            ["survey_id", "state", "test_entry", "start_datetime", "end_datetime"]
        )
        self.env.cr.execute(
            """SELECT survey_id,
                      percentile_cont(0.5) WITHIN GROUP (
                          ORDER BY extract(epoch FROM end_datetime - start_datetime))
                 FROM survey_user_input
                WHERE survey_id = ANY(%s)
                      AND state = 'done'
                      AND test_entry IS NOT TRUE
                      AND start_datetime IS NOT NULL
                      AND end_datetime IS NOT NULL
             GROUP BY survey_id""",
            [self.ids],
        )
        return {survey_id: median or 0 for survey_id, median in self.env.cr.fetchall()}

    def _get_supported_lang_codes(self) -> list[str]:
        self.check_singleton()
        return self.lang_ids.mapped("code") or [
            lg[0] for lg in self.env["res.lang"].get_installed()
        ]
