# -*- coding: utf-8 -*-
"""Utilities for generating, parsing and checking XML/XSD files on top of the lxml.etree module."""

import base64
from io import BytesIO
from lxml import etree

from odoo.exceptions import UserError


class odoo_resolver(etree.Resolver):
    """Odoo specific file resolver that can be added to the XML Parser.

    It will search filenames in the ir.attachments
    """

    def __init__(self, env):
        super().__init__()
        self.env = env

    def resolve(self, url, id, context):
        """Search url in ``ir.attachment`` and return the resolved content."""
        attachment = self.env['ir.attachment'].search([('name', '=', url)])
        if attachment:
            return self.resolve_string(base64.b64decode(attachment.datas), context)


def _check_with_xsd(tree_or_str, stream, env=None):
    """Check an XML against an XSD schema.

    This will raise a UserError if the XML file is not valid according to the
    XSD file.

    :param str | etree._Element tree_or_str: representation of the tree to be checked
    :param io.IOBase | str stream: the byte stream used to build the XSD schema.
        If env is given, it can also be the name of an attachment in the filestore
    :param odoo.api.Environment env: If it is given, it enables resolving the
        imports of the schema in the filestore with ir.attachments.
    """
    if not isinstance(tree_or_str, etree._Element):
        tree_or_str = etree.fromstring(tree_or_str)
    parser = etree.XMLParser()
    if env:
        parser.resolvers.add(odoo_resolver(env))
        if isinstance(stream, str) and stream.endswith('.xsd'):
            attachment = env['ir.attachment'].search([('name', '=', stream)])
            if not attachment:
                raise FileNotFoundError()
            stream = BytesIO(base64.b64decode(attachment.datas))
    xsd_schema = etree.XMLSchema(etree.parse(stream, parser=parser))
    try:
        xsd_schema.assertValid(tree_or_str)
    except etree.DocumentInvalid as xml_errors:
        raise UserError('\n'.join(str(e) for e in xml_errors.error_log))


def create_xml_node_chain(first_parent_node, nodes_list, last_node_value=None):
    """Generate a hierarchical chain of nodes.

    Each new node being the child of the previous one based on the tags contained
    in `nodes_list`, under the given node `first_parent_node`.

    :param etree._Element first_parent_node: parent of the created tree/chain
    :param iterable[str] nodes_list: tag names to be created
    :param str last_node_value: if specified, set the last node's text to this value
    :returns: the list of created nodes
    :rtype: list[etree._Element]
    """
    res = []
    current_node = first_parent_node
    for tag in nodes_list:
        current_node = etree.SubElement(current_node, tag)
        res.append(current_node)

    if last_node_value is not None:
        current_node.text = last_node_value
    return res


def create_xml_node(parent_node, node_name, node_value=None):
    """Create a new node.

    :param etree._Element parent_node: parent of the created node
    :param str node_name: name of the created node
    :param str node_value: value of the created node (optional)
    :rtype: etree._Element
    """
    return create_xml_node_chain(parent_node, [node_name], node_value)[0]
