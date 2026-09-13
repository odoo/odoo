import contextlib
import datetime
import logging
import re
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import _, api, exceptions, fields, models, tools
from odoo.exceptions import LockError, MissingError
from odoo.fields import Domain
from odoo.tools import safe_eval
from odoo.tools.date_utils import get_timedelta, time_unit_selection

from ._canvas import (
    NODE_HEADER_HEIGHT,
    NODE_SIZE_DEFAULT,
    NODE_SIZE_MAX,
    NODE_SIZE_MIN,
)

_logger = logging.getLogger(__name__)

CRON_INTERVAL_TOLERANCE_PERCENT = 0.10

DEFAULT_CRON_INTERVAL_MINUTES = 4 * 60

MIN_CRON_INTERVAL_MINUTES = 1

MAX_CRON_INTERVAL_MINUTES = 4 * 60


MONTH_APPROXIMATION_DAYS = 30

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


# Minutes per delay unit, only to size the scheduler's polling interval: a month
# is approximated because the interval is a fixed number of minutes.
MINUTES_PER_DELAY_UNIT = {
    "minute": 1,
    "hour": 60,
    "day": 24 * 60,
    "month": MONTH_APPROXIMATION_DAYS * 24 * 60,
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


LIVE_RUNTIME_STATES = ("in_progress", "waiting_resume")
RUNTIME_HISTORY_LIMIT = 10


class AutomationRule(models.Model):
    _name = "automation.rule"
    _inherit = [
        "mixin.mail.thread",
        "mixin.mail.activity",
        "mixin.bus.listener",
    ]
    _description = "Automation Rule"
    _order = "sequence, id"

    CRITICAL_FIELDS = ["model_id", "active", "trigger", "on_change_field_ids"]
    RANGE_FIELDS = ["trg_date_range", "trg_date_range_type"]

    sequence = fields.Integer(
        default=10,
        help="Determines the execution order when multiple automations match the same trigger.",
    )
    name = fields.Char(
        string="Automation Rule Name",
        translate=True,
        required=True,
        tracking=True,
    )
    active = fields.Boolean(
        default=True,
        help="When unchecked, the rule is hidden and will not be executed.",
    )
    description = fields.Html()
    model_id = fields.Many2one(
        comodel_name="ir.model",
        required=True,
        domain=[("abstract", "=", False)],
        ondelete="cascade",
        tracking=True,
    )
    model_name = fields.Char(
        related="model_id.model",
        string="Model Name",
        inverse="_inverse_model_name",
        readonly=True,
    )
    model_is_mail_thread = fields.Boolean(related="model_id.is_mail_thread")
    last_run = fields.Datetime(
        string="Process Records From",
        copy=False,
        help="Lower bound of the window the scheduler examines; it advances to "
        "the current time after every run.\n\n"
        "Leave empty and the first run reaches back over the entire history — "
        "every record that already satisfies the condition is processed at "
        "once, which on an existing database can mean thousands of records. "
        "Set it to scope that first run.",
    )
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
        default=lambda self: self.filter_domain,
        store=False,
    )
    action_server_ids = fields.One2many(
        comodel_name="ir.actions.server",
        inverse_name="automation_rule_id",
        string="Actions",
        context={"default_usage": "automation"},
    )
    edge_ids = fields.One2many(
        comodel_name="workflow.edge",
        inverse_name="automation_rule_id",
        string="Workflow Edges",
        copy=False,
        help="Typed dependencies between this automation's steps",
    )
    step_count = fields.Count(
        count_of="action_server_ids",
        string="Steps",
        store=True,
        help="How many steps this automation runs",
    )
    edge_count = fields.Count(
        count_of="edge_ids",
        string="Connections",
        # An edge is cascade-deleted with either endpoint, and the ORM sees that
        # as a change to `action_server_ids` rather than to `edge_ids`, so
        # counting only what Count counts leaves the stored value one high after
        # a step is removed. `test_the_counts_follow_the_graph` reads exactly
        # that sequence.
        depends=["edge_ids", "action_server_ids"],
        store=True,
        help="How many typed dependencies order this automation's steps",
    )
    run_mode = fields.Selection(
        selection=[
            ("immediate", "Immediately"),
            ("queued", "In Batches"),
        ],
        default="immediate",
        required=True,
        help="Immediately: a run executes its steps as soon as it starts, or as soon "
        "as a step becomes ready.\n"
        "In Batches: steps wait for the background dispatcher, which executes the "
        "ready steps of all runs together, one batch per step.",
    )
    step_error_policy = fields.Selection(
        selection=[
            ("fail_run", "Fail the run"),
            ("close_branch", "Close only its branch"),
        ],
        default="fail_run",
        required=True,
        help="What an unhandled failure of a step does.\n"
        "Fail the run: the whole run stops, and its unfinished steps are marked "
        "failed.\n"
        "Close only its branch: what depended on the failed step is skipped, and "
        "the run's other branches carry on.",
    )
    create_runtime_instance = fields.Boolean(
        string="Record Every Run",
        default=False,
        help="Create an Automation Runtime for every execution, so each step's "
        "outcome is recorded and the workflow's edge conditions are evaluated.\n\n"
        "Off by default: an automation on a high-volume trigger would write one "
        "runtime per event. Leave it off for a lightweight rule; turn it on for "
        "anything that branches, or whose history you need.",
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
            ("on_write", "On update"),
        ],
        compute="_compute_trigger",
        store=True,
        readonly=False,
        required=True,
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
        model_field="trg_field_ref_model_name",
        string="Trigger Reference",
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
        selection=time_unit_selection("minute", "hour", "day", "month"),
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
        relation="automation_rule_onchange_fields_rel",
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

    @api.constrains("model_id", "action_server_ids")
    def _check_action_server_model(self):
        for automation in self:
            if automation.model_name == "automation.rule":
                continue

            failing_actions = automation.action_server_ids.filtered(
                lambda action: action.model_id != automation.model_id,  # noqa: B023 - filtered() evaluates the lambda immediately, within this same loop iteration
            )
            if failing_actions:
                raise exceptions.ValidationError(
                    _(
                        "Automation '%(automation)s': The following actions target different models: %(action_names)s.\n\n"
                        "Expected model: %(expected_model)s\n"
                        "Action models: %(action_models)s\n\n"
                        "All actions must target the same model as the automation rule.",
                        automation=automation.name,
                        action_names=", ".join(failing_actions.mapped("name")),
                        expected_model=automation.model_id.name,
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
                        "Mail triggers (%(mail_triggers)s) require the model to inherit from 'mixin.mail.thread'.\n\n"
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

    @api.model_create_multi
    def create(self, vals_list):
        automation_rules = super().create(vals_list)
        self.env.registry.clear_cache()
        self._update_cron()
        if automation_rules._patches_models():
            self._update_registry()
        if automation_rules._has_trigger_onchange():
            self.env.registry.clear_cache("templates")
        return automation_rules

    def write(self, vals: dict):
        clear_templates = self._has_trigger_onchange()
        patched_before = self._patches_models()
        res = super().write(vals)
        self.env.registry.clear_cache()
        if set(vals).intersection(self.CRITICAL_FIELDS):
            if "model_id" in vals:
                self._clean_action_server_ids()
            self._update_cron()
            if patched_before or self._patches_models():
                self._update_registry()
            if clear_templates or self._has_trigger_onchange():
                self.env.registry.clear_cache("templates")
        elif set(vals).intersection(self.RANGE_FIELDS):
            self._update_cron()

        return res

    def unlink(self):
        clear_templates = self._has_trigger_onchange()
        patched = self._patches_models()
        res = super().unlink()
        self.env.registry.clear_cache()
        self._update_cron()
        if patched:
            self._update_registry()
        if clear_templates:
            self.env.registry.clear_cache("templates")
        return res

    def copy(self, default=None):
        new_automations = super().copy(default)
        for old_automation, new_automation in zip(self, new_automations, strict=True):
            old_automation._copy_actions_to(new_automation)
        return new_automations

    def _is_runtime_backed(self):
        self.check_singleton()
        return self.create_runtime_instance or self.trigger == "on_hand"

    @api.constrains("trigger", "create_runtime_instance")
    def _check_conditions_can_be_honoured(self):
        for automation in self:
            if automation._is_runtime_backed():
                continue
            conditional = automation.edge_ids.filtered(
                lambda edge: edge.condition != "on_success",
            )
            if conditional:
                raise exceptions.ValidationError(
                    _(
                        "Automation '%(name)s' has conditional connections "
                        "(%(edges)s) but does not record its runs, so those "
                        "conditions would be ignored.\n\n"
                        "Switch on 'Record Every Run', or make the connections "
                        "unconditional.",
                        name=automation.name,
                        edges=", ".join(conditional.mapped("display_name")),
                    ),
                )

    def _pick_runtime(self, runtime_id):
        self.check_singleton()
        Runtime = self.env["automation.runtime"]
        if runtime_id is False:
            return Runtime
        if runtime_id is not None:
            return (
                Runtime.browse(runtime_id)
                .exists()
                .filtered(lambda run: run.automation_id == self)
            )
        return Runtime.search(
            [("automation_id", "=", self.id), ("state", "in", LIVE_RUNTIME_STATES)],
            limit=1,
        )

    def _recent_runtime_vals(self):
        self.check_singleton()
        Runtime = self.env["automation.runtime"]
        runs = Runtime.search(
            [("automation_id", "=", self.id)],
            limit=RUNTIME_HISTORY_LIMIT,
        )
        labels = dict(Runtime._fields["state"]._description_selection(self.env))
        return [
            {
                "id": run.id,
                "name": run.name,
                "state": run.state,
                "state_label": labels.get(run.state, run.state),
                "progress": run.progress_display,
                "create_date": fields.Datetime.to_string(run.create_date),
                "live": run.state in LIVE_RUNTIME_STATES,
            }
            for run in runs
        ]

    def _recorded_step_ids(self, nodes):
        return {
            action.id
            for [action] in self.env["automation.runtime.line"]
            .sudo()
            ._read_group(
                [("action_id", "in", nodes.ids)],
                ["action_id"],
            )
        }

    @api.readonly
    def get_workflow_graph(self, runtime_id=None):
        self.check_singleton()
        nodes = self.action_server_ids.sorted("sequence")
        runtime = self._pick_runtime(runtime_id)
        state_per_action = {line.action_id.id: line.state for line in runtime.line_ids}
        recorded_ids = self._recorded_step_ids(nodes)
        event_labels = self._workflow_event_labels()
        return {
            "automation_id": self.id,
            "runtime_id": runtime.id or None,
            "runtime_state": runtime.state or None,
            "runs": self._recent_runtime_vals(),
            "runtime_backed": self._is_runtime_backed(),
            "is_positioned": any(node.pos_x or node.pos_y for node in nodes),
            "node_size": {
                "default": NODE_SIZE_DEFAULT,
                "min": NODE_SIZE_MIN,
                "max": NODE_SIZE_MAX,
                "header_height": NODE_HEADER_HEIGHT,
            },
            "viewport": self.env["automation.canvas.viewport"]._get_viewport(self),
            "nodes": [
                {
                    "id": node.id,
                    "name": node.name,
                    "state": node.state,
                    "node_type": node.node_type,
                    "sequence": node.sequence,
                    "pos_x": node.pos_x,
                    "pos_y": node.pos_y,
                    "width": node.pos_width or NODE_SIZE_DEFAULT["width"],
                    "height": node.pos_height or NODE_SIZE_DEFAULT["height"],
                    "runtime_state": state_per_action.get(node.id),
                    "deletable": node.id not in recorded_ids,
                    "wait_delay": node.wait_delay,
                    "wait_unit": node.wait_unit,
                    "approver_names": ", ".join(
                        node.approval_user_ids.mapped("display_name")
                    ),
                    "subflow_name": node.subflow_automation_id.display_name or "",
                    "detail": node._workflow_step_detail(),
                }
                for node in nodes
            ],
            "edges": [
                {
                    "id": edge.id,
                    "source": edge.source_node_id.id,
                    "target": edge.target_node_id.id,
                    **edge._runtime_copy_vals(),
                    "label": edge.label,
                    "event_label": event_labels.get(
                        (edge.condition, edge.event_code), ""
                    ),
                }
                for edge in self.edge_ids
            ],
        }

    def _workflow_event_labels(self):
        return {}

    def set_workflow_viewport(self, x, y, scale):
        """Remember where this reader left the canvas of this automation.

        Separate from `write` on purpose: the viewport is the reader's own
        state, so storing it needs read access to the automation and nothing
        more, and it never marks the automation itself as modified.
        """
        self.check_singleton()
        self.check_access("read")
        self.env["automation.canvas.viewport"]._update_viewport(self, x, y, scale)
        return True

    def _copy_actions_to(self, target):
        self.check_singleton()
        target.check_singleton()
        new_by_old = {
            action.id: action.copy({"automation_rule_id": target.id})
            for action in self.action_server_ids
        }
        self.env["workflow.edge"].create(
            [
                {
                    "source_node_id": new_by_old[edge.source_node_id.id].id,
                    "target_node_id": new_by_old[edge.target_node_id.id].id,
                    **edge._runtime_copy_vals(),
                    "label": edge.label,
                }
                for edge in self.edge_ids
                if edge.source_node_id.id in new_by_old
                and edge.target_node_id.id in new_by_old
            ]
        )

    def _inverse_model_name(self):
        for rec in self:
            rec.model_id = self.env["ir.model"]._get(rec.model_name)

    @api.depends("model_id")
    def _compute_trigger(self):
        self.trigger = False

    def _clean_action_server_ids(self):
        for automation in self.filtered("model_id"):
            if automation.model_name == "automation.rule":
                continue

            actions_to_remove = automation.action_server_ids.filtered(
                lambda action: action.model_id != automation.model_id,  # noqa: B023 - filtered() evaluates the lambda immediately, within this same loop iteration
            )
            if actions_to_remove:
                actions_to_remove.unlink()

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
            if not record.trg_date_range_mode or record.trigger != "on_time":
                record.trg_date_range_mode = "after"

    @api.depends("trigger", "trg_date_id", "trg_date_range_type")
    def _compute_trg_date_calendar_id(self):
        to_reset = self.filtered(
            lambda a: (
                a.trigger not in TIME_TRIGGERS
                or not a.trg_date_id
                or a.trg_date_range_type != "day"
            ),
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
            lambda a: (
                a.trigger in ["on_stage_set", "on_tag_set"]
                and a.trg_field_ref is not False
            ),
        )
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

    @api.onchange("trigger")
    def _onchange_trigger(self):
        self.check_singleton()
        field = (
            self._get_trigger_specific_field()
            if self.trigger not in TIME_TRIGGERS
            else False
        )
        self.trigger_field_ids = field

    @api.onchange("trigger", "action_server_ids")
    def _onchange_trigger_or_actions(self):
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

        doomed = self.action_server_ids.filtered(
            lambda action: action._is_live_record_required()
        )
        if self.trigger == "on_unlink" and doomed:
            action_states = dict(
                self.action_server_ids._fields["state"]._description_selection(
                    self.env,
                ),
            )
            return {
                "warning": {
                    "title": _("Warning"),
                    "message": _(
                        "A rule that runs on deletion runs once the record is "
                        "already gone, and these actions each need it to still "
                        "be there:\n%(actions)s\n\nThey would do nothing, "
                        "every time the rule fired.",
                        actions="\n".join(
                            f"- {action.name} ({action_states.get(action.state, action.state)})"
                            for action in doomed
                        ),
                    ),
                },
            }
        return None

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

    def action_view_scheduled_action(self):
        cron = self.env.ref(
            "automation.ir_cron_data_automation_check",
            raise_if_not_found=False,
        )
        if not cron:
            message = _(
                "The scheduled action for Automation Rules cannot be found.\n\n"
                "This scheduled action (external ID: automation.ir_cron_data_automation_check) "
                "is required for time-based automations to work.\n\n"
                "Recovery steps:\n"
                "1. Go to Settings → Technical → Automation → Scheduled Actions\n"
                "2. Look for 'Automation Rules: check and execute'\n"
                "3. If missing, update the 'automation' module to recreate it\n"
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

    def action_manual_trigger(self):
        self.check_singleton()

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

        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])

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

        has_dag = bool(self.edge_ids)

        if has_dag:
            runtimes = self._run_through_runtimes(filtered_records)

            if len(runtimes) == 1:
                return {
                    "type": "ir.actions.act_window",
                    "res_model": "automation.runtime",
                    "res_id": runtimes.id,
                    "view_mode": "form",
                    "views": [[False, "form"]],
                    "target": "current",
                }
            return {
                "type": "ir.actions.act_window",
                "res_model": "automation.runtime",
                "view_mode": "list,form",
                "domain": [("id", "in", runtimes.ids)],
            }

        try:
            self._process(filtered_records)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Automation Executed"),
                    "message": _(
                        "Successfully processed %(processed)d of %(total)d selected record(s).",
                        processed=len(filtered_records),
                        total=len(records),
                    ),
                    "type": "success",
                },
            }
        except Exception as e:
            self._add_postmortem(e)
            raise

    @api.model
    def _add_postmortem(self, e):
        if self.env.user._is_internal():
            e.context = {}
            e.context["exception_class"] = "automation"
            e.context["automation"] = {
                "id": self.id,
                "name": self.sudo().name,
            }

    @api.model
    def _cron_process_time_based_actions(self):
        if "__action_done" not in self.env.context:
            self = self.with_context(__action_done={})

        final_exception = None
        automations = self.with_context(active_test=True).search(
            [("trigger", "in", TIME_TRIGGERS)],
        )

        for automation in automations:
            automation = automation.with_prefetch()
            try:
                if not automation.active:
                    continue
            except MissingError:
                continue
            _logger.info("Starting time-based automation rule `%s`.", automation.name)
            now = self.env.cr.now()
            first_run = not automation.last_run
            records = automation._search_time_based_automation_records(until=now)
            if first_run and records:
                _logger.warning(
                    "Automation rule `%s` has no 'Process Records From' date: its "
                    "first run covers the entire history and will process %s "
                    "record(s) now. Set that field to scope the first run.",
                    automation.name,
                    len(records),
                )
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
            self.env["ir.cron"]._commit_progress()
        if final_exception is not None:
            raise final_exception

    def _filter_pre(self, records, feedback=False):
        self_sudo = self.sudo()
        if self_sudo.filter_pre_domain and records:
            if feedback:
                records = records.with_context(__action_feedback=True)
            domain = safe_eval.safe_eval(
                self_sudo.filter_pre_domain,
                self._prepare_eval_context(),
            )
            changed_fields = self.env.context.get("changed_fields", ())
            to_compute = {
                dep: comp
                for f in changed_fields
                for dep in self.env.registry.get_dependent_fields(f)
                if (comp := self.env.get_records_to_compute(dep))
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
        return self._filter_post_export_domain(records, feedback)[0]

    def _filter_post_export_domain(self, records, feedback=False):
        self_sudo = self.sudo()
        if self_sudo.filter_domain and records:
            if feedback:
                records = records.with_context(__action_feedback=True)
            domain = safe_eval.safe_eval(
                self_sudo.filter_domain,
                self._prepare_eval_context(),
            )
            return records.sudo().filtered_domain(domain).with_env(records.env), domain
        else:
            return records, None

    def _get_actions(self, records, triggers):
        if "__action_done" not in self.env.context:
            self = self.with_context(__action_done={})
        ids = self._get_automation_ids(records._name, tuple(triggers))
        return self.browse(ids).with_env(self.env)

    @api.model
    @tools.ormcache("model_name", "triggers")
    def _get_automation_ids(self, model_name, triggers):
        domain = [("model_name", "=", model_name), ("trigger", "in", list(triggers))]
        return tuple(
            self.with_context(active_test=True).sudo().search(domain).ids,
        )

    @api.model
    def _get_calendar(self, automation, record):
        return automation.trg_date_calendar_id

    def _get_cron_interval(self, automations=None):
        def get_delay(rec):
            return abs(rec.trg_date_range) * MINUTES_PER_DELAY_UNIT.get(
                rec.trg_date_range_type, 0
            )

        if automations is None:
            automations = self.with_context(active_test=True).search(
                [("trigger", "in", TIME_TRIGGERS)],
            )

        delays = [d for d in automations.mapped(get_delay) if d]
        if delays:
            tolerance_interval = int(min(delays) * CRON_INTERVAL_TOLERANCE_PERCENT)
            interval = min(
                max(MIN_CRON_INTERVAL_MINUTES, tolerance_interval),
                MAX_CRON_INTERVAL_MINUTES,
            )
        else:
            interval = DEFAULT_CRON_INTERVAL_MINUTES

        unit = "minute"
        if interval % 60 == 0:
            interval //= 60
            unit = "hour"
        return interval, unit

    def _prepare_eval_context(self):
        self.check_singleton()
        model = self.env[self.model_name]
        return {
            "datetime": safe_eval.datetime,
            "dateutil": safe_eval.dateutil,
            "time": safe_eval.time,
            "uid": self.env.uid,
            "user": self.env.user,
            "model": model,
        }

    def _get_trigger_specific_field(self):
        self.check_singleton()
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

    def _prepare_logging_values(self, **values):
        self.check_singleton()
        defaults = {
            "name": _("Webhook Log"),
            "type": "server",
            "dbname": self.env.cr.dbname,
            "level": "INFO",
            "path": f"automation({self.id})",
            "func": "",
            "line": "",
        }
        defaults.update(**values)
        return defaults

    def _run_through_runtimes(self, records):
        self.check_singleton()
        runtimes = self.env["automation.runtime"]
        for record in records:
            runtime = self.env["automation.runtime"].create(
                {
                    "automation_id": self.id,
                    "res_model": records._name,
                    "res_id": record.id,
                }
            )
            runtime._launch()
            runtimes |= runtime
        return runtimes

    def _process(self, records, domain_post=None):
        automation_done = self.env.context.get("__action_done", {})
        records_done = automation_done.get(self, records.browse())
        records -= records_done
        if not records:
            return

        if records.env.context.get("__action_feedback"):
            automation_done[self] = records_done + records
        else:
            automation_done = dict(automation_done)
            automation_done[self] = records_done + records
            self = self.with_context(__action_done=automation_done)
            records = records.with_context(__action_done=automation_done)

        records = records.filtered(self._check_trigger_fields)
        automation_done[self] = records_done + records
        if not records:
            return

        if "date_automation_last" in records._fields:
            records.with_context(
                __automation_bookkeeping=True,
            ).date_automation_last = self.env.cr.now()

        batch_context = {
            "active_model": records._name,
            "active_ids": records.ids,
            "active_id": records[0].id,
            "domain_post": domain_post,
        }
        contexts = [
            {
                "active_model": record._name,
                "active_ids": record.ids,
                "active_id": record.id,
                "domain_post": domain_post,
            }
            for record in records
        ]

        if self.sudo().create_runtime_instance:
            self.sudo()._run_through_runtimes(records)
            return

        for action in self.sudo().action_server_ids._sorted_by_dependency():
            action_contexts = [batch_context] if action._is_batchable() else contexts
            for ctx in action_contexts:
                try:
                    action.with_context(**ctx).run()
                except Exception as e:
                    self._add_postmortem(e)
                    raise

    def _register_hook(self):

        def prepare_create():
            @api.model_create_multi
            def create(self, vals_list, **kw):
                automations = self.env["automation.rule"]._get_actions(
                    self,
                    CREATE_TRIGGERS,
                )
                if not automations:
                    return create.origin(self, vals_list, **kw)
                records = create.origin(self.with_env(automations.env), vals_list, **kw)
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

        def prepare_write():
            def write(self, vals, **kw):
                if self.env.context.get("__automation_bookkeeping"):
                    return write.origin(self, vals, **kw)
                automations = self.env["automation.rule"]._get_actions(
                    self,
                    WRITE_TRIGGERS,
                )
                if not (automations and self):
                    return write.origin(self, vals, **kw)
                records = self.with_env(automations.env).filtered("id")
                pre = {a: a._filter_pre(records) for a in automations}
                old_values = {
                    record.id: {
                        field_name: record[field_name]
                        for field_name in vals
                        if field_name in record._fields
                        and record._fields[field_name].store
                    }
                    for record in records
                }
                write.origin(self.with_env(automations.env), vals, **kw)
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

        def prepare_compute_field_value():

            def _compute_field_value(self, field, validate=True):
                stored_fnames = [
                    f.name for f in self.pool.field_computed[field] if f.store
                ]
                if not stored_fnames:
                    return _compute_field_value.origin(self, field, validate=validate)
                automations = self.env["automation.rule"]._get_actions(
                    self,
                    WRITE_TRIGGERS,
                )
                stored_fnames_set = set(stored_fnames)
                automations = automations.filtered(
                    lambda a: (
                        stored_fnames_set & set(a.trigger_field_ids.mapped("name"))
                    )
                )
                records = self.filtered("id").with_env(automations.env)
                if not (automations and records):
                    _compute_field_value.origin(self, field, validate=validate)
                    return True
                changed_fields = [
                    f for f in records._fields.values() if f.compute == field.compute
                ]
                pre = {
                    a: a.with_context(changed_fields=changed_fields)._filter_pre(
                        records
                    )
                    for a in automations
                }
                old_values = {
                    record.id: {fname: record[fname] for fname in stored_fnames}
                    for record in records
                }
                _compute_field_value.origin(self, field, validate=validate)
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

        def prepare_unlink():
            def unlink(self, **kwargs):
                automations = self.env["automation.rule"]._get_actions(
                    self,
                    ["on_unlink"],
                )
                records = self.with_env(automations.env)
                for automation in automations:
                    _logger.debug(
                        "Processing automation rule %s (#%s) on %s records (unlink)",
                        automation.sudo().name,
                        automation.sudo().id,
                        len(records),
                    )
                    automation._process(automation._filter_post(records, feedback=True))
                return unlink.origin(self, **kwargs)

            return unlink

        def prepare_onchange(automation_rule_id):
            def automation_onchange(self):
                automation_rule = self.env["automation.rule"].browse(automation_rule_id)

                if not automation_rule._filter_post(self):
                    return None

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

            return automation_onchange

        def prepare_message_post():
            def _message_post(self, *args, **kwargs):
                message = _message_post.origin(self, *args, **kwargs)
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

                mail_trigger = (
                    "on_message_received"
                    if not message_sudo.author_id
                    or message_sudo.author_id.partner_share
                    else "on_message_sent"
                )
                automations = self.env["automation.rule"]._get_actions(
                    self,
                    [mail_trigger],
                )
                for automation in automations.with_context(old_values=None):
                    records = automation._filter_pre(self, feedback=True)
                    records, domain_post = automation._filter_post_export_domain(
                        records,
                        feedback=True,
                    )
                    _logger.debug(
                        "Processing automation rule %s (#%s) on %s records (_message_post)",
                        automation.sudo().name,
                        automation.sudo().id,
                        len(records),
                    )
                    automation._process(records, domain_post=domain_post)

                return message

            return _message_post

        patched_models = defaultdict(set)

        def patch(model, name, method):
            if model not in patched_models[name]:
                patched_models[name].add(model)
                ModelClass = model.env.registry[model._name]
                method.origin = getattr(ModelClass, name)
                setattr(ModelClass, name, method)

        for automation_rule in self.with_context({}).search([]):
            Model = self.env.get(automation_rule.model_name)

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
                    patch(Model, "create", prepare_create())
                if automation_rule.trigger in WRITE_TRIGGERS:
                    patch(Model, "write", prepare_write())
                    patch(Model, "_compute_field_value", prepare_compute_field_value())

            elif automation_rule.trigger == "on_unlink":
                patch(Model, "unlink", prepare_unlink())

            elif automation_rule.trigger == "on_change":
                method = prepare_onchange(automation_rule.id)
                onchange_methods = Model._onchange_methods
                for field in automation_rule.on_change_field_ids:
                    onchange_methods.setdefault(field.name, []).append(method)

            if (
                automation_rule.model_id.is_mail_thread
                and automation_rule.trigger in MAIL_TRIGGERS
            ):
                patch(Model, "message_post", prepare_message_post())

    def _search_time_based_automation_records(self, *, until):
        automation = self.check_singleton()

        domain = Domain.TRUE
        if automation.filter_domain:
            eval_context = automation._prepare_eval_context()
            domain = Domain(safe_eval.safe_eval(automation.filter_domain, eval_context))
        Model = self.env[automation.model_name]
        date_field = Model._fields.get(automation.trg_date_id.name)
        if not date_field:
            _logger.warning(
                "Missing date trigger field in automation rule `%s`",
                automation.name,
            )
            return Model

        last_run = automation.last_run or datetime.datetime.fromtimestamp(0, tz=None)
        is_date_automation_last = (
            date_field.name == "date_automation_last" and "create_date" in Model._fields
        )
        range_sign = 1 if automation.trg_date_range_mode == "before" else -1
        date_range = range_sign * automation.trg_date_range

        def get_record_dt(record):
            dt = record[date_field.name]
            if not dt and is_date_automation_last:
                dt = record.create_date
            return fields.Datetime.to_datetime(dt)

        if automation.trg_date_calendar_id and automation.trg_date_range_type == "day":
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

        relative_offset = (
            get_timedelta(date_range, automation.trg_date_range_type)
            if automation.trg_date_range_type
            else relativedelta()
        )
        relative_until = until + relative_offset
        relative_last_run = last_run + relative_offset
        if date_field.type == "date":
            time_domain = Domain(
                date_field.name,
                ">",
                relative_last_run.date(),
            ) & Domain(date_field.name, "<=", relative_until.date())
            if is_date_automation_last:
                time_domain |= (
                    Domain(date_field.name, "=", False)
                    & Domain("create_date", ">", relative_last_run.date())
                    & Domain("create_date", "<=", relative_until.date())
                )
        else:
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
        NAMES = [
            "create",
            "write",
            "_compute_field_value",
            "unlink",
            "_onchange_methods__",
            "message_post",
        ]
        for Model in self.env.registry.values():
            for name in NAMES:
                with contextlib.suppress(AttributeError):
                    delattr(Model, name)

    def _update_cron(self):
        cron = self.env.ref(
            "automation.ir_cron_data_automation_check",
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
            repeat_interval, repeat_unit = self._get_cron_interval(automations)
            vals = {"active": bool(automations)}

            # Compared by where each cadence lands from one instant, not by a
            # length: a month has none, and the old table priced it at 30 days.
            reference = fields.Datetime.now()
            if (
                reference + get_timedelta(repeat_interval, repeat_unit)
                < reference + cron._get_recurrence_delta()
            ):
                vals.update(
                    {"repeat_unit": repeat_unit, "repeat_interval": repeat_interval},
                )
            cron.write(vals)

    def _patches_models(self):
        return any(
            rule.trigger in CREATE_WRITE_SET
            or rule.trigger in ("on_unlink", "on_change")
            or rule.trigger in MAIL_TRIGGERS
            for rule in self
        )

    def _update_registry(self):
        if self.env.registry.ready and not self.env.context.get("import_file"):
            self._unregister_hook()
            self._register_hook()
            self.env.registry.registry_invalidated = True

    def _check_trigger_fields(self, record):
        self_sudo = self.sudo()
        if not self_sudo.trigger_field_ids:
            return True

        if self.env.context.get("old_values") is None:
            return True

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

    @api.deprecated("Since 19.0, use _cron_process_time_based_actions")
    def _check(self, automatic=False, use_new_cursor=False):
        if not automatic:
            raise RuntimeError("can run time-based automations only in automatic mode")
        self._cron_process_time_based_actions()
