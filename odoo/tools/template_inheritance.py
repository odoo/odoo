from lxml import etree

from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.libs.xml import XPathExpressionError
from odoo.libs.xml import (
    apply_inheritance_specs as _apply_inheritance_specs_base,
)
from odoo.libs.xml import (
    locate_node as _locate_node_base,
)
from odoo.tools.translate import LazyTranslate

__all__ = ["apply_inheritance_specs", "locate_node"]

_lt = LazyTranslate("base")
_debug = DebugLog(__name__)


def locate_node(arch: etree._Element, spec: etree._Element) -> etree._Element | None:
    try:
        return _locate_node_base(arch, spec)
    except XPathExpressionError as e:
        expr = spec.get("expr")
        _debug.logic("template_inheritance.locate_failed", expr=expr)
        if not expr:
            message = _lt("Missing 'expr' attribute in xpath specification")
        elif isinstance(e.__cause__, etree.XPathSyntaxError):
            # the msgid the translations carry, curly quotes included
            message = _lt("Invalid Expression while parsing xpath “%s”", expr)
        else:
            message = _lt("The xpath “%s” must select elements, not a value", expr)
        raise ValidationError(message) from e


def apply_inheritance_specs(
    source: etree._Element,
    specs_tree: etree._Element,
    inherit_branding: bool = False,
) -> etree._Element:
    try:
        with _debug.perf(
            "template_inheritance.applied",
            specs=len(specs_tree),
            branding=inherit_branding,
        ):
            return _apply_inheritance_specs_base(source, specs_tree, inherit_branding)
    except XPathExpressionError as e:
        _debug.logic("template_inheritance.spec_failed", error=type(e).__name__)
        raise ValidationError(str(e)) from e
