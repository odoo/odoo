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
        raise UserError('\n'.join([e.message for e in xml_errors.error_log]))
