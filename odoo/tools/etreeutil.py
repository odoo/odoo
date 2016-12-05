# -*- coding: utf-8 -*-

from lxml import etree

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

def tree_as_str(tree):
    ''' Transforms a node tree into a well indended string.
    '''
    return etree.tostring(
        tree, 
        pretty_print=True, 
        encoding='UTF-8',
        xml_declaration=True)

def get_parent_node(node):
    ''' Return the parent of the node
    '''
    return next(node.iterancestors())