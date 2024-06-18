# -*- coding: utf-8 -*-

from odoo import api, models


class IrQweb(models.AbstractModel):
    """Add ``raise_on_forbidden_code`` option for qweb.

    When this option is activated, only a whitelist of expressions is allowed.
    """

    _inherit = "ir.qweb"

    allowed_directives = (
        "out",
        "inner-content",
        "att",
        "tag-open",
        "tag-close",
    )

    def _get_template_cache_keys(self):
        return super()._get_template_cache_keys() + ["raise_on_forbidden_code"]

    def _compile_directive(self, el, compile_context, directive, level):
        if (
            compile_context.get("raise_on_forbidden_code")
            and directive not in self.allowed_directives
        ):
            raise PermissionError("This directive is not allowed for this rendering mode.")
        return super()._compile_directive(el, compile_context, directive, level)

    def _compile_directive_att(self, el, compile_context, level):
        if compile_context.get("raise_on_forbidden_code"):
            if set(el.attrib) - {"t-out", "t-tag-open", "t-tag-close", "t-inner-content"}:
                raise PermissionError("This directive is not allowed for this rendering mode.")
        return super()._compile_directive_att(el, compile_context, level)

    def _compile_expr(self, expr, raise_on_missing=False):
        if self.env.context.get("raise_on_forbidden_code") and not self._is_expression_allowed(expr):
            raise PermissionError("This directive is not allowed for this rendering mode.")
        return super()._compile_expr(expr, raise_on_missing)

    def _compile_directive_out(self, el, compile_context, level):
        if compile_context.get("raise_on_forbidden_code"):
            if len(el) != 0:
                raise PermissionError("No child allowed for t-out.")
            if set(el.attrib) - {'t-out', 't-tag-open', 't-tag-close'}:
                raise PermissionError("No other attribute allowed for t-out.")
        return super()._compile_directive_out(el, compile_context, level)

    def _is_expression_allowed(self, expression):
        return expression.strip() in self.allowed_qweb_expressions()

    @api.model
    def allowed_qweb_expressions(self):
        # QWeb expressions allowed if we are not template editor
        return (
            "object.name",
            "object.contact_name",
            "object.partner_id",
            "object.partner_id.name",
            "object.user_id",
            "object.user_id.name",
            "object.user_id.signature",
        )
