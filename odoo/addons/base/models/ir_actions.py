import base64
import collections.abc
import re
from collections import defaultdict
from typing import Any, Self

from odoo import api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.libs.datetime.tz import timezone
from odoo.libs.numbers.float_utils import float_compare
from odoo.tools import SQL, _, frozendict
from odoo.tools.safe_eval import safe_eval
from odoo.orm._typing import ValuesType


class IrActionsActions(models.Model):
    _name = "ir.actions.actions"
    _description = "Actions"
    _table = "ir_actions"
    _order = "name, id"
    _allow_sudo_commands = False

    _path_unique = models.Constraint(
        "unique(path)",
        "Path to show in the URL must be unique! Please choose another one.",
    )

    name = fields.Char(string="Action Name", required=True, translate=True)
    type = fields.Char(string="Action Type", required=True)
    xml_id = fields.Char(compute="_compute_xml_id", string="External ID")
    path = fields.Char(string="Path to show in the URL")
    help = fields.Html(
        string="Action Description",
        help="Optional help text for the users with a description of the target view, such as its usage and purpose.",
        translate=True,
    )
    binding_model_id = fields.Many2one(
        "ir.model",
        ondelete="cascade",
        help="Setting a value makes this action available in the sidebar for the given model.",
    )
    binding_type = fields.Selection(
        [("action", "Action"), ("report", "Report")],
        required=True,
        default="action",
    )
    binding_view_types = fields.Char(default="list,form")

    @api.constrains("path")
    def _check_path(self) -> None:
        """Validate action path format and cross-table uniqueness."""
        for action in self:
            if action.path:
                if not re.fullmatch(r"[a-z][a-z0-9_-]*", action.path):
                    raise ValidationError(
                        _(
                            "The path should contain only lowercase alphanumeric characters, underscore, and dash, and it should start with a letter."
                        )
                    )
                if action.path.startswith("m-"):
                    raise ValidationError(_("'m-' is a reserved prefix."))
                if action.path.startswith("action-"):
                    raise ValidationError(_("'action-' is a reserved prefix."))
                if action.path == "new":
                    raise ValidationError(
                        _("'new' is reserved, and can not be used as path.")
                    )

        # Cross-table uniqueness: ir_act_window, ir_act_report_xml, etc. all
        # inherit from ir_actions.  PostgreSQL unique indexes only apply per
        # child table, so we check across all tables with a single grouped
        # query instead of one search_count per action.
        # See https://www.postgresql.org/docs/14/ddl-inherit.html#DDL-INHERIT-CAVEATS
        paths = [action.path for action in self if action.path]
        if paths and self.env["ir.actions.actions"]._read_group(
            [("path", "in", paths)],
            groupby=["path"],
            aggregates=["__count"],
            having=[("__count", ">", 1)],
        ):
            raise ValidationError(
                _("Path to show in the URL must be unique! Please choose another one.")
            )

    def _compute_xml_id(self) -> None:
        res = self.get_external_id()
        for record in self:
            record.xml_id = res.get(record.id)

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        res = super().create(vals_list)
        # self.get_bindings() depends on action records
        self.env.registry.clear_cache()
        return res

    def write(self, vals: dict[str, Any]) -> bool:
        res = super().write(vals)
        # self.get_bindings() depends on action records
        self.env.registry.clear_cache()
        return res

    def unlink(self) -> bool:
        """unlink ir.action.todo/ir.filters which are related to actions which will be deleted.
        NOTE: ondelete cascade will not work on ir.actions.actions so we will need to do it manually.
        """
        todos = self.env["ir.actions.todo"].search([("action_id", "in", self.ids)])
        todos.unlink()
        filters = self.env["ir.filters"].search([("action_id", "in", self.ids)])
        filters.unlink()
        res = super().unlink()
        # self.get_bindings() depends on action records
        self.env.registry.clear_cache()
        return res

    @api.ondelete(at_uninstall=True)
    def _unlink_check_home_action(self) -> None:
        self.env["res.users"].with_context(active_test=False).search(
            [("action_id", "in", self.ids)]
        ).sudo().write({"action_id": None})

    @api.model
    def _get_eval_context(self, action: Any = None) -> dict[str, Any]:
        """evaluation context to pass to safe_eval"""
        return {
            "uid": self.env.uid,
            "user": self.env.user,
            "time": tools.safe_eval.time,
            "datetime": tools.safe_eval.datetime,
            "dateutil": tools.safe_eval.dateutil,
            "timezone": timezone,
            "float_compare": float_compare,
            "b64encode": base64.b64encode,
            "b64decode": base64.b64decode,
            "Command": Command,
        }

    @api.model
    def get_bindings(self, model_name: str) -> dict[str, list[dict[str, Any]]]:
        """Retrieve the list of actions bound to the given model.

        :return: a dict mapping binding types to a list of dict describing
                 actions, where the latter is given by calling the method
                 ``read`` on the action record.
        """
        result = {}
        for action_type, all_actions in self._get_bindings(model_name).items():
            actions = []
            for action in all_actions:
                action = dict(action)
                groups = action.pop("group_ids", None)
                if groups and not any(
                    self.env.user.has_group(ext_id) for ext_id in groups
                ):
                    # the user may not perform this action
                    continue
                res_model = action.pop("res_model", None)
                if res_model and not self.env["ir.model.access"].check(
                    res_model, mode="read", raise_exception=False
                ):
                    # the user won't be able to read records
                    continue
                actions.append(action)
            if actions:
                result[action_type] = actions
        return result

    @tools.ormcache("model_name", "self.env.lang")
    def _get_bindings(self, model_name: str) -> frozendict:
        """Retrieve bound actions for a model, batch-reading per action type."""
        cr = self.env.cr
        result = defaultdict(list)

        self.env.flush_all()
        cr.execute(
            """
            SELECT a.id, a.type, a.binding_type
              FROM ir_actions a
              JOIN ir_model m ON a.binding_model_id = m.id
             WHERE m.model = %s
          ORDER BY a.id
        """,
            [model_name],
        )
        rows = cr.fetchall()
        if not rows:
            return frozendict(result)

        # Group by action model type for batch browse+read (O(k) queries
        # where k = distinct action types, instead of O(n) per action)
        by_model = defaultdict(list)
        for action_id, action_model, binding_type in rows:
            by_model[action_model].append((action_id, binding_type))

        # Pre-compute read fields per action model (field set is static per
        # model class, so introspection only needs to happen once per type).
        optional_fields = ("group_ids", "res_model", "sequence", "domain")
        fields_cache: dict[str, list[str]] = {}

        for action_model, entries in by_model.items():
            if action_model not in self.env.registry:
                continue
            action_ids = [e[0] for e in entries]
            binding_map = dict(entries)  # action_id -> binding_type

            actions = self.env[action_model].sudo().browse(action_ids).exists()
            if not actions:
                continue
            if action_model not in fields_cache:
                model_fields = actions._fields
                fields_cache[action_model] = [
                    "name",
                    "binding_view_types",
                    *(f for f in optional_fields if f in model_fields),
                ]
            for action_data in actions.read(fields_cache[action_model]):
                binding_type = binding_map[action_data["id"]]
                if action_data.get("group_ids"):
                    groups = self.env["res.groups"].browse(action_data["group_ids"])
                    action_data["group_ids"] = list(groups._ensure_xml_id().values())
                if "domain" in action_data and not action_data.get("domain"):
                    action_data.pop("domain")
                result[binding_type].append(frozendict(action_data))

        # sort actions by their sequence if sequence available
        if result.get("action"):
            result["action"] = sorted(
                result["action"], key=lambda vals: vals.get("sequence", 0)
            )
        # Freeze all binding lists to tuples — this method is ormcached and
        # mutable lists would let callers corrupt the shared cache.
        return frozendict({key: tuple(val) for key, val in result.items()})

    @api.model
    def _for_xml_id(self, full_xml_id: str) -> dict[str, Any]:
        """Returns the action content for the provided xml_id

        :param full_xml_id: the namespace-less id of the action (the @id
            attribute from the XML file)
        :return: A read() view of the ir.actions.action safe for web use
        """
        record = self.env.ref(full_xml_id)
        if not isinstance(self.env[record._name], self.env.registry[self._name]):
            raise ValidationError(
                _("Record %s is not a valid action type", full_xml_id)
            )
        return record._get_action_dict()

    def _get_action_dict(self) -> dict[str, Any]:
        """Returns the action content for the provided action record."""
        self.ensure_one()
        readable_fields = self._get_readable_fields()
        return {
            field: value
            for field, value in self.sudo().read()[0].items()
            if field in readable_fields
        }

    def _get_readable_fields(self) -> set[str]:
        """return the list of fields that are safe to read

        Fetched via /web/action/load or _for_xml_id method
        Only fields used by the web client should included
        Accessing content useful for the server-side must
        be done manually with superuser
        """
        return {
            "binding_model_id",
            "binding_type",
            "binding_view_types",
            "display_name",
            "help",
            "id",
            "name",
            "type",
            "xml_id",
            "path",
        }


