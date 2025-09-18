# ruff: noqa: F401
"""
Odoo template inheritance utilities.

This module wraps odoo.libs.xml.template_inheritance to provide Odoo-specific
error handling (ValidationError for XPath errors) for better user experience.

For agnostic usage without Odoo dependencies, use odoo.libs.xml.template_inheritance directly.
"""

from lxml import etree

from odoo.exceptions import ValidationError

# Re-export everything from libs (agnostic versions)
from odoo.libs.xml.template_inheritance import (
    PYTHON_ATTRIBUTES,
    SKIPPED_ELEMENT_TYPES,
    _compile_xpath,
    add_stripped_items_before,
    add_text_before,
    remove_element,
)
from odoo.libs.xml.template_inheritance import (
    apply_inheritance_specs as _apply_inheritance_specs_base,
)

# Import agnostic versions for wrapping
from odoo.libs.xml.template_inheritance import (
    locate_node as _locate_node_base,
)
from odoo.tools.translate import LazyTranslate

__all__ = []

_lt = LazyTranslate("base")


def locate_node(arch, spec):
    """Locate a node in a source (parent) architecture.

    Given a complete source (parent) architecture (i.e. the field
    `arch` in a view), and a 'spec' node (a node in an inheriting
    view that specifies the location in the source view of what
    should be changed), return (if it exists) the node in the
    source view matching the specification.

    :param arch: a parent architecture to modify
    :param spec: a modifying node in an inheriting view
    :return: a node in the source matching the spec
    :raise: ValidationError if the xpath expression is invalid
    """
    if spec.tag == "xpath":
        expr = spec.get("expr")
        try:
            xPath = _compile_xpath(expr)
        except etree.XPathSyntaxError as e:
            raise ValidationError(
                _lt('Invalid Expression while parsing xpath "%s"', expr)
            ) from e
        nodes = xPath(arch)
        return nodes[0] if nodes else None
    # For non-xpath specs, delegate to base implementation
    return _locate_node_base(arch, spec)


def apply_inheritance_specs(
    source, specs_tree, inherit_branding=False, pre_locate=None
):
    """Apply an inheriting view (a descendant of the base view)

    Apply to a source architecture all the spec nodes (i.e. nodes
    describing where and what changes to apply to some parent
    architecture) given by an inheriting view.

    :param Element source: a parent architecture to modify
    :param Element specs_tree: a modifying architecture in an inheriting view
    :param bool inherit_branding:
    :param pre_locate: function that is executed before locating a node.
                        This function receives an arch as argument.
                        This is required by studio to properly handle group_ids.
    :return: a modified source where the specs are applied
    :rtype: Element
    :raise: ValidationError for invalid xpath expressions
    :raise: ValueError for other invalid specs or if nodes cannot be located
    """
    # We need to wrap locate_node calls to use ValidationError for XPath errors.
    # The simplest approach is to handle XPath validation before delegating.
    # However, since apply_inheritance_specs uses locate_node internally,
    # we need to patch the behavior or re-implement with our locate_node.

    # For now, we catch ValueError from the base implementation and convert
    # XPath-related errors to ValidationError
    try:
        return _apply_inheritance_specs_base(
            source, specs_tree, inherit_branding, pre_locate
        )
    except ValueError as e:
        error_msg = str(e)
        if "Invalid Expression while parsing xpath" in error_msg:
            raise ValidationError(error_msg)  # pylint: disable=E8502
        # Re-raise other ValueErrors — messages are dynamic (contain view/element
        # names from the underlying library) so cannot be statically translated.
        if "cannot be located in parent view" in error_msg:  # pylint: disable=E8502
            raise ValueError(error_msg)
        if (
            "Invalid specification for moved nodes" in error_msg
        ):  # pylint: disable=E8502
            raise ValueError(error_msg)
        if "Invalid mode attribute" in error_msg:  # pylint: disable=E8502
            raise ValueError(error_msg)
        if "Invalid position attribute" in error_msg:  # pylint: disable=E8502
            raise ValueError(error_msg)
        if "Invalid attributes" in error_msg:  # pylint: disable=E8502
            raise ValueError(error_msg)
        if "Invalid separator" in error_msg:  # pylint: disable=E8502
            raise ValueError(error_msg)
        if "cannot contain text" in error_msg:  # pylint: disable=E8502
            raise ValueError(error_msg)
        raise
