from .parsers import default_parser, fromstring, parse, strict_parser

from .dict_to_xml import dict_to_xml

from .dsig import (
    DS_NS,
    EXC_C14N_ALGORITHM,
    XmlSigError,
    canonicalize,
    canonicalize_signed_info,
    update_reference_digests,
    resolve_reference,
)

from .utils import (
    remove_control_characters,
    create_xml_node_chain,
    create_xml_node,
)

from .template_inheritance import (
    locate_node,
    apply_inheritance_specs,
    add_stripped_items_before,
    add_text_before,
    remove_element,
    merge_attribute_value,
    SKIPPED_ELEMENT_TYPES,
    PYTHON_ATTRIBUTES,
    XPathExpressionError,
)

__all__ = [
    "DS_NS",
    "EXC_C14N_ALGORITHM",
    "PYTHON_ATTRIBUTES",
    "SKIPPED_ELEMENT_TYPES",
    "XPathExpressionError",
    "XmlSigError",
    "add_stripped_items_before",
    "add_text_before",
    "apply_inheritance_specs",
    "canonicalize",
    "canonicalize_signed_info",
    "create_xml_node",
    "create_xml_node_chain",
    "default_parser",
    "dict_to_xml",
    "fromstring",
    "locate_node",
    "merge_attribute_value",
    "parse",
    "remove_control_characters",
    "remove_element",
    "resolve_reference",
    "strict_parser",
    "update_reference_digests",
]