class IrActionsAct_Window(models.Model):
    _name = "ir.actions.act_window"
    _description = "Action Window"
    _table = "ir_act_window"
    _inherit = ["ir.actions.actions"]
    _order = "name, id"
    _allow_sudo_commands = False

    @api.constrains("res_model", "binding_model_id")
    def _check_model(self) -> None:
        for action in self:
            if action.res_model not in self.env:
                raise ValidationError(
                    _(
                        "Invalid model name “%s” in action definition.",
                        action.res_model,
                    )
                )
            if (
                action.binding_model_id
                and action.binding_model_id.model not in self.env
            ):
                raise ValidationError(
                    _(
                        "Invalid model name “%s” in action definition.",
                        action.binding_model_id.model,
                    )
                )

    @api.depends("view_ids.view_mode", "view_mode", "view_id.type")
    def _compute_views(self) -> None:
        """Compute an ordered list of the specific view modes that should be
        enabled when displaying the result of this action, along with the
        ID of the specific view to use for each mode, if any were required.

        This function hides the logic of determining the precedence between
        the view_modes string, the view_ids o2m, and the view_id m2o that
        can be set on the action.
        """
        for act in self:
            views = []
            got_modes = []
            for view in act.view_ids:
                views.append((view.view_id.id, view.view_mode))
                got_modes.append(view.view_mode)
            act.views = views
            all_modes = act.view_mode.split(",")
            missing_modes = [mode for mode in all_modes if mode not in got_modes]
            if missing_modes:
                if act.view_id.type in missing_modes:
                    # reorder missing modes to put view_id first if present
                    missing_modes.remove(act.view_id.type)
                    act.views.append((act.view_id.id, act.view_id.type))
                act.views.extend([(False, mode) for mode in missing_modes])

    @api.constrains("view_mode")
    def _check_view_mode(self) -> None:
        for rec in self:
            modes = rec.view_mode.split(",")
            if len(modes) != len(set(modes)):
                raise ValidationError(
                    _(
                        "The modes in view_mode must not be duplicated: %s",
                        modes,
                    )
                )
            if any(" " in mode for mode in modes):
                raise ValidationError(_("No spaces allowed in view_mode: “%s”", modes))

    type = fields.Char(default="ir.actions.act_window")
    view_id = fields.Many2one("ir.ui.view", string="View Ref.", ondelete="set null")
    domain = fields.Char(
        string="Domain Value",
        help="Optional domain filtering of the destination data, as a Python expression",
    )
    context = fields.Char(
        string="Context Value",
        default="{}",
        required=True,
        help="Context dictionary as Python expression, empty by default (Default: {})",
    )
    res_id = fields.Integer(
        string="Record ID",
        help="Database ID of record to open in form view, when ``view_mode`` is set to 'form' only",
    )
    res_model = fields.Char(
        string="Destination Model",
        required=True,
        help="Model name of the object to open in the view window",
    )
    target = fields.Selection(
        [
            ("current", "Current Window"),
            ("new", "New Window"),
            ("fullscreen", "Full Screen"),
            ("main", "Main action of Current Window"),
        ],
        default="current",
        string="Target Window",
    )
    view_mode = fields.Char(
        required=True,
        default="list,form",
        help="Comma-separated list of allowed view modes, such as 'form', 'list', 'calendar', etc. (Default: list,form)",
    )
    mobile_view_mode = fields.Char(
        default="kanban",
        help="First view mode in mobile and small screen environments (default='kanban'). If it can't be found among available view modes, the same mode as for wider screens is used)",
    )
    usage = fields.Char(
        string="Action Usage",
        help="Used to filter menu and home actions from the user form.",
    )
    view_ids = fields.One2many(
        "ir.actions.act_window.view", "act_window_id", string="No of Views"
    )
    views = fields.Binary(
        compute="_compute_views",
        help="This function field computes the ordered list of views that should be enabled "
        "when displaying the result of an action, federating view mode, views and "
        "reference view. The result is returned as an ordered list of pairs (view_id,view_mode).",
    )
    limit = fields.Integer(default=80, help="Default limit for the list view")
    group_ids = fields.Many2many(
        "res.groups",
        "ir_act_window_group_rel",
        "act_id",
        "gid",
        string="Groups",
    )
    search_view_id = fields.Many2one("ir.ui.view", string="Search View Ref.")
    embedded_action_ids = fields.One2many(
        "ir.embedded.actions", compute="_compute_embedded_actions"
    )
    filter = fields.Boolean()
    cache = fields.Boolean(
        string="Data Caching",
        default=True,
        help="If enabled, this action will cache the related data used in list, Kanban and form views with the aim to increase the loading speed",
    )

    def _compute_embedded_actions(self) -> None:
        embedded_actions = (
            self.env["ir.embedded.actions"]
            .search([("parent_action_id", "in", self.ids)])
            .filtered(lambda x: x.is_visible)
        )
        grouped = embedded_actions.grouped("parent_action_id")
        for action in self:
            action.embedded_action_ids = grouped.get(
                action, self.env["ir.embedded.actions"]
            )

    def read(
        self, fields: collections.abc.Sequence[str] | None = None, load: str = "_classic_read"
    ) -> list[ValuesType]:
        """call the method get_empty_list_help of the model and set the window action help message"""
        result = super().read(fields, load=load)
        if not fields or "help" in fields:
            for values in result:
                if (model := values.get("res_model")) in self.env:
                    eval_ctx = dict(self.env.context)
                    try:
                        ctx = safe_eval(values.get("context", "{}"), eval_ctx)
                        if not isinstance(ctx, dict):
                            ctx = {}
                    except Exception:
                        ctx = {}
                    values["help"] = (
                        self.with_context(**ctx)
                        .env[model]
                        .get_empty_list_help(values.get("help", ""))
                    )
        return result

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        self.env.registry.clear_cache()
        for vals in vals_list:
            if not vals.get("name") and vals.get("res_model"):
                vals["name"] = self.env[vals["res_model"]]._description
        return super().create(vals_list)

    def unlink(self) -> bool:
        self.env.registry.clear_cache()
        return super().unlink()

    def exists(self) -> Self:
        ids = self._existing()
        return self.filtered(lambda rec: rec.id in ids)

    @api.model
    @tools.ormcache()
    def _existing(self) -> set[int]:
        self.env.cr.execute(SQL("SELECT id FROM %s", SQL.identifier(self._table)))
        return {row[0] for row in self.env.cr.fetchall()}

    def _get_readable_fields(self) -> set[str]:
        return super()._get_readable_fields() | {
            "context",
            "cache",
            "mobile_view_mode",
            "domain",
            "filter",
            "group_ids",
            "limit",
            "res_id",
            "res_model",
            "search_view_id",
            "target",
            "view_id",
            "view_mode",
            "views",
            "embedded_action_ids",
            # this is used by frontend, with the document layout wizard before send and print
            "close_on_report_download",
        }

    def _get_action_dict(self) -> dict[str, Any]:
        """Override to return action content with detailed embedded actions data if available.

        :return: A dict with updated action dictionary including embedded actions information.
        """
        result = super()._get_action_dict()
        if embedded_action_ids := result["embedded_action_ids"]:
            EmbeddedActions = self.env["ir.embedded.actions"]
            embedded_fields = EmbeddedActions._get_readable_fields()
            result["embedded_action_ids"] = EmbeddedActions.browse(
                embedded_action_ids
            ).read(embedded_fields)
        return result


