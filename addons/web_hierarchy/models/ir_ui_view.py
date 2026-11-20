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
    'child_field',
    'default_order',
    'card_id',
}


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[('hierarchy', "Hierarchy")])

    def _is_qweb_based_view(self, view_type):
        return super()._is_qweb_based_view(view_type) or view_type == "hierarchy"

    def _postprocess_tag_hierarchy(self, node, name_manager, node_info):
        if child_field_name := node.get('child_field'):
            child_field = name_manager.model._fields.get(child_field_name)
            names = [child_field_name, child_field.inverse_name] if child_field else [child_field_name]
            name_manager.must_have_fields(node, names, node_info, ('child_field', child_field_name))
        if card_id := node.get('card_id'):
            card_arch, _card_view = self._get_view(view_id=int(card_id), view_type='card')
            node.append(card_arch)

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

        card_id = node.get('card_id')
        if card_id and not card_id.isdigit():
            self._raise_view_error(_("Invalid card_id '%s' in hierarchy view, it must be a view id", card_id), node)
        if not card_id and not templates_count:
            self._raise_view_error(_("Hierarchy view must have a card_id attribute or a templates tag"), node)

        child_field_name = node.get('child_field')
        if not child_field_name:
            self._raise_view_error(_("Hierarchy view must have a child_field attribute"), node)
        child_field = name_manager.model._fields.get(child_field_name)
        if child_field is None:
            self._raise_view_error(_(
                "Field '%(field)s' set as child_field does not exist on model '%(model)s'",
                field=child_field_name, model=name_manager.model._name,
            ), node)
        if child_field.type != 'one2many':
            self._raise_view_error(_(
                "Field '%s' set as child_field must be a one2many field", child_field_name,
            ), node)
        if child_field.comodel_name != name_manager.model._name:
            self._raise_view_error(_(
                "Field '%(field)s' set as child_field must target the model of the view '%(model)s'",
                field=child_field_name, model=name_manager.model._name,
            ), node)
        if not child_field.inverse_name:
            self._raise_view_error(_(
                "Field '%s' set as child_field must have an inverse many2one field", child_field_name,
            ), node)

        remaining = set(node.attrib) - HIERARCHY_VALID_ATTRIBUTES
        if remaining:
            msg = _(
                "Invalid attributes (%(invalid_attributes)s) in hierarchy view. Attributes must be in (%(valid_attributes)s)",
                invalid_attributes=remaining,
                valid_attributes=HIERARCHY_VALID_ATTRIBUTES,
            )
            self._raise_view_error(msg, node)

    def _get_view_info(self):
        return {'hierarchy': {'icon': 'family_history'}} | super()._get_view_info()
