import copy
import datetime
import logging
import typing
from collections.abc import Callable, Collection
from typing import Any, Literal, Self

import babel
from lxml import etree, html
from markupsafe import Markup

from odoo import _, api, fields, models, tools
from odoo.api import ValuesType
from odoo.db.errors import PG_RECOVERABLE_EXCEPTIONS
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools.mail import (
    is_html_empty,
    prepend_html_content,
    replace_local_links,
)
from odoo.tools.rendering_tools import (
    BINARY_TYPES,
    QWebError,
    StaticRenderUnsupported,
    compile_static_template,
    convert_inline_template_to_qweb,
    parse_inline_template,
    render_inline_template,
    render_static_program,
    renders_as_no_value,
    template_env_globals,
)

from odoo.addons.base.models.ir_qweb import RenderScopedDict

if typing.TYPE_CHECKING:
    from odoo.api import Environment

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

BYPASS_RESTRICTED_RENDERING = object()

TEMPLATE_FIELD_TYPES = ("char", "text", "html")

MAIL_RENDER_QWEB_CONTEXT = {"mail_render_format_values": True}

QWEB_RENDER_OPTIONS = frozenset({"preserve_comments"})

ENCAPSULATE_DEFAULTS = {
    "author_user": False,
    "button_access": False,
    "email_add_signature": False,
    "has_button_access": False,
    "is_html_empty": is_html_empty,
    "show_unfollow": False,
    "signature": "",
    "website_url": "",
}

ENCAPSULATE_CONTEXT_DEFAULTS = {
    "email_notification_allow_footer": False,
    "email_notification_allow_header": True,
    "email_notification_force_footer": False,
    "email_notification_force_header": False,
}


def format_date(
    env: Environment,
    date: datetime.datetime | datetime.date | str,
    pattern: str | Literal[False] = False,
    lang_code: str | Literal[False] = False,
) -> str | datetime.datetime | datetime.date:
    try:
        return tools.format_date(env, date, date_format=pattern, lang_code=lang_code)
    except babel.core.UnknownLocaleError:
        return date


def format_datetime(
    env: Environment,
    dt: datetime.datetime | str,
    tz: str | Literal[False] = False,
    dt_format: str | Literal[False] = False,
    lang_code: str | Literal[False] = False,
) -> str | datetime.datetime:
    try:
        return tools.format_datetime(
            env, dt, tz=tz, dt_format=dt_format, lang_code=lang_code
        )
    except babel.core.UnknownLocaleError:
        return dt


def format_time(
    env: Environment,
    time: datetime.time | datetime.datetime | str,
    tz: str | Literal[False] = False,
    time_format: str | Literal[False] = False,
    lang_code: str | Literal[False] = False,
) -> str | datetime.time | datetime.datetime:
    try:
        return tools.format_time(
            env, time, tz=tz, time_format=time_format, lang_code=lang_code
        )
    except babel.core.UnknownLocaleError:
        return time


def format_amount(
    env: Environment,
    amount: float,
    currency: models.BaseModel,
    lang_code: str | Literal[False] = False,
) -> str | float:
    try:
        return tools.format_amount(env, amount, currency, lang_code)
    except babel.core.UnknownLocaleError:
        return amount


