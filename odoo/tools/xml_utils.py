# -*- coding: utf-8 -*-
from lxml import etree
from odoo.tools.misc import file_open
from odoo.exceptions import UserError

def check_with_xsd(tree_or_str, stream):
    raise UserError("Method 'check_with_xsd' deprecated ")


def _check_with_xsd(tree_or_str, stream):
    if not isinstance(tree_or_str, etree._Element):
        tree_or_str = etree.fromstring(tree_or_str)
    xml_schema_doc = etree.parse(stream)
    xsd_schema = etree.XMLSchema(xml_schema_doc)
    try:
        xsd_schema.assertValid(tree_or_str)
    except etree.DocumentInvalid as xml_errors:
        #import UserError only here to avoid circular import statements with tools.func being imported in exceptions.py
        from odoo.exceptions import UserError
        raise UserError('\n'.join(str(e) for e in xml_errors.error_log))


def create_xml_node_chain(first_parent_node, nodes_list, last_node_value=None):
    """ Utility function for generating XML files nodes. Generates as a hierarchical
    chain of nodes (each new node being the son of the previous one) based on the tags
    contained in `nodes_list`, under the given node `first_parent_node`.
    It will also set the value of the last of these nodes to `last_node_value` if it is
    specified. This function returns the list of created nodes.
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
    """ Utility function for managing XML. It creates a new node with the specified
    `node_name` as a child of given `parent_node` and assigns it `node_value` as value.
    :param parent_node: valid etree Element
    :param node_name: string
    :param node_value: string
    """
    return create_xml_node_chain(parent_node, [node_name], node_value)[0]
