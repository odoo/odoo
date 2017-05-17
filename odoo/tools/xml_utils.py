# -*- coding: utf-8 -*-

from lxml import etree
from odoo.tools.misc import file_open

def check_with_xsd(tree_or_str, xsd_path):
    if not isinstance(tree_or_str, etree._Element):
        tree_or_str = etree.fromstring(tree_or_str)
    xml_schema_doc = etree.parse(file_open(xsd_path))
    xsd_schema = etree.XMLSchema(xml_schema_doc)
    try:
        xsd_schema.assertValid(tree_or_str)
    except etree.DocumentInvalid as xml_errors:
        #import UserError only here to avoid circular import statements with tools.func being imported in exceptions.py
        from odoo.exceptions import UserError
        raise UserError('\n'.join(str(e) for e in xml_errors.error_log))

def xml_node_chain(first_parent_node, tags_list, str_value=None, return_node=None):
    """ Utility function for generating XML files nodes. Generates as a hierarchical
    chain of nodes (each node is the son of the previous one) the tags contained
    in tags_list as children of node first_parent_node (previously created by
    etree), setting the value of the last of these nodes to str_value if it is
    specified. This function returns the created node whose tag is equal no
    return_node parameter, or None, if this parameter is None or does not
    match any node.
    """
    rslt = None
    current_node = first_parent_node
    for tag in tags_list:
        current_node = etree.SubElement(current_node, tag)
        if current_node.tag == return_node: #And so, cannot be None
            rslt = current_node

    if str_value:
        current_node.text = str_value

    return rslt

def xml_node(parent_node, tag, str_value=None):
    """ Utility function for managing XML. It creates a new node with the specified
    tag as a child of the previously generated parent_node node. It also gives it
    str_value as its value, if this parameter is specified.
    """
    return xml_node_chain(parent_node, [tag], str_value, tag)
