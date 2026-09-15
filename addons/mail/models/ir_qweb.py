import re
from typing import Any

from lxml import etree

from odoo import models
from odoo.libs.debug_log import DebugLog
from odoo.tools.rendering_tools import BINARY_TYPES

from odoo.addons.base.models.ir_qweb import CompileContext, indent_code

_debug = DebugLog(__name__)

STATIC_EXPRESSION_RE = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\Z")


class IrQweb(models.AbstractModel):
    _inherit = "ir.qweb"

    allowed_directives = (
        "out",
        "inner-content",
        "att",
        "tag-open",
        "tag-close",
    )

    def _get_template_cache_keys(self) -> list[str]:
        return super()._get_template_cache_keys() + [
            "raise_on_forbidden_code_for_model",
            "mail_render_format_values",
            "mail_render_model",
        ]

    def _compile_out_set_content(
        self,
        el: etree._Element,
        ttype: str,
        expr: str,
        has_options: bool,
        level: int,
    ) -> tuple[list[str], bool]:
        model = self.env.context.get("mail_render_model")
        if (
            ttype == "t-out"
            and not has_options
            and model
            and self.env.context.get("mail_render_format_values")
            and self._is_expression_allowed(expr, model)
        ):
            code = [
                indent_code(
                    f"""
                    content = self._mail_resolve_allowed({expr.strip()!r}, values)
                    force_display = True
                    """,
                    level,
                )
            ]
            force_display_dependent = True
        else:
            code, force_display_dependent = super()._compile_out_set_content(
                el, ttype, expr, has_options, level
            )
        if self.env.context.get("mail_render_format_values"):
            code.append(
                indent_code("content = self._mail_normalize_out(content)", level)
            )
        return code, force_display_dependent

    def _mail_resolve_allowed(self, expression: str, values: dict[str, Any]) -> Any:
        root, *path = expression.strip().split(".")
        value = values.get(root)
        for fname in path:
            if value is None:
                return None
            try:
                value = value[fname]
            except KeyError, TypeError:
                return None
        return value

    def _mail_normalize_out(self, content: Any) -> Any:
        if isinstance(content, BINARY_TYPES):
            return None
        if isinstance(content, models.BaseModel) and len(content) <= 1:
            return content.display_name or None
        return content

    def _compile_directive(
        self,
        el: etree._Element,
        compile_context: CompileContext,
        directive: str,
        level: int,
    ) -> list[str]:
        if (
            "raise_on_forbidden_code_for_model" in compile_context
            and directive not in self.allowed_directives
        ):
            _debug.logic("directive_refused", directive=directive)
            raise PermissionError(
                "This directive is not allowed for this rendering mode."
            )
        return super()._compile_directive(el, compile_context, directive, level)

    def _compile_directive_att(
        self, el: etree._Element, compile_context: CompileContext, level: int
    ) -> list[str]:
        if "raise_on_forbidden_code_for_model" in compile_context:
            self._check_restricted_attributes(
                el, {"t-out", "t-tag-open", "t-tag-close", "t-inner-content"}
            )
        return super()._compile_directive_att(el, compile_context, level)

    @staticmethod
    def _check_restricted_attributes(el: etree._Element, allowed: set[str]) -> None:
        if forbidden := {
            name for name in el.attrib if name.startswith("t-") and name not in allowed
        }:
            _debug.logic("attributes_refused", attributes=sorted(forbidden))
            raise PermissionError(
                f"QWeb directives not allowed for this rendering mode: "
                f"{', '.join(sorted(forbidden))}"
            )

    def _compile_expr(self, expr: str, raise_on_missing: bool = False) -> str:
        model = self.env.context.get("raise_on_forbidden_code_for_model")
        if model is not None and not self._is_expression_allowed(expr, model):
            _debug.logic("expression_refused", model=model, expression=expr.strip())
            raise PermissionError(
                "This directive is not allowed for this rendering mode."
            )
        return super()._compile_expr(expr, raise_on_missing)

    def _compile_directive_out(
        self, el: etree._Element, compile_context: CompileContext, level: int
    ) -> list[str]:
        if "raise_on_forbidden_code_for_model" in compile_context:
            if len(el) != 0:
                raise PermissionError("No child allowed for t-out.")
            self._check_restricted_attributes(
                el, {"t-out", "t-tag-open", "t-tag-close"}
            )
        return super()._compile_directive_out(el, compile_context, level)

    def _compile_to_str(self, expr: Any) -> str:
        if self.env.context.get("mail_render_format_values") and isinstance(
            expr, models.BaseModel
        ):
            return expr.display_name or ""
        return super()._compile_to_str(expr)

    def _is_expression_allowed(self, expression: str, model: str) -> bool:
        expression = expression.strip()
        return bool(
            model
            and STATIC_EXPRESSION_RE.match(expression)
            and expression in self.env[model].mail_allowed_qweb_expressions()
        )
