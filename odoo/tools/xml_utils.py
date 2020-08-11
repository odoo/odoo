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
    :param tree_or_str (etree, str): representation of the tree to be checked
    :param stream (io.IOBase, str): the byte stream used to build the XSD schema.
        If env is given, it can also be the name of an attachment in the filestore
    :param env (odoo.api.Environment): If it is given, it enables resolving the
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
    :param first_parent_node (etree._Element): parent of the created tree/chain
    :param nodes_list (iterable<str>): tag names to be created
    :param last_node_value (str): if specified, set the last node's text to this value
    :returns (list<etree._Element>): the list of created nodes
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

    :param parent_node (etree._Element): parent of the created node
    :param node_name (str): name of the created node
    :param node_value (str): value of the created node (optional)
    :returns (etree._Element):
    """
    return create_xml_node_chain(parent_node, [node_name], node_value)[0]