class MixinMailRender(models.AbstractModel):
    _name = "mixin.mail.render"
    _description = "Mail Render Mixin"

    _unrestricted_rendering = False

    _dynamic_field_names = None

    lang = fields.Char(
        string="Language",
        help="Optional translation language (ISO code) to select when sending out an email. "
        "If not set, the main partner's language will be used. This should usually be a placeholder expression "
        "that provides the appropriate language, e.g. {{ object.partner_id.lang }}.",
    )
    render_model = fields.Char(
        string="Rendering Model",
        compute="_compute_render_model",
        store=False,
    )

    def _compute_render_model(self) -> None:
        self.render_model = False

    def _is_valid_field_parameter(self, field: fields.Field, name: str) -> bool:
        return name in [
            "render_engine",
            "render_options",
        ] or super()._is_valid_field_parameter(field, name)

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        records = super().create(vals_list)
        if self._unrestricted_rendering:
            records._check_access_right_dynamic_template()
        return records

    def write(self, vals: ValuesType) -> Literal[True]:
        if not self._unrestricted_rendering:
            return super().write(vals)

        dynamic_fnames = self._get_dynamic_field_names()
        written = vals.keys() & dynamic_fnames
        may_move_model = not vals.keys() <= dynamic_fnames
        models_before = (
            {record.id: record.render_model for record in self}
            if may_move_model
            else {}
        )

        result = super().write(vals)

        moved = (
            self.filtered(
                lambda record: record.render_model != models_before[record.id]
            )
            if may_move_model
            else self.browse()
        )
        _debug.logic(
            "write_dynamic_checked",
            model=self._name,
            records=self.ids,
            written=sorted(written),
            moved=len(moved),
        )
        if rest := self - moved:
            if written:
                rest._check_access_right_dynamic_template(fnames=written)
        if moved:
            moved._check_access_right_dynamic_template()
        return result

    def _update_field_translations(
        self,
        field_name: str,
        translations: dict[str, str | Literal[False] | dict[str, str]],
        digest: Callable[[str], str] | None = None,
        source_lang: str = "",
    ) -> bool:
        res = super()._update_field_translations(
            field_name, translations, digest=digest, source_lang=source_lang
        )
        if self._unrestricted_rendering and field_name in (
            self._get_dynamic_field_names()
        ):
            for lang in translations:
                localized = self.with_context(lang=lang)
                localized._check_access_right_dynamic_template(fnames={field_name})
                localized._check_rendering(fnames={field_name})
        return res

    def _check_rendering(
        self,
        fnames: Collection[str] | None = None,
        render_options: dict | None = None,
    ) -> None:
        return

    def _replace_local_links(
        self,
        html_content: str,
        base_url: str | Callable[[], str] | None = None,
    ) -> str:
        def resolve() -> str:
            if base_url:
                return base_url() if callable(base_url) else base_url
            return self.env["ir.config_parameter"].sudo().get_param("web.base.url")

        return replace_local_links(html_content, resolve)

    @api.model
    def _render_encapsulate(
        self,
        layout_xmlid: str,
        html_content: str,
        add_context: dict | None = None,
        context_record: models.BaseModel | None = None,
    ) -> Markup:
        template_ctx = self._render_encapsulate_context(
            html_content, add_context or {}, context_record
        )
        with _debug.perf(
            "encapsulate",
            cr=self.env.cr,
            layout=layout_xmlid,
            lang=template_ctx["lang"],
            record=context_record.id if context_record else None,
        ):
            rendered = self.env["ir.qweb"]._render(
                layout_xmlid,
                template_ctx,
                minimal_qcontext=True,
                raise_if_not_found=False,
                lang=template_ctx["lang"],
            )
        if not rendered:
            _debug.logic("encapsulate_layout_missing", layout=layout_xmlid)
            _logger.warning(
                "QWeb template %s not found when rendering encapsulation template; "
                "sending the body without layout.",
                layout_xmlid,
            )
            return self._replace_local_links(html_content)
        return self._replace_local_links(rendered)

    @api.model
    def _render_encapsulate_context(
        self,
        html_content: str,
        add_context: dict,
        context_record: models.BaseModel | None,
    ) -> dict:
        record_name = add_context.get("record_name")
        if record_name is None:
            record_name = context_record.display_name if context_record else ""
            add_context = {**add_context, "record_name": record_name}
        subtype = add_context.get("subtype", self.env["mail.message.subtype"].sudo())
        template_ctx = {
            "body": html_content,
            "record": context_record,
            "record_name": record_name,
            "subtype": subtype,
            "subtitles": [record_name],
            "tracking_values": [],
            "lang": self.env.lang,
            **ENCAPSULATE_DEFAULTS,
            **{
                key: self.env.context.get(key, default)
                for key, default in ENCAPSULATE_CONTEXT_DEFAULTS.items()
            },
            **add_context,
        }
        if not template_ctx.get("message"):
            template_ctx["message"] = self._render_encapsulate_message(
                html_content, context_record
            )
        if "is_discussion" not in add_context:
            template_ctx["is_discussion"] = bool(subtype) and subtype.id == self.env[
                "ir.model.data"
            ]._xmlid_to_res_id("mail.mt_comment")
        if "model_description" not in add_context:
            template_ctx["model_description"] = (
                context_record.with_context(
                    lang=template_ctx["lang"]
                )._get_model_description(context_record._name)
                if context_record and hasattr(context_record, "_get_model_description")
                else False
            )
        if "company" not in add_context:
            template_ctx["company"] = (
                context_record._mail_get_companies(default=self.env.company)[
                    context_record.id
                ]
                if context_record
                else self.env.company
            )
        return template_ctx

    @api.model
    def _render_encapsulate_message(
        self, html_content: str, context_record: models.BaseModel | None
    ) -> models.BaseModel:
        msg_vals = {"body": html_content}
        if context_record:
            msg_vals.update(
                {"model": context_record._name, "res_id": context_record.id}
            )
        return self.env["mail.message"].sudo().new(msg_vals)

    @api.model
    def _prepend_preview(self, html_content: str, preview: str | Literal[False]) -> str:
        preview = preview.strip() if preview else preview
        if not preview:
            return html_content

        html_preview = Markup("""
                <div style="display:none;font-size:1px;height:0px;width:0px;opacity:0;">
                    {}
                </div>
            """).format(convert_inline_template_to_qweb(preview))
        return prepend_html_content(html_content, html_preview)

    def _is_restricted(self) -> bool:
        return (
            not self._unrestricted_rendering
            and self.env.context.get("bypass_restricted_rendering")
            is not BYPASS_RESTRICTED_RENDERING
            and not self.env.is_admin()
            and not self.env.user.has_group("mail.group_mail_template_editor")
        )

    def _get_dynamic_field_names(self) -> set[str]:
        if self._dynamic_field_names is not None:
            return set(self._dynamic_field_names)
        return {
            fname
            for fname, field in self._fields.items()
            if field.type in TEMPLATE_FIELD_TYPES and field.store
        }

    def _has_unsafe_expression(self, fnames: set | None = None) -> bool:
        scanned = self._get_dynamic_field_names()
        if fnames is not None:
            scanned &= fnames
        if not scanned:
            return False
        for template in self.sudo():
            for fname in sorted(scanned):
                engine = getattr(
                    template._fields[fname], "render_engine", "inline_template"
                )
                if engine == "qweb_view":
                    continue
                check = (
                    template._has_unsafe_expression_template_qweb
                    if engine == "qweb"
                    else template._has_unsafe_expression_template_inline_template
                )
                if check(template[fname], template.render_model, fname):
                    _debug.logic(
                        "unsafe_expression",
                        model=self._name,
                        record=template.id,
                        field=fname,
                        engine=engine,
                    )
                    return True
        return False

    @api.model
    def _has_unsafe_expression_template_qweb(
        self, template_src: str, model: str, fname: str | None = None
    ) -> bool:
        if template_src:
            try:
                node = self._get_qweb_template_node(str(template_src))[0]
                self.env["ir.qweb"].with_context(
                    raise_on_forbidden_code_for_model=model
                )._generate_code(node)
            except PermissionError:
                return True
            except PG_RECOVERABLE_EXCEPTIONS:
                raise
            except Exception:
                _debug.logic("qweb_check_compile_failed", model=model, field=fname)
                _logger.debug(
                    "QWeb refused to compile a %s template while checking it "
                    "for unsafe placeholders; treating it as unsafe.",
                    model,
                    exc_info=True,
                )
                return True
        return False

    @api.model
    def _has_unsafe_expression_template_inline_template(
        self, template_txt: str, model: str, fname: str | None = None
    ) -> bool:
        return (
            bool(template_txt)
            and self._parse_static_inline_template(str(template_txt), model) is None
        )

    @api.model
    def _parse_static_inline_template(
        self, template_txt: str, model: str
    ) -> list[tuple] | None:
        template = parse_inline_template(template_txt)
        if all(
            self._is_static_expression(expression, model)
            for _string, expression, _default in template
            if expression
        ):
            return template
        return None

    def _check_access_right_dynamic_template(self, fnames: set | None = None) -> None:
        if (
            not self.env.su
            and not self.env.user.has_group("mail.group_mail_template_editor")
            and self._has_unsafe_expression(fnames=fnames)
        ):
            _debug.logic(
                "dynamic_template_refused",
                model=self._name,
                records=self.ids,
                uid=self.env.uid,
            )
            raise AccessError(self._prepare_template_editor_error())

    def _prepare_template_editor_error(self) -> str:
        group = self.env.ref("mail.group_mail_template_editor")
        return _(
            "Only members of %(group_name)s group are allowed to edit templates containing sensible placeholders",
            group_name=group.name,
        )

    @api.model
    def _render_eval_context(self) -> dict:
        render_context = dict(template_env_globals)
        render_context.update(
            {
                "ctx": self.env.context,
                "format_addr": tools.formataddr,
                "format_date": lambda date, date_format=False, lang_code=False: (
                    format_date(self.env, date, date_format, lang_code)
                ),
                "format_datetime": lambda dt, tz=False, dt_format=False, lang_code=False: (
                    format_datetime(self.env, dt, tz, dt_format, lang_code)
                ),
                "format_time": lambda time, tz=False, time_format=False, lang_code=False: (
                    format_time(self.env, time, tz, time_format, lang_code)
                ),
                "format_amount": lambda amount, currency, lang_code=False: (
                    format_amount(self.env, amount, currency, lang_code)
                ),
                "format_duration": tools.format_duration,
                "is_html_empty": is_html_empty,
                "slug": self.env["ir.http"]._slug,
                "user": self.env.user,
                "env": self.env,
            }
        )
        return render_context

    @api.model
    @tools.ormcache("template_src", cache="templates.mail")
    def _get_qweb_template_node(self, template_src: str) -> tuple:
        return (
            html.fragment_fromstring(template_src, create_parent="div"),
            RenderScopedDict(),
            {},
        )

    @api.model
    def _render_template_qweb(
        self,
        template_src: str,
        model: str,
        res_ids: list[int],
        add_context: dict | None = None,
        options: dict | None = None,
    ) -> dict:
        results = dict.fromkeys(res_ids, Markup())
        if not template_src or not res_ids:
            return results

        options = dict(options or {})
        try:
            return self._render_template_qweb_static(
                template_src, model, res_ids, options=options
            )
        except StaticRenderUnsupported:
            pass

        _debug.logic(
            "qweb_render_by", model=model, records=len(res_ids), by="evaluator"
        )
        variables = self._render_eval_context()
        if add_context:
            variables.update(add_context)

        qweb_options = {
            name: value
            for name, value in options.items()
            if name in QWEB_RENDER_OPTIONS
        }
        if self._is_restricted():
            qweb_options["raise_on_forbidden_code_for_model"] = model

        template_node, compiled_cache, _programs = self._get_qweb_template_node(
            str(template_src)
        )
        qweb = self.env["ir.qweb"].with_context(
            __qweb_compiled_cache=compiled_cache,
            mail_render_model=model,
            **MAIL_RENDER_QWEB_CONTEXT,
        )
        records = self.env[model].browse(res_ids)
        try:
            with _debug.perf(
                "qweb_render", cr=self.env.cr, model=model, records=len(res_ids)
            ):
                rendered = qweb._render_batch(
                    template_node,
                    variables,
                    ({"object": record} for record in records),
                    **qweb_options,
                )
        except Exception as error:
            self._check_render_error(error, template_src, model, engine="qweb")
            raise
        for record, render_result in zip(records, rendered, strict=True):
            results[record.id] = render_result.removeprefix("<div>").removesuffix(
                "</div>"
            )

        return results

    _RENDER_ERRORS_PASSED_THROUGH = (AccessError, MissingError)

    def _check_render_error(
        self, error: Exception, template_src: str, model: str, engine: str = "qweb"
    ) -> typing.NoReturn:
        if isinstance(error, QWebError) and isinstance(
            error.__cause__, PermissionError
        ):
            raise AccessError(self._prepare_template_editor_error()) from error
        if isinstance(error, self._RENDER_ERRORS_PASSED_THROUGH):
            raise error
        if isinstance(error, QWebError) and isinstance(
            error.__cause__, self._RENDER_ERRORS_PASSED_THROUGH
        ):
            raise error.__cause__ from error

        if isinstance(error, QWebError):
            error_details = str(error).split("\nTemplate:")[0].strip()
        else:
            error_details = str(error)

        template_label = self._get_render_error_label()
        truncated_src = self._truncate_render_error_source(template_src)
        lang_context = self.env.context.get(
            "lang", _("No language detected in context")
        )

        _debug.logic(
            "render_error",
            engine=engine,
            model=model,
            error=type(error).__name__,
            lang=lang_context,
        )
        _logger.error(
            "Failed to render %s template for %s - Context language:%s\n"
            "Target Model: %s\nError: %s\n%s",
            engine,
            template_label,
            lang_context,
            model,
            error_details,
            truncated_src,
        )
        _logger.debug(
            "Failed to render %s template for %s",
            engine,
            template_label,
            exc_info=error,
        )

        raise UserError(
            _(
                "Failed to render %(engine)s template for %(template_label)s\n"
                "Target Model: %(model_name)s\n"
                "Language context: %(lang_context)s\n"
                "Error: %(error_details)s\n\n"
                "Template Source Snippet:\n%(template_src)s",
                engine=engine,
                template_label=template_label,
                model_name=model,
                lang_context=lang_context,
                error_details=error_details,
                template_src=truncated_src,
            )
        ) from error

    @api.model
    def _truncate_render_error_source(
        self, template_src: str, limit: int = 1000
    ) -> str:
        template_src = str(template_src)
        if len(template_src) <= limit:
            return template_src
        half = limit // 2
        return (
            f"{template_src[:half]}\n[...] (content truncated) [...]\n"
            f"{template_src[-half:]}"
        )

    def _get_render_error_label(self) -> str:
        return _("Template name not identified")

    @api.model
    def _is_static_expression(self, expression: str, model: str) -> bool:
        return self.env["ir.qweb"]._is_expression_allowed(expression, model)

    @api.model
    def _static_expression_roots(self, record: models.BaseModel) -> dict[str, Any]:
        return {"object": record, "user": self.env.user}

    @api.model
    def _get_static_expression_value(
        self, expression: str, record: models.Model
    ) -> Any:
        roots = self._static_expression_roots(record)
        root, *path = expression.strip().split(".")
        if root not in roots:
            raise StaticRenderUnsupported(
                f"unsupported root {root!r} for the static mode in {expression!r}"
            )
        value = roots[root]
        for fname in path:
            value = value[fname]
        return value

    @api.model
    def _get_static_value(self, expression: str, record: models.Model) -> Any:
        try:
            value = self._get_static_expression_value(expression, record)
        except KeyError:
            return None
        if isinstance(value, models.BaseModel):
            value = value.display_name or False
        elif isinstance(value, BINARY_TYPES):
            warned = self.env.cr.cache.setdefault("_mail_render_binary_warned", set())
            if (record._name, expression) not in warned:
                warned.add((record._name, expression))
                _logger.warning(
                    "Placeholder %r on %s resolves to binary data, which has no "
                    "text form; rendering it as empty.",
                    expression,
                    record._name,
                )
            return None
        return value

    @api.model
    def _get_static_render_program(
        self, template_src: str, model: str, preserve_comments: bool
    ) -> tuple[list[str], list[tuple[str, str]]] | None:
        programs = self._get_qweb_template_node(template_src)[2]
        key = (model, preserve_comments)
        if key not in programs:
            try:
                programs[key] = self._compile_static_render_program(
                    template_src, model, preserve_comments
                )
            except StaticRenderUnsupported as reason:
                _debug.logic("static_render_declined", model=model, reason=str(reason))
                _logger.debug(
                    "Evaluation-free renderer declined a template for model %s: %s",
                    model,
                    reason,
                )
                programs[key] = None
            _debug.perf.count(
                "static_program_compiled",
                model=model,
                preserve_comments=preserve_comments,
                compiled=programs[key] is not None,
            )
        return programs[key]

    @api.model
    def _compile_static_render_program(
        self, template_src: str, model: str, preserve_comments: bool
    ) -> tuple[list[str], list[tuple[str, str]]]:
        if self._has_unsafe_expression_template_qweb(template_src, model):
            raise StaticRenderUnsupported(
                "the template holds an expression only an evaluator can resolve"
            )

        tree = copy.deepcopy(self._get_qweb_template_node(template_src)[0])
        if not preserve_comments:
            etree.strip_elements(tree, etree.Comment, with_tail=False)

        roots = self._static_expression_roots(self.env[model])
        for element in tree.iter():
            if not isinstance(element.tag, str) or element.get("t-out") is None:
                continue
            expression = element.get("t-out").strip()
            directives = {
                name
                for name in element.attrib
                if name.startswith("t-") and name != "t-out"
            }
            if directives or len(element):
                raise StaticRenderUnsupported(
                    f"t-out element this renderer does not reproduce: "
                    f"directives {sorted(directives)}, "
                    f"{len(element)} child element(s)"
                )
            if not self._is_static_expression(expression, model):
                raise StaticRenderUnsupported(
                    f"expression not allowed without evaluation: {expression!r}"
                )
            if expression.split(".", 1)[0] not in roots:
                raise StaticRenderUnsupported(
                    f"expression this renderer cannot resolve a root for: "
                    f"{expression!r}"
                )

        return compile_static_template(tree)

    @api.model
    def _render_template_qweb_static(
        self,
        template_src: str,
        model: str,
        res_ids: list[int],
        options: dict | None = None,
    ) -> dict:
        program = self._get_static_render_program(
            str(template_src), model, bool((options or {}).get("preserve_comments"))
        )
        if program is None:
            raise StaticRenderUnsupported(
                "this template needs an evaluator; see the debug log for which part"
            )
        segments, holes = program
        _debug.logic(
            "qweb_render_by",
            model=model,
            records=len(res_ids),
            by="static",
            holes=len(holes),
        )
        return {
            record.id: self._render_static_program(segments, holes, record)
            for record in self.env[model].browse(res_ids)
        }

    @api.model
    def _render_static_program(
        self,
        segments: list[str],
        holes: list[tuple[str, str]],
        record: models.BaseModel,
    ) -> Markup:
        return render_static_program(
            segments, holes, lambda expr: self._get_static_value(expr, record)
        )

    @api.model
    def _render_template_qweb_view(
        self,
        view_ref: models.BaseModel | str | int,
        model: str,
        res_ids: list[int],
        add_context: dict | None = None,
        options: dict | None = None,
        add_context_per_record: dict[int, dict] | None = None,
    ) -> dict:
        results = dict.fromkeys(res_ids, Markup())
        if not res_ids:
            return results

        variables = self._render_eval_context()
        if add_context:
            variables.update(add_context)
        add_context_per_record = add_context_per_record or {}

        view_ref = view_ref.id if isinstance(view_ref, models.BaseModel) else view_ref
        qweb = self.env["ir.qweb"].with_context(
            mail_render_model=model, **MAIL_RENDER_QWEB_CONTEXT
        )
        records = self.env[model].browse(res_ids)
        try:
            with _debug.perf(
                "qweb_view_render",
                cr=self.env.cr,
                view=view_ref,
                model=model,
                records=len(res_ids),
            ):
                rendered = qweb._render_batch(
                    view_ref,
                    variables,
                    (
                        {"object": record, **add_context_per_record.get(record.id, {})}
                        for record in records
                    ),
                    minimal_qcontext=True,
                    raise_if_not_found=False,
                    **{
                        name: value
                        for name, value in (options or {}).items()
                        if name in QWEB_RENDER_OPTIONS
                    },
                )
        except Exception as error:
            self._check_render_error(error, str(view_ref), model, engine="qweb_view")
            raise
        results.update(zip(res_ids, rendered, strict=True))
        return results

    @api.model
    def _render_template_inline_template(
        self,
        template_txt: str,
        model: str,
        res_ids: list[int],
        add_context: dict | None = None,
        options: dict | None = None,
    ) -> dict:
        results = dict.fromkeys(res_ids, "")
        if not template_txt or not res_ids:
            return results

        static_template = self._parse_static_inline_template(str(template_txt), model)
        if static_template is not None:
            try:
                return self._render_template_inline_template_static(
                    static_template, model, res_ids
                )
            except StaticRenderUnsupported:
                _debug.logic(
                    "static_inline_declined", model=model, records=len(res_ids)
                )
                _logger.debug(
                    "Evaluation-free renderer declined an inline template; "
                    "falling back to evaluation for model %s",
                    model,
                )

        if self._is_restricted():
            _debug.logic("inline_render_refused", model=model, reason="restricted")
            raise AccessError(self._prepare_template_editor_error())

        _debug.logic(
            "inline_render_by", model=model, records=len(res_ids), by="evaluator"
        )
        variables = self._render_eval_context()
        if add_context:
            variables.update(add_context)

        parsed_template = parse_inline_template(str(template_txt))
        for record in self.env[model].browse(res_ids):
            variables["object"] = record

            try:
                results[record.id] = render_inline_template(
                    parsed_template, variables, format_value=_format_template_value
                )
            except Exception as error:
                self._check_render_error(
                    error, str(template_txt), model, engine="inline_template"
                )

        return results

    @api.model
    def _render_template_inline_template_static(
        self, template: list[tuple], model: str, res_ids: list[int]
    ) -> dict:
        result = {}
        for record in self.env[model].browse(res_ids):
            renderer = []
            for string, expression, default in template:
                renderer.append(string)
                if not expression:
                    continue
                value = self._get_static_value(expression, record)
                if renders_as_no_value(value):
                    value = default
                renderer.append("" if value == "" else str(value))
            result[record.id] = "".join(renderer)
        return result

    @api.model
    def _render_template_postprocess(
        self, model: str, rendered: dict[int, str]
    ) -> dict:
        if not model:
            return {
                res_id: self._replace_local_links(rendered_html)
                for res_id, rendered_html in rendered.items()
            }
        records = self.env[model].browse(rendered.keys())
        return {
            record.id: self._replace_local_links(
                rendered[record.id], record.get_base_url
            )
            for record in records
        }

    @api.model
    def _render_template_get_valid_options(self) -> set:
        return {"post_process", "preserve_comments"}

    @api.model
    def _render_template_engines(self) -> dict[str, Callable]:
        return {
            "inline_template": type(self)._render_template_inline_template,
            "qweb": type(self)._render_template_qweb,
            "qweb_view": type(self)._render_template_qweb_view,
        }

    @api.model
    def _render_template(
        self,
        template_src: str,
        model: str,
        res_ids: list[int],
        engine: str = "inline_template",
        add_context: dict | None = None,
        options: dict | None = None,
    ) -> dict:
        options = options or {}

        if not isinstance(res_ids, (list, tuple)):
            raise ValueError(
                f"Template rendering takes a list of IDs; received {res_ids!r}."
            )
        engines = self._render_template_engines()
        if engine not in engines:
            raise ValueError(
                f"Template rendering supports only {', '.join(sorted(engines))}; "
                f"received {engine!r} instead."
            )
        if model not in self.env:
            raise UserError(
                _(
                    "Cannot render %(template_label)s: %(model_name)s is not a model.",
                    template_label=self._get_render_error_label(),
                    model_name=repr(model),
                )
            )
        valid_render_options = self._render_template_get_valid_options()
        if not options.keys() <= valid_render_options:
            raise ValueError(
                "Not supported as rendering options: "
                f"{', '.join(sorted(options.keys() - valid_render_options))}"
            )

        with _debug.perf(
            "render_template",
            cr=self.env.cr,
            engine=engine,
            model=model,
            records=len(res_ids),
            post_process=bool(options.get("post_process")),
        ):
            rendered = engines[engine](
                self,
                template_src,
                model,
                res_ids,
                add_context=add_context,
                options=options,
            )

            if options.get("post_process"):
                rendered = self._render_template_postprocess(model, rendered)

        return rendered

    def _render_lang(
        self, res_ids: list[int], engine: str = "inline_template"
    ) -> dict[int, str | Literal[False]]:
        self.check_singleton()
        if self.lang:
            return self._render_template(
                self.lang, self.render_model, res_ids, engine=engine
            )
        if not self.render_model:
            return dict.fromkeys(res_ids, False)

        records = self.env[self.render_model].browse(res_ids)
        customers = records._mail_get_partners()
        return {
            record.id: (customers[record.id][0].lang if customers[record.id] else False)
            for record in records
        }

    def _get_res_ids_lang(
        self, res_ids: list[int], engine: str = "inline_template"
    ) -> dict[int, str]:
        self.check_singleton()
        if preview_lang := self.env.context.get("template_preview_lang"):
            return dict.fromkeys(res_ids, preview_lang)
        return self._render_lang(res_ids, engine=engine)

    def _classify_per_lang(
        self,
        res_ids: list[int],
        engine: str = "inline_template",
        res_ids_lang: dict[int, str] | None = None,
        default_lang: str | Literal[False] | None = None,
    ) -> dict:
        self.check_singleton()
        if res_ids_lang is None:
            res_ids_lang = self._get_res_ids_lang(res_ids, engine=engine)

        lang_to_res_ids = {}
        for res_id in res_ids:
            lang = res_ids_lang.get(res_id, default_lang)
            lang_to_res_ids.setdefault(lang, []).append(res_id)

        _debug.logic(
            "classified_per_lang",
            model=self._name,
            record=self.id,
            records=len(res_ids),
            langs=sorted(lang or "" for lang in lang_to_res_ids),
        )
        return {
            lang: (self._with_render_lang(lang), lang_res_ids)
            for lang, lang_res_ids in lang_to_res_ids.items()
        }

    def _with_render_lang(self, lang: str | Literal[False] | None) -> Self:
        return self.with_context(lang=lang) if lang else self

    def _render_field(
        self,
        field: str,
        res_ids: list[int],
        engine: str = "inline_template",
        compute_lang: bool = False,
        res_ids_lang: dict[int, str] | Literal[False] = False,
        set_lang: str | Literal[False] = False,
        add_context: dict | None = None,
        options: dict | None = None,
    ) -> dict:
        if field not in self:
            raise ValueError(
                f"Cannot render {field!r}: it is not a field of {self._name}."
            )
        self.check_singleton()
        if res_ids_lang:
            templates_res_ids = self._classify_per_lang(
                res_ids,
                res_ids_lang=res_ids_lang,
                default_lang=self.env.context.get("lang"),
            )
        elif compute_lang:
            templates_res_ids = self._classify_per_lang(res_ids)
        elif set_lang:
            templates_res_ids = {set_lang: (self.with_context(lang=set_lang), res_ids)}
        else:
            templates_res_ids = {self.env.context.get("lang"): (self, res_ids)}

        template_field = self._fields[field]
        engine = getattr(template_field, "render_engine", None) or engine
        render_options = {
            **(getattr(template_field, "render_options", None) or {}),
            **(options or {}),
        }
        _debug.logic(
            "render_field",
            model=self._name,
            record=self.id,
            field=field,
            engine=engine,
            records=len(res_ids),
            lang_by="given"
            if res_ids_lang
            else "computed"
            if compute_lang
            else "set"
            if set_lang
            else "context",
            langs=len(templates_res_ids),
        )

        return {
            res_id: rendered
            for (template, tpl_res_ids) in templates_res_ids.values()
            for res_id, rendered in template._render_template(
                template[field],
                template.render_model,
                tpl_res_ids,
                engine=engine,
                add_context=add_context,
                options=render_options,
            ).items()
        }


def _format_template_value(value: Any) -> str:
    if isinstance(value, models.BaseModel):
        return value.display_name or ""
    return str(value)