VIEW_TYPES = [
    ("list", "List"),
    ("form", "Form"),
    ("graph", "Graph"),
    ("pivot", "Pivot"),
    ("calendar", "Calendar"),
    ("kanban", "Kanban"),
]


class IrActionsAct_WindowView(models.Model):
    _name = "ir.actions.act_window.view"
    _description = "Action Window View"
    _table = "ir_act_window_view"
    _rec_name = "view_id"
    _order = "sequence,id"
    _allow_sudo_commands = False

    _unique_mode_per_action = models.UniqueIndex("(act_window_id, view_mode)")

    sequence = fields.Integer()
    view_id = fields.Many2one("ir.ui.view", string="View")
    view_mode = fields.Selection(VIEW_TYPES, string="View Type", required=True)
    act_window_id = fields.Many2one(
        "ir.actions.act_window",
        string="Action",
        ondelete="cascade",
        index="btree_not_null",
    )
    multi = fields.Boolean(
        string="On Multiple Doc.",
        help="If set to true, the action will not be displayed on the right toolbar of a form view.",
    )


class IrActionsAct_Window_Close(models.Model):
    _name = "ir.actions.act_window_close"
    _description = "Action Window Close"
    _inherit = ["ir.actions.actions"]
    _table = "ir_actions"
    _allow_sudo_commands = False

    type = fields.Char(default="ir.actions.act_window_close")

    def _get_readable_fields(self) -> set[str]:
        return super()._get_readable_fields() | {
            # 'effect' and 'infos' are not real fields of `ir.actions.act_window_close` but they are
            # used to display the rainbowman ('effect') and waited by the action_service ('infos').
            "effect",
            "infos",
        }


