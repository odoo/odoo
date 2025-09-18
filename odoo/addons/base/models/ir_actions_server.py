import contextlib
import json
import logging
from functools import reduce
from operator import getitem
from typing import Any, Self

import babel

from odoo import api, fields, models, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.http import request
from odoo.libs.datetime import utc
from odoo.libs.json import OPT_SORT_KEYS
from odoo.libs.json import dumps as json_dumps
from odoo.tools import _, get_lang
from odoo.tools.misc import get_diff, unquote
from odoo.tools.safe_eval import safe_eval, test_python_expr
from odoo.orm._typing import ValuesType

_logger = logging.getLogger(__name__)
# Use original module path to preserve logger name for tests/monitoring
_server_action_logger = logging.getLogger(
    "odoo.addons.base.models.ir_actions.server_action_safe_eval"
)


class LoggerProxy:
    """Proxy of the `_logger` element in order to be used in server actions.
    We purposefully restrict its method as it will be executed in `safe_eval`.
    """

    @staticmethod
    def log(
        level: int,
        message: str,
        *args: Any,
        stack_info: bool = False,
        exc_info: bool = False,
    ) -> None:
        _server_action_logger.log(
            level, message, *args, stack_info=stack_info, exc_info=exc_info
        )

    @staticmethod
    def info(
        message: str,
        *args: Any,
        stack_info: bool = False,
        exc_info: bool = False,
    ) -> None:
        _server_action_logger.info(
            message, *args, stack_info=stack_info, exc_info=exc_info
        )

    @staticmethod
    def warning(
        message: str,
        *args: Any,
        stack_info: bool = False,
        exc_info: bool = False,
    ) -> None:
        _server_action_logger.warning(
            message, *args, stack_info=stack_info, exc_info=exc_info
        )

    @staticmethod
    def error(
        message: str,
        *args: Any,
        stack_info: bool = False,
        exc_info: bool = False,
    ) -> None:
        _server_action_logger.error(
            message, *args, stack_info=stack_info, exc_info=exc_info
        )

    @staticmethod
    def exception(
        message: str,
        *args: Any,
        stack_info: bool = False,
        exc_info: bool = True,
    ) -> None:
        _server_action_logger.exception(
            message, *args, stack_info=stack_info, exc_info=exc_info
        )


class ServerActionHistoryWizard(models.TransientModel):
    """A wizard to compare and reset server action code."""

    _name = "server.action.history.wizard"
    _description = "Server Action History Wizard"

    @api.model
    def _default_revision(self) -> Self:
        action_id = self.env["ir.actions.server"].browse(
            self.env.context.get("default_action_id", False)
        )
        return self.env["ir.actions.server.history"].search(
            [
                ("action_id", "=", action_id.id),
                ("code", "!=", action_id.code),
            ],
            limit=1,
        )

    action_id = fields.Many2one("ir.actions.server")
    code_diff = fields.Html(compute="_compute_code_diff", sanitize_tags=False)
    current_code = fields.Text(related="action_id.code", readonly=True)
    revision = fields.Many2one(
        "ir.actions.server.history",
        domain="[('action_id', '=', action_id), ('code', '!=', current_code)]",
        default=_default_revision,
        required=True,
    )

    @api.depends("revision")
    def _compute_code_diff(self) -> None:
        for wizard in self:
            rev_code = wizard.revision.code
            actual_code = wizard.action_id.code
            has_diff = actual_code != rev_code
            wizard.code_diff = (
                get_diff(
                    (actual_code or "", _("Actual Code")),
                    (rev_code or "", _("Revision Code")),
                    dark_color_scheme=request
                    and request.cookies.get("color_scheme") == "dark",
                )
                if has_diff
                else False
            )

    def restore_revision(self) -> None:
        self.ensure_one()
        self.action_id.code = self.revision.code


class IrActionsServerHistory(models.Model):
    _name = "ir.actions.server.history"
    _description = "Server Action History"
    _order = "create_date desc, id desc"
    _max_entries_per_action = 100

    action_id = fields.Many2one("ir.actions.server", required=True, ondelete="cascade")
    code = fields.Text()

    def _compute_display_name(self) -> None:
        self.display_name = False
        for history in self.filtered("create_date"):
            locale = get_lang(self.env).code
            tzinfo = self.env.tz
            datetime = history.create_date.replace(microsecond=0)
            datetime = datetime.replace(tzinfo=utc)
            datetime = datetime.astimezone(tzinfo) if tzinfo else datetime
            date_label = babel.dates.format_datetime(
                datetime,
                tzinfo=tzinfo,
                locale=locale,
            )
            author = history.create_uid.name
            history.display_name = _(
                "%(date_label)s - %(author)s",
                date_label=date_label,
                author=author,
            )

    @api.autovacuum
    def _gc_histories(self) -> None:
        result = self._read_group(
            domain=[],
            groupby=["action_id"],
            aggregates=["id:recordset"],
            having=[("__count", ">", self._max_entries_per_action)],
        )
        to_clean = self
        for _action_id, history_ids in result:
            to_clean |= history_ids.sorted()[self._max_entries_per_action :]
        to_clean.unlink()


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


