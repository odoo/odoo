import base64
import logging
from collections.abc import Callable
from functools import partial
from typing import Any, Literal, Self

from odoo import api, fields, models, tools
from odoo.api import ValuesType
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs import webhook
from odoo.libs.debug_log import DebugLog
from odoo.libs.json import OPT_INDENT_2, OPT_SORT_KEYS
from odoo.libs.json import dumps as json_dumps
from odoo.libs.netguard import DestinationRefused
from odoo.tools import _
from odoo.tools.misc import unquote
from odoo.tools.safe_eval import safe_eval, test_python_expr

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)
_server_action_logger = logging.getLogger(
    "odoo.addons.base.models.ir_actions.server_action_safe_eval"
)


def _webhook_json_default(value: Any) -> str:
    if isinstance(value, bytes | bytearray):
        try:
            return bytes(value).decode()
        except UnicodeDecodeError:
            return base64.b64encode(value).decode()
    return str(value)


class LoggerProxy:
    _ALLOWED = frozenset({"log", "info", "warning", "error", "exception"})

    def __getattr__(self, name: str) -> Any:
        if name in self._ALLOWED:
            return getattr(_server_action_logger, name)
        msg = f"LoggerProxy has no attribute {name!r}"
        raise AttributeError(msg)


_LOGGER_PROXY = LoggerProxy()


WEBHOOK_SAMPLE_VALUES = {
    "integer": 42,
    "float": 42.42,
    "monetary": 42.42,
    "char": "Hello World",
    "text": "Hello World",
    "html": "<p>Hello World</p>",
    "boolean": True,
    "selection": "option1",
    "date": "2020-01-01",
    "datetime": "2020-01-01 00:00:00",
    "binary": "<base64_data>",
    "many2one": 47,
    "many2many": [42, 47],
    "one2many": [42, 47],
    "reference": "res.partner,42",
    None: "some_data",
}

CRUD_STATES = ("object_write", "object_create", "object_copy")


class ServerActionWithWarningsError(UserError):
    pass