class IrActionsAct_Url(models.Model):
    _name = "ir.actions.act_url"
    _description = "Action URL"
    _table = "ir_act_url"
    _inherit = ["ir.actions.actions"]
    _order = "name, id"
    _allow_sudo_commands = False

    type = fields.Char(default="ir.actions.act_url")
    url = fields.Text(string="Action URL", required=True)
    target = fields.Selection(
        [
            ("new", "New Window"),
            ("self", "This Window"),
            ("download", "Download"),
        ],
        string="Action Target",
        default="new",
        required=True,
    )

    def _get_readable_fields(self) -> set[str]:
        return super()._get_readable_fields() | {
            "target",
            "url",
            "close",
        }


class IrActionsTodo(models.Model):
    """
    Configuration Wizards
    """

    _name = "ir.actions.todo"
    _description = "Configuration Wizards"
    _rec_name = "action_id"
    _order = "sequence, id"
    _allow_sudo_commands = False

    action_id = fields.Many2one(
        "ir.actions.actions", string="Action", required=True, index=True
    )
    sequence = fields.Integer(default=10)
    state = fields.Selection(
        [("open", "To Do"), ("done", "Done")],
        string="Status",
        default="open",
        required=True,
    )
    name = fields.Char()

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        todos = super().create(vals_list)
        for todo in todos:
            if todo.state == "open":
                self.ensure_one_open_todo()
        return todos

    def write(self, vals: dict[str, Any]) -> bool:
        res = super().write(vals)
        if vals.get("state", "") == "open":
            self.ensure_one_open_todo()
        return res

    @api.model
    def ensure_one_open_todo(self) -> None:
        open_todo = self.search(
            [("state", "=", "open")], order="sequence asc, id desc", offset=1
        )
        if open_todo:
            open_todo.write({"state": "done"})

    def unlink(self) -> bool:
        if self:
            try:
                todo_open_menu = self.env.ref("base.open_menu")
                # don't remove base.open_menu todo but set its original action
                if todo_open_menu in self:
                    todo_open_menu.action_id = self.env.ref(
                        "base.action_client_base_menu"
                    ).id
                    self -= todo_open_menu
            except ValueError:
                pass
        return super().unlink()

    def action_launch(self) -> dict[str, Any]:
        """Launch Action of Wizard"""
        self.ensure_one()

        self.write({"state": "done"})

        # Load action
        action_type = self.action_id.type
        action = self.env[action_type].browse(self.action_id.id)

        result = action.read()[0]
        if action_type != "ir.actions.act_window":
            return result
        result.setdefault("context", "{}")

        # Open a specific record when res_id is provided in the context
        try:
            ctx = safe_eval(result["context"], {"user": self.env.user})
            if not isinstance(ctx, dict):
                ctx = {}
        except Exception:
            ctx = {}
        if ctx.get("res_id"):
            result["res_id"] = ctx.pop("res_id")

        # disable log for automatic wizards
        ctx["disable_log"] = True

        result["context"] = ctx

        return result

    def action_open(self) -> bool:
        """Sets configuration wizard in TODO state"""
        return self.write({"state": "open"})