class ServerActionWithWarningsError(UserError):
    """Exception raised when a server action that has warnings is run."""

    pass


class IrActionsServer(models.Model):
    """Server actions model. Server action work on a base model and offer various
    type of actions that can be executed automatically, for example using base
    action rules, of manually, by adding the action in the 'More' contextual
    menu.

    Since Odoo 8.0 a button 'Create Menu Action' button is available on the
    action form view. It creates an entry in the More menu of the base model.
    This allows to create server actions and run them in mass mode easily through
    the interface.

    The available actions are :

    - 'Execute Python Code': a block of python code that will be executed
    - 'Create a new Record': create a new record with new values
    - 'Write on a Record': update the values of a record
    - 'Execute several actions': define an action that triggers several other
      server actions
    """

    _name = "ir.actions.server"
    _description = "Server Actions"
    _table = "ir_act_server"
    _inherit = ["ir.actions.actions"]
    _order = "sequence,name,id"
    _allow_sudo_commands = False

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
                return field_name
        return ""

    name = fields.Char(compute="_compute_name", store=True, readonly=False)
    automated_name = fields.Char(compute="_compute_name", store=True)
    type = fields.Char(default="ir.actions.server")
    usage = fields.Selection(
        [
            ("ir_actions_server", "Server Action"),
            ("ir_cron", "Scheduled Action"),
        ],
        string="Usage",
        default="ir_actions_server",
        required=True,
    )
    state = fields.Selection(
        [
            ("object_write", "Update Record"),
            ("object_create", "Create Record"),
            ("object_copy", "Duplicate Record"),
            ("code", "Execute Code"),
            ("webhook", "Send Webhook Notification"),
            ("multi", "Multi Actions"),
        ],
        string="Type",
        required=True,
        copy=True,
        help="Type of server action. The following values are available:\n"
        "- 'Update a Record': update the values of a record\n"
        "- 'Create Activity': create an activity (Discuss)\n"
        "- 'Send Email': post a message, a note or send an email (Discuss)\n"
        "- 'Send SMS': send SMS, log them on documents (SMS)"
        "- 'Add/Remove Followers': add or remove followers to a record (Discuss)\n"
        "- 'Create Record': create a new record with new values\n"
        "- 'Execute Code': a block of Python code that will be executed\n"
        "- 'Send Webhook Notification': send a POST request to an external system, also known as a Webhook\n"
        "- 'Multi Actions': define an action that triggers several other server actions\n",
    )
    allowed_states = fields.Json(
        string="Allowed states", compute="_compute_allowed_states"
    )
    # Generic
    sequence = fields.Integer(
        default=5,
        help="When dealing with multiple actions, the execution order is "
        "based on the sequence. Low number means high priority.",
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        index=True,
        help="Model on which the server action runs.",
    )
    available_model_ids = fields.Many2many(
        "ir.model",
        string="Available Models",
        compute="_compute_available_model_ids",
        store=False,
    )
    model_name = fields.Char(related="model_id.model", string="Model Name")
    warning = fields.Text(string="Warning", compute="_compute_warning", recursive=True)
    # Inverse relation of ir.cron.ir_actions_server_id (has delegate=True, so either 0 or 1 cron, even if o2m field)
    ir_cron_ids = fields.One2many(
        "ir.cron",
        "ir_actions_server_id",
        "Scheduled Action",
        context={"active_test": False},
    )
    # Python code
    code = fields.Text(
        string="Python Code",
        groups="base.group_system",
        help="Write Python code that the action will execute. Some variables are "
        "available for use; help about python expression is given in the help tab.",
    )
    show_code_history = fields.Boolean(compute="_compute_show_code_history")
    # Multi
    parent_id = fields.Many2one(
        "ir.actions.server",
        string="Parent Action",
        index=True,
        ondelete="cascade",
    )
    child_ids = fields.One2many(
        "ir.actions.server",
        "parent_id",
        copy=True,
        domain=lambda self: str(self._get_children_domain()),
        string="Child Actions",
        help="Child server actions that will be executed. Note that the last return returned action value will be used as global return value.",
    )
    # Create
    crud_model_id = fields.Many2one(
        "ir.model",
        string="Record to Create",
        compute="_compute_crud_relations",
        inverse="_set_crud_model_id",
        readonly=False,
        store=True,
        help="Specify which kind of record should be created. Set this field only to specify a different model than the base model.",
    )
    crud_model_name = fields.Char(
        related="crud_model_id.model", string="Target Model Name", readonly=True
    )
    link_field_id = fields.Many2one(
        "ir.model.fields",
        string="Link Field",
        help="Specify a field used to link the newly created record on the record used by the server action.",
    )
    group_ids = fields.Many2many(
        "res.groups",
        "ir_act_server_group_rel",
        "act_id",
        "gid",
        string="Allowed Groups",
        help="Groups that can execute the server action. Leave empty to allow everybody.",
    )

    update_field_id = fields.Many2one(
        "ir.model.fields",
        string="Field to Update",
        ondelete="cascade",
        compute="_compute_crud_relations",
        store=True,
        readonly=False,
    )
    update_path = fields.Char(
        string="Field to Update Path",
        help="Path to the field to update, e.g. 'partner_id.name'",
        default=_default_update_path,
    )
    update_related_model_id = fields.Many2one(
        "ir.model",
        compute="_compute_crud_relations",
        readonly=False,
        store=True,
    )
    update_field_type = fields.Selection(related="update_field_id.ttype", readonly=True)
    update_m2m_operation = fields.Selection(
        [
            ("add", "Adding"),
            ("remove", "Removing"),
            ("set", "Setting it to"),
            ("clear", "Clearing it"),
        ],
        string="Many2many Operations",
        default="add",
    )
    update_boolean_value = fields.Selection(
        [("true", "Yes (True)"), ("false", "No (False)")],
        string="Boolean Value",
        default="true",
    )

    value = fields.Text(
        help="For Python expressions, this field may hold a Python expression "
        "that can use the same values as for the code field on the server action,"
        "e.g. `env.user.name` to set the current user's name as the value "
        "or `record.id` to set the ID of the record on which the action is run.\n\n"
        "For Static values, the value will be used directly without evaluation, e.g."
        "`42` or `My custom name` or the selected record."
    )
    evaluation_type = fields.Selection(
        [
            ("value", "Update"),
            ("sequence", "Sequence"),
            ("equation", "Compute"),
        ],
        "Value Type",
        default="value",
        change_default=True,
    )
    html_value = fields.Html()
    sequence_id = fields.Many2one("ir.sequence", string="Sequence to use")
    resource_ref = fields.Reference(
        string="Record",
        selection="_selection_target_model",
        inverse="_set_resource_ref",
    )
    selection_value = fields.Many2one(
        "ir.model.fields.selection",
        string="Custom Value",
        ondelete="cascade",
        domain='[("field_id", "=", update_field_id)]',
        inverse="_set_selection_value",
    )

    value_field_to_show = fields.Selection(
        [
            ("value", "value"),
            ("html_value", "html_value"),
            ("sequence_id", "sequence_id"),
            ("resource_ref", "reference"),
            ("update_boolean_value", "update_boolean_value"),
            ("selection_value", "selection_value"),
        ],
        compute="_compute_value_field_to_show",
    )
    # Webhook
    webhook_url = fields.Char(
        string="Webhook URL", help="URL to send the POST request to."
    )
    webhook_field_ids = fields.Many2many(
        "ir.model.fields",
        "ir_act_server_webhook_field_rel",
        "server_id",
        "field_id",
        string="Webhook Fields",
        help="Fields to send in the POST request. "
        "The id and model of the record are always sent as '_id' and '_model'. "
        "The name of the action that triggered the webhook is always sent as '_name'.",
    )
    webhook_sample_payload = fields.Text(
        string="Sample Payload", compute="_compute_webhook_sample_payload"
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        for vals in vals_list:
            if parent_id := vals.get("parent_id"):
                parent = self.browse(parent_id)
                vals["model_id"] = parent.model_id.id
                vals["group_ids"] = parent.group_ids.ids
        actions = super().create(vals_list)

        # create first history entries
        history_vals = []
        for action, vals in zip(actions, vals_list, strict=True):
            if "code" in vals:
                history_vals.append({"action_id": action.id, "code": vals.get("code")})
        if history_vals:
            self.env["ir.actions.server.history"].create(history_vals)

        return actions

    def write(self, vals: dict[str, Any]) -> bool:
        if new_code := vals.get("code"):
            history_vals = [
                {"action_id": action.id, "code": new_code}
                for action in self
                if new_code != action.code
            ]
            if history_vals:
                self.env["ir.actions.server.history"].create(history_vals)
        return super().write(vals)

    @api.depends("state", "code")
    def _compute_show_code_history(self) -> None:
        """Batch-check whether any code-type action has differing history entries."""
        self.show_code_history = False
        code_actions = self.filtered(lambda a: a.state == "code")
        if not code_actions:
            return

        # Single query: fetch all history entries for relevant actions
        History = self.env["ir.actions.server.history"]
        all_history = History.search_fetch(
            [("action_id", "in", code_actions.ids)],
            ["action_id", "code"],
        )

        # Compare in Python instead of N search_count calls
        action_codes = {a.id: a.code for a in code_actions}
        actions_with_diff = set()
        for hist in all_history:
            aid = hist.action_id.id
            if aid not in actions_with_diff and hist.code != action_codes.get(aid):
                actions_with_diff.add(aid)

        for action in code_actions:
            action.show_code_history = action.id in actions_with_diff

    @api.model
    def _warning_depends(self) -> list[str]:
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
            "webhook_field_ids",
        ]

    def _get_warning_messages(self) -> list[str]:
        self.ensure_one()
        warnings = []

        if self.model_id and (
            children_with_different_model := self.child_ids.filtered(
                lambda a: a.model_id != self.model_id
            )
        ):
            warnings.append(
                _(
                    "Following child actions should have the same model (%(model)s): %(children)s",
                    model=self.model_id.name,
                    children=", ".join(children_with_different_model.mapped("name")),
                )
            )

        if self.group_ids and (
            children_with_different_groups := self.child_ids.filtered(
                lambda a: a.group_ids != self.group_ids
            )
        ):
            warnings.append(
                _(
                    "Following child actions should have the same groups (%(groups)s): %(children)s",
                    groups=", ".join(self.group_ids.mapped("name")),
                    children=", ".join(children_with_different_groups.mapped("name")),
                )
            )

        if children_with_warnings := self.child_ids.filtered("warning"):
            warnings.append(
                _(
                    "Following child actions have warnings: %(children)s",
                    children=", ".join(children_with_warnings.mapped("name")),
                )
            )

        if (
            (relation_chain := self._get_relation_chain("update_path"))
            and relation_chain[0]
            and isinstance(relation_chain[0][-1], fields.Json)
        ):
            warnings.append(
                _(
                    "I'm sorry to say that JSON fields (such as '%s') are currently not supported.",
                    relation_chain[0][-1].string,
                )
            )

        if (
            self.state == "object_write"
            and self.evaluation_type == "sequence"
            and self.update_field_type
            and self.update_field_type not in ("char", "text")
        ):
            warnings.append(_("A sequence must only be used with character fields."))

        if self.state == "webhook" and self.model_id:
            restricted_fields = []
            Model = self.env[self.model_id.model]
            for model_field in self.webhook_field_ids:
                # you might think that the ir.model.field record holds references
                # to the groups, but that's not the case - we need to field object itself
                field = Model._fields[model_field.name]
                if field.groups:
                    restricted_fields.append(f"- {model_field.field_description}")
            if restricted_fields:
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

    def _compute_allowed_states(self) -> None:
        self.allowed_states = [value for value, __ in self._fields["state"].selection]

    @api.depends(lambda self: self._warning_depends())
    def _compute_warning(self) -> None:
        for action in self:
            if warnings := action._get_warning_messages():
                action.warning = "\n\n".join(warnings)
            else:
                action.warning = False

    @api.model
    def _get_children_domain(self) -> Domain:
        return Domain(
            [
                ("model_id", "=", unquote("model_id")),
                ("parent_id", "=", False),
                ("id", "!=", unquote("id")),
            ]
        )

    def _generate_action_name(self) -> str:
        self.ensure_one()
        if self.state == "object_create":
            return _("Create %(model_name)s", model_name=self.crud_model_id.name)
        if self.state == "object_write":
            return _("Update %(model_name)s", model_name=self.crud_model_id.name)
        if self.state == "object_copy":
            if not self.crud_model_id or not self.resource_ref:
                return _("Duplicate ...")
            record = self.env[self.crud_model_id.model].browse(self.resource_ref.id)
            return _("Duplicate %(record)s", record=record.display_name)
        return dict(self._fields["state"]._description_selection(self.env)).get(
            self.state, ""
        )

    def _name_depends(self) -> list[str]:
        return [
            "state",
            "crud_model_id",
            "resource_ref",
        ]

    @api.depends(lambda self: self._name_depends())
    def _compute_name(self) -> None:
        for action in self:
            was_automated = action.name == action.automated_name
            action.automated_name = action._generate_action_name()
            if was_automated:
                action.name = action.automated_name

    @api.onchange("name")
    def _onchange_name(self) -> None:
        if not self.name:
            self.automated_name = self._generate_action_name()
            self.name = self.automated_name

    @api.depends("state")
    def _compute_available_model_ids(self) -> None:
        allowed_models = self.env["ir.model"].search(
            [
                (
                    "model",
                    "in",
                    list(self.env["ir.model.access"]._get_allowed_models()),
                )
            ]
        )
        self.available_model_ids = allowed_models.ids

    @api.depends("model_id", "update_path", "state")
    def _compute_crud_relations(self) -> None:
        """Compute the crud_model_id and update_field_id fields.

        The crud_model_id is the model on which the action will create or update
        records. In the case of record creation, it is the same as the main model
        of the action. For record update, it will be the model linked to the last
        field in the update_path.
        This is only used for object_create and object_write actions.
        The update_field_id is the field at the end of the update_path that will
        be updated by the action - only used for object_write actions.
        """
        for action in self:
            if action.model_id and action.state in (
                "object_write",
                "object_create",
                "object_copy",
            ):
                if action.state in ("object_create", "object_copy"):
                    action.crud_model_id = action.model_id
                    action.update_field_id = False
                    action.update_path = False
                elif action.state == "object_write":
                    if action.update_path:
                        # we need to traverse relations to find the target model and field
                        model, field = action._traverse_path()
                        action.crud_model_id = model
                        action.update_field_id = field
                        need_update_model = (
                            action.evaluation_type == "value"
                            and action.update_field_id
                            and action.update_field_id.relation
                        )
                        action.update_related_model_id = (
                            action.env["ir.model"]._get_id(field.relation)
                            if need_update_model
                            else False
                        )
                    else:
                        action.crud_model_id = action.model_id
                        action.update_field_id = False
            else:
                action.crud_model_id = False
                action.update_field_id = False
                action.update_path = False

    def _traverse_path(self) -> tuple[Any, Any]:
        """Traverse the update_path to find the target model and field.

        :return: a tuple (model, field) where model is the target model and field is the target field
        """
        self.ensure_one()
        field_chain, _field_chain_str = self._get_relation_chain("update_path")
        if not field_chain:
            return False, False
        last_field = field_chain[-1]
        model_id = self.env["ir.model"]._get(last_field.model_name)
        field_id = self.env["ir.model.fields"]._get(
            last_field.model_name, last_field.name
        )
        return model_id, field_id

    def _get_relation_chain(self, searched_field_name: str) -> tuple[list[Any], str]:
        self.ensure_one()
        if (
            not searched_field_name
            or searched_field_name not in self._fields
            or not self[searched_field_name]
            or not self.model_id
        ):
            return [], ""
        path = self[searched_field_name].split(".")
        if not path:
            return [], ""
        model = self.env[self.model_id.model]
        chain = []
        for field_name in path:
            is_last_field = field_name == path[-1]
            field = model._fields[field_name]
            if not is_last_field:
                if not field.relational:
                    # sanity check: this should be the last field in the path
                    current_field = field.get_description(self.env)["string"]
                    searched_field = self._fields[searched_field_name].get_description(
                        self.env
                    )["string"]
                    raise ValidationError(
                        _(
                            "The path contained by the field '%(searched_field)s' contains a non-relational field (%(current_field)s) that is not the last field in the path. You can't traverse non-relational fields (even in the quantum realm). Make sure only the last field in the path is non-relational.",
                            searched_field=searched_field,
                            current_field=current_field,
                        )
                    )
                model = self.env[field.comodel_name]
            chain.append(field)
        stringified_path = " > ".join(
            [field.get_description(self.env)["string"] for field in chain]
        )
        return chain, stringified_path

    @api.depends("state", "model_id.model", "webhook_field_ids", "name")
    def _compute_webhook_sample_payload(self) -> None:
        for action in self:
            if action.state != "webhook":
                action.webhook_sample_payload = False
                continue
            payload = {
                "_id": 1,
                "_model": action.model_id.model,
                "_action": f"{action.name}(#{action.id})",
            }
            if action.model_id:
                sample_record = (
                    self.env[action.model_id.model]
                    .with_context(active_test=False)
                    .search([], limit=1)
                )
                if sample_record:
                    payload["_id"] = sample_record.id
                    payload.update(
                        sample_record.read(
                            action.webhook_field_ids.mapped("name"), load=None
                        )[0]
                    )
                else:
                    for field in action.webhook_field_ids:
                        payload[field.name] = (
                            WEBHOOK_SAMPLE_VALUES[field.ttype]
                            if field.ttype in WEBHOOK_SAMPLE_VALUES
                            else WEBHOOK_SAMPLE_VALUES[None]
                        )
            action.webhook_sample_payload = json.dumps(
                payload, indent=4, sort_keys=True, default=str
            )

    @api.constrains("code")
    def _check_python_code(self) -> None:
        for action in self.sudo().filtered("code"):
            msg = test_python_expr(expr=action.code.strip(), mode="exec")
            if msg:
                raise ValidationError(msg)

    @api.constrains("parent_id", "child_ids")
    def _check_children(self) -> None:
        if self._has_cycle():
            raise ValidationError(_("Recursion found in child server actions"))

        if children_with_warnings := self.child_ids.filtered("warning"):
            raise ValidationError(
                _(
                    "Following child actions have warnings: %(children)s",
                    children=", ".join(children_with_warnings.mapped("name")),
                )
            )

    def _get_readable_fields(self) -> set[str]:
        return super()._get_readable_fields() | {
            "group_ids",
            "model_name",
        }

    def _get_runner(self) -> tuple[Any, bool]:
        multi = True
        t = self.env.registry[self._name]
        fn = getattr(t, f"_run_action_{self.state}_multi", None)
        if not fn:
            multi = False
            fn = getattr(t, f"_run_action_{self.state}", None)
        return fn, multi

    def create_action(self) -> bool:
        """Create a contextual action for each server action."""
        for model_id, actions in self.grouped("model_id").items():
            actions.write({"binding_model_id": model_id.id, "binding_type": "action"})
        return True

    def unlink_action(self) -> bool:
        """Remove the contextual actions created for the server actions."""
        self.check_access("write")
        self.filtered("binding_model_id").write({"binding_model_id": False})
        return True

    def history_wizard_action(self) -> dict[str, Any]:
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Code History"),
            "target": "new",
            "views": [(False, "form")],
            "res_model": "server.action.history.wizard",
            "context": {"default_action_id": self.id},
        }

    def _run_action_code_multi(self, eval_context: dict[str, Any]) -> Any:
        if not self.code:
            return None
        safe_eval(self.code.strip(), eval_context, mode="exec", filename=str(self))
        return eval_context.get("action")

    def _run_action_multi(self, eval_context: dict[str, Any] | None = None) -> Any:
        res = False
        for act in self.child_ids.sorted():
            res = act.run() or res
        return res

    def _run_action_object_write(
        self, eval_context: dict[str, Any] | None = None
    ) -> None:
        """Apply specified write changes to active_id."""
        vals = self._eval_value(eval_context=eval_context)
        res = {action.update_field_id.name: vals[action.id] for action in self}

        if self.env.context.get("onchange_self"):
            record_cached = self.env.context["onchange_self"]
            for field, new_value in res.items():
                record_cached[field] = new_value
        elif self.update_path:
            starting_record = self.env[self.model_id.model].browse(
                self.env.context.get("active_id")
            )
            path = self.update_path.split(".")
            target_records = reduce(getitem, path[:-1], starting_record)
            target_records.write(res)

    def _run_action_webhook(self, eval_context: dict[str, Any] | None = None) -> None:
        """Send a post request with a read of the selected field on active_id."""
        record = self.env[self.model_id.model].browse(self.env.context.get("active_id"))
        url = self.webhook_url
        if not record:
            return
        if not url:
            raise UserError(
                _(
                    "I'll be happy to send a webhook for you, but you really need to give me a URL to reach out to..."
                )
            )
        vals = {
            "_model": self.model_id.model,
            "_id": record.id,
            "_action": f"{self.name}(#{self.id})",
        }
        if self.webhook_field_ids:
            # you might think we could use the default json serializer of the requests library
            # but it will fail on many fields, e.g. datetime, date or binary
            # so we use the json.dumps serializer instead with the str() function as default
            vals.update(
                record.read(self.webhook_field_ids.mapped("name"), load=None)[0]
            )
        json_values = json_dumps(vals, default=str, option=OPT_SORT_KEYS)
        _logger.info("Webhook call to %s", url)
        _logger.debug("POST JSON data for webhook call: %s", json_values)

        @self.env.cr.postrollback.add
        def _add_post_rollback():
            _logger.warning("Webhook call to %s - cancelled due to a rollback", url)

        @self.env.cr.postcommit.add
        def _add_post_commit():
            _logger.debug("Webhook call to %s - start", url)
            import requests

            try:
                # 'send and forget' strategy, and avoid locking the user if the webhook
                # is slow or non-functional (we still allow for a 1s timeout so that
                # if we get a proper error response code like 400, 404 or 500 we can log)
                response = requests.post(
                    url,
                    data=json_values,
                    headers={"Content-Type": "application/json"},
                    timeout=1,
                )
                response.raise_for_status()
                _logger.info("Webhook call to %s - succeeded", url)
            except requests.exceptions.ReadTimeout:
                _logger.warning(
                    "Webhook call timed out after 1s - it may or may not have failed. "
                    "If this happens often, it may be a sign that the system you're "
                    "trying to reach is slow or non-functional."
                )
            except requests.exceptions.RequestException as e:
                _logger.warning("Webhook call failed: %s", e)

    def _run_action_object_copy(
        self, eval_context: dict[str, Any] | None = None
    ) -> None:
        """Duplicate specified model object.
        If applicable, link active_id.<self.link_field_id> to the new record.
        """
        dupe = self.env[self.crud_model_id.model].browse(self.resource_ref.id).copy()

        if self.link_field_id:
            record = self.env[self.model_id.model].browse(
                self.env.context.get("active_id")
            )
            if self.link_field_id.ttype in ["one2many", "many2many"]:
                record.write({self.link_field_id.name: [Command.link(dupe.id)]})
            else:
                record.write({self.link_field_id.name: dupe.id})

    def _run_action_object_create(
        self, eval_context: dict[str, Any] | None = None
    ) -> None:
        """Create specified model object with specified name contained in value.

        If applicable, link active_id.<self.link_field_id> to the new record.
        """
        res_id, _res_name = self.env[self.crud_model_id.model].name_create(self.value)

        if self.link_field_id:
            record = self.env[self.model_id.model].browse(
                self.env.context.get("active_id")
            )
            if self.link_field_id.ttype in ["one2many", "many2many"]:
                record.write({self.link_field_id.name: [Command.link(res_id)]})
            else:
                record.write({self.link_field_id.name: res_id})

    def _get_eval_context(self, action: Self | None = None) -> dict[str, Any]:
        """Prepare the context used when evaluating python code, like the
        python formulas or code server actions.

        :param action: the current server action
        :type action: browse record
        :returns: dict -- evaluation context given to (safe_)safe_eval"""

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

        eval_context = super()._get_eval_context(action=action)
        model_name = action.model_id.sudo().model
        model = self.env[model_name]
        record = None
        records = None
        if self.env.context.get("active_model") == model_name and self.env.context.get(
            "active_id"
        ):
            record = model.browse(self.env.context["active_id"])
        if self.env.context.get("active_model") == model_name and self.env.context.get(
            "active_ids"
        ):
            records = model.browse(self.env.context["active_ids"])
        if self.env.context.get("onchange_self"):
            record = self.env.context["onchange_self"]
        eval_context.update(
            {
                # orm
                "env": self.env,
                "model": model,
                # Exceptions
                "UserError": UserError,
                # record
                "record": record,
                "records": records,
                # helpers
                "log": log,
                "_logger": LoggerProxy,
            }
        )
        return eval_context

    def run(self) -> dict[str, Any] | bool:
        """Runs the server action. For each server action, the
        :samp:`_run_action_{TYPE}[_multi]` method is called. This allows easy
        overriding of the server actions.

        The ``_multi`` suffix means the runner can operate on multiple records,
        otherwise if there are multiple records the runner will be called once
        for each.

        The call context should contain the following keys:

        active_id
            id of the current object (single mode)
        active_model
            current model that should equal the action's model
        active_ids (optional)
           ids of the current records (mass mode). If ``active_ids`` and
           ``active_id`` are present, ``active_ids`` is given precedence.

        :return: an ``action_id`` to be executed, or ``False`` is finished
                 correctly without return action
        """
        res = False
        for action in self.sudo():
            eval_context = self._get_eval_context(action)
            records = eval_context.get("record") or eval_context["model"]
            records |= eval_context.get("records") or eval_context["model"]
            action._can_execute_action_on_records(records)
            res = action._run(records, eval_context)
        return res

    def _run(self, records: Any, eval_context: dict[str, Any]) -> dict[str, Any] | bool:
        self.ensure_one()
        if self.warning:
            raise ServerActionWithWarningsError(
                _(
                    "Server action %(action_name)s has one or more warnings, address them first.",
                    action_name=self.name,
                )
            )

        runner, multi = self._get_runner()
        res = False
        if runner and multi:
            # call the multi method
            run_self = self.with_context(eval_context["env"].context)
            res = runner(run_self, eval_context=eval_context)
        elif runner:
            active_id = self.env.context.get("active_id")
            if not active_id and self.env.context.get("onchange_self"):
                active_id = self.env.context["onchange_self"]._origin.id
                if not active_id:  # onchange on new record
                    res = runner(self, eval_context=eval_context)
            active_ids = self.env.context.get(
                "active_ids", [active_id] if active_id else []
            )
            for active_id in active_ids:
                # run context dedicated to a particular active_id
                run_self = self.with_context(
                    active_ids=[active_id], active_id=active_id
                )
                eval_context["env"] = eval_context["env"](context=run_self.env.context)
                eval_context["records"] = eval_context["record"] = records.browse(
                    active_id
                )
                res = runner(run_self, eval_context=eval_context)
        else:
            _logger.warning(
                "Found no way to execute server action %r of type %r, ignoring it. "
                "Verify that the type is correct or add a method called "
                "`_run_action_<type>` or `_run_action_<type>_multi`.",
                self.name,
                self.state,
            )
        return res or False

    def _can_execute_action_on_records(self, records: Any) -> None:
        self.ensure_one()

        action_groups = self.group_ids
        if action_groups:
            if not (action_groups & self.env.user.all_group_ids):
                raise AccessError(
                    _("You don't have enough access rights to run this action.")
                )
        else:
            model_name = self.model_id.model
            try:
                self.env[model_name].check_access("write")
            except AccessError:
                _logger.warning(
                    "Forbidden server action %r executed while the user %s does not have access to %s.",
                    self.name,
                    self.env.user.login,
                    model_name,
                )
                raise

        if not self.group_ids and records.ids:
            # check access rules on real records only; base automations of
            # type 'onchange' can run server actions on new records
            try:
                records.check_access("write")
            except AccessError:
                _logger.warning(
                    "Forbidden server action %r executed while the user %s does not have access to %s.",
                    self.name,
                    self.env.user.login,
                    records,
                )
                raise

    @api.depends("evaluation_type", "update_field_id.ttype")
    def _compute_value_field_to_show(
        self,
    ) -> (
        None
    ):  # check if value_field_to_show can be removed and use ttype in xml view instead
        for action in self:
            if action.evaluation_type == "sequence":
                action.value_field_to_show = "sequence_id"
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

    @api.model
    @tools.ormcache("self.env.lang")
    def _selection_target_model(self) -> list[tuple[str, str]]:
        """Return all models as selection list. Cached because the model list
        only changes on module install/update (which clears the registry cache).
        """
        return [
            (model.model, model.name)
            for model in self.env["ir.model"].sudo().search([])
        ]

    @api.onchange("crud_model_id")
    def _set_crud_model_id(self) -> None:
        invalid = self.filtered(
            lambda a: a.state == "object_copy"
            and a.resource_ref
            and a.resource_ref._name != a.crud_model_id.model
        )
        invalid.resource_ref = False
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
    def _set_resource_ref(self) -> None:
        for action in self.filtered(
            lambda action: action.value_field_to_show == "resource_ref"
        ):
            if action.resource_ref:
                action.value = str(action.resource_ref.id)

    @api.onchange("selection_value")
    def _set_selection_value(self) -> None:
        for action in self.filtered(
            lambda action: action.value_field_to_show == "selection_value"
        ):
            if action.selection_value:
                action.value = action.selection_value.value

    def _eval_value(self, eval_context: dict[str, Any] | None = None) -> dict[int, Any]:
        result = {}
        for action in self:
            expr = action.value
            if action.evaluation_type == "equation":
                expr = safe_eval(action.value, eval_context)
            elif action.evaluation_type == "sequence":
                expr = action.sequence_id.next_by_id()
            elif action.update_field_id.ttype in ["one2many", "many2many"]:
                match action.update_m2m_operation:
                    case "add":
                        expr = [Command.link(int(action.value))]
                    case "remove":
                        expr = [Command.unlink(int(action.value))]
                    case "set":
                        expr = [Command.set([int(action.value)])]
                    case "clear":
                        expr = [Command.clear()]
            elif action.update_field_id.ttype == "boolean":
                expr = action.update_boolean_value == "true"
            elif action.update_field_id.ttype in ["many2one", "integer"]:
                try:
                    expr = int(action.value)
                    if expr == 0 and action.update_field_id.ttype == "many2one":
                        expr = False
                except ValueError, TypeError:
                    pass
            elif action.update_field_id.ttype == "float":
                with contextlib.suppress(ValueError, TypeError):
                    expr = float(action.value)
            elif action.update_field_id.ttype == "html":
                expr = action.html_value
            result[action.id] = expr
        return result

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        default = default or {}
        vals_list = super().copy_data(default=default)
        if not default.get("name"):
            for vals in vals_list:
                vals["name"] = _("%s (copy)", vals.get("name", ""))
        return vals_list

    def action_open_parent_action(self) -> dict[str, Any]:
        return {
            "type": "ir.actions.act_window",
            "target": "current",
            "views": [[False, "form"]],
            "res_model": self._name,
            "res_id": self.parent_id.id,
        }

    def action_open_scheduled_action(self) -> dict[str, Any]:
        self.ensure_one()
        if not self.ir_cron_ids:
            raise UserError(
                _("No scheduled action is associated with this server action.")
            )
        return {
            "type": "ir.actions.act_window",
            "target": "current",
            "views": [[False, "form"]],
            "res_model": "ir.cron",
            "res_id": self.ir_cron_ids.ids[0],
        }
