# -*- coding: utf-8 -*-
from lxml import etree

from odoo import _, models
from odoo.tools import float_repr


class AccountEdiXml(models.AbstractModel):
    _name = "account.edi.xml"
    _description = "XMl Builder for EDI documents"

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def format_float(self, amount, precision_digits):
        if amount is None:
            return None
        return float_repr(amount, precision_digits)

    def cleanup_xml_content(self, xml_content):
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.fromstring(xml_content, parser=parser)

        def cleanup_node(parent_node, node):
            # Clean children nodes recursively.
            for child_node in node:
                cleanup_node(node, child_node)

            # Remove empty node.
            if parent_node is not None and not len(node) and not (node.text or '').strip():
                parent_node.remove(node)

        cleanup_node(None, tree)

        return etree.tostring(tree, pretty_print=True, encoding='unicode')

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    def _check_required_fields(self, record, field_names):
        if not isinstance(field_names, list):
            field_names = [field_names]

        has_values = any(record[field_name] for field_name in field_names)
        if has_values:
            return

        display_field_names = record.fields_get(field_names)
        if len(field_names) == 1:
            display_field = f"'{display_field_names[field_names[0]]['string']}'"
            return _("The field %s is required on %s.", display_field, record.display_name)
        else:
            display_fields = ', '.join(f"'{display_field_names[x]['string']}'" for x in display_field_names)
            return _("At least one of the following fields %s is required on %s.", display_fields, record.display_name)

    def _check_constraints(self, constraints):
        return [x for x in constraints.values() if x]