class IrActionsClient(models.Model):
    _name = "ir.actions.client"
    _description = "Client Action"
    _inherit = ["ir.actions.actions"]
    _table = "ir_act_client"
    _order = "name, id"
    _allow_sudo_commands = False

    type = fields.Char(default="ir.actions.client")

    tag = fields.Char(
        string="Client action tag",
        required=True,
        help="An arbitrary string, interpreted by the client"
        " according to its own needs and wishes. There "
        "is no central tag repository across clients.",
    )
    target = fields.Selection(
        [
            ("current", "Current Window"),
            ("new", "New Window"),
            ("fullscreen", "Full Screen"),
            ("main", "Main action of Current Window"),
        ],
        default="current",
        string="Target Window",
    )
    res_model = fields.Char(
        string="Destination Model",
        help="Optional model, mostly used for needactions.",
    )
    context = fields.Char(
        string="Context Value",
        default="{}",
        required=True,
        help="Context dictionary as Python expression, empty by default (Default: {})",
    )
    params = fields.Binary(
        compute="_compute_params",
        inverse="_inverse_params",
        string="Supplementary arguments",
        help="Arguments sent to the client along with the view tag",
    )
    params_store = fields.Binary(
        string="Params storage", readonly=True, attachment=False
    )

    @api.depends("params_store")
    def _compute_params(self) -> None:
        self_bin = self.with_context(bin_size=False, bin_size_params_store=False)
        for record, record_bin in zip(self, self_bin, strict=True):
            record.params = record_bin.params_store and safe_eval(
                record_bin.params_store, {"uid": self.env.uid}
            )

    def _inverse_params(self) -> None:
        for record in self:
            params = record.params
            record.params_store = repr(params) if isinstance(params, dict) else params

    def _get_readable_fields(self) -> set[str]:
        return super()._get_readable_fields() | {
            "context",
            "params",
            "res_model",
            "tag",
            "target",
        }
