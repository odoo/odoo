import re
from collections.abc import Iterable

from lxml import etree

# Pre-compiled regex for XML-invalid control character removal
_CONTROL_CHAR_RE = re.compile(
    "[^"
    "\u0009"
    "\u000a"
    "\u000d"
    "\u0020-\ud7ff"
    "\ue000-\ufffd"
    "\U00010000-\U0010ffff"
    "]".encode()
)


def remove_control_characters(byte_node: bytes) -> bytes:
    """Remove XML-invalid control characters from a byte string.

    The characters to be removed are the control characters #x0 to #x1F and #x7F
    (most of which cannot appear in XML).

    XML processors must accept any character in the range specified for Char:
    ``Char ::= #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]``

    See: https://www.w3.org/TR/xml/

    :param byte_node: XML content as bytes
    :return: Cleaned XML content with control characters removed
    """
    return _CONTROL_CHAR_RE.sub(b"", byte_node)


def create_xml_node_chain(
    first_parent_node: etree._Element,
    nodes_list: Iterable[str],
    last_node_value: str | None = None,
) -> list[etree._Element]:
    """Generate a hierarchical chain of nodes.

    Each new node being the child of the previous one based on the tags contained
    in `nodes_list`, under the given node `first_parent_node`.

    :param first_parent_node: parent of the created tree/chain
    :param nodes_list: tag names to be created
    :param last_node_value: if specified, set the last node's text to this value
    :returns: the list of created nodes

    Example::

        >>> from lxml import etree
        >>> root = etree.Element('root')
        >>> nodes = create_xml_node_chain(root, ['a', 'b', 'c'], 'value')
        >>> etree.tostring(root, encoding='unicode')
        '<root><a><b><c>value</c></b></a></root>'
    """
    res = []
    current_node = first_parent_node
    for tag in nodes_list:
        current_node = etree.SubElement(current_node, tag)
        res.append(current_node)

    if last_node_value is not None:
        current_node.text = last_node_value
    return res


def create_xml_node(
    parent_node: etree._Element,
    node_name: str,
    node_value: str | None = None,
) -> etree._Element:
    """Create a new XML node.

    :param parent_node: parent of the created node
    :param node_name: name of the created node
    :param node_value: value of the created node (optional)
    :returns: the created node

    Example::

        >>> from lxml import etree
        >>> root = etree.Element('root')
        >>> child = create_xml_node(root, 'child', 'text')
        >>> etree.tostring(root, encoding='unicode')
        '<root><child>text</child></root>'
    """
    return create_xml_node_chain(parent_node, [node_name], node_value)[0]
