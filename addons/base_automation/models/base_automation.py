import datetime
import logging
import re
import traceback
from collections import defaultdict
from uuid import uuid4

from dateutil.relativedelta import relativedelta
from odoo import _, api, exceptions, fields, models
from odoo.exceptions import LockError, MissingError
from odoo.fields import Command, Domain
from odoo.http import request
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)

# ============================================================================
# CRON INTERVAL CONFIGURATION
# ============================================================================

CRON_INTERVAL_TOLERANCE_PERCENT = 0.10
"""Tolerance percentage for cron interval adjustments (10%).

When calculating the optimal cron interval based on automation delays,
we use 10% of the minimum delay to ensure the cron runs frequently
enough to catch all time-based automations without excessive overhead.

Example: If minimum delay is 100 minutes, cron runs every 10 minutes.
"""

DEFAULT_CRON_INTERVAL_MINUTES = 4 * 60  # 4 hours = 240 minutes
"""Default cron check interval when no time-based automations exist.

This conservative default balances system resources with responsiveness.
When no automations are configured, the cron still runs periodically to
check for newly created automations.
"""

MIN_CRON_INTERVAL_MINUTES = 1
"""Minimum allowed cron check interval (1 minute).

Prevents the cron from running too frequently, which could cause
performance issues with excessive automation checks.
"""

MAX_CRON_INTERVAL_MINUTES = 4 * 60  # 4 hours = 240 minutes
"""Maximum cron check interval to prevent excessive delays.

Even with very long automation delays (e.g., monthly), the cron runs
at least every 4 hours to maintain reasonable responsiveness.
"""

# ============================================================================
# DATE/TIME CALCULATIONS
# ============================================================================

MONTH_APPROXIMATION_DAYS = 30
"""Approximation of days per month for non-calendar timedelta calculations.

Used when converting months to days for datetime.timedelta operations,
which don't support month-based deltas. This is an approximation:
- Actual average: ~30.44 days (365.25 / 12)
- We use 30 for simplicity and consistency

Note: For exact month calculations, use dateutil.relativedelta or
resource.calendar when calendar-aware scheduling is required.

See Also: TIMEDELTA_TYPES dict
"""

DOMAIN_FIELDS_RE = re.compile(
    r"""
    [([]\s*                 # opening bracket with any whitespace
    (?P<quote>['"])         # opening quote
    (?P<field>[a-z]\w*)     # field name, should start with a letter then any [a-z0-9_]
    (?:\.[.\w]*)?           # dot followed by dots or text in between i.e. relation traversal (optional)
    (?P=quote)              # closing quote, matching the opening one
    (?:[^,]*?,){2}          # anything with two commas (to ensure that we are inside a triplet)
    [^,]*?[()[\]]           # anything except a comma followed by a closing bracket or another opening bracket
""",
    re.VERBOSE,
)


def _get_domain_fields(env, model, domain):
    IrModelFields = env["ir.model.fields"]
    if not domain:
        return IrModelFields
    fields = IrModelFields
    # wondering why we use a regex instead of safe_eval?
    # because this method is called on a compute method hence could be triggered
    # from an onchange call (i.e. a manually crafted malicious one)
    # see: https://github.com/odoo/odoo/pull/189772#issuecomment-2548804283
    for match in DOMAIN_FIELDS_RE.finditer(domain):
        if field := match.groupdict().get("field"):
            fields |= IrModelFields._get(model, field)
    return fields


def _domain_fields_differences(automation, domain1, domain2):
    IrModelFields = automation.env["ir.model.fields"]
    if not automation.model_id:
        return IrModelFields, IrModelFields
    d1_fields = _get_domain_fields(automation.env, automation.model_id.model, domain1)
    d2_fields = _get_domain_fields(automation.env, automation.model_id.model, domain2)
    in_d1_only_fields = d1_fields - d2_fields
    in_d2_only_fields = d2_fields - d1_fields
    return in_d1_only_fields, in_d2_only_fields


DATE_RANGE = {
    "minutes": relativedelta(minutes=1),
    "hour": relativedelta(hours=1),
    "day": relativedelta(days=1),
    "month": relativedelta(months=1),
    False: relativedelta(0),
}

DATE_RANGE_FACTOR = {
    "minutes": 1,
    "hour": 60,
    "day": 24 * 60,
    "month": MONTH_APPROXIMATION_DAYS * 24 * 60,
    False: 0,
}

TIMEDELTA_TYPES = {
    "minutes": lambda interval: datetime.timedelta(minutes=interval),
    "hours": lambda interval: datetime.timedelta(hours=interval),
    "days": lambda interval: datetime.timedelta(days=interval),
    "weeks": lambda interval: datetime.timedelta(weeks=interval),
    "months": lambda interval: datetime.timedelta(
        days=MONTH_APPROXIMATION_DAYS * interval
    ),
}

CREATE_TRIGGERS = [
    "on_create",
    "on_create_or_write",
    "on_priority_set",
    "on_stage_set",
    "on_state_set",
    "on_tag_set",
    "on_user_set",
]

WRITE_TRIGGERS = [
    "on_write",
    "on_archive",
    "on_unarchive",
    "on_create_or_write",
    "on_priority_set",
    "on_stage_set",
    "on_state_set",
    "on_tag_set",
    "on_user_set",
]

MAIL_TRIGGERS = ("on_message_received", "on_message_sent")

CREATE_WRITE_SET = set(CREATE_TRIGGERS + WRITE_TRIGGERS)

TIME_TRIGGERS = [
    "on_time",
    "on_time_created",
    "on_time_updated",
]


def get_webhook_request_payload():
    if not request:
        return None
    try:
        payload = request.get_json_data()
    except ValueError:
        payload = {**request.httprequest.args}
    return payload


