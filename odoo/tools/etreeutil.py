# -*- coding: utf-8 -*-

from lxml import etree
from odoo.tools.misc import file_open

def dict_to_obj(dictionary):
    ''' This method is usefull to bring more genericity during the rendering.
    Sometimes, a subtemplate can get its values from a object or a dictionnary but
    this is not supported by Qweb. So, this method create an object from a dict.
    '''
    class SubValues:
        def __init__(self, dictionary):
            for key, value in dictionary.items():
                setattr(self, key, value)
    return SubValues(dictionary)

def str_as_tree(string):
    ''' Transforms the content of the template into a node tree.
    '''
    xml_parser = etree.XMLParser(remove_blank_text=True)
    xml_tree = etree.fromstring(string, parser=xml_parser)
    return xml_tree

def tree_as_str(tree, pretty_print=True, xml_declaration=True):
    ''' Transforms a node tree into a well indended string.
    '''
    return etree.tostring(
        tree, 
        pretty_print=pretty_print,        
        xml_declaration=xml_declaration,
        encoding='UTF-8',)

def get_parent_node(node):
    ''' Return the parent of the node
    '''
    return next(node.iterancestors())

def check_with_xsd(tree_or_str, xsd_path):
    if not isinstance(tree_or_str, etree._Element):
        tree_or_str = str_as_tree(tree_or_str)
    xml_schema_doc = etree.parse(file_open(xsd_path))
    xsd_schema = etree.XMLSchema(xml_schema_doc)
    try:
        xsd_schema.assertValid(tree_or_str)
        return []
    except etree.DocumentInvalid, xml_errors:
        return [e.message for e in xml_errors.error_log]