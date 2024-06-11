# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import fields, models, _

HIERARCHY_VALID_ATTRIBUTES = {
    '__validate__',                     # ir.ui.view implementation detail
    'class',
    'js_class',
    'string',
    'create',
    'edit',
    'delete',
    'parent_field',
    'child_field',
    'icon',
    'draggable',
}

class View(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[('hierarchy', "Hierarchy")])

    def _is_qweb_based_view(self, view_type):
        return super()._is_qweb_based_view(view_type) or view_type == "hierarchy"

    def _validate_tag_hierarchy(self, node, name_manager, node_info):
        if not node_info['validate']:
            return

        templates_count = 0
        for child in node.iterchildren(tag=etree.Element):
            if child.tag == 'templates':
                if not templates_count:
                    templates_count += 1
                else:
                    msg = _('Hierarchy view can contain only one templates tag')
                    self._raise_view_error(msg, child)
            elif child.tag != 'field':
                msg = _('Hierarchy child can only be field or template, got %s', child.tag)
                self._raise_view_error(msg, child)

        remaining = set(node.attrib) - HIERARCHY_VALID_ATTRIBUTES
        if remaining:
            msg = _(
                "Invalid attributes (%s) in hierarchy view. Attributes must be in (%s)",
                ','.join(remaining), ','.join(HIERARCHY_VALID_ATTRIBUTES),
            )
            self._raise_view_error(msg, node)