class IrActionsServer(models.Model):
    _name = "ir.actions.server"
    _description = "Server Actions"
    _table = "ir_act_server"
    _inherit = ["ir.actions.actions"]
    _order = "sequence,name,id"

    # FIELDS
    name = fields.Char(
        compute="_compute_names",
        store=True,
        readonly=False,
    )
    automated_name = fields.Char(
        compute="_compute_names",
        store=True,
    )
    name_is_custom = fields.Boolean(
        copy=True,
        help="Set once the name has been typed rather than derived from the "
        "action's type, so that changing the type stops renaming it.",
    )
    usage = fields.Selection(
        selection=[
            ("ir_actions_server", "Server Action"),
            ("ir_cron", "Scheduled Action"),
        ],
        default="ir_actions_server",
        required=True,
    )
    state = fields.Selection(
        selection=[
            ("object_write", "Update Record"),
            ("object_create", "Create Record"),
            ("object_copy", "Duplicate Record"),
            ("code", "Execute Code"),
            ("webhook", "Send Webhook Notification"),
            ("multi", "Multi Actions"),
        ],
        string="Type",
        copy=True,
        required=True,
        help="Type of server action. The following values are available:\n"
        "- 'Update Record': update the values of a record\n"
        "- 'Create Record': create a new record with new values\n"
        "- 'Duplicate Record': copy an existing record\n"
        "- 'Execute Code': a block of Python code that will be executed\n"
        "- 'Send Webhook Notification': send a POST request to an external system\n"
        "- 'Multi Actions': define an action that triggers several other server actions\n"
        "\nAdditional types may be added by other modules (e.g. Discuss, SMS).",
    )
    allowed_states = fields.Json(
        string="Allowed states",
        compute="_compute_allowed_states",
    )
    sequence = fields.Integer(
        default=5,
        help="When dealing with multiple actions, the execution order is "
        "based on the sequence. Low number means high priority.",
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        index=True,
        required=True,
        ondelete="cascade",
        help="Model on which the server action runs.",
    )
    available_model_ids = fields.Many2many(
        comodel_name="ir.model",
        string="Available Models",
        compute="_compute_available_model_ids",
        store=False,
    )
    model_name = fields.Char(
        related="model_id.model",
        string="Model Name",
    )
    warning = fields.Text(
        compute="_compute_warning",
        recursive=True,
    )
    ir_cron_ids = fields.One2many(
        comodel_name="ir.cron",
        inverse_name="ir_actions_server_id",
        string="Scheduled Action",
        context={"active_test": False},
    )
    code = fields.Text(
        string="Python Code",
        groups="base.group_system",
        help="Write Python code that the action will execute. Some variables are "
        "available for use; help about python expression is given in the help tab.",
    )
    show_code_history = fields.Boolean(compute="_compute_show_code_history")
    parent_id = fields.Many2one(
        comodel_name="ir.actions.server",
        string="Parent Action",
        index=True,
        ondelete="cascade",
    )
    child_ids = fields.One2many(
        comodel_name="ir.actions.server",
        inverse_name="parent_id",
        string="Child Actions",
        copy=True,
        domain=lambda self: str(self._get_domain_children()),
        help="Child server actions that will be executed. The global return value is the action returned by the last child that returns one; children that return nothing are skipped over.",
    )
    crud_model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Record to Create",
        compute="_compute_crud_relations",
        inverse="_inverse_crud_model_id",
        store=True,
        readonly=False,
        help="Kind of record to create or duplicate. Defaults to the action's own model; a value set here is kept.",
    )
    crud_model_name = fields.Char(
        related="crud_model_id.model",
        string="Target Model Name",
        readonly=True,
    )
    link_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        help="Specify a field used to link the newly created record on the record used by the server action.",
    )
    group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="ir_act_server_group_rel",
        column1="act_id",
        column2="gid",
        string="Allowed Groups",
        help="Groups that can execute the server action. Leave empty to allow everybody.",
    )

    update_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Field to Update",
        compute="_compute_crud_relations",
        store=True,
        readonly=False,
        ondelete="cascade",
    )
    update_path = fields.Char(
        string="Field to Update Path",
        default=lambda self: self._default_update_path(),
        help="Path to the field to update, e.g. 'partner_id.name'",
    )
    update_related_model_id = fields.Many2one(
        comodel_name="ir.model",
        compute="_compute_crud_relations",
        store=True,
        readonly=False,
    )
    update_field_type = fields.Selection(
        related="update_field_id.ttype",
        readonly=True,
    )
    update_m2m_operation = fields.Selection(
        selection=[
            ("add", "Adding"),
            ("remove", "Removing"),
            ("set", "Setting it to"),
            ("clear", "Clearing it"),
        ],
        string="Many2many Operations",
        default="add",
    )
    update_boolean_value = fields.Selection(
        selection=[("true", "Yes (True)"), ("false", "No (False)")],
        string="Boolean Value",
        default="true",
    )

    value = fields.Text(
        help="What to write, read according to 'Value Type'.\n\n"
        "Update: the value is used as typed, without evaluation -- `42`, "
        "`My custom name`, or the id of the selected record.\n\n"
        "Compute: a Python expression evaluated with the same names the "
        "'Execute Code' action gets, e.g. `env.user.name` or `record.id`.\n\n"
        "'Create Record' does not read 'Value Type': this field is the name of "
        "the record to create, taken literally."
    )
    evaluation_type = fields.Selection(
        selection=[
            ("value", "Update"),
            ("sequence", "Sequence"),
            ("equation", "Compute"),
        ],
        string="Value Type",
        default="value",
        change_default=True,
    )
    html_value = fields.Html()
    sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Sequence to use",
    )
    resource_ref = fields.Reference(
        selection="_selection_target_model",
        string="Record",
        inverse="_inverse_resource_ref",
    )
    selection_value = fields.Many2one(
        comodel_name="ir.model.fields.selection",
        string="Custom Value",
        inverse="_inverse_selection_value",
        domain='[("field_id", "=", update_field_id)]',
        ondelete="cascade",
    )

    value_field_to_show = fields.Selection(
        selection=[
            ("value", "value"),
            ("html_value", "html_value"),
            ("sequence_id", "sequence_id"),
            ("resource_ref", "reference"),
            ("update_boolean_value", "update_boolean_value"),
            ("selection_value", "selection_value"),
        ],
        compute="_compute_value_field_to_show",
    )
    webhook_url = fields.Char(
        string="Webhook URL",
        help="URL to send the POST request to.\n\n"
        "The request is UNAUTHENTICATED: no credential, no signature, no "
        "retry, and no record of the exchange beyond the server log. That is "
        "the right shape for notifying a receiver that accepts an open URL.\n\n"
        "For anything that needs a credential, a retry policy, a rate limit, "
        "secret redaction or an auditable record of what was sent, use an "
        "'Execute Code' action against a configured outbound endpoint "
        "instead. With the API Transport application installed:\n"
        "    endpoint = env['integration.service'].search(\n"
        "        [('code', '=', 'my_service')], limit=1)\n"
        "    endpoint._get_api_client().post('/path', json={'id': record.id})\n"
        "That endpoint owns the credential, the retry policy and the "
        "integration.exchange row.",
    )
    webhook_timeout = fields.Integer(
        string="Webhook Timeout (s)",
        default=1,
        help="Seconds to wait for the receiver before giving up.\n\n"
        "The default of 1 second is deliberately short, and the cost of "
        "raising it is paid by a worker: the call is made after the "
        "transaction commits, so the request thread is held for however long "
        "this allows.\n\n"
        "It is also short enough that a receiver which merely thinks for a "
        "moment times out, and a timeout here is genuinely ambiguous — the "
        "receiver may well have processed the payload. Raise it for a slow "
        "but trusted receiver; if delivery has to be certain, this action is "
        "the wrong tool (see Webhook URL).",
    )
    webhook_field_ids = fields.Many2many(
        comodel_name="ir.model.fields",
        relation="ir_act_server_webhook_field_rel",
        column1="server_id",
        column2="field_id",
        string="Webhook Fields",
        help="Fields to send in the POST request.\n\n"
        "Four keys are always present, whatever is selected here: the record's "
        "id as both 'id' and '_id', its model as '_model', and the name of the "
        "action that triggered the webhook as '_action'.",
    )
    webhook_sample_payload = fields.Text(
        string="Sample Payload",
        compute="_compute_webhook_sample_payload",
    )

    _WEBHOOK_TIMEOUT_CEILING = 60

    # CONSTRAINT METHODS

    @api.constrains("webhook_timeout", "state")
    def _check_webhook_timeout(self) -> None:
        for action in self:
            if action.state != "webhook":
                continue
            if not 1 <= action.webhook_timeout <= self._WEBHOOK_TIMEOUT_CEILING:
                _debug.logic(
                    "webhook_timeout_refused",
                    action=action.id,
                    timeout=action.webhook_timeout,
                    ceiling=self._WEBHOOK_TIMEOUT_CEILING,
                )
                raise ValidationError(
                    _(
                        "Webhook timeout must be between 1 and %(ceiling)s "
                        "seconds. The call is made after the transaction "
                        "commits, so this is time a worker spends waiting; a "
                        "receiver that needs longer should be given a queue "
                        "rather than a synchronous webhook.",
                        ceiling=self._WEBHOOK_TIMEOUT_CEILING,
                    )
                )

    @api.constrains("code")
    def _check_python_code(self) -> None:
        for action in self.sudo().filtered("code"):
            msg = test_python_expr(expr=action.code.strip(), mode="exec")
            if msg:
                _debug.logic("python_code_refused", action=action.id, reason="syntax")
                raise ValidationError(msg)

    @api.constrains("update_path", "model_id", "state")
    def _check_update_path(self) -> None:
        for action in self:
            if (
                action.state == "object_write"
                and action.update_path
                and action.model_id
            ):
                action._get_relation_chain("update_path", raise_on_error=True)

    @api.constrains("parent_id", "child_ids")
    def _check_children(self) -> None:
        if self._has_cycle():
            _debug.logic("children_refused", actions=self.ids, reason="cycle")
            raise ValidationError(_("Recursion found in child server actions"))

        if children_with_warnings := self.child_ids.filtered("warning"):
            _debug.logic(
                "children_refused",
                actions=self.ids,
                reason="child_warnings",
                children=children_with_warnings.ids,
            )
            raise ValidationError(
                _(
                    "Following child actions have warnings: %(children)s",
                    children=", ".join(children_with_warnings.mapped("name")),
                )
            )

    # CRUD METHODS

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:

        def with_inherited(vals: ValuesType) -> ValuesType:
            if not (parent_id := vals.get("parent_id")):
                return dict(vals)
            parent = self.browse(parent_id)
            return {
                **vals,
                "model_id": parent.model_id.id,
                "group_ids": parent.group_ids.ids,
            }

        vals_list = [with_inherited(vals) for vals in vals_list]
        automated_names = 0
        for vals in vals_list:
            if vals.get("name"):
                vals.setdefault("name_is_custom", True)
            else:
                vals["name"] = self.new(vals)._prepare_automated_name()
                vals["name_is_custom"] = False
                automated_names += 1
        _debug.pipeline(
            "create_prepared",
            count=len(vals_list),
            inherited=sum(1 for vals in vals_list if vals.get("parent_id")),
            automated_names=automated_names,
        )
        actions = super().create(vals_list)

        history_vals = [
            {"action_id": action.id, "code": vals["code"]}
            for action, vals in zip(actions, vals_list, strict=True)
            if vals.get("code")
        ]
        if history_vals:
            self.env["ir.actions.server.history"].create(history_vals)

        _debug.lifecycle(
            "create",
            count=len(actions),
            states=sorted(
                {vals.get("state") for vals in vals_list if vals.get("state")}
            ),
            code_histories=len(history_vals),
        )
        return actions

    def write(self, vals: dict[str, Any]) -> bool:
        if "name" in vals and not vals["name"]:
            _debug.logic("name_emptied", actions=self.ids)
            vals = {key: value for key, value in vals.items() if key != "name"}
            vals["name_is_custom"] = False
        name_decides_custom = "name" in vals and "name_is_custom" not in vals
        if name_decides_custom:
            vals = {**vals, "name_is_custom": True}
        if "code" in vals:
            new_code = vals.get("code")
            history_vals = [
                {"action_id": action.id, "code": new_code}
                for action in self
                if new_code != action.code
            ]
            _debug.lifecycle(
                "code_history", actions=len(self), changed=len(history_vals)
            )
            if history_vals:
                self.env["ir.actions.server.history"].create(history_vals)
        _debug.lifecycle("write", count=len(self), fields=list(vals))
        res = super().write(vals)
        if name_decides_custom:
            self._release_automated_names()
        return res

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        default = default or {}
        vals_list = super().copy_data(default=default)
        for vals in vals_list:
            if not default.get("name"):
                vals["name"] = _("%s (copy)", vals.get("name", ""))
            vals["name_is_custom"] = True
        return vals_list

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )

    # COMPUTE METHODS

    @api.depends("state", "code")
    def _compute_show_code_history(self) -> None:
        self.show_code_history = False
        code_actions = self.filtered(lambda a: a.state == "code")
        if not code_actions:
            return

        History = self.env["ir.actions.server.history"].sudo()
        all_history = History.search_fetch(
            [("action_id", "in", code_actions.ids)],
            ["action_id", "code"],
        )

        action_codes = {a.id: a.code for a in code_actions}
        actions_with_diff = set()
        for hist in all_history:
            aid = hist.action_id.id
            if aid not in actions_with_diff and hist.code != action_codes.get(aid):
                actions_with_diff.add(aid)

        for action in code_actions:
            action.show_code_history = action.id in actions_with_diff

    def _compute_allowed_states(self) -> None:
        self.allowed_states = [value for value, __ in self._fields["state"].selection]

    @api.depends(lambda self: self._get_fields_warning_depends())
    def _compute_warning(self) -> None:
        for action in self:
            if warnings := action._get_warning_messages():
                _debug.logic(
                    "warnings_computed",
                    action=action.id,
                    state=action.state,
                    warnings=len(warnings),
                )
                action.warning = "\n\n".join(warnings)
            else:
                action.warning = False

    @api.depends(lambda self: self._get_fields_name_depends())
    def _compute_names(self) -> None:
        self._prefetch_automated_name_sources()
        renamed = 0
        for action in self:
            action.automated_name = action._prepare_automated_name()
            if not action.name_is_custom:
                action.name = action.automated_name
                renamed += 1
        _debug.perf.count("names_computed", count=len(self), automated=renamed)

    @api.depends_context("uid")
    def _compute_available_model_ids(self) -> None:
        if not self:
            return
        with _debug.perf(
            "available_models", cr=self.env.cr, uid=self.env.uid, actions=len(self)
        ) as span:
            allowed_models = self.env["ir.model"].search(
                [
                    (
                        "model",
                        "in",
                        list(self.env["ir.model.access"]._get_models_allowed()),
                    )
                ]
            )
            span.set(models=len(allowed_models))
        self.available_model_ids = allowed_models.ids

    @api.depends("model_id", "update_path", "state", "evaluation_type")
    def _compute_crud_relations(self) -> None:
        for action in self:
            action.update_related_model_id = False
            if not (action.model_id and action.state in CRUD_STATES):
                action.crud_model_id = False
                action.update_field_id = False
            elif action.state in ("object_create", "object_copy"):
                if not action.crud_model_id:
                    action.crud_model_id = action.model_id
                action.update_field_id = False
            elif action.update_path:
                model, field = action._get_update_path_target()
                _debug.logic(
                    "crud_relations_resolved",
                    action=action.id,
                    depth=len(action.update_path.split(".")),
                    resolved=bool(field),
                )
                action.crud_model_id = model
                action.update_field_id = field
                if action.evaluation_type == "value" and field and field.relation:
                    action.update_related_model_id = action.env["ir.model"]._get_id(
                        field.relation
                    )
            else:
                action.crud_model_id = action.model_id
                action.update_field_id = False

    @api.depends("state", "model_id.model", "webhook_field_ids", "name")
    def _compute_webhook_sample_payload(self) -> None:
        self.webhook_sample_payload = False
        webhooks = self.filtered(lambda action: action.state == "webhook")
        samples = {}
        for model_name in set(webhooks.model_id.mapped("model")):
            samples[model_name] = (
                self.env[model_name].with_context(active_test=False).search([], limit=1)
            )  # noqa: E8507  loop variable is the model -- a different table each time
        _debug.perf.count("webhook_samples", actions=len(webhooks), models=len(samples))
        for model_name, actions in webhooks.grouped("model_name").items():
            sample = samples.get(model_name)
            if sample:
                sample.read(
                    list(set(actions.webhook_field_ids.mapped("name"))), load=None
                )
            for action in actions:
                if sample:
                    payload = action._get_webhook_payload(sample)
                else:
                    _debug.logic(
                        "webhook_sample_synthetic", action=action.id, model=model_name
                    )
                    payload = action._get_webhook_payload(self.env[model_name])
                    payload["_id"] = payload["id"] = 1
                    for field in action.webhook_field_ids:
                        payload[field.name] = WEBHOOK_SAMPLE_VALUES.get(
                            field.ttype, WEBHOOK_SAMPLE_VALUES[None]
                        )
                action.webhook_sample_payload = action._dump_webhook_payload(
                    payload, indent=True
                )

    @api.depends("evaluation_type", "update_field_id.ttype")
    def _compute_value_field_to_show(self) -> None:
        for action in self:
            if action.evaluation_type == "sequence":
                action.value_field_to_show = "sequence_id"
            elif action.evaluation_type == "equation":
                action.value_field_to_show = "value"
            elif action.update_field_id.ttype in (
                "one2many",
                "many2one",
                "many2many",
            ):
                action.value_field_to_show = "resource_ref"
            elif action.update_field_id.ttype == "selection":
                action.value_field_to_show = "selection_value"
            elif action.update_field_id.ttype == "boolean":
                action.value_field_to_show = "update_boolean_value"
            elif action.update_field_id.ttype == "html":
                action.value_field_to_show = "html_value"
            else:
                action.value_field_to_show = "value"

    # INVERSE METHODS

    @api.onchange("crud_model_id")
    def _inverse_crud_model_id(self) -> None:
        invalid = self.filtered(
            lambda a: (
                a.state == "object_copy"
                and a.resource_ref
                and a.resource_ref._name != a.crud_model_id.model
            )
        )
        invalid.resource_ref = False
        _debug.logic("crud_model_changed", actions=self.ids, cleared_refs=len(invalid))
        invalid = self.filtered(
            lambda a: (
                a.link_field_id
                and not (
                    a.link_field_id.model == a.model_id.model
                    and a.link_field_id.relation == a.crud_model_id.model
                )
            )
        )
        invalid.link_field_id = False

    @api.onchange("resource_ref")
    def _inverse_resource_ref(self) -> None:
        for action in self.filtered(
            lambda action: action.value_field_to_show == "resource_ref"
        ):
            if action.resource_ref:
                action.value = str(action.resource_ref.id)

    @api.onchange("selection_value")
    def _inverse_selection_value(self) -> None:
        for action in self.filtered(
            lambda action: action.value_field_to_show == "selection_value"
        ):
            if action.selection_value:
                action.value = action.selection_value.value

    # ONCHANGE METHODS

    @api.onchange("name")
    def _onchange_name(self) -> None:
        self.name_is_custom = bool(self.name) and (
            self.name != self._prepare_automated_name()
        )
        if not self.name:
            self.automated_name = self._prepare_automated_name()
            self.name = self.automated_name

    # ACTION METHODS

    def action_view_code_history(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": _("Code History"),
            "target": "new",
            "views": [(False, "form")],
            "res_model": "server.action.history.wizard",
            "context": {"default_action_id": self.id},
        }

    def action_view_parent_action(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "target": "current",
            "views": [[False, "form"]],
            "res_model": self._name,
            "res_id": self.parent_id.id,
        }

    def action_view_scheduled_action(self) -> dict[str, Any]:
        self.check_singleton()
        if not self.ir_cron_ids:
            _debug.logic("scheduled_action_missing", action=self.id)
            raise UserError(
                _("No scheduled action is associated with this server action.")
            )
        return {
            "type": "ir.actions.act_window",
            "target": "current",
            "views": [[False, "form"]],
            "res_model": "ir.cron",
            "res_id": self.ir_cron_ids[:1].id,
        }

    # RUN METHODS

    def _is_batchable(self) -> bool:
        self.check_singleton()
        if self.state == "multi":
            return bool(self.child_ids) and all(
                child._is_batchable() for child in self.child_ids
            )
        if self.state == "object_write":
            return self.evaluation_type == "value"
        return False

    @api.model
    def _get_states_needing_a_live_record(self) -> frozenset[str]:
        return frozenset((*CRUD_STATES, "webhook"))

    def _is_live_record_required(self) -> bool:
        self.check_singleton()
        if self.state not in self._get_states_needing_a_live_record():
            return False
        if self.state in ("object_create", "object_copy"):
            return bool(self.link_field_id)
        return True

    def _resolve_runner(self) -> tuple[Callable | None, bool]:
        self.check_singleton()
        model_class = self.env.registry[self._name]
        fn = getattr(model_class, f"_run_action_{self.state}", None)
        fn_multi = getattr(model_class, f"_run_action_{self.state}_multi", None)
        batches_itself = self.state in ("multi", "object_write")
        if fn_multi is None and batches_itself:
            fn_multi = fn
        if fn_multi and (not batches_itself or self._is_batchable()):
            return fn_multi, True
        if _debug.logic.enabled and fn_multi:
            _debug.logic("batch_runner_declined", action=self.id, state=self.state)
        return fn, False

    def _run_action_code_multi(self, eval_context: dict[str, Any]) -> Any:
        if not self.code:
            _debug.logic("action_code_skipped", action=self.id, reason="no_code")
            return None
        with _debug.perf(
            "action_code", cr=self.env.cr, action=self.id, name=self.name
        ) as span:
            safe_eval(self.code.strip(), eval_context, mode="exec", filename=str(self))
            span.set(returned_action=eval_context.get("action") is not None)
        return eval_context.get("action")

    def _run_action_multi(self, eval_context: dict[str, Any] | None = None) -> Any:
        res = False
        children = self.child_ids.sorted()
        if (env := (eval_context or {}).get("env")) is not None:
            children = children.with_env(env)
        _debug.pipeline("action_multi", action=self.id, children=children.ids)
        for act in children:
            res = act.run() or res
        _debug.pipeline(
            "action_multi_done",
            action=self.id,
            children=len(children),
            returned_action=bool(res),
        )
        return res

    def _get_records_from_eval_context(
        self, eval_context: dict[str, Any] | None
    ) -> Any:
        records = (eval_context or {}).get("records")
        if records is None:
            _debug.logic("records_from_context", action=self.id, source="targeted")
            return self._get_records_targeted()
        return records

    def _run_action_object_write(
        self, eval_context: dict[str, Any] | None = None
    ) -> None:
        self._write_update_path(
            self._get_records_from_eval_context(eval_context),
            self._eval_value(eval_context=eval_context),
        )

    def _write_update_path(self, records: Any, vals: dict[int, Any]) -> None:
        self.check_singleton()
        if not self.update_path:
            _debug.logic("update_path_refused", action=self.id, reason="no_path")
            raise UserError(
                _(
                    "The 'Update Record' action '%(name)s' has no field to update. "
                    "Please set an update path.",
                    name=self.name,
                )
            )
        path = self.update_path.split(".")
        value = {self.update_field_id.name: vals[self.id]}

        if record_cached := self.env.context.get("onchange_self"):
            _debug.logic(
                "update_path_target",
                action=self.id,
                by="onchange_self",
                depth=len(path),
            )
            if len(path) > 1:
                raise UserError(
                    _(
                        "The 'Update Record' action '%(name)s' updates "
                        "'%(path)s', which lives on another record. An "
                        "on-change action may only touch the record being "
                        "edited.",
                        name=self.name,
                        path=self.update_path,
                    )
                )
            record_cached.update(value)
            return

        targets = records.mapped(".".join(path[:-1])) if len(path) > 1 else records
        _debug.logic(
            "update_path_target",
            action=self.id,
            by="records",
            depth=len(path),
            records=len(records),
            targets=len(targets),
        )
        targets.write(value)

    def _run_action_webhook(self, eval_context: dict[str, Any] | None = None) -> None:
        record = self._get_records_from_eval_context(eval_context)[:1]
        url = self.webhook_url
        if not record:
            _debug.logic("webhook_skipped", action=self.id, reason="no_record")
            return
        if not url:
            _debug.logic("webhook_skipped", action=self.id, reason="no_url")
            raise UserError(
                _(
                    "The webhook action '%(name)s' has no URL to send the request "
                    "to. Please set a Webhook URL.",
                    name=self.name,
                )
            )
        try:
            self.env["ir.egress"].check_url(url)
            blocked = None
        except DestinationRefused as refusal:
            blocked = str(refusal)
        _debug.logic(
            "webhook_guard",
            phase="action",
            action=self.id,
            target=webhook.get_log_target(url),
            blocked=blocked,
        )
        if blocked:
            raise UserError(
                _(
                    "The webhook action '%(name)s' targets a forbidden address "
                    "(%(reason)s). Webhooks may only call public hosts.",
                    name=self.name,
                    reason=blocked,
                )
            )
        payload = self._get_webhook_payload(record)
        json_values = self._dump_webhook_payload(payload)

        action_label = payload["_action"]
        timeout = self.webhook_timeout
        target = webhook.get_log_target(url)

        _logger.info("Webhook %s to %s", action_label, target)
        _logger.debug("POST JSON data for webhook call: %s", json_values)
        _debug.pipeline(
            "webhook_scheduled",
            action=self.id,
            target=target,
            payload_bytes=len(json_values),
            timeout=timeout,
        )
        deliver = self._prepare_webhook_delivery(url, timeout, action_label, target)

        @self.env.cr.postrollback.add
        def _warn_webhook_rolled_back():
            _debug.lifecycle("webhook_cancelled", target=target, reason="rollback")
            _logger.warning(
                "Webhook %s to %s cancelled: the transaction rolled back",
                action_label,
                target,
            )

        @self.env.cr.postcommit.add
        def _deliver_webhook_after_commit():
            deliver(json_values)

    def _link_to_active_record(
        self, new_id: int, eval_context: dict[str, Any] | None = None
    ) -> None:
        if not self.link_field_id:
            _debug.logic("link_skipped_no_field", action=self.id, new_id=new_id)
            return
        record = self._get_records_from_eval_context(eval_context)[:1]
        if not record:
            _debug.logic("link_skipped_no_record", action=self.id, new_id=new_id)
            return
        _debug.lifecycle(
            "record_linked",
            action=self.id,
            record=record.id,
            field=self.link_field_id.name,
            new_id=new_id,
        )
        if self.link_field_id.ttype in ("one2many", "many2many"):
            record.write({self.link_field_id.name: [Command.link(new_id)]})
        else:
            record.write({self.link_field_id.name: new_id})

    def _run_action_object_copy(
        self, eval_context: dict[str, Any] | None = None
    ) -> None:
        if not self.resource_ref:
            _debug.logic("copy_refused", action=self.id, reason="no_resource_ref")
            raise UserError(_("No record selected to duplicate."))
        with _debug.perf(
            "action_copy", cr=self.env.cr, action=self.id, source=self.resource_ref
        ) as span:
            dupe = self.resource_ref.copy()
            span.set(new_id=dupe.id)
        self._link_to_active_record(dupe.id, eval_context)

    def _run_action_object_create(
        self, eval_context: dict[str, Any] | None = None
    ) -> None:
        with _debug.perf(
            "action_create",
            cr=self.env.cr,
            action=self.id,
            model=self.crud_model_id.model,
        ) as span:
            res_id, _res_name = self.env[self.crud_model_id.model].name_create(
                self.value
            )
            span.set(new_id=res_id)
        self._link_to_active_record(res_id, eval_context)

    def _prepare_eval_context(self, action: Self) -> dict[str, Any]:

        def log(message, level="info"):
            with self.pool.cursor() as cr:
                cr.execute(
                    """
                    INSERT INTO ir_logging(create_date, create_uid, type, dbname, name, level, message, path, line, func)
                    VALUES (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        self.env.uid,
                        "server",
                        self.env.cr.dbname,
                        __name__,
                        level,
                        message,
                        "action",
                        action.id,
                        action.name,
                    ),
                )

        eval_context = super()._prepare_eval_context(action=action)
        model_name = action.model_id.sudo().model
        model = self.env[model_name]
        targets = self._get_records_targeted(action)
        records = targets or None
        record = targets[:1] or None
        if onchange_self := self.env.context.get("onchange_self"):
            record = onchange_self
        _debug.pipeline(
            "eval_context_prepared",
            action=action.id,
            model=model_name,
            records=len(targets),
            onchange=onchange_self is not None,
        )
        eval_context.update(
            {
                "env": self.env,
                "model": model,
                "UserError": UserError,
                "record": record,
                "records": records,
                "log": log,
                "_logger": _LOGGER_PROXY,
            }
        )
        return eval_context

    def _get_records_targeted(self, action: Self | None = None) -> Any:
        action = action or self
        model = self.env[action.sudo().model_name]
        context = self.env.context
        if context.get("active_model") != model._name:
            if onchange_self := context.get("onchange_self"):
                if onchange_self._name == model._name:
                    return model.browse(onchange_self._origin.id or ())
            _debug.logic(
                "targets_model_mismatch",
                action=action.id,
                model=model._name,
                active_model=context.get("active_model"),
            )
            return model
        if active_ids := context.get("active_ids"):
            _debug.logic(
                "targets_resolved",
                action=action.id,
                by="active_ids",
                count=len(active_ids),
            )
            return model.browse(active_ids)
        if active_id := context.get("active_id"):
            _debug.logic("targets_resolved", action=action.id, by="active_id")
            return model.browse(active_id)
        if onchange_self := context.get("onchange_self"):
            _debug.logic("targets_resolved", action=action.id, by="onchange_self")
            return model.browse(onchange_self._origin.id or ())
        _debug.logic("targets_resolved", action=action.id, by="none")
        return model

    def run(self) -> dict[str, Any] | bool:
        res = False
        for action in self.sudo():
            eval_context = self._prepare_eval_context(action)
            records = eval_context["records"]
            if records is None:
                records = eval_context["model"]
            action.sudo(self.env.su)._check_access_to_run(records)
            with _debug.perf(
                "run",
                cr=self.env.cr,
                action=action.id,
                state=action.state,
                model=records._name,
                records=len(records),
                uid=self.env.uid,
            ):
                res = action._run(records, eval_context)
        return res

    def _log_missing_target(self, runner: Any) -> None:
        _debug.logic(
            "run_skipped",
            action=self.id,
            state=self.state,
            runner=runner.__name__,
            reason="no_target",
        )
        _logger.warning(
            "Server action %r (type %r) was triggered with no target record "
            "(no active_id/active_ids in context, or they name another model); "
            "its %s runner needs one and will be skipped.%s",
            self.name,
            self.state,
            runner.__name__,
            " It is the 'Link Field' that needs one; clear that field and the "
            "action runs on its own."
            if self.state in ("object_create", "object_copy")
            else "",
        )

    def _run(self, records: Any, eval_context: dict[str, Any]) -> dict[str, Any] | bool:
        self.check_singleton()
        if self.warning:
            _debug.logic("run_refused", action=self.id, reason="warnings")
            raise ServerActionWithWarningsError(
                _(
                    "Server action %(action_name)s has one or more warnings, address them first.",
                    action_name=self.name,
                )
            )

        runner, multi = self._resolve_runner()
        _debug.logic(
            "runner_resolved",
            action=self.id,
            state=self.state,
            runner=runner.__name__ if runner else None,
            multi=multi,
            records=len(records),
        )
        if not runner:
            _logger.warning(
                "Found no way to execute server action %r of type %r, ignoring it. "
                "Verify that the type is correct or add a method called "
                "`_run_action_<type>` or `_run_action_<type>_multi`.",
                self.name,
                self.state,
            )
            return False

        if (
            not records
            and not self.env.context.get("onchange_self")
            and self._is_live_record_required()
        ):
            self._log_missing_target(runner)
            return False

        if multi:
            run_self = self.with_context(eval_context["env"].context)
            return runner(run_self, eval_context=eval_context) or False

        if not records:
            _debug.logic("run_without_records", action=self.id, state=self.state)
            return runner(self, eval_context=eval_context) or False

        res = False
        _debug.pipeline(
            "run_per_record", action=self.id, state=self.state, records=len(records)
        )
        for record in records:
            run_self = self.with_context(active_ids=record.ids, active_id=record.id)
            env = eval_context["env"](context=run_self.env.context)
            eval_context["env"] = env
            if (model := eval_context.get("model")) is not None:
                eval_context["model"] = model.with_env(env)
            eval_context["records"] = eval_context["record"] = record.with_env(env)
            res = runner(run_self, eval_context=eval_context)
        return res or False

    def _check_access_to_run(self, records: Any) -> None:
        self.check_singleton()
        config = self.sudo()

        action_groups = config.group_ids
        if action_groups:
            if not (action_groups & self.env.user.sudo().all_group_ids):
                _debug.logic(
                    "run_denied", action=self.id, uid=self.env.uid, by="groups"
                )
                raise AccessError(
                    _("You don't have enough access rights to run this action.")
                )
        else:
            self._check_access_to_model_and_records(records)
        self._check_access_to_crud_targets(records)

    def _check_access_to_model_and_records(self, records: Any) -> None:
        config = self.sudo()
        model_name = config.model_id.model
        try:
            self.env[model_name].check_access("write")
        except AccessError:
            _debug.logic(
                "run_denied", action=self.id, uid=self.env.uid, by="model_write"
            )
            _logger.warning(
                "Forbidden server action %r executed while the user %s does not have access to %s.",
                config.name,
                self.env.user.login,
                model_name,
            )
            raise

        if records.ids:
            try:
                records.check_access("write")
            except AccessError:
                _debug.logic(
                    "run_denied",
                    action=self.id,
                    uid=self.env.uid,
                    by="record_write",
                    records=len(records),
                )
                _logger.warning(
                    "Forbidden server action %r executed while the user %s does not have access to %s.",
                    config.name,
                    self.env.user.login,
                    records,
                )
                raise

    def _check_access_to_crud_targets(self, records: Any) -> None:
        config = self.sudo()
        if config.state not in CRUD_STATES:
            return
        _debug.logic(
            "crud_access_checked",
            action=self.id,
            state=config.state,
            records=len(records),
            linked=bool(config.link_field_id),
        )
        if config.state == "object_write":
            records.check_access("write")
            return
        if config.state == "object_create":
            self.env[config.crud_model_id.model].check_access("create")
        elif config.resource_ref:
            source = self.env[config.resource_ref._name].browse(config.resource_ref.id)
            source.check_access("read")
            self.env[source._name].check_access("create")
        if config.link_field_id:
            records.check_access("write")

    # WEBHOOK METHODS

    def _get_webhook_payload(self, record: models.Model) -> dict[str, Any]:
        self.check_singleton()
        payload = {
            "_model": self.model_id.model,
            "_id": record.id,
            "_action": f"{self.name}(#{self.id})",
        }
        if self.webhook_field_ids and record:
            payload.update(
                record.read(self.webhook_field_ids.mapped("name"), load=None)[0]
            )
        payload["id"] = record.id
        _debug.pipeline(
            "webhook_payload_built",
            action=self.id,
            record=record.id,
            fields=len(self.webhook_field_ids),
        )
        return payload

    def _dump_webhook_payload(
        self, payload: dict[str, Any], indent: bool = False
    ) -> str:
        option = OPT_SORT_KEYS | (OPT_INDENT_2 if indent else 0)
        return json_dumps(payload, default=_webhook_json_default, option=option)

    def _prepare_webhook_delivery(self, url, timeout, action_label, target):
        return partial(
            webhook.deliver,
            self.env["ir.egress"].session(
                purpose="webhook", max_bytes=webhook.RESPONSE_MAX_BYTES
            ),
            url,
            timeout,
            action_label,
            target,
        )

    # HELPER METHODS

    @api.model
    def _default_update_path(self) -> str:
        if not self.env.context.get("default_model_id"):
            return ""
        ir_model = self.env["ir.model"].browse(self.env.context["default_model_id"])
        model = self.env[ir_model.model]
        sensible_default_fields = [
            "partner_id",
            "user_id",
            "user_ids",
            "stage_id",
            "state",
            "active",
        ]
        for field_name in sensible_default_fields:
            if field_name in model._fields and not model._fields[field_name].readonly:
                _debug.logic("default_update_path", model=model._name, field=field_name)
                return field_name
        _debug.logic("default_update_path", model=model._name, field=None)
        return ""

    def _release_automated_names(self) -> None:
        self._prefetch_automated_name_sources()
        for action in self:
            if (
                action.name_is_custom
                and action.name == action._prepare_automated_name()
            ):
                _debug.logic("automated_name_released", action=action.id)
                action.name_is_custom = False

    @api.model
    def _get_fields_warning_depends(self) -> list[str]:
        return [
            "state",
            "model_id",
            "group_ids",
            "parent_id",
            "child_ids.warning",
            "child_ids.model_id",
            "child_ids.group_ids",
            "update_path",
            "update_field_type",
            "evaluation_type",
            "sequence_id",
            "webhook_field_ids",
            "usage",
        ]

    def _get_child_warnings(self) -> list[str]:
        self.check_singleton()
        warnings = []
        children_wrong_model = self.env["ir.actions.server"]
        children_wrong_groups = self.env["ir.actions.server"]
        children_with_warnings = self.env["ir.actions.server"]
        for child in self.child_ids:
            if self.model_id and child.model_id != self.model_id:
                children_wrong_model |= child
            if self.group_ids and child.group_ids != self.group_ids:
                children_wrong_groups |= child
            if child.warning:
                children_with_warnings |= child
        if _debug.logic.enabled and (
            children_wrong_model or children_wrong_groups or children_with_warnings
        ):
            _debug.logic(
                "child_warnings",
                action=self.id,
                children=len(self.child_ids),
                wrong_model=len(children_wrong_model),
                wrong_groups=len(children_wrong_groups),
                with_warnings=len(children_with_warnings),
            )

        if children_wrong_model:
            warnings.append(
                _(
                    "Following child actions should have the same model (%(model)s): %(children)s",
                    model=self.model_id.name,
                    children=", ".join(children_wrong_model.mapped("name")),
                )
            )

        if children_wrong_groups:
            warnings.append(
                _(
                    "Following child actions should have the same groups (%(groups)s): %(children)s",
                    groups=", ".join(self.group_ids.mapped("name")),
                    children=", ".join(children_wrong_groups.mapped("name")),
                )
            )

        if children_with_warnings:
            warnings.append(
                _(
                    "Following child actions have warnings: %(children)s",
                    children=", ".join(children_with_warnings.mapped("name")),
                )
            )
        return warnings

    def _get_warning_messages(self) -> list[str]:
        self.check_singleton()
        warnings = self._get_child_warnings()

        relation_chain = (
            self._get_relation_chain("update_path")
            if self.state == "object_write"
            else []
        )
        if relation_chain and isinstance(relation_chain[-1], fields.Json):
            warnings.append(
                _(
                    "JSON fields (such as '%s') are not supported.",
                    relation_chain[-1].string,
                )
            )

        if self.usage == "ir_cron" and self._is_live_record_required():
            _debug.logic("cron_needs_record", action=self.id, state=self.state)
            warnings.append(
                _(
                    "A scheduled action runs on no record, and this one needs "
                    "one to act on. It would do nothing, every time it ran."
                )
            )

        if self.state == "object_write" and self.evaluation_type == "sequence":
            if self.update_field_type and self.update_field_type not in (
                "char",
                "text",
            ):
                warnings.append(
                    _("A sequence must only be used with character fields.")
                )
            if not self.sequence_id:
                _debug.logic("sequence_missing", action=self.id)
                warnings.append(_("Choose the sequence the value is drawn from."))

        if self.state == "webhook" and self.model_id:
            restricted_fields = []
            Model = self.env[self.model_id.model]
            for model_field in self.webhook_field_ids:
                field = Model._fields.get(model_field.name)
                if field and field.groups:
                    restricted_fields.append(f"- {model_field.field_description}")
            if restricted_fields:
                _debug.logic(
                    "webhook_fields_restricted",
                    action=self.id,
                    restricted=len(restricted_fields),
                    total=len(self.webhook_field_ids),
                )
                warnings.append(
                    _(
                        "Group-restricted fields cannot be included in "
                        "webhook payloads, as it could allow any user to "
                        "accidentally leak sensitive information. You will "
                        "have to remove the following fields from the webhook payload:\n%(restricted_fields)s",
                        restricted_fields="\n".join(restricted_fields),
                    )
                )

        return warnings

    @api.model
    def _get_domain_children(self) -> Domain:
        return Domain(
            [
                ("model_id", "=", unquote("model_id")),
                ("parent_id", "=", False),
                ("id", "!=", unquote("id")),
            ]
        )

    def _prepare_automated_name(self) -> str:
        self.check_singleton()
        if self.state == "object_create":
            return _("Create %(model_name)s", model_name=self.crud_model_id.name)
        if self.state == "object_write":
            return _("Update %(model_name)s", model_name=self.crud_model_id.name)
        if self.state == "object_copy":
            if not self.resource_ref:
                return _("Duplicate ...")
            return _("Duplicate %(record)s", record=self.resource_ref.display_name)
        return dict(self._fields["state"]._description_selection(self.env)).get(
            self.state, ""
        )

    @api.model
    def _get_fields_name_depends(self) -> list[str]:
        return [
            "state",
            "crud_model_id",
            "resource_ref",
            "name_is_custom",
        ]

    def _prefetch_automated_name_sources(self) -> None:
        by_model = {}
        for action in self:
            reference = action.resource_ref if action.state == "object_copy" else None
            if reference:
                by_model.setdefault(reference._name, []).append(reference.id)
        for model_name, ids in by_model.items():
            self.env[model_name].browse(ids).mapped("display_name")

    def _get_update_path_target(
        self,
    ) -> tuple[models.Model | Literal[False], models.Model | Literal[False]]:
        self.check_singleton()
        field_chain = self._get_relation_chain("update_path")
        if not field_chain:
            return False, False
        last_field = field_chain[-1]
        model_id = self.env["ir.model"]._get(last_field.model_name)
        field_id = self.env["ir.model.fields"]._get(
            last_field.model_name, last_field.name
        )
        return model_id, field_id

    def _get_relation_chain(
        self, searched_field_name: str, raise_on_error: bool = False
    ) -> list[fields.Field]:
        self.check_singleton()
        if (
            not searched_field_name
            or searched_field_name not in self._fields
            or not self[searched_field_name]
            or not self.model_id
        ):
            return []
        path = self[searched_field_name].split(".")
        model = self.env[self.model_id.model]
        chain = []
        for i, field_name in enumerate(path):
            is_last_field = i == len(path) - 1
            if not field_name:
                _debug.logic(
                    "relation_chain_broken",
                    action=self.id,
                    field=searched_field_name,
                    segment=i,
                    reason="empty_segment",
                )
                if raise_on_error:
                    raise ValidationError(
                        _(
                            "The path '%(path)s' contains an empty segment. "
                            "Remove the extra '.'.",
                            path=self[searched_field_name],
                        )
                    )
                return []
            if field_name not in model._fields:
                _debug.logic(
                    "relation_chain_broken",
                    action=self.id,
                    field=searched_field_name,
                    segment=i,
                    model=model._name,
                    reason="unknown_field",
                )
                if raise_on_error:
                    raise ValidationError(
                        _(
                            "Unknown field '%(field_name)s' on model '%(model_name)s'.",
                            field_name=field_name,
                            model_name=model._name,
                        )
                    )
                return []
            field = model._fields[field_name]
            if not is_last_field:
                if not field.relational:
                    _debug.logic(
                        "relation_chain_broken",
                        action=self.id,
                        field=searched_field_name,
                        segment=i,
                        model=model._name,
                        reason="non_relational",
                    )
                    if raise_on_error:
                        current_field = field.get_description(self.env)["string"]
                        searched_field = self._fields[
                            searched_field_name
                        ].get_description(self.env)["string"]
                        raise ValidationError(
                            _(
                                "The path in field '%(searched_field)s' contains a non-relational field (%(current_field)s) that is not the last segment. Only the last field in a path may be non-relational.",
                                searched_field=searched_field,
                                current_field=current_field,
                            )
                        )
                    return []
                model = self.env[field.comodel_name]
            chain.append(field)
        _debug.logic(
            "relation_chain_resolved",
            action=self.id,
            field=searched_field_name,
            depth=len(chain),
            target=model._name,
        )
        return chain

    def _get_relation_chain_label(self, chain: list[fields.Field]) -> str:
        return " > ".join(field.get_description(self.env)["string"] for field in chain)

    def _get_field_target_model(self) -> str:
        return "model_name"

    def _get_field_groups(self) -> str:
        return "group_ids"

    def _get_fields_binding_extra(self) -> tuple[str, ...]:
        return ("group_ids",)

    def _get_fields_readable(self) -> frozenset[str]:
        return super()._get_fields_readable() | {
            "group_ids",
            "model_name",
        }

    @api.model
    @tools.ormcache("self.env.lang")
    def _selection_target_model(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (model.model, model.name)
            for model in self.env["ir.model"].sudo().search([])
        )

    def _coerce_number(self, converter: Any) -> Any:
        self.check_singleton()
        try:
            return converter(self.value)
        except ValueError, TypeError:
            _debug.logic(
                "value_coercion_refused",
                action=self.id,
                converter=converter.__name__,
                field=self.update_field_id.name,
            )
            raise UserError(
                _(
                    "The value '%(value)s' configured on action '%(action)s' is not a "
                    "valid number for field '%(field)s'.",
                    value=self.value,
                    action=self.name,
                    field=self.update_field_id.field_description,
                )
            ) from None

    def _eval_value(self, eval_context: dict[str, Any] | None = None) -> dict[int, Any]:
        result = {}
        for action in self:
            expr = action.value
            if action.evaluation_type == "equation":
                expr = safe_eval(action.value, eval_context)
            elif action.evaluation_type == "sequence":
                if not action.sequence_id:
                    _debug.logic("sequence_missing", action=action.id)
                    raise UserError(
                        _(
                            "The 'Update Record' action '%(name)s' draws its value "
                            "from a sequence, and none is chosen.",
                            name=action.name,
                        )
                    )
                expr = action.sequence_id.next_by_id()
            elif action.update_field_id.ttype in ("one2many", "many2many"):
                expr = action._prepare_x2many_commands()
            elif action.update_field_id.ttype == "boolean":
                expr = action.update_boolean_value == "true"
            elif action.update_field_id.ttype in ("many2one", "integer"):
                ttype = action.update_field_id.ttype
                if not action.value:
                    expr = False if ttype == "many2one" else 0
                else:
                    expr = action._coerce_number(int)
                    if expr == 0 and ttype == "many2one":
                        expr = False
            elif action.update_field_id.ttype == "float":
                expr = 0.0 if not action.value else action._coerce_number(float)
            elif action.update_field_id.ttype == "html":
                expr = action.html_value or action.value
            result[action.id] = expr
            _debug.logic(
                "value_evaluated",
                action=action.id,
                evaluation_type=action.evaluation_type,
                ttype=action.update_field_id.ttype,
                m2m_operation=action.update_m2m_operation,
            )
        return result

    def _prepare_x2many_commands(self) -> list:
        self.check_singleton()
        operation = self.update_m2m_operation
        if operation == "clear":
            return [Command.clear()]
        target_id = self._coerce_number(int) if self.value else 0
        if not target_id:
            return []
        match operation:
            case "add":
                return [Command.link(target_id)]
            case "remove":
                return [Command.unlink(target_id)]
            case "set":
                return [Command.set([target_id])]
        return []
