import ast
import base64
import contextlib
import logging
import re
import threading
import typing
from ast import literal_eval
from collections.abc import Collection, Iterator
from itertools import batched
from types import NotImplementedType
from typing import Any, Literal, Self

from lxml import etree

from odoo import _, api, fields, models, tools
from odoo.api import ValuesType
from odoo.db.errors import PG_RECOVERABLE_EXCEPTIONS
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL
from odoo.tools.rendering_tools import parse_inline_template
from odoo.tools.safe_eval import safe_eval, time

if typing.TYPE_CHECKING:
    from .ir_mail_server import IrMail_Server
    from .mail_mail import MailMail
    from odoo.addons.base.models.ir_actions_act_window import IrActionsAct_Window
    from odoo.addons.base.models.ir_actions_report import IrActionsReport
    from odoo.addons.base.models.ir_model import IrModel
    from odoo.addons.bus.models.ir_attachment import IrAttachment
    from odoo.addons.bus.models.res_users import ResUsers

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

type RenderResults = dict[int, dict[str, Any]]

DYNAMIC_FIELD_NAMES = frozenset(
    {
        "body_html",
        "email_cc",
        "email_from",
        "email_to",
        "lang",
        "partner_to",
        "reply_to",
        "scheduled_date",
        "subject",
    }
)

TEMPLATE_SPECIFIC_FIELD_NAMES = frozenset(
    {
        "attachment_ids",
        "auto_delete",
        "email_cc",
        "email_layout_xmlid",
        "email_to",
        "mail_server_id",
        "model",
        "partner_to",
        "report_template_ids",
        "res_id",
        "scheduled_date",
    }
)

RECIPIENT_FIELD_NAMES = frozenset({"email_cc", "email_to", "partner_to"})

ATTACHMENT_FIELD_NAMES = frozenset({"attachment_ids", "report_template_ids"})

SEND_RENDER_FIELDS = frozenset(
    {
        "attachment_ids",
        "auto_delete",
        "body_html",
        "email_cc",
        "email_from",
        "email_to",
        "mail_server_id",
        "model",
        "partner_to",
        "reply_to",
        "report_template_ids",
        "res_id",
        "scheduled_date",
        "subject",
    }
)

ACCUMULATED_VALUE_KEYS = frozenset({"attachment_ids", "attachments", "partner_ids"})

QWEB_EXPRESSION_ATTRIBUTES = frozenset(
    {
        "t-elif",
        "t-esc",
        "t-field",
        "t-foreach",
        "t-if",
        "t-log",
        "t-options",
        "t-out",
        "t-raw",
        "t-value",
    }
)

NO_RECORD_RES_ID = 0


_MODIFYING_STATEMENT = re.compile(
    r"(INSERT|UPDATE|DELETE|COPY|TRUNCATE)\b", re.IGNORECASE
)


def _iter_inline_expressions(source: str) -> Iterator[str]:
    for _string, expression, _default in parse_inline_template(source):
        if expression:
            yield expression


def _iter_qweb_expressions(node: etree._Element) -> Iterator[str]:
    for element in node.iter(etree.Element):
        for attribute, value in element.attrib.items():
            if attribute in QWEB_EXPRESSION_ATTRIBUTES or attribute.startswith(
                "t-att-"
            ):
                yield value
            elif attribute.startswith("t-attf-"):
                yield from _iter_inline_expressions(value)


def _parse_expression(expression: str) -> ast.AST | None:
    try:
        return ast.parse(expression.strip(), mode="eval")
    except SyntaxError, ValueError:
        return None


def _hasattr_guarded_chains(tree: ast.AST) -> list[list[str]]:
    chains = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "hasattr"
            and len(node.args) == 2
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            target = node.args[0]
            if isinstance(target, ast.Name):
                base = [target.id]
            elif isinstance(target, ast.Attribute):
                base = _attribute_chain(target)
            else:
                continue
            if base:
                chains.append([*base, node.args[1].value])
    return chains


def _attribute_chain(node: ast.Attribute) -> list[str] | None:
    names = []
    while isinstance(node, ast.Attribute):
        names.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    names.append(node.id)
    names.reverse()
    return names


def _merge_render_results(
    target: RenderResults, contribution: RenderResults
) -> RenderResults:
    for res_id, values in contribution.items():
        merged = target.setdefault(res_id, {})
        for key, value in values.items():
            if key in ACCUMULATED_VALUE_KEYS and isinstance(value, list):
                merged.setdefault(key, []).extend(value)
            else:
                merged[key] = value
    return target