class BaseAutomation(models.Model):
    _name = "base.automation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Automation Rule"

    # which fields have an impact on the registry and the cron
    CRITICAL_FIELDS = ["model_id", "active", "trigger", "on_change_field_ids"]
    RANGE_FIELDS = ["trg_date_range", "trg_date_range_type"]

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    name = fields.Char(
        string="Automation Rule Name",
        required=True,
        translate=True,
        tracking=True,
    )
    active = fields.Boolean(
        default=True,
        help="When unchecked, the rule is hidden and will not be executed.",
    )
    description = fields.Html(string="Description")
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
        domain=[("abstract", "=", False)],
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    model_name = fields.Char(
        related="model_id.model",
        string="Model Name",
        readonly=True,
        inverse="_inverse_model_name",
    )
    model_is_mail_thread = fields.Boolean(
        related="model_id.is_mail_thread",
    )
    last_run = fields.Datetime(readonly=True, copy=False)
    filter_pre_domain = fields.Char(
        string="Before Update Domain",
        compute="_compute_filter_pre_domain",
        store=True,
        readonly=False,
        help="If present, this condition must be satisfied before the update of the record. "
        "Not checked on record creation.",
    )
    filter_domain = fields.Char(
        string="Apply on",
        compute="_compute_filter_domain",
        store=True,
        readonly=False,
        help="If present, this condition must be satisfied before executing the automation rule.",
    )
    previous_domain = fields.Char(
        store=False,
        default=lambda self: self.filter_domain,
    )
    action_server_ids = fields.One2many(
        comodel_name="ir.actions.server",
        inverse_name="base_automation_id",
        string="Actions",
        context={"default_usage": "base_automation"},
        compute="_compute_action_server_ids",
        store=True,
        readonly=False,
    )

    url = fields.Char(
        compute="_compute_url",
        help="Use this URL in the third-party app to call this webhook.",
    )
    webhook_uuid = fields.Char(
        string="Webhook UUID",
        default=lambda self: str(uuid4()),
        readonly=True,
        copy=False,
    )
    record_getter = fields.Char(
        default="model.env[payload.get('_model')].browse(int(payload.get('_id')))",
        help="This code will be run to find on which record the automation rule should be run.",
    )
    log_webhook_calls = fields.Boolean(
        string="Log Calls",
        default=False,
    )

    trigger = fields.Selection(
        selection=[
            ("on_archive", "On archived"),
            ("on_change", "On UI change"),
            ("on_create", "On create"),
            ("on_create_or_write", "On create and edit"),
            ("on_hand", "Manual trigger"),
            ("on_message_received", "On incoming message"),
            ("on_message_sent", "On outgoing message"),
            ("on_priority_set", "Priority is set to"),
            ("on_stage_set", "Stage is set to"),
            ("on_state_set", "State is set to"),
            ("on_tag_set", "Tag is added"),
            ("on_time", "Based on date field"),
            ("on_time_created", "After creation"),
            ("on_time_updated", "After last update"),
            ("on_unarchive", "On unarchived"),
            ("on_unlink", "On deletion"),
            ("on_user_set", "User is set"),
            ("on_webhook", "On webhook"),
            ("on_write", "On update"),  # deprecated, use 'on_create_or_write' instead
        ],
        string="Trigger",
        required=True,
        compute="_compute_trigger",
        store=True,
        readonly=False,
        tracking=True,
    )
    trg_selection_field_id = fields.Many2one(
        comodel_name="ir.model.fields.selection",
        string="Trigger Field",
        compute="_compute_trg_selection_field_id",
        store=True,
        readonly=False,
        domain="[('field_id', 'in', trigger_field_ids)]",
        help="Some triggers need a reference to a selection field. This field is used to store it.",
    )
    trg_field_ref_model_name = fields.Char(
        string="Trigger Field Model",
        compute="_compute_trg_field_ref_model_name",
    )
    trg_field_ref = fields.Many2oneReference(
        string="Trigger Reference",
        model_field="trg_field_ref_model_name",
        compute="_compute_trg_field_ref",
        store=True,
        readonly=False,
        help="Some triggers need a reference to another field. This field is used to store it.",
    )
    trg_date_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Trigger Date",
        compute="_compute_trg_date_id",
        store=True,
        readonly=False,
        domain="[('model_id', '=', model_id), ('ttype', 'in', ('date', 'datetime'))]",
        tracking=True,
        help="""When should the condition be triggered.
                If present, will be checked by the scheduler. If empty, will be checked at creation and update.""",
    )
    trg_date_range = fields.Integer(
        string="Delay",
        compute="_compute_trg_date_range_data",
        store=True,
        readonly=False,
        tracking=True,
    )
    trg_date_range_mode = fields.Selection(
        selection=[("after", "After"), ("before", "Before")],
        string="Delay mode",
        compute="_compute_trg_date_range_data",
        store=True,
        readonly=False,
        tracking=True,
    )
    trg_date_range_type = fields.Selection(
        selection=[
            ("minutes", "Minutes"),
            ("hour", "Hours"),
            ("day", "Days"),
            ("month", "Months"),
        ],
        string="Delay unit",
        compute="_compute_trg_date_range_data",
        store=True,
        readonly=False,
        tracking=True,
    )
    trg_date_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Use Calendar",
        compute="_compute_trg_date_calendar_id",
        store=True,
        readonly=False,
        help="When calculating a day-based timed condition, it is possible "
        "to use a calendar to compute the date based on working days.",
    )
    on_change_field_ids = fields.Many2many(
        comodel_name="ir.model.fields",
        relation="base_automation_onchange_fields_rel",
        string="On Change Fields Trigger",
        compute="_compute_on_change_field_ids",
        store=True,
        readonly=False,
        help="Fields that trigger the onchange.",
    )
    trigger_field_ids = fields.Many2many(
        comodel_name="ir.model.fields",
        string="Trigger Fields",
        compute="_compute_trigger_field_ids",
        store=True,
        readonly=False,
        help="The automation rule will be triggered if and only if one of these fields is updated."
        "If empty, all fields are watched.",
    )

    use_workflow_dag = fields.Boolean(
        string="Use Workflow DAG",
        default=False,
        help="Enable to use this automation as a multi-step workflow with dependencies between actions",
    )
    auto_execute_workflow = fields.Boolean(
        string="Auto-Execute Workflow",
        default=False,
        help="If enabled, workflow will automatically execute next ready actions.\n"
        "If disabled, user must manually click 'Execute Next' button.",
    )

    # Workflow statistics computed fields
    action_count_total = fields.Integer(
        string="Total Actions",
        compute="_compute_action_counts",
        help="Total number of actions in this automation",
    )
    action_count_waiting = fields.Integer(
        string="Waiting Actions",
        compute="_compute_action_counts",
        help="Number of actions in waiting state",
    )
    action_count_ready = fields.Integer(
        string="Ready Actions",
        compute="_compute_action_counts",
        help="Number of actions in ready state",
    )
    action_count_in_progress = fields.Integer(
        string="In Progress Actions",
        compute="_compute_action_counts",
        help="Number of actions in progress",
    )
    action_count_done = fields.Integer(
        string="Done Actions",
        compute="_compute_action_counts",
        help="Number of completed actions",
    )
    action_count_error = fields.Integer(
        string="Error Actions",
        compute="_compute_action_counts",
        help="Number of actions with errors",
    )

    # ------------------------------------------------------------
    # CONSTRAINT METHODS
    # ------------------------------------------------------------

    @api.constrains("model_id", "action_server_ids")
    def _check_action_server_model(self):
        for automation in self:
            # Allow cross-model actions when automation targets base.automation itself
            # This enables meta-workflows that orchestrate other automations
            if automation.model_name == "base.automation":
                continue

            failing_actions = automation.action_server_ids.filtered(
                lambda action: action.model_id != automation.model_id,
            )
            if failing_actions:
                raise exceptions.ValidationError(
                    _(
                        "Automation '%(automation)s': The following actions target different models: %(action_names)s.\n\n"
                        "Expected model: %(expected_model)s\n"
                        "Action models: %(action_models)s\n\n"
                        "All actions must target the same model as the automation rule.",
                        automation=self.name,
                        action_names=", ".join(failing_actions.mapped("name")),
                        expected_model=self.model_id.name,
                        action_models=", ".join(
                            set(failing_actions.mapped("model_id.name"))
                        ),
                    ),
                )

    @api.constrains("trigger", "model_id")
    def _check_trigger(self):
        for automation in self:
            if (
                automation.trigger in MAIL_TRIGGERS
                and not automation.model_id.is_mail_thread
            ):
                raise exceptions.ValidationError(
                    _(
                        "Automation '%(automation)s': Mail event trigger '%(trigger)s' cannot be used on model '%(model)s'.\n\n"
                        "Mail triggers (%(mail_triggers)s) require the model to inherit from 'mail.thread'.\n\n"
                        "Solution: Either change the trigger type or select a model that has the discussion feature enabled.",
                        automation=automation.name,
                        trigger=automation.trigger,
                        model=automation.model_id.name,
                        mail_triggers=", ".join(MAIL_TRIGGERS),
                    ),
                )

    @api.constrains("trigger", "trg_date_range")
    def _check_time_trigger(self):
        for automation in self:
            if automation.trigger in TIME_TRIGGERS and automation.trg_date_range < 0:
                raise exceptions.ValidationError(
                    _(
                        "Automation '%(automation)s': Delay value must be positive (currently: %(delay)s).\n\n"
                        "To trigger before a date, use a positive delay and set 'Delay mode' to 'Before'.\n"
                        "To trigger after a date, use a positive delay and set 'Delay mode' to 'After'.\n\n"
                        "Example: To send a reminder 3 days before an invoice due date:\n"
                        "  - Delay: 3 days\n"
                        "  - Mode: Before",
                        automation=automation.name,
                        delay=automation.trg_date_range,
                    ),
                )

    @api.constrains("trigger", "action_server_ids")
    def _check_trigger_state(self):
        for automation in self:
            warning_actions = automation.action_server_ids.filtered("warning")
            if warning_actions:
                warning_details = "\n".join(
                    [
                        f"  • {action.name}: {action.warning}"
                        for action in warning_actions
                    ]
                )
                raise exceptions.ValidationError(
                    _(
                        "Automation '%(automation)s': The following actions have configuration issues:\n\n"
                        "%(warning_details)s\n\n"
                        "Please fix these warnings before saving the automation.",
                        automation=automation.name,
                        warning_details=warning_details,
                    ),
                )
            no_code_actions = automation.action_server_ids.filtered(
                lambda a: a.state != "code",
            )
            if automation.trigger == "on_change" and no_code_actions:
                invalid_action_types = ", ".join(set(no_code_actions.mapped("state")))
                raise exceptions.ValidationError(
                    _(
                        "Automation '%(automation)s': 'On live update' trigger can only use 'Execute Python Code' actions.\n\n"
                        "Invalid actions: %(actions)s (types: %(types)s)\n\n"
                        "Reason: On-change automations execute in the browser during form editing, "
                        "so they can only return field values via Python code. Other action types "
                        "require committed database records.\n\n"
                        "Solution: Change these actions to type 'Execute Python Code' or use a different trigger.",
                        automation=automation.name,
                        actions=", ".join(no_code_actions.mapped("name")),
                        types=invalid_action_types,
                    ),
                )
            mail_actions = automation.action_server_ids.filtered(
                lambda a: a.state in ["mail_post", "followers", "next_activity"],
            )
            if automation.trigger == "on_unlink" and mail_actions:
                raise exceptions.ValidationError(
                    _(
                        "Automation '%(automation)s': Mail actions cannot be used with 'On Deletion' trigger.\n\n"
                        "Invalid actions: %(actions)s\n\n"
                        "Reason: Records are deleted before actions execute, so there's no record "
                        "to post messages to, add followers to, or create activities on.\n\n"
                        "Solution: Consider using 'On Update' trigger with a domain filter for "
                        "state transitions, or send notifications before deletion using archive workflows.",
                        automation=automation.name,
                        actions=", ".join(mail_actions.mapped("name")),
                    ),
                )

    # ------------------------------------------------------------
    # CRUD METHODS
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        base_automations = super().create(vals_list)
        self._update_cron()
        self._update_registry()
        if base_automations._has_trigger_onchange():
            # Invalidate templates cache to update on_change attributes if needed
            self.env.registry.clear_cache("templates")
        return base_automations

    def write(self, vals: dict):
        clear_templates = self._has_trigger_onchange()
        res = super().write(vals)
        if set(vals).intersection(self.CRITICAL_FIELDS):
            self._update_cron()
            self._update_registry()
            if clear_templates or self._has_trigger_onchange():
                # Invalidate templates cache to update on_change attributes if needed
                self.env.registry.clear_cache("templates")
        elif set(vals).intersection(self.RANGE_FIELDS):
            self._update_cron()

        # Handle workflow DAG toggle - update action states
        if "use_workflow_dag" in vals:
            for automation in self:
                if automation.use_workflow_dag:
                    # Workflow enabled - set actions to 'waiting' if currently 'no'
                    no_state_actions = automation.action_server_ids.filtered(
                        lambda a: a.action_state == "no",
                    )
                    if no_state_actions:
                        no_state_actions.write({"action_state": "waiting"})
                else:
                    # Workflow disabled - reset workflow states to 'no'
                    workflow_actions = automation.action_server_ids.filtered(
                        lambda a: a.action_state
                        in ("waiting", "ready", "in_progress", "done", "error"),
                    )
                    if workflow_actions:
                        workflow_actions.write({"action_state": "no"})

        return res

    def unlink(self):
        clear_templates = self._has_trigger_onchange()
        res = super().unlink()
        self._update_cron()
        self._update_registry()
        if clear_templates:
            # Invalidate templates cache to update on_change attributes if needed
            self.env.registry.clear_cache("templates")
        return res

    def copy(self, default=None):
        """Copy the actions of the automation while
        copying the automation itself."""
        actions = self.action_server_ids.copy()
        record_copy = super().copy(default)
        record_copy.action_server_ids = actions
        return record_copy

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    @api.depends("trigger", "webhook_uuid")
    def _compute_url(self):
        for automation in self:
            if automation.trigger != "on_webhook":
                automation.url = ""
            else:
                automation.url = "%s/web/hook/%s" % (
                    automation.get_base_url(),
                    automation.webhook_uuid,
                )

    def _inverse_model_name(self):
        for rec in self:
            rec.model_id = self.env["ir.model"]._get(rec.model_name)

    @api.depends("model_id")
    def _compute_trigger(self):
        self.trigger = False

    @api.depends("model_id")
    def _compute_action_server_ids(self):
        """When changing / setting model, remove actions that are not targeting
        the same model anymore.

        Exception: When automation targets base.automation itself, allow
        cross-model actions to enable meta-workflow orchestration.
        """
        for automation in self.filtered("model_id"):
            # Allow cross-model actions for meta-workflows on base.automation
            if automation.model_name == "base.automation":
                continue

            actions_to_remove = automation.action_server_ids.filtered(
                lambda action: action.model_id != automation.model_id,
            )
            if actions_to_remove:
                automation.action_server_ids = [
                    Command.unlink(action.id) for action in actions_to_remove
                ]

    @api.depends("action_server_ids.action_state")
    def _compute_action_counts(self):
        """Compute action statistics by state for workflow status display.

        Uses _read_group for efficient database-level aggregation instead of
        fetching all records and filtering in Python.
        """
        # Initialize all counts to 0
        for automation in self:
            automation.action_count_total = 0
            automation.action_count_waiting = 0
            automation.action_count_ready = 0
            automation.action_count_in_progress = 0
            automation.action_count_done = 0
            automation.action_count_error = 0

        # Efficient database aggregation with _read_group
        if self.ids:
            domain = [("base_automation_id", "in", self.ids)]
            groups = self.env["ir.actions.server"]._read_group(
                domain=domain,
                groupby=["base_automation_id", "action_state"],
                aggregates=["__count"],
            )

            # Map results back to automations
            for group in groups:
                automation_id = group[0].id
                state = group[1]
                count = group[2]

                automation = self.browse(automation_id)
                automation.action_count_total += count

                if state == "waiting":
                    automation.action_count_waiting = count
                elif state == "ready":
                    automation.action_count_ready = count
                elif state == "in_progress":
                    automation.action_count_in_progress = count
                elif state == "done":
                    automation.action_count_done = count
                elif state == "error":
                    automation.action_count_error = count

    @api.depends("trigger")
    def _compute_trg_date_id(self):
        to_reset = self.filtered(lambda a: a.trigger not in TIME_TRIGGERS)
        to_reset.trg_date_id = False
        for record in self - to_reset:
            record.trg_date_id = record._get_trigger_specific_field()

    @api.onchange("trg_date_range")
    def _onchange_trg_date_range_data(self):
        if self.trg_date_range < 0:
            self.trg_date_range = abs(self.trg_date_range)
            if self.trigger == "on_time":
                self.trg_date_range_mode = (
                    "before" if self.trg_date_range_mode == "after" else "after"
                )

    @api.depends("trigger")
    def _compute_trg_date_range_data(self):
        for record in self:
            if record.trigger not in TIME_TRIGGERS:
                record.trg_date_range = False
                record.trg_date_range_type = False
                record.trg_date_range_mode = False
                continue
            if not record.trg_date_range_type:
                record.trg_date_range_type = "hour"
            if not record.trg_date_range_mode or record.trigger not in "on_time":
                record.trg_date_range_mode = "after"

    @api.depends("trigger", "trg_date_id", "trg_date_range_type")
    def _compute_trg_date_calendar_id(self):
        to_reset = self.filtered(
            lambda a: a.trigger not in TIME_TRIGGERS
            or not a.trg_date_id
            or a.trg_date_range_type != "day",
        )
        to_reset.trg_date_calendar_id = False

    @api.depends("trigger")
    def _compute_trg_selection_field_id(self):
        self.trg_selection_field_id = False

    @api.depends("trigger")
    def _compute_trg_field_ref(self):
        self.trg_field_ref = False

    @api.depends("trigger", "trg_field_ref")
    def _compute_trg_field_ref_model_name(self):
        to_compute = self.filtered(
            lambda a: a.trigger in ["on_stage_set", "on_tag_set"]
            and a.trg_field_ref is not False,
        )
        # wondering why we check based on 'is not'? Because the ref could be an empty recordset
        # and we still need to introspec on the model in that case - not just ignore it
        to_reset = self - to_compute
        to_reset.trg_field_ref_model_name = False
        for automation in to_compute:
            relation = automation._get_trigger_specific_field().relation
            if not relation:
                automation.trg_field_ref_model_name = False
                continue
            automation.trg_field_ref_model_name = relation

    @api.depends("trigger", "trg_field_ref")
    def _compute_filter_pre_domain(self):
        to_reset = self.filtered(lambda a: a.trigger != "on_tag_set")
        to_reset.filter_pre_domain = False
        for automation in self - to_reset:
            field = automation._get_trigger_specific_field().name
            value = automation.trg_field_ref
            automation.filter_pre_domain = (
                repr([(field, "not in", [value])]) if value else False
            )

    @api.depends("trigger", "trg_selection_field_id", "trg_field_ref")
    def _compute_filter_domain(self):
        for automation in self:
            field = (
                automation._get_trigger_specific_field()
                if automation.trigger not in ["on_create_or_write", *TIME_TRIGGERS]
                else False
            )
            if not field:
                automation.filter_domain = False
                continue

            # some triggers require a domain
            match automation.trigger:
                case "on_state_set" | "on_priority_set":
                    value = automation.trg_selection_field_id.value
                    automation.filter_domain = (
                        repr([(field.name, "=", value)]) if value else False
                    )
                case "on_stage_set":
                    value = automation.trg_field_ref
                    automation.filter_domain = (
                        repr([(field.name, "=", value)]) if value else False
                    )
                case "on_tag_set":
                    value = automation.trg_field_ref
                    automation.filter_domain = (
                        repr([(field.name, "in", [value])]) if value else False
                    )
                case "on_user_set":
                    automation.filter_domain = repr([(field.name, "!=", False)])
                case "on_archive":
                    automation.filter_domain = repr([(field.name, "=", False)])
                case "on_unarchive":
                    automation.filter_domain = repr([(field.name, "=", True)])

    @api.depends("model_id", "trigger", "filter_domain")
    def _compute_on_change_field_ids(self):
        to_reset = self.filtered(lambda a: a.trigger != "on_change")
        to_reset.on_change_field_ids = False
        for automation in self - to_reset:
            automation._onchange_domain()

    @api.depends("model_id", "trigger", "filter_domain")
    def _compute_trigger_field_ids(self):
        for automation in self:
            if automation.trigger == "on_create_or_write":
                automation._onchange_domain()
                continue
            automation._onchange_trigger()

    # ------------------------------------------------------------
    # ONCHANGE METHODS
    # ------------------------------------------------------------

    @api.onchange("trigger")
    def _onchange_trigger(self):
        self.ensure_one()
        field = (
            self._get_trigger_specific_field()
            if self.trigger not in TIME_TRIGGERS
            else False
        )
        self.trigger_field_ids = field

    @api.onchange("trigger", "action_server_ids")
    def _onchange_trigger_or_actions(self):
        # Validation for on_change trigger
        no_code_actions = self.action_server_ids.filtered(lambda a: a.state != "code")
        if self.trigger == "on_change" and len(no_code_actions) > 0:
            trigger_field = self._fields["trigger"]
            action_states = dict(
                self.action_server_ids._fields["state"]._description_selection(
                    self.env,
                ),
            )
            return {
                "warning": {
                    "title": _("Warning"),
                    "message": _(
                        'The "%(trigger_value)s" %(trigger_label)s can only be '
                        'used with the "%(state_value)s" action type',
                        trigger_value=dict(
                            trigger_field._description_selection(self.env),
                        )["on_change"],
                        trigger_label=trigger_field._description_string(self.env),
                        state_value=action_states["code"],
                    ),
                },
            }

        # Validation for on_unlink trigger
        MAIL_STATES = ("mail_post", "followers", "next_activity")
        mail_actions = self.action_server_ids.filtered(lambda a: a.state in MAIL_STATES)
        if self.trigger == "on_unlink" and len(mail_actions) > 0:
            return {
                "warning": {
                    "title": _("Warning"),
                    "message": _(
                        "You cannot send an email, add followers or create an activity "
                        "for a deleted record.  It simply does not work.",
                    ),
                },
            }

    @api.onchange("filter_domain")
    def _onchange_domain(self):
        removed_fields, added_fields = _domain_fields_differences(
            self,
            self.previous_domain,
            self.filter_domain,
        )
        if self.trigger == "on_change":
            self.on_change_field_ids = self.on_change_field_ids.filtered(
                lambda f: f._origin.id not in removed_fields.ids,
            )
            self.on_change_field_ids |= added_fields
        if self.trigger == "on_create_or_write":
            self.trigger_field_ids = self.trigger_field_ids.filtered(
                lambda f: f._origin.id not in removed_fields.ids,
            )
            self.trigger_field_ids |= added_fields
        self.previous_domain = self.filter_domain

    # ------------------------------------------------------------
    # ACTION METHODS
    # ------------------------------------------------------------

    def action_open_scheduled_action(self):
        cron = self.env.ref(
            "base_automation.ir_cron_data_base_automation_check",
            raise_if_not_found=False,
        )
        if not cron:
            message = _(
                "The scheduled action for Automation Rules cannot be found.\n\n"
                "This scheduled action (external ID: base_automation.ir_cron_data_base_automation_check) "
                "is required for time-based automations to work.\n\n"
                "Recovery steps:\n"
                "1. Go to Settings → Technical → Automation → Scheduled Actions\n"
                "2. Look for 'Automation Rules: check and execute'\n"
                "3. If missing, update the 'base_automation' module to recreate it\n"
                "4. Alternatively, contact your system administrator",
            )
            raise exceptions.MissingError(message)
        return {
            "type": "ir.actions.act_window",
            "name": _("Scheduled Action"),
            "view_mode": "form",
            "res_model": "ir.cron",
            "res_id": cron.id,
        }

    def action_rotate_webhook_uuid(self):
        for automation in self:
            automation.webhook_uuid = str(uuid4())

    def action_view_webhook_logs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Webhook Logs"),
            "res_model": "ir.logging",
            "view_mode": "list,form",
            "domain": [("path", "=", "base_automation(%s)" % self.id)],
        }

    def action_manual_trigger(self):
        """Manually trigger automation on active records.

        This method supports two execution modes:
        1. Workflow DAG mode: Initiates workflow by resetting and executing first step
        2. Standalone mode: Directly processes selected records through automation

        Returns:
            dict: Action result (notification or next workflow step)
        """
        self.ensure_one()

        if self.trigger != "on_hand":
            raise exceptions.ValidationError(
                _(
                    "Automation '%(automation)s' cannot be triggered manually.\n\n"
                    "Current trigger: %(current_trigger)s\n"
                    "Required trigger: on_hand (Manual trigger)\n\n"
                    "To manually trigger this automation:\n"
                    "1. Edit the automation\n"
                    "2. Change 'Trigger' field to 'Manual trigger'\n"
                    "3. Save and try again",
                    automation=self.name,
                    current_trigger=dict(self._fields["trigger"].selection).get(
                        self.trigger, self.trigger
                    ),
                ),
            )

        # Mode 1: Workflow DAG - Orchestrated execution
        if self.use_workflow_dag:
            # Reset workflow to initial state
            self.action_reset_workflow()

            # Execute first ready action
            result = self.action_execute_next()

            # Add context about workflow mode
            if isinstance(result, dict) and result.get("type") == "ir.actions.client":
                if "params" not in result:
                    result["params"] = {}
                result["params"]["sticky"] = False

            return result

        # Mode 2: Standalone - Direct record processing
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])

        # Validate context
        if not active_model or not active_ids:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No Records Selected"),
                    "message": _("Please select one or more records to process."),
                    "type": "warning",
                },
            }

        if active_model != self.model_name:
            raise exceptions.ValidationError(
                _(
                    "Automation '%(automation)s': Model mismatch.\n\n"
                    "This automation is configured for: %(expected)s\n"
                    "You are trying to use it on: %(actual)s\n\n"
                    "Solution: Either select records from '%(expected)s' or edit the automation "
                    "to change its target model.",
                    automation=self.name,
                    expected=self.model_name,
                    actual=active_model,
                ),
            )

        # Get records and filter them
        records = self.env[active_model].browse(active_ids)
        filtered_records = self._filter_post(records)

        if not filtered_records:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No Matching Records"),
                    "message": _(
                        "None of the selected records match the automation filter conditions.",
                    ),
                    "type": "warning",
                },
            }

        # Process the records
        try:
            self._process(filtered_records)

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Automation Executed"),
                    "message": _("Successfully processed %d of %d selected record(s).")
                    % (len(filtered_records), len(records)),
                    "type": "success",
                },
            }
        except Exception as e:
            self._add_postmortem(e)
            raise

    def action_reset_workflow(self):
        """Reset all action states to initial configuration.

        Sets root actions (no predecessors) to 'ready',
        all others to 'waiting'.
        """
        self.ensure_one()

        if not self.use_workflow_dag:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Not a Workflow"),
                    "message": _(
                        "This automation is not configured to use workflow DAG.",
                    ),
                    "type": "warning",
                },
            }

        # Reset all actions to waiting
        self.action_server_ids.action_reset()

        # Mark root actions (no predecessors) as ready
        root_actions = self.action_server_ids.filtered(lambda a: not a.predecessor_ids)

        if not root_actions:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No Root Actions"),
                    "message": _(
                        "Workflow has no root actions (actions without predecessors).",
                    ),
                    "type": "danger",
                },
            }

        root_actions.action_mark_ready()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Workflow Reset"),
                "message": _("%d actions reset, %d ready to execute")
                % (
                    len(self.action_server_ids),
                    len(root_actions),
                ),
                "type": "success",
            },
        }

    def action_execute_next(self):
        """Execute next ready action in workflow.

        Returns:
            Action dict, notification, or result of action execution
        """
        self.ensure_one()

        if not self.use_workflow_dag:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Not a Workflow"),
                    "message": _(
                        "This automation is not configured to use workflow DAG.",
                    ),
                    "type": "warning",
                },
            }

        # Get ready actions
        ready_actions = self.action_server_ids.filtered(
            lambda a: a.action_state == "ready",
        )

        if not ready_actions:
            # Check if workflow is complete or blocked
            waiting_actions = self.action_server_ids.filtered(
                lambda a: a.action_state == "waiting",
            )
            error_actions = self.action_server_ids.filtered(
                lambda a: a.action_state == "error",
            )

            if not waiting_actions and not error_actions:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Workflow Complete"),
                        "message": _("All actions have been executed successfully."),
                        "type": "success",
                    },
                }
            elif error_actions:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Workflow Has Errors"),
                        "message": _(
                            "%d actions failed. Please fix errors and reset workflow.",
                        )
                        % len(error_actions),
                        "type": "danger",
                    },
                }
            else:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Workflow Blocked"),
                        "message": _(
                            "%d actions waiting but none are ready. Check dependencies.",
                        )
                        % len(waiting_actions),
                        "type": "warning",
                    },
                }

        # Execute first ready action
        action = ready_actions[0]
        return self._execute_workflow_action(action)

    def _execute_workflow_action(self, action):
        """Execute a single workflow action.

        Args:
            action: ir.actions.server record to execute

        Returns:
            Result of action execution or next action
        """
        action.ensure_one()

        # Mark as in progress
        action.action_mark_in_progress()

        _logger.info(
            "Executing workflow action '%s' (#%d) for automation '%s'",
            action.name,
            action.id,
            self.name,
        )

        try:
            # Execute the server action
            # Note: Context should be set by the caller
            result = action.run()

            # Mark as done (this will auto-activate ready successors)
            action.action_mark_done()

            _logger.info(
                "Workflow action '%s' (#%d) completed successfully",
                action.name,
                action.id,
            )

            # If auto-execute is enabled, continue to next action
            if self.auto_execute_workflow:
                return self.action_execute_next()
            else:
                # Return result or prompt to continue
                return result or {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Action Complete"),
                        "message": _(
                            "Action '%s' completed. Click 'Execute Next' to continue.",
                        )
                        % action.name,
                        "type": "success",
                        "sticky": False,
                    },
                }

        except Exception as e:
            error_msg = str(e)
            _logger.error(
                "Workflow action '%s' (#%d) failed: %s",
                action.name,
                action.id,
                error_msg,
                exc_info=True,
            )

            # Mark as error
            action.action_mark_error(error_msg)

            # Re-raise to show error to user
            raise

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    @api.model
    def _add_postmortem(self, e):
        if self.env.user._is_internal():
            e.context = {}
            e.context["exception_class"] = "base_automation"
            e.context["base_automation"] = {
                "id": self.id,
                "name": self.sudo().name,
            }

    @api.model
    def _cron_process_time_based_actions(self):
        """Execute the time-based automations."""
        if "__action_done" not in self.env.context:
            self = self.with_context(__action_done={})

        # retrieve all the automation rules to run based on a timed condition
        final_exception = None
        automations = self.with_context(active_test=True).search(
            [("trigger", "in", TIME_TRIGGERS)],
        )
        self.env["ir.cron"]._commit_progress(remaining=len(automations))

        for automation in automations:
            # is automation deactivated or disappeared between commits?
            try:
                if not automation.active:
                    continue
            except MissingError:
                continue
            _logger.info("Starting time-based automation rule `%s`.", automation.name)
            now = self.env.cr.now()
            records = automation._search_time_based_automation_records(until=now)
            # run the automation on the records
            try:
                for record in records:
                    automation._process(record)
                self.env.flush_all()
            except Exception as e:
                self.env.cr.rollback()
                _logger.exception(
                    "Error in time-based automation rule `%s`.",
                    automation.name,
                )
                final_exception = e
                continue

            automation.write({"last_run": now})
            _logger.info("Time-based automation rule `%s` done.", automation.name)
            if not self.env["ir.cron"]._commit_progress(1):
                break
        if final_exception is not None:
            # raise the last found exception to mark the cron job as failing
            raise final_exception

    def _execute_webhook(self, payload):
        """Execute the webhook for the given payload.
        The payload is a dictionnary that can be used by the `record_getter` to
        identify the record on which the automation should be run.
        """
        self.ensure_one()
        ir_logging_sudo = self.env["ir.logging"].sudo()

        # info logging is done by the ir.http logger
        msg = "Webhook #%s triggered with payload %s"
        msg_args = (self.id, payload)
        _logger.debug(msg, *msg_args)
        if self.log_webhook_calls:
            ir_logging_sudo.create(self._prepare_loggin_values(message=msg % msg_args))

        record = self.env[self.model_name]
        if self.record_getter:
            try:
                record = safe_eval.safe_eval(
                    self.record_getter,
                    self._get_eval_context(payload=payload),
                )
            except Exception as e:  # noqa: BLE001
                msg = "Webhook #%s could not be triggered because the record_getter failed:\n%s"
                msg_args = (self.id, traceback.format_exc())
                _logger.warning(msg, *msg_args)
                if self.log_webhook_calls:
                    ir_logging_sudo.create(
                        self._prepare_loggin_values(
                            message=msg % msg_args,
                            level="ERROR",
                        ),
                    )
                raise e

        if not record.exists():
            msg = "Webhook #%s could not be triggered because no record to run it on was found."
            msg_args = (self.id,)
            _logger.warning(msg, *msg_args)
            if self.log_webhook_calls:
                ir_logging_sudo.create(
                    self._prepare_loggin_values(message=msg % msg_args, level="ERROR"),
                )
            raise exceptions.ValidationError(
                _("No record to run the automation on was found."),
            )

        try:
            return self._process(record)
        except Exception as e:  # noqa: BLE001
            msg = "Webhook #%s failed with error:\n%s"
            msg_args = (self.id, traceback.format_exc())
            _logger.warning(msg, *msg_args)
            if self.log_webhook_calls:
                ir_logging_sudo.create(
                    self._prepare_loggin_values(message=msg % msg_args, level="ERROR"),
                )
            raise e

    def _filter_pre(self, records, feedback=False):
        """Filter records that satisfy the automation's pre-condition.

        Pre-conditions (filter_pre_domain) are evaluated BEFORE a record is
        modified. This is used primarily for 'on_write' triggers to check if
        the record was in a specific state before the update occurred.

        The method uses safe_eval to evaluate the domain expression with
        restricted context to prevent code injection attacks.

        Args:
            records (Model): Recordset to filter against pre-conditions.
            feedback (bool): If True, sets __action_feedback context flag to
                detect recursive automation execution during domain evaluation.
                Used to prevent infinite loops. Default is False.

        Returns:
            Model: Filtered recordset containing only records matching the
                filter_pre_domain. Returns original recordset if no pre-condition
                is configured.

        Security:
            - Always executes with sudo() privileges
            - Domain evaluated using safe_eval with restricted context
            - Prevents arbitrary code execution

        Example:
            >>> # Automation with pre-condition: record was in 'draft' state
            >>> automation = self.env['base.automation'].browse(1)
            >>> automation.filter_pre_domain = "[('state', '=', 'draft')]"
            >>> partners = self.env['res.partner'].search([])
            >>> draft_partners = automation._filter_pre(partners)
            >>> # Returns only partners that were in draft before update

        See Also:
            _filter_post(): Post-condition filtering (after event)
            _get_eval_context(): Context used for safe domain evaluation
        """
        self_sudo = self.sudo()
        if self_sudo.filter_pre_domain and records:
            if feedback:
                # this context flag enables to detect the executions of
                # automations while evaluating their precondition
                records = records.with_context(__action_feedback=True)
            domain = safe_eval.safe_eval(
                self_sudo.filter_pre_domain,
                self._get_eval_context(),
            )
            # keep computed fields depending on the currently changed field
            # as-is so they are recomputed after the value is set
            # see `test_computation_sequence`
            changed_fields = self.env.context.get("changed_fields", ())
            to_compute = {
                dep: comp
                for f in changed_fields
                for dep in self.env.registry.get_dependent_fields(f)
                if (comp := self.env.records_to_compute(dep))
            }
            records = (
                records.with_context(changed_fields=())
                .sudo()
                .filtered_domain(domain)
                .sudo(records.env.su)
            )
            for dep, comp in to_compute.items():
                self.env.add_to_compute(dep, comp)
        return records

    def _filter_post(self, records, feedback=False):
        """Filter records that satisfy the automation's post-condition.

        Post-conditions (filter_domain) are evaluated AFTER a record event
        (create/write/unlink). This determines which records should have
        automation actions executed on them.

        This is a convenience wrapper around _filter_post_export_domain()
        that returns only the filtered records without the domain.

        Args:
            records (Model): Recordset to filter against post-conditions.
            feedback (bool): If True, sets __action_feedback context flag to
                detect recursive automation execution during domain evaluation.
                Default is False.

        Returns:
            Model: Filtered recordset containing only records matching the
                filter_domain. Returns original recordset if no post-condition
                is configured.

        Performance:
            Uses filtered_domain() for database-level filtering when possible,
            which is more efficient than Python-level filtering.

        Example:
            >>> # Automation with post-condition: record must be confirmed
            >>> automation = self.env['base.automation'].browse(1)
            >>> automation.filter_domain = "[('state', '=', 'confirmed')]"
            >>> orders = self.env['sale.order'].search([])
            >>> confirmed = automation._filter_post(orders)
            >>> # Execute actions only on confirmed orders

        See Also:
            _filter_pre(): Pre-condition filtering (before event)
            _filter_post_export_domain(): Returns both records and domain
        """
        return self._filter_post_export_domain(records, feedback)[0]

    def _filter_post_export_domain(self, records, feedback=False):
        """Filter the records that satisfy the postcondition of automation ``self``."""
        self_sudo = self.sudo()
        if self_sudo.filter_domain and records:
            if feedback:
                # this context flag enables to detect the executions of
                # automations while evaluating their postcondition
                records = records.with_context(__action_feedback=True)
            domain = safe_eval.safe_eval(
                self_sudo.filter_domain,
                self._get_eval_context(),
            )
            return records.sudo().filtered_domain(domain).with_env(records.env), domain
        else:
            return records, None

    def _get_actions(self, records, triggers):
        """Retrieve active automation rules matching given triggers for records' model.

        This method finds all automation rules that should be executed for a
        given model and set of trigger types. It initializes the __action_done
        context to track which automations have already been processed, preventing
        infinite recursion when automations trigger other automations.

        The method is called during CRUD operations and other events to determine
        which automations should be evaluated and potentially executed.

        Args:
            records (Model): Recordset whose model determines which automations
                to retrieve. Only the model name (_name) is used, not the actual
                record data.
            triggers (list): List of trigger type strings to match against.
                Examples: ['on_create', 'on_write'], ['on_time'], etc.

        Returns:
            base.automation: Recordset of active automation rules matching the
                model and triggers, with __action_done context initialized for
                recursion prevention.

        Context Management:
            - __action_done (dict): Maps automation → processed records to prevent
              re-processing. Initialized to empty dict if not present.
            - active_test=True: Only retrieves active automations

        Security:
            - Executes with sudo() to access all automations regardless of user rights
            - Results returned with original user's environment (with_env)

        Performance:
            - Single database query with domain filter
            - Results cached in request context via __action_done

        """
        # Note: we keep the old action naming for the method and context variable
        # to avoid breaking existing code/downstream modules
        if "__action_done" not in self.env.context:
            self = self.with_context(__action_done={})
        domain = [("model_name", "=", records._name), ("trigger", "in", triggers)]
        automations = self.with_context(active_test=True).sudo().search(domain)
        return automations.with_env(self.env)

    @api.model
    def _get_calendar(self, automation, record):
        return automation.trg_date_calendar_id

    def _get_cron_interval(self, automations=None):
        """Return the expected time interval used by the cron, in minutes or hours."""

        def get_delay(rec):
            return abs(rec.trg_date_range) * DATE_RANGE_FACTOR[rec.trg_date_range_type]

        if automations is None:
            automations = self.with_context(active_test=True).search(
                [("trigger", "in", TIME_TRIGGERS)],
            )

        # Calculate interval based on minimum delay with tolerance, respecting min/max bounds
        delays = [d for d in automations.mapped(get_delay) if d]
        if delays:
            # Use tolerance percentage of minimum delay to determine cron frequency
            tolerance_interval = int(min(delays) * CRON_INTERVAL_TOLERANCE_PERCENT)
            interval = min(
                max(MIN_CRON_INTERVAL_MINUTES, tolerance_interval),
                MAX_CRON_INTERVAL_MINUTES,
            )
        else:
            interval = DEFAULT_CRON_INTERVAL_MINUTES

        # Convert to hours if interval is a multiple of 60 minutes
        interval_type = "minutes"
        if interval % 60 == 0:
            interval //= 60
            interval_type = "hours"
        return interval, interval_type

    def _get_eval_context(self, payload=None):
        """Prepare the context used when evaluating python code
        :returns: dict -- evaluation context given to safe_eval
        """
        self.ensure_one()
        model = self.env[self.model_name]
        eval_context = {
            "datetime": safe_eval.datetime,
            "dateutil": safe_eval.dateutil,
            "time": safe_eval.time,
            "uid": self.env.uid,
            "user": self.env.user,
            "model": model,
        }
        if payload is not None:
            eval_context["payload"] = payload
        return eval_context

    def _get_trigger_specific_field(self):
        self.ensure_one()
        match self.trigger:
            case "on_create_or_write":
                return _get_domain_fields(
                    self.env,
                    self.model_id.model,
                    self.filter_domain,
                )
            case "on_stage_set":
                domain = [
                    ("ttype", "=", "many2one"),
                    ("name", "in", ["stage_id", "x_studio_stage_id"]),
                ]
            case "on_tag_set":
                domain = [
                    ("ttype", "=", "many2many"),
                    ("name", "in", ["tag_ids", "x_studio_tag_ids"]),
                ]
            case "on_priority_set":
                domain = [
                    ("ttype", "=", "selection"),
                    ("name", "in", ["priority", "x_studio_priority"]),
                ]
            case "on_state_set":
                domain = [
                    ("ttype", "=", "selection"),
                    ("name", "in", ["state", "x_studio_state"]),
                ]
            case "on_user_set":
                domain = [
                    ("relation", "=", "res.users"),
                    ("ttype", "in", ["many2one", "many2many"]),
                    (
                        "name",
                        "in",
                        [
                            "user_id",
                            "user_ids",
                            "x_studio_user_id",
                            "x_studio_user_ids",
                        ],
                    ),
                ]
            case "on_archive" | "on_unarchive":
                domain = [
                    ("ttype", "=", "boolean"),
                    ("name", "in", ["active", "x_active"]),
                ]
            case "on_time_created":
                domain = [("ttype", "=", "datetime"), ("name", "=", "create_date")]
            case "on_time_updated":
                domain = [("ttype", "=", "datetime"), ("name", "=", "write_date")]
            case _:
                return self.env["ir.model.fields"]
        domain += [("model_id", "=", self.model_id.id)]
        return self.env["ir.model.fields"].search(domain, limit=1)

    def _prepare_loggin_values(self, **values):
        self.ensure_one()
        defaults = {
            "name": _("Webhook Log"),
            "type": "server",
            "dbname": self.env.cr.dbname,
            "level": "INFO",
            "path": "base_automation(%s)" % self.id,
            "func": "",
            "line": "",
        }
        defaults.update(**values)
        return defaults

    def _process(self, records, domain_post=None):
        """Process automation ``self`` on the ``records`` that have not been done yet."""
        # filter out the records on which self has already been done
        automation_done = self.env.context.get("__action_done", {})
        records_done = automation_done.get(self, records.browse())
        records -= records_done
        if not records:
            return

        # mark the remaining records as done (to avoid recursive processing)
        if self.env.context.get("__action_feedback"):
            # modify the context dict in place: this is useful when fields are
            # computed during the pre/post filtering, in order to know which
            # automations have already been run by the computation itself
            automation_done[self] = records_done + records
        else:
            automation_done = dict(automation_done)
            automation_done[self] = records_done + records
            self = self.with_context(__action_done=automation_done)
            records = records.with_context(__action_done=automation_done)

        # we process the automation on the records for which any watched field
        # has been modified, and only mark the automation as done for those
        records = records.filtered(self._check_trigger_fields)
        automation_done[self] = records_done + records

        if records and "date_automation_last" in records._fields:
            records.date_automation_last = self.env.cr.now()

        # prepare the contexts for server actions
        contexts = [
            {
                "active_model": record._name,
                "active_ids": record.ids,
                "active_id": record.id,
                "domain_post": domain_post,
            }
            for record in records
        ]

        # execute server actions
        for action in self.sudo().action_server_ids:
            for ctx in contexts:
                try:
                    action.with_context(**ctx).run()
                except Exception as e:
                    self._add_postmortem(e)
                    raise

    def _register_hook(self):
        """Dynamically patch Odoo models to intercept CRUD operations for automation.

        This method is the core of the automation framework. It uses Python
        metaprogramming to dynamically wrap (patch) the create(), write(),
        unlink(), and other methods of models that have automation rules.

        When a model operation occurs (e.g., partner.create()), the patched
        method:
        1. Retrieves applicable automation rules via _get_actions()
        2. Executes the original method (e.g., create.origin())
        3. Evaluates automation conditions (pre/post filters)
        4. Executes automation actions on matching records

        This approach allows automations to work transparently across all Odoo
        models without requiring modifications to those models.

        Methods Patched:
            - create(): For 'on_create' and 'on_create_or_write' triggers
            - write(): For 'on_write' and related triggers
            - _compute_field_value(): For computed field write triggers
            - unlink(): For 'on_unlink' trigger
            - message_post(): For 'on_message_received' and 'on_message_sent'
            - onchange methods: For 'on_change' trigger (field-specific)

        Patching Strategy:
            - Uses method origin attribute to store original implementation
            - Each patched method calls origin to preserve normal behavior
            - Patches applied per-model (not per-instance)
            - Patches persist for life of registry (until module update)

        Performance Impact:
            - Adds <1ms overhead per CRUD operation
            - Only patches models that have automation rules
            - Automation lookup cached in request context
            - No overhead when no automations are configured

        Closure Pattern:
            Patched methods are defined in nested factory functions (make_create,
            make_write, etc.) to ensure proper closure over the 'origin' variable.
            This prevents bugs where closures in loops reference the wrong function.

        Registry Lifecycle:
            - Called during module load (post_load hook)
            - Re-applied when automation rules are created/modified/deleted
            - Removed during module uninstall (_unregister_hook)
            - Registry invalidation triggers re-patching across workers

        Security Considerations:
            - Patches execute with original user's permissions
            - Automation actions execute with sudo() privileges
            - Domain evaluation uses safe_eval with restricted context
            - Cannot bypass record rules or access restrictions

        Known Limitations:
            - Cannot patch private methods (starting with _)
            - Onchange patches apply to form UI only (not API/RPC)
            - Computed field patches only catch explicit recomputations
            - Performance impact accumulates with many automations

        Note:
            This is advanced metaprogramming that modifies the Odoo ORM at
            runtime. Modifications to this method should be thoroughly tested
            across all trigger types and model combinations.
        """
        #
        # Note: the patched methods must be defined inside another function,
        # otherwise their closure may be wrong. For instance, the function
        # create refers to the outer variable 'create', which you expect to be
        # bound to create itself. But that expectation is wrong if create is
        # defined inside a loop; in that case, the variable 'create' is bound to
        # the last function defined by the loop.
        #

        def make_create():
            """Instanciate a create method that processes automation rules."""

            @api.model_create_multi
            def create(self, vals_list, **kw):
                # retrieve the automation rules to possibly execute
                automations = self.env["base.automation"]._get_actions(
                    self,
                    CREATE_TRIGGERS,
                )
                if not automations:
                    return create.origin(self, vals_list, **kw)
                # call original method
                records = create.origin(self.with_env(automations.env), vals_list, **kw)
                # check postconditions, and execute actions on the records that satisfy them
                for automation in automations.with_context(old_values=None):
                    _logger.debug(
                        "Processing automation rule %s (#%s) on %s records (create)",
                        automation.sudo().name,
                        automation.sudo().id,
                        len(records),
                    )
                    automation._process(automation._filter_post(records, feedback=True))
                return records.with_env(self.env)

            return create

        def make_write():
            """Instanciate a write method that processes automation rules."""

            def write(self, vals, **kw):
                # retrieve the automation rules to possibly execute
                automations = self.env["base.automation"]._get_actions(
                    self,
                    WRITE_TRIGGERS,
                )
                if not (automations and self):
                    return write.origin(self, vals, **kw)
                records = self.with_env(automations.env).filtered("id")
                # check preconditions on records
                pre = {a: a._filter_pre(records) for a in automations}
                # read old values before the update
                old_values = {
                    record.id: {
                        field_name: record[field_name]
                        for field_name in vals
                        if field_name in record._fields
                        and record._fields[field_name].store
                    }
                    for record in records
                }
                # call original method
                write.origin(self.with_env(automations.env), vals, **kw)
                # check postconditions, and execute actions on the records that satisfy them
                for automation in automations.with_context(old_values=old_values):
                    _logger.debug(
                        "Processing automation rule %s (#%s) on %s records (write)",
                        automation.sudo().name,
                        automation.sudo().id,
                        len(records),
                    )
                    records, domain_post = automation._filter_post_export_domain(
                        pre[automation],
                        feedback=True,
                    )
                    automation._process(records, domain_post=domain_post)
                return True

            return write

        def make_compute_field_value():
            """Instanciate a compute_field_value method that processes automation rules."""

            #
            # Note: This is to catch updates made by field recomputations.
            #
            def _compute_field_value(self, field):
                # determine fields that may trigger an automation
                stored_fnames = [
                    f.name for f in self.pool.field_computed[field] if f.store
                ]
                if not stored_fnames:
                    return _compute_field_value.origin(self, field)
                # retrieve the action rules to possibly execute
                automations = self.env["base.automation"]._get_actions(
                    self,
                    WRITE_TRIGGERS,
                )
                records = self.filtered("id").with_env(automations.env)
                if not (automations and records):
                    _compute_field_value.origin(self, field)
                    return True
                # check preconditions on records
                # changed fields are all fields computed by the function
                changed_fields = [f for f in records._fields.values() if f.compute == field.compute]
                pre = {a: a.with_context(changed_fields=changed_fields)._filter_pre(records) for a in automations}                # read old values before the update
                old_values = {
                    record.id: {fname: record[fname] for fname in stored_fnames}
                    for record in records
                }
                # call original method
                _compute_field_value.origin(self, field)
                # check postconditions, and execute automations on the records that satisfy them
                for automation in automations.with_context(old_values=old_values):
                    _logger.debug(
                        "Processing automation rule %s (#%s) on %s records (_compute_field_value)",
                        automation.sudo().name,
                        automation.sudo().id,
                        len(records),
                    )
                    records, domain_post = automation._filter_post_export_domain(
                        pre[automation],
                        feedback=True,
                    )
                    automation._process(records, domain_post=domain_post)
                return True

            return _compute_field_value

        def make_unlink():
            """Instanciate an unlink method that processes automation rules."""

            def unlink(self, **kwargs):
                # retrieve the action rules to possibly execute
                automations = self.env["base.automation"]._get_actions(
                    self,
                    ["on_unlink"],
                )
                records = self.with_env(automations.env)
                # check conditions, and execute actions on the records that satisfy them
                for automation in automations:
                    _logger.debug(
                        "Processing automation rule %s (#%s) on %s records (unlink)",
                        automation.sudo().name,
                        automation.sudo().id,
                        len(records),
                    )
                    automation._process(automation._filter_post(records, feedback=True))
                # call original method
                return unlink.origin(self, **kwargs)

            return unlink

        def make_onchange(automation_rule_id):
            """Instanciate an onchange method for the given automation rule."""

            def base_automation_onchange(self):
                automation_rule = self.env["base.automation"].browse(automation_rule_id)

                if not automation_rule._filter_post(self):
                    # Do nothing if onchange record does not satisfy the filter_domain
                    return

                result = {}
                actions = automation_rule.sudo().action_server_ids.with_context(
                    active_model=self._name,
                    active_id=self._origin.id,
                    active_ids=self._origin.ids,
                    onchange_self=self,
                )
                for action in actions:
                    try:
                        res = action.run()
                    except Exception as e:
                        automation_rule._add_postmortem(e)
                        raise

                    if res:
                        if "value" in res:
                            res["value"].pop("id", None)
                            self.update(
                                {
                                    key: val
                                    for key, val in res["value"].items()
                                    if key in self._fields
                                },
                            )
                        if "domain" in res:
                            result.setdefault("domain", {}).update(res["domain"])
                        if "warning" in res:
                            result["warning"] = res["warning"]
                return result

            return base_automation_onchange

        def make_message_post():
            def _message_post(self, *args, **kwargs):
                message = _message_post.origin(self, *args, **kwargs)
                # Don't execute automations for a message emitted during
                # the run of automations for a real message
                # Don't execute if we know already that a message is only internal
                message_sudo = message.sudo().with_context(active_test=False)
                if (
                    "__action_done" in self.env.context
                    or message_sudo.is_internal
                    or message_sudo.subtype_id.internal
                ):
                    return message
                if message_sudo.message_type in (
                    "notification",
                    "auto_comment",
                    "user_notification",
                ):
                    return message

                # always execute actions when the author is a customer
                # if author is not set, it means the message is coming from outside
                mail_trigger = (
                    "on_message_received"
                    if not message_sudo.author_id
                    or message_sudo.author_id.partner_share
                    else "on_message_sent"
                )
                automations = self.env["base.automation"]._get_actions(
                    self,
                    [mail_trigger],
                )
                for automation in automations.with_context(old_values=None):
                    records = automation._filter_pre(self, feedback=True)
                    _logger.debug(
                        "Processing automation rule %s (#%s) on %s records (_message_post)",
                        automation.sudo().name,
                        automation.sudo().id,
                        len(records),
                    )
                    automation._process(records)

                return message

            return _message_post

        patched_models = defaultdict(set)

        def patch(model, name, method):
            """Patch method `name` on `model`, unless it has been patched already."""
            if model not in patched_models[name]:
                patched_models[name].add(model)
                ModelClass = model.env.registry[model._name]
                method.origin = getattr(ModelClass, name)
                setattr(ModelClass, name, method)

        # retrieve all actions, and patch their corresponding model
        for automation_rule in self.with_context({}).search([]):
            Model = self.env.get(automation_rule.model_name)

            # Do not crash if the model of the base_action_rule was uninstalled
            if Model is None:
                _logger.warning(
                    "Automation rule with name '%s' (ID %d) depends on model %s (ID: %d)",
                    automation_rule.name,
                    automation_rule.id,
                    automation_rule.model_name,
                    automation_rule.model_id.id,
                )
                continue

            if automation_rule.trigger in CREATE_WRITE_SET:
                if automation_rule.trigger in CREATE_TRIGGERS:
                    patch(Model, "create", make_create())
                if automation_rule.trigger in WRITE_TRIGGERS:
                    patch(Model, "write", make_write())
                    patch(Model, "_compute_field_value", make_compute_field_value())

            elif automation_rule.trigger == "on_unlink":
                patch(Model, "unlink", make_unlink())

            elif automation_rule.trigger == "on_change":
                # register an onchange method for the automation_rule
                method = make_onchange(automation_rule.id)
                for field in automation_rule.on_change_field_ids:
                    Model._onchange_methods[field.name].append(method)

            if (
                automation_rule.model_id.is_mail_thread
                and automation_rule.trigger in MAIL_TRIGGERS
            ):
                patch(Model, "message_post", make_message_post())

    def _search_time_based_automation_records(self, *, until):
        """Search for records that should trigger time-based automation.

        This method finds all records matching a time-based automation rule
        ('on_time', 'on_time_created', 'on_time_updated') between the last
        execution and the specified 'until' timestamp.

        The method handles complex scenarios including:
        - Calendar-aware date calculations (working days only)
        - Relative date offsets (before/after trigger date)
        - Date vs datetime field types
        - Fallback to create_date for special date_automation_last field
        - Optimization for searchable vs computed fields

        Args:
            until (datetime): The upper bound timestamp for record search.
                Typically set to current time (datetime.now()) by the cron job.
                Only records with trigger dates between last_run and until
                are returned.

        Returns:
            Model: Recordset of records that should trigger the automation.
                Empty recordset if no matches or if date field is missing.

        Trigger Date Calculation:
            - trg_date_range: Numeric offset (e.g., 7 for "7 days")
            - trg_date_range_type: Unit ('minutes', 'hour', 'day', 'month')
            - trg_date_range_mode: 'before' or 'after' the trigger date
            - Formula: trigger_dt = record_date ± (range × range_type)

        Calendar-Aware Mode:
            When trg_date_calendar_id is set and range_type is 'day':
            - Uses resource.calendar.plan_days() for working day calculations
            - Respects calendar leaves (holidays, weekends)
            - Caches calendar calculations per calendar ID
            - Falls back to Python filtering (cannot optimize in database)

        Non-Calendar Mode:
            - Direct database query with relative date domain
            - More efficient but doesn't respect working days
            - Uses database-level date arithmetic

        Date vs Datetime Handling:
            - Date fields: Compares date portions only, uses .date()
            - Datetime fields: Precise timestamp comparison
            - Both handle timezone-aware datetimes correctly

        Special date_automation_last Field:
            If trigger field is 'date_automation_last':
            - Falls back to 'create_date' if date_automation_last is NULL
            - Allows scheduling based on record creation when field unset
            - Useful for "X days after creation" automations

        Performance Optimizations:
            - Single query for searchable/stored fields
            - Two-phase for computed fields (search + filter)
            - Calendar calculations cached per calendar
            - Early return if date field missing

        Security:
            - Evaluates filter_domain using safe_eval with restricted context
            - Always executes with sudo() internally via Model.search()
        """
        automation = self.ensure_one()

        # retrieve the domain and field
        domain = Domain.TRUE
        if automation.filter_domain:
            eval_context = automation._get_eval_context()
            domain = Domain(safe_eval.safe_eval(automation.filter_domain, eval_context))
        Model = self.env[automation.model_name]
        date_field = Model._fields.get(automation.trg_date_id.name)
        if not date_field:
            _logger.warning(
                "Missing date trigger field in automation rule `%s`",
                automation.name,
            )
            return Model

        # get the time information and find the records
        last_run = automation.last_run or datetime.datetime.fromtimestamp(0, tz=None)
        is_date_automation_last = (
            date_field.name == "date_automation_last" and "create_date" in Model._fields
        )
        range_sign = 1 if automation.trg_date_range_mode == "before" else -1
        date_range = range_sign * automation.trg_date_range

        def get_record_dt(record):
            # the field can be a date or datetime, cast always to a datetime
            dt = record[date_field.name]
            if not dt and is_date_automation_last:
                dt = record.create_date
            return fields.Datetime.to_datetime(dt)

        if automation.trg_date_calendar_id and automation.trg_date_range_type == "day":
            # use the calendar information from the record
            # _get_calendar can be overwritten and cannot be optimized
            time_domain = (
                Domain.TRUE
                if is_date_automation_last
                else Domain(date_field.name, "!=", False)
            )
            if date_field.store or date_field.search:
                records = Model.search(time_domain & domain)
            else:
                records = Model.search(domain).filtered_domain(time_domain)

            past_until = {}
            past_last_run = {}

            def calendar_filter(record):
                record_dt = get_record_dt(record)
                if not record_dt:
                    return False
                calendar = self._get_calendar(automation, record)
                if calendar.id not in past_until:
                    past_until[calendar.id] = calendar.plan_days(
                        date_range,
                        until,
                        compute_leaves=True,
                    )
                    past_last_run[calendar.id] = calendar.plan_days(
                        date_range,
                        last_run,
                        compute_leaves=True,
                    )
                return past_last_run[calendar.id] <= record_dt < past_until[calendar.id]

            return records.filtered(calendar_filter)

        # we can search for the records to trigger
        # find the relative dates
        relative_offset = DATE_RANGE[automation.trg_date_range_type] * date_range
        relative_until = until + relative_offset
        relative_last_run = last_run + relative_offset
        if date_field.type == "date":
            # find records that have a date in past, but were not yet executed that day
            time_domain = Domain(
                date_field.name,
                ">",
                relative_last_run.date(),
            ) & Domain(date_field.name, "<=", relative_until.date())
            if is_date_automation_last:
                time_domain |= (
                    Domain(date_field.name, "=", False)
                    & Domain("create_date", ">", relative_last_run.date())
                    & Domain("create_date", "<=", relative_until.today())
                )
        else:  # datetime
            time_domain = Domain(date_field.name, ">=", relative_last_run) & Domain(
                date_field.name,
                "<",
                relative_until,
            )
            if is_date_automation_last:
                time_domain |= (
                    Domain(date_field.name, "=", False)
                    & Domain("create_date", ">=", relative_last_run)
                    & Domain("create_date", "<", relative_until)
                )

        if date_field.store or date_field.search:
            return Model.search(time_domain & domain)
        else:
            return Model.search(domain).filtered_domain(time_domain)

    def _unregister_hook(self):
        """Remove the patches installed by _register_hook()"""
        NAMES = [
            "create",
            "write",
            "_compute_field_value",
            "unlink",
            "_onchange_methods",
            "message_post",
        ]
        for Model in self.env.registry.values():
            for name in NAMES:
                try:
                    delattr(Model, name)
                except AttributeError:
                    pass

    def _update_cron(self):
        """Activate the cron job depending on whether there exists automation rules
        based on time conditions.  Also update its frequency according to
        the smallest automation delay, or restore the default 4 hours if there
        is no time based automation.
        """
        cron = self.env.ref(
            "base_automation.ir_cron_data_base_automation_check",
            raise_if_not_found=False,
        )
        if cron:
            try:
                cron.lock_for_update(allow_referencing=True)
            except LockError:
                return
            automations = self.with_context(active_test=True).search(
                [("trigger", "in", TIME_TRIGGERS)],
            )
            interval_number, interval_type = self._get_cron_interval(automations)
            vals = {"active": bool(automations)}

            actual_cron_timedelta = TIMEDELTA_TYPES[cron.interval_type](
                cron.interval_number,
            )
            new_cron_timedelta = TIMEDELTA_TYPES[interval_type](interval_number)
            if new_cron_timedelta < actual_cron_timedelta:
                # we only update the cron interval if the new delay is shorter than the current one
                vals.update(
                    {
                        "interval_type": interval_type,
                        "interval_number": interval_number,
                    },
                )
            cron.write(vals)

    def _update_registry(self):
        """Update the registry after a modification on automation rules."""
        if self.env.registry.ready and not self.env.context.get("import_file"):
            # re-install the model patches, and notify other workers
            self._unregister_hook()
            self._register_hook()
            self.env.registry.registry_invalidated = True

    # ------------------------------------------------------------
    # VALIDATION METHODS
    # ------------------------------------------------------------

    def _check_trigger_fields(self, record):
        """Check if any configured trigger fields were modified on the record.

        This method determines whether an automation should execute based on
        which fields changed. It's used for 'on_write' and 'on_create_or_write'
        triggers to execute actions only when specific fields are modified.

        The method compares old field values (stored in context during write
        operations) with current values to detect changes.

        Args:
            record (Model): Single record (not a recordset) to check for
                field modifications.

        Returns:
            bool: True if any trigger field was modified, or if no specific
                trigger fields are configured (meaning all fields trigger),
                or if this is a create operation. False otherwise.

        Behavior by Trigger Type:
            - No trigger_field_ids: Returns True (all fields trigger automation)
            - Create operation: Returns True (all fields considered modified)
            - Write operation: Returns True only if a trigger field changed

        Context Requirements:
            - old_values (dict): Maps record.id → {field_name: old_value}.
              Populated during write operations by _register_hook() patches.
              If None/missing, assumes create operation.

        Performance:
            - O(n) where n = number of trigger fields configured
            - Early return optimizations for common cases
            - Lightweight comparison (no database queries)
        """
        self_sudo = self.sudo()
        if not self_sudo.trigger_field_ids:
            # all fields are implicit triggers
            return True

        if self.env.context.get("old_values") is None:
            # this is a create: all fields are considered modified
            return True

        # note: old_vals are in the record format
        old_vals = self.env.context["old_values"].get(record.id, {})

        def differ(name):
            return name in old_vals and record[name] != old_vals[name]

        return any(differ(field.name) for field in self_sudo.trigger_field_ids)

    def _has_trigger_onchange(self):
        return any(
            automation.active
            and automation.trigger == "on_change"
            and automation.on_change_field_ids
            for automation in self
        )

    # ------------------------------------------------------------
    # DEPRECATED METHODS
    # ------------------------------------------------------------

    @api.deprecated("Since 19.0, use _cron_process_time_based_automations")
    def _check(self, automatic=False, use_new_cursor=False):
        if not automatic:
            raise RuntimeError("can run time-based automations only in automatic mode")
        self._cron_process_time_based_actions()
