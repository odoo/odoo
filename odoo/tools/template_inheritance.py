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
from odoo.libs.xml.template_inheritance import _compile_xpath
from odoo.tools.translate import LazyTranslate

__all__ = ["apply_inheritance_specs", "locate_node"]

_lt = LazyTranslate("base")
_debug = DebugLog(__name__)


def locate_node(arch: etree._Element, spec: etree._Element) -> etree._Element | None:
    if spec.tag == "xpath":
        expr = spec.get("expr")
        if expr is None:
            raise ValidationError(
                _lt("Missing 'expr' attribute in xpath specification")
            )
        try:
            xPath = _compile_xpath(expr)
        except etree.XPathSyntaxError as e:
            _debug.logic("template_inheritance.xpath_invalid", expr=expr)
            raise ValidationError(
                _lt('Invalid Expression while parsing xpath "%s"', expr)
            ) from e
        nodes = xPath(arch)
        _debug.logic(
            "template_inheritance.xpath_located",
            expr=expr,
            matches=len(nodes) if isinstance(nodes, list) else None,
            position=spec.get("position"),
        )
        return nodes[0] if nodes else None
    return _locate_node_base(arch, spec)


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