class MailTemplate(models.Model):
    _name = "mail.template"
    _inherit = [
        "mixin.mail.attachment.owner",
        "mixin.mail.render",
        "mixin.template.reset",
    ]
    _description = "Email Templates"
    _order = "user_id, name, id"

    _unrestricted_rendering = True
    _dynamic_field_names = DYNAMIC_FIELD_NAMES

    @api.model
    def default_get(self, fields: list[str]) -> ValuesType:
        res = super().default_get(fields)
        if res.get("model"):
            res["model_id"] = self.env["ir.model"]._get(res.pop("model")).id
        return res

    name = fields.Char(translate=True)
    description = fields.Text(
        string="Template Description",
        translate=True,
        help="This field is used for internal description of the template's usage.",
    )
    active = fields.Boolean(default=True)
    template_category = fields.Selection(
        selection=[
            ("base_template", "Base Template"),
            ("hidden_template", "Hidden Template"),
            ("custom_template", "Custom Template"),
        ],
        compute="_compute_template_category",
        search="_search_template_category",
    )
    model_id: IrModel = fields.Many2one(
        comodel_name="ir.model",
        string="Applies to",
        domain=[("abstract", "=", False)],
        ondelete="cascade",
    )
    model = fields.Char(
        related="model_id.model",
        string="Related Document Model",
        readonly=True,
    )
    subject = fields.Char(
        translate=True,
        prefetch=True,
        help="Subject (placeholders may be used here)",
    )
    email_from = fields.Char(
        string="Send From",
        help="Sender address (placeholders may be used here). If not set, the default "
        "value will be the author's email alias if configured, or email address.",
    )
    user_id: ResUsers = fields.Many2one(
        comodel_name="res.users",
        string="Owner",
        domain="[('share', '=', False)]",
    )
    use_default_to = fields.Boolean(
        string="Default Recipients",
        default=True,
        help="Default recipients of the record:\n"
        "- partner (using id on a partner or the partner_id field) OR\n"
        "- email (using email_from or email field)",
    )
    email_to = fields.Char(
        string="To (Emails)",
        help="Comma-separated recipient addresses (placeholders may be used here)",
    )
    partner_to = fields.Char(
        string="To (Partners)",
        help="Comma-separated ids of recipient partners (placeholders may be used here)",
    )
    email_cc = fields.Char(
        string="Cc",
        help="Carbon copy recipients (placeholders may be used here)",
    )
    reply_to = fields.Char(
        help="Email address to which replies will be redirected when sending emails in mass; only used when the reply is not logged in the original discussion thread."
    )
    body_html = fields.Html(
        string="Body",
        translate=True,
        sanitize="email_outgoing",
        prefetch=True,
        render_engine="qweb",
        render_options={"post_process": True},
    )
    attachment_ids: IrAttachment = fields.Many2many(
        comodel_name="ir.attachment",
        relation="email_template_attachment_rel",
        column1="email_template_id",
        column2="attachment_id",
        string="Attachments",
        bypass_search_access=True,
    )
    report_template_ids: IrActionsReport = fields.Many2many(
        comodel_name="ir.actions.report",
        relation="mail_template_ir_actions_report_rel",
        column1="mail_template_id",
        column2="ir_actions_report_id",
        string="Dynamic Reports",
        domain="[('model', '=', model)]",
    )
    email_layout_xmlid = fields.Char(
        string="Email Notification Layout",
        copy=False,
    )
    mail_server_id: IrMail_Server = fields.Many2one(
        comodel_name="ir.mail_server",
        string="Outgoing Mail Server",
        index="btree_not_null",
        readonly=False,
        help="Optional preferred server for outgoing mails. If not set, the highest "
        "priority one will be used.",
    )
    scheduled_date = fields.Char(
        help="If set, the queue manager will send the email after the date. If not set, the email will be send as soon as possible. You can use dynamic expression."
    )
    auto_delete = fields.Boolean(
        default=True,
        help="This option permanently removes any track of email after it's been sent, including from the Technical menu in the Settings, in order to preserve storage space of your Odoo database.",
    )
    ref_ir_act_window: IrActionsAct_Window = fields.Many2one(
        comodel_name="ir.actions.act_window",
        string="Sidebar action",
        copy=False,
        readonly=True,
        help="Sidebar action to make this template available on records "
        "of the related document model",
    )

    can_write = fields.Boolean(
        compute="_compute_can_write",
        help="The current user can edit the template.",
    )
    is_template_editor = fields.Boolean(compute="_compute_is_template_editor")

    has_dynamic_reports = fields.Boolean(compute="_compute_has_dynamic_reports")
    has_mail_server = fields.Boolean(compute="_compute_has_mail_server")

    @api.depends("model")
    def _compute_has_dynamic_reports(self) -> None:
        models_with_reports = {
            model
            for (model,) in self.env["ir.actions.report"]
            .sudo()
            ._read_group(
                domain=[("model", "in", self.mapped("model"))],
                groupby=["model"],
            )
        }
        for template in self:
            template.has_dynamic_reports = template.model in models_with_reports

    @api.depends()
    def _compute_has_mail_server(self) -> None:
        has_mail_server = bool(self.env["ir.mail_server"].sudo().search([], limit=1))
        for template in self:
            template.has_mail_server = has_mail_server

    @api.depends("model")
    def _compute_render_model(self) -> None:
        for template in self:
            template.render_model = template.model

    @api.depends_context("uid")
    def _compute_can_write(self) -> None:
        writable_ids = set(self._filtered_access("write")._ids)
        for template in self:
            template.can_write = template.id in writable_ids

    @api.depends_context("uid")
    def _compute_is_template_editor(self) -> None:
        self.is_template_editor = self.env.user.has_group(
            "mail.group_mail_template_editor"
        )

    @api.model
    def _get_domain_module_xmlid(self) -> Domain:
        return Domain(
            "id",
            "in",
            self.env["ir.model.data"]
            .sudo()
            ._search([("model", "=", "mail.template"), ("module", "!=", "__export__")])
            .subselect("res_id"),
        )

    def _get_module_owned_ids(self) -> set[int]:
        if not self:
            return set()
        return {
            res_id
            for (res_id,) in self.env["ir.model.data"]
            .sudo()
            ._read_group(
                domain=[
                    ("model", "=", "mail.template"),
                    ("module", "!=", "__export__"),
                    ("res_id", "in", self.ids),
                ],
                groupby=["res_id"],
            )
        }

    @api.depends("active", "description")
    def _compute_template_category(self) -> None:
        deactivated = self.filtered(lambda template: not template.active)
        if deactivated:
            deactivated.template_category = "hidden_template"
        remaining = self - deactivated
        if not remaining:
            return
        module_owned_ids = remaining._get_module_owned_ids()
        for template in remaining:
            if template.id not in module_owned_ids:
                template.template_category = "custom_template"
            elif template.description:
                template.template_category = "base_template"
            else:
                template.template_category = "hidden_template"

    @api.model
    def _search_template_category(
        self, operator: str, value: Any
    ) -> Domain | NotImplementedType:
        if operator != "in":
            return NotImplemented

        module_owned = self._get_domain_module_xmlid()
        domain = Domain.FALSE

        if "hidden_template" in value:
            domain |= Domain("active", "=", False) | (
                Domain("active", "=", True)
                & Domain("description", "=", False)
                & module_owned
            )

        if "base_template" in value:
            domain |= (
                Domain("active", "=", True)
                & Domain("description", "!=", False)
                & module_owned
            )

        if "custom_template" in value:
            domain |= Domain("active", "=", True) & ~module_owned

        return domain

    @api.onchange("model")
    def _onchange_model(self) -> None:
        for template in self.filtered("model"):
            if upd_values := self._prepare_model_template_defaults(template.model):
                template.update(upd_values)

    def _get_render_error_label(self) -> str:
        if not self.id:
            return super()._get_render_error_label()
        return _(
            "Mail Template: '%(name)s' (ID: %(record_id)s)",
            name=self.name or _("Unnamed Mail Template"),
            record_id=self.id,
        )

    def _check_rendering(
        self,
        fnames: Collection[str] | None = None,
        render_options: dict | None = None,
    ) -> None:

        if self.env.context.get("install_mode"):
            return
        checked_fnames = self._get_dynamic_field_names()
        if fnames is not None:
            checked_fnames &= set(fnames)
        if not checked_fnames:
            return
        _debug.pipeline(
            "check_rendering", templates=self.ids, fields=sorted(checked_fnames)
        )
        for template in self:
            if failure := template._compile_dynamic_fields(checked_fnames):
                fname, error = failure
                _debug.logic(
                    "compile_failed",
                    template=template.id,
                    field=fname,
                    error=type(error).__name__,
                )
                raise template._prepare_rendering_error(fname, error) from error
        self._probe_rendering_samples(checked_fnames, render_options)

    def _probe_rendering_samples(
        self, fnames: Collection[str], render_options: dict | None
    ) -> None:
        samples = self.sudo()._get_rendering_samples()
        if not samples:
            return
        with _debug.perf(
            "probe_samples", cr=self.env.cr, templates=self.ids, samples=len(samples)
        ):
            failure = self.sudo()._render_dynamic_fields(
                samples, fnames, render_options
            )
        if not failure:
            return
        template_id, fname, error = failure
        _debug.logic(
            "probe_failed",
            template=template_id,
            field=fname,
            error=type(error).__name__,
        )
        _logger.info(
            "mail.template %s: field %s compiles but does not render on sample "
            "%s; saved anyway, sending on records of that shape will fail",
            template_id,
            fname,
            samples[self.browse(template_id).model],
            exc_info=error,
        )

    def _get_rendering_samples(self) -> dict[str, models.BaseModel]:

        samples = {}
        for model in set(self.mapped("model_id.model")):
            if not model or model not in self.env:
                continue
            if record := self.env[model].search([], limit=1):  # noqa: E8507  the loop is over distinct models, not records: one sample row per table
                samples[model] = record
        _debug.perf.count(
            "rendering_samples", templates=self.ids, models=sorted(samples)
        )
        return samples

    def _compile_dynamic_fields(
        self, fnames: Collection[str]
    ) -> tuple[str, Exception] | None:
        self.check_singleton()
        model = self.env.get(self.model)
        for fname in sorted(fnames):
            if not self[fname]:
                continue
            try:
                expressions = self._compile_field_expressions(fname)
                if model is not None:
                    guarded = [
                        chain
                        for expression in expressions
                        if (tree := _parse_expression(expression)) is not None
                        for chain in _hasattr_guarded_chains(tree)
                    ]
                    for expression in expressions:
                        if message := self._get_unknown_object_attribute_error(
                            expression, model, guarded
                        ):
                            raise AttributeError(message)
            except PG_RECOVERABLE_EXCEPTIONS:
                raise
            except Exception as error:
                return (fname, error)
        return None

    def _compile_field_expressions(self, fname: str) -> list[str]:
        self.check_singleton()
        source = str(self[fname])
        engine = getattr(self._fields[fname], "render_engine", "inline_template")
        if engine == "qweb":
            node = self._get_qweb_template_node(source)[0]
            expressions = list(_iter_qweb_expressions(node))
            self.env["ir.qweb"]._generate_code(node)
            return expressions
        if engine == "inline_template":
            expressions = list(_iter_inline_expressions(source))
            for expression in expressions:
                compile(expression, "<mail.template>", "eval")
            return expressions
        return []

    def _get_unknown_object_attribute_error(
        self,
        expression: str,
        model: models.BaseModel,
        guarded: Collection[list[str]] = (),
    ) -> str | None:
        tree = _parse_expression(expression)
        if tree is None:
            return None
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue
            chain = _attribute_chain(node)
            if not chain or chain[0] != "object":
                continue
            if any(chain[: len(guard)] == guard for guard in guarded):
                continue
            if message := self._get_unknown_model_attribute_error(chain[1:], model):
                return message
        return None

    def _get_unknown_model_attribute_error(
        self, names: list[str], model: models.BaseModel
    ) -> str | None:
        for name in names:
            if not hasattr(type(model), name):
                return _(
                    "%(model)s has no field or attribute '%(name)s'",
                    model=model._name,
                    name=name,
                )
            field = model._fields.get(name)
            if field is None or not field.relational:
                return None
            model = self.env[field.comodel_name]
        return None

    @contextlib.contextmanager
    def _probe_isolation(self) -> typing.Iterator[None]:

        cr = self.env.cr
        thread = threading.current_thread()
        hooks = getattr(thread, "query_hooks", None)
        if hooks is None:
            hooks = thread.query_hooks = []
        modified = False

        def watch(_cr, query, _params, _start, _delay):
            nonlocal modified
            if not modified:
                code = getattr(query, "code", query)
                modified = bool(_MODIFYING_STATEMENT.match(str(code).lstrip()))

        savepoint = cr.savepoint()
        hooks.append(watch)
        try:
            yield

            self.env.flush_all()
        except BaseException:
            modified = True
            raise
        finally:
            hooks.remove(watch)
            _debug.logic(
                "probe_isolation_closed", templates=self.ids, rolled_back=modified
            )
            savepoint.close(rollback=modified)

    def _render_dynamic_fields(
        self,
        samples: dict[str, models.BaseModel],
        fnames: Collection[str],
        render_options: dict | None,
    ) -> tuple[int, str, Exception] | None:
        failures: list[tuple[int, str, Exception]] = []
        with self._probe_isolation():
            for template in self:
                record = samples.get(template.model_id.model)
                if not record:
                    continue
                for fname in sorted(fnames):
                    try:
                        template._render_field(
                            fname, record.ids, options=render_options
                        )
                    except PG_RECOVERABLE_EXCEPTIONS:
                        raise
                    except Exception as error:
                        failures.append((template.id, fname, error))
                        break
                if failures:
                    break
        return failures[0] if failures else None

    def _prepare_rendering_error(self, fname: str, error: Exception) -> ValidationError:
        self.check_singleton()
        _logger.info(
            "mail.template %s: field %s does not compile",
            self.id,
            fname,
            exc_info=error,
        )
        return ValidationError(
            _(
                "Oops! We couldn't save your template due to an issue.\n\n"
                "Field: %(field_name)s\n"
                "Error: %(error_details)s\n\n"
                "Correct it and try again.",
                field_name=self._fields[fname].string or fname,
                error_details=str(error),
            )
        )

    @api.constrains("model_id")
    def _check_model_not_abstract(self) -> None:
        for model in set(self.mapped("model_id.model")):
            if model in self.env and self.env[model]._abstract:
                raise ValidationError(
                    _("You may not define a template on an abstract model: %s", model)
                )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        records = super().create(vals_list)
        _debug.lifecycle(
            "create",
            count=len(records),
            models=sorted({vals.get("model") or "" for vals in vals_list}),
        )
        records._check_rendering(fnames={fname for vals in vals_list for fname in vals})
        records._update_attachment_ownership(self._get_linked_attachment_ids(vals_list))
        return records

    def write(self, vals: ValuesType) -> Literal[True]:
        super().write(vals)
        _debug.lifecycle("write", templates=self.ids, fields=list(vals))
        self._check_rendering(
            fnames=None if not {"model", "model_id"}.isdisjoint(vals) else vals.keys()
        )
        if "attachment_ids" in vals:
            self._update_attachment_ownership(self._get_linked_attachment_ids([vals]))
        return True

    def unlink(self) -> Literal[True]:
        _debug.lifecycle("unlink", templates=self.ids)
        self.unlink_action()
        return super().unlink()

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        vals_list = super().copy_data(default=default)
        for vals, template in zip(vals_list, self, strict=True):
            if "name" not in (default or {}) and vals.get("name") == template.name:
                vals["name"] = self.env._("%s (copy)", template.name)
        return vals_list

    def copy_translations(self, new: Self, excluded: Collection[str] = ()) -> None:
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )

    def copy(self, default: ValuesType | None = None) -> Self:
        default = dict(default or {})
        copy_attachments = "attachment_ids" not in default
        if copy_attachments:
            default["attachment_ids"] = False
        copies = super().copy(default=default)

        if copy_attachments:
            for copy, original in zip(copies, self, strict=True):
                if original.attachment_ids:
                    copy.attachment_ids = original.attachment_ids.copy(
                        default={"res_id": copy.id, "res_model": original._name}
                    )
        return copies

    def unlink_action(self) -> bool:
        self.ref_ir_act_window.unlink()
        return True

    def create_action(self) -> bool:
        self.unlink_action()
        view = self.env.ref("mail.email_compose_message_wizard_form")
        actions = self.env["ir.actions.act_window"].create(
            [
                {
                    "name": _("Send Mail (%s)", template.name or template.display_name),
                    "type": "ir.actions.act_window",
                    "res_model": "mail.compose.message",
                    "context": repr(
                        {
                            "default_composition_mode": "mass_mail",
                            "default_model": template.model,
                            "default_template_id": template.id,
                        }
                    ),
                    "view_mode": "form,list",
                    "view_id": view.id,
                    "target": "new",
                    "binding_model_id": template.model_id.id,
                }
                for template in self
            ]
        )
        for template, action in zip(self, actions, strict=True):
            template.ref_ir_act_window = action
        _debug.lifecycle("actions_created", templates=self.ids, actions=actions.ids)
        return True

    def action_view_mail_preview(self) -> dict:
        self.check_singleton()
        action = self.env.ref("mail.mail_template_preview_action")._get_action_dict()
        action.update(
            {
                "name": _(
                    'Template Preview: "%(template_name)s"', template_name=self.name
                )
            }
        )
        return action

    def _render_report_per_record(
        self, report: IrActionsReport, res_ids: list[int]
    ) -> dict[int, tuple[bytes, str]]:
        IrActionsReport = self.env["ir.actions.report"]

        if report.report_type in ("qweb-html", "qweb-pdf"):
            batched_streams = self._get_report_streams_batch(report, res_ids)
            _debug.logic(
                "report_render_strategy",
                template=self.id,
                report=report.id,
                records=len(res_ids),
                by="batch" if batched_streams is not None else "per_record",
            )
            if batched_streams is not None:
                return {
                    res_id: (stream.getvalue(), "pdf")
                    for res_id, stream in batched_streams.items()
                }
            return {
                res_id: IrActionsReport._render_qweb_pdf(report, [res_id])
                for res_id in res_ids
            }

        rendered = {}
        for res_id in res_ids:
            render_res = IrActionsReport._render(report, [res_id])
            if not render_res:
                raise UserError(
                    _("Unsupported report type %s found.", report.report_type)
                )
            rendered[res_id] = render_res
        return rendered

    def _get_report_streams_batch(
        self, report: IrActionsReport, res_ids: list[int]
    ) -> dict | None:
        IrActionsReport = self.env["ir.actions.report"]
        if (
            len(res_ids) < 2
            or report.attachment
            or not IrActionsReport._is_pdf_rendering_enabled()
        ):
            return None
        collected, report_type = IrActionsReport._pre_render_qweb_pdf(
            report, res_ids=list(res_ids)
        )
        if report_type != "pdf":
            return None
        streams = {}
        for res_id in res_ids:
            stream = (collected.get(res_id) or {}).get("stream")
            if not stream:
                return None
            streams[res_id] = stream
        return streams

    def _prepare_attachment_vals(
        self,
        res_ids: Collection[int],
        render_fields: Collection[str],
        render_results: RenderResults | None = None,
    ) -> RenderResults:
        self.check_singleton()
        res_ids = list(res_ids)
        render_fields = set(render_fields)
        contribution: RenderResults = {}

        if "attachment_ids" in render_fields and self.attachment_ids:
            for res_id in res_ids:
                contribution.setdefault(res_id, {})["attachment_ids"] = (
                    self.attachment_ids.ids
                )

        if "report_template_ids" in render_fields and res_ids:
            for res_id in res_ids:
                contribution.setdefault(res_id, {}).setdefault("attachments", [])
            if self.report_template_ids:
                records_by_id = {
                    record.id: record for record in self._get_records(res_ids)
                }
                for report in self.report_template_ids:
                    with _debug.perf(
                        "report_rendered",
                        cr=self.env.cr,
                        template=self.id,
                        report=report.id,
                        records=len(res_ids),
                    ):
                        rendered = self._render_report_per_record(report, res_ids)
                    for res_id, (report_content, report_format) in rendered.items():
                        report_name = self._get_report_attachment_name(
                            report, records_by_id[res_id], report_format
                        )
                        contribution[res_id]["attachments"].append(
                            (report_name, base64.b64encode(report_content))
                        )

        if render_fields & ATTACHMENT_FIELD_NAMES and self._is_thread_model():
            records_attachments = self._get_records(
                res_ids
            )._process_attachments_for_template_post(self)
            for res_id, additional_attachments in records_attachments.items():
                if not additional_attachments:
                    continue
                values = contribution.setdefault(res_id, {})
                for key in ("attachment_ids", "attachments"):
                    if additional_attachments.get(key):
                        values.setdefault(key, []).extend(additional_attachments[key])

        return _merge_render_results(
            {} if render_results is None else render_results, contribution
        )

    def _get_report_attachment_name(
        self, report: IrActionsReport, record: models.BaseModel, report_format: str
    ) -> str:
        name = ""
        if report.print_report_name:
            name = safe_eval(report.print_report_name, {"object": record, "time": time})
        name = str(name or "") or _("Report - %(report_name)s", report_name=report.name)
        extension = "." + report_format
        return name if name.endswith(extension) else name + extension

    def _prepare_recipient_vals(
        self,
        res_ids: Collection[int],
        render_fields: Collection[str],
        allow_suggested: bool = False,
        find_or_create_partners: bool = False,
        render_results: RenderResults | None = None,
    ) -> RenderResults:
        self.check_singleton()
        res_ids = list(res_ids)
        render_fields = set(render_fields)
        contribution: RenderResults = {}
        partner_to_by_res_id = {}
        emails_by_res_id: dict[int, dict[str, str]] = {}

        if self.use_default_to and self.model:
            if allow_suggested:
                self._update_recipient_vals_suggested(
                    res_ids,
                    contribution,
                    emails_by_res_id,
                    find_or_create_partners,
                )
            else:
                default_recipients = self._get_records(
                    res_ids
                )._message_get_default_recipients()
                for res_id, recipients in default_recipients.items():
                    values = dict(recipients)
                    partner_to_by_res_id[res_id] = values.pop("partner_to", "")
                    emails_by_res_id.setdefault(res_id, {}).update(
                        {
                            key: values.pop(key)
                            for key in ("email_to", "email_cc")
                            if key in values
                        }
                    )
                    if values:
                        contribution.setdefault(res_id, {}).update(values)
        else:
            for field in RECIPIENT_FIELD_NAMES & render_fields:
                generated_field_values = self._render_field(field, res_ids)
                for res_id in res_ids:
                    value = generated_field_values[res_id]
                    if field == "partner_to":
                        partner_to_by_res_id[res_id] = value
                    else:
                        emails_by_res_id.setdefault(res_id, {})[field] = value

        for res_id in res_ids:
            incoming = (render_results or {}).get(res_id)
            if incoming and "partner_to" in incoming:
                partner_to_by_res_id.setdefault(res_id, incoming.pop("partner_to"))

        if find_or_create_partners:
            self._update_recipient_vals_partner_ids(
                res_ids, contribution, emails_by_res_id
            )

        for res_id, emails in emails_by_res_id.items():
            contribution.setdefault(res_id, {}).update(emails)

        self._update_partner_to(partner_to_by_res_id, contribution)

        _debug.logic(
            "recipients_prepared",
            template=self.id,
            records=len(res_ids),
            by="default_to" if self.use_default_to and self.model else "fields",
            suggested=allow_suggested,
            find_or_create=find_or_create_partners,
            partner_to=len(partner_to_by_res_id),
        )
        return _merge_render_results(
            {} if render_results is None else render_results, contribution
        )

    def _update_recipient_vals_suggested(
        self,
        res_ids: list[int],
        contribution: RenderResults,
        emails_by_res_id: dict[int, dict[str, str]],
        find_or_create_partners: bool,
    ) -> None:
        suggested_recipients = self._get_records(
            res_ids
        )._message_get_suggested_recipients_batch(
            reply_discussion=True,
            no_create=not find_or_create_partners,
        )
        for res_id, suggested_list in suggested_recipients.items():
            contribution.setdefault(res_id, {})["partner_ids"] = [
                r["partner_id"] for r in suggested_list if r["partner_id"]
            ]
            emails_by_res_id.setdefault(res_id, {})["email_to"] = ", ".join(
                tools.mail.formataddr((r["name"] or "", r["email"] or ""))
                for r in suggested_list
                if not r["partner_id"]
            )

    def _update_recipient_vals_partner_ids(
        self,
        res_ids: list[int],
        contribution: RenderResults,
        emails_by_res_id: dict[int, dict[str, str]],
    ) -> None:
        records = self._get_records(res_ids)
        records_emails = {}
        for record in records:
            emails = emails_by_res_id.pop(record.id, {})
            records_emails[record] = tools.email_split(
                emails.get("email_to", "")
            ) + tools.email_split(emails.get("email_cc", ""))
        resolved = records._partner_get_or_create_from_emails(records_emails)
        _debug.logic(
            "recipient_partners_resolved",
            template=self.id,
            records=len(records),
            emails=sum(len(emails) for emails in records_emails.values()),
            partners=sum(len(partners) for partners in resolved.values()),
        )
        for res_id, partners in resolved.items():
            contribution.setdefault(res_id, {}).setdefault("partner_ids", []).extend(
                partners.ids
            )

    def _update_partner_to(
        self, partner_to_by_res_id: dict[int, str], contribution: RenderResults
    ) -> None:

        parsed = {
            res_id: self._parse_partner_to(partner_to)
            for res_id, partner_to in partner_to_by_res_id.items()
            if partner_to
        }
        if not parsed:
            return
        existing_pids = set(
            self.env["res.partner"]
            .sudo()
            .browse(list(set().union(*(map(set, parsed.values())))))
            .exists()
            ._ids
        )
        _debug.logic(
            "partner_to_resolved",
            template=self.id,
            records=len(parsed),
            existing=len(existing_pids),
        )
        for res_id, pids in parsed.items():
            contribution.setdefault(res_id, {}).setdefault("partner_ids", []).extend(
                pid for pid in dict.fromkeys(pids) if pid in existing_pids
            )

    def _prepare_scheduled_date_vals(
        self, res_ids: Collection[int], render_results: RenderResults | None = None
    ) -> RenderResults:
        self.check_singleton()
        res_ids = list(res_ids)
        scheduled_dates = self._render_field("scheduled_date", res_ids)
        contribution = {
            res_id: {
                "scheduled_date": self.env["mail.mail"]._normalize_scheduled_date(
                    scheduled_dates.get(res_id)
                )
            }
            for res_id in res_ids
        }
        return _merge_render_results(
            {} if render_results is None else render_results, contribution
        )

    def _prepare_static_vals(
        self,
        res_ids: Collection[int],
        render_fields: Collection[str],
        render_results: RenderResults | None = None,
    ) -> RenderResults:
        self.check_singleton()
        render_fields = set(render_fields)
        static = {
            "auto_delete": self.auto_delete,
            "email_layout_xmlid": self.email_layout_xmlid,
            "mail_server_id": self.mail_server_id.id,
            "model": self.model,
        }
        contribution = {}
        for res_id in res_ids:
            values = {
                fname: value
                for fname, value in static.items()
                if fname in render_fields
            }
            if "res_id" in render_fields:
                values["res_id"] = res_id or False
            contribution[res_id] = values
        return _merge_render_results(
            {} if render_results is None else render_results, contribution
        )

    def _prepare_mail_vals(
        self,
        res_ids: Collection[int],
        render_fields: Collection[str],
        recipients_allow_suggested: bool = False,
        find_or_create_partners: bool = False,
        res_ids_lang: dict[int, str] | None = None,
    ) -> RenderResults:
        self.check_singleton()
        self._check_has_model()
        res_ids = list(res_ids)
        render_fields_set = set(render_fields)
        fields_torender = render_fields_set - TEMPLATE_SPECIFIC_FIELD_NAMES

        render_results: RenderResults = {}
        per_lang = self._classify_per_lang(res_ids, res_ids_lang=res_ids_lang)
        _debug.pipeline(
            "prepare_mail_vals",
            template=self.id,
            records=len(res_ids),
            fields=sorted(fields_torender),
            langs=len(per_lang),
        )
        for template, template_res_ids in per_lang.values():
            for field in fields_torender:
                generated_field_values = template._render_field(field, template_res_ids)
                _merge_render_results(
                    render_results,
                    {
                        res_id: {field: field_value}
                        for res_id, field_value in generated_field_values.items()
                    },
                )

            if render_fields_set & RECIPIENT_FIELD_NAMES:
                template._prepare_recipient_vals(
                    template_res_ids,
                    render_fields_set,
                    render_results=render_results,
                    allow_suggested=recipients_allow_suggested,
                    find_or_create_partners=find_or_create_partners,
                )

            if "scheduled_date" in render_fields_set:
                template._prepare_scheduled_date_vals(
                    template_res_ids, render_results=render_results
                )

            template._prepare_static_vals(
                template_res_ids, render_fields_set, render_results=render_results
            )

            if render_fields_set & ATTACHMENT_FIELD_NAMES:
                template._prepare_attachment_vals(
                    template_res_ids, render_fields_set, render_results=render_results
                )

        return render_results

    @classmethod
    def _parse_partner_to(cls, partner_to: Any) -> list[int]:
        try:
            parsed = literal_eval(partner_to or "[]")
        except ValueError, SyntaxError, TypeError, MemoryError, RecursionError:
            parsed = str(partner_to).split(",")
        if not isinstance(parsed, (list, tuple, set)):
            parsed = [parsed]
        partner_ids = []
        for pid in parsed:
            if isinstance(pid, str):
                if pid.strip().isdigit():
                    partner_ids.append(int(pid.strip()))
            elif isinstance(pid, int) and not isinstance(pid, bool) and pid > 0:
                partner_ids.append(pid)
        return partner_ids

    def _get_model(self) -> models.Model:
        self._check_has_model()
        return self.env[self.model]

    def _get_records(self, res_ids: Collection[int]) -> models.Model:
        return self._get_model().browse(res_ids)

    def _is_thread_model(self) -> bool:
        return bool(
            self.model
            and isinstance(self.env[self.model], self.pool["mixin.mail.thread"])
        )

    def _check_has_model(self) -> None:
        if not self.model:
            raise UserError(
                _(
                    "Mail template %(template_name)s has no target model, so it cannot "
                    "be rendered or sent.",
                    template_name=self.display_name,
                )
            )

    def _send_check_access(self, res_ids: Collection[int]) -> None:
        self._get_records(res_ids).check_access("read")

    def send_mail(
        self,
        res_id: int,
        force_send: bool = False,
        raise_exception: bool = False,
        email_values: dict | None = None,
        email_layout_xmlid: str | Literal[False] = False,
    ) -> int:
        self.check_singleton()
        return self.send_mail_batch(
            [res_id],
            force_send=force_send,
            raise_exception=raise_exception,
            email_values=email_values,
            email_layout_xmlid=email_layout_xmlid,
        )[0].id

    def send_mail_batch(
        self,
        res_ids: Collection[int],
        force_send: bool = False,
        raise_exception: bool = False,
        email_values: dict | None = None,
        email_layout_xmlid: str | Literal[False] = False,
    ) -> MailMail:
        self.check_singleton()
        res_ids = list(dict.fromkeys(res_ids))
        self._send_check_access(res_ids)
        layout_xmlid = email_layout_xmlid or self.email_layout_xmlid

        mails_sudo = self.env["mail.mail"].sudo()
        batch_size = self.env["mail.mail"]._get_send_batch_size()
        with _debug.perf(
            "send_mail_batch",
            cr=self.env.cr,
            template=self.id,
            records=len(res_ids),
            batch_size=batch_size,
            layout=layout_xmlid or None,
            force_send=force_send,
        ) as span:
            for res_ids_chunk in batched(res_ids, batch_size, strict=False):
                mails_sudo += self._send_chunk(
                    list(res_ids_chunk), layout_xmlid, email_values
                )
            span.set(mails=len(mails_sudo))

        if force_send:
            mails_sudo.send(raise_exception=raise_exception)
        return mails_sudo

    def _send_chunk(
        self,
        res_ids: list[int],
        layout_xmlid: str | Literal[False],
        email_values: dict | None,
    ) -> MailMail:
        self.check_singleton()
        res_ids_lang = self._get_res_ids_lang(res_ids)
        values_by_res_id = self._prepare_mail_vals(
            res_ids, SEND_RENDER_FIELDS, res_ids_lang=res_ids_lang
        )
        records = self._get_model().browse(res_ids).with_prefetch(res_ids)
        values_list = [values_by_res_id[res_id] for res_id in res_ids]
        attachments_list = [values.pop("attachments", []) for values in values_list]

        res_ids_companies = (
            records._mail_get_companies(default=self.env.company)
            if layout_xmlid
            else {}
        )
        for record, values in zip(records, values_list, strict=True):
            self._finalize_mail_vals(
                values,
                record,
                layout_xmlid,
                res_ids_lang.get(record.id),
                res_ids_companies.get(record.id),
                email_values,
            )

        mails = self.env["mail.mail"].sudo().create(values_list)
        _debug.pipeline(
            "send_chunk",
            template=self.id,
            records=len(res_ids),
            mails=len(mails),
            langs=len(set(res_ids_lang.values())),
            attachments=sum(len(a) for a in attachments_list),
        )
        self._attach_rendered_reports(mails, attachments_list)
        return mails

    def _finalize_mail_vals(
        self,
        values: dict[str, Any],
        record: models.BaseModel,
        layout_xmlid: str | Literal[False],
        lang: str | Literal[False] | None,
        company: models.BaseModel | None,
        email_values: dict | None,
    ) -> None:
        self.check_singleton()
        values["recipient_ids"] = [
            Command.link(pid) for pid in (values.get("partner_ids") or [])
        ]
        values["attachment_ids"] = [
            Command.link(aid) for aid in (values.get("attachment_ids") or [])
        ]
        values.update(email_values or {})

        if "email_from" in values and not values.get("email_from"):
            values.pop("email_from")

        if layout_xmlid:
            lang = lang or self.env.lang
            values["body_html"] = self.with_context(lang=lang)._render_encapsulate(
                layout_xmlid,
                values.get("body_html", ""),
                add_context={
                    "company": company or self.env.company,
                    "model_description": self.env["ir.model"]
                    ._get(self.model)
                    .with_context(lang=lang)
                    .display_name,
                },
                context_record=record.with_context(lang=lang),
            )
        values.setdefault("body", values.get("body_html", ""))

    def _attach_rendered_reports(
        self, mails: MailMail, attachments_list: list[list[tuple[str, bytes]]]
    ) -> None:

        attachment_vals, owners = [], []
        for mail, attachments in zip(mails, attachments_list, strict=True):
            for name, datas in attachments:
                attachment_vals.append(
                    {
                        "name": name,
                        "datas": datas,
                        "type": "binary",
                        "res_model": "mail.message",
                        "res_id": mail.mail_message_id.id,
                    }
                )
                owners.append(mail)
        if not attachment_vals:
            return

        created = (
            self.env["ir.attachment"]
            .sudo()
            .with_context(default_type=None)
            .create(attachment_vals)
        )
        messages = (
            self.env["mail.message"]
            .sudo()
            .browse([mail.mail_message_id.id for mail in owners])
        )
        relation = self.env["mail.message"]._fields["attachment_ids"]
        self.env.execute_query(
            SQL(
                """
                INSERT INTO %(table)s (%(column1)s, %(column2)s)
                     SELECT * FROM unnest(%(message_ids)s::int[], %(attachment_ids)s::int[])
                ON CONFLICT DO NOTHING
                """,
                table=SQL.identifier(relation.relation),
                column1=SQL.identifier(relation.column1),
                column2=SQL.identifier(relation.column2),
                message_ids=messages.ids,
                attachment_ids=created.ids,
            )
        )
        touched = self.env["mail.message"].sudo().browse(set(messages.ids))
        touched.invalidate_recordset(["attachment_ids"])
        mails.invalidate_recordset(["attachment_ids"])
        touched.modified(["attachment_ids"])
        _debug.lifecycle(
            "reports_attached",
            template=self.id,
            mails=len(set(messages.ids)),
            attachments=len(created),
        )

    def _has_unsafe_expression_template_qweb(
        self, template_src: str, model: str, fname: str | None = None
    ) -> bool:
        if self._expression_is_default(template_src, model, fname):
            return False
        return super()._has_unsafe_expression_template_qweb(
            template_src, model, fname=fname
        )

    def _has_unsafe_expression_template_inline_template(
        self, template_txt: str, model: str, fname: str | None = None
    ) -> bool:
        if self._expression_is_default(template_txt, model, fname):
            return False
        return super()._has_unsafe_expression_template_inline_template(
            template_txt, model, fname=fname
        )

    def _expression_is_default(
        self, source: str, model: str, fname: str | None
    ) -> bool:
        if not fname or not model:
            return False
        return source == self._prepare_model_template_defaults(model).get(fname)

    @api.model
    def _prepare_model_template_defaults(self, model: str) -> dict:
        if model not in self.env:
            return {}
        defaults = getattr(self.env[model], "_mail_template_default_values", None)
        return (defaults and defaults()) or {}
