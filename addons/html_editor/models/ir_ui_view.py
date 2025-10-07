# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from lxml import etree

from odoo import api, models
from odoo.exceptions import MissingError

_logger = logging.getLogger(__name__)


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def _view_get_inherited_children(self, view):
        if self.env.context.get('no_primary_children', False):
            original_hierarchy = self.env.context.get('__views_get_original_hierarchy', [])
            return view.inherit_children_ids.filtered(lambda extension: extension.mode != 'primary' or extension.id in original_hierarchy)
        return view.inherit_children_ids

    # Returns all views (called and inherited) related to a view
    # Used by translation mechanism, SEO and optional templates

    @api.model
    def _views_get(self, view_id, get_children=True, bundles=False, root=True, visited=None):
        """ For a given view ``view_id``, should return:
                * the view itself (starting from its top most parent)
                * all views inheriting from it, enabled or not
                  - but not the optional children of a non-enabled child
                * all views called from it (via t-call)

            :returns: recordset of ir.ui.view
        """
        try:
            if isinstance(view_id, models.BaseModel):
                view = view_id
            else:
                view = self._get_template_view(view_id)
        except MissingError:
            _logger.warning("Could not find view object with view_id '%s'", view_id)
            return self.env['ir.ui.view']

        if visited is None:
            visited = []
        original_hierarchy = self.env.context.get('__views_get_original_hierarchy', [])
        while root and view.inherit_id:
            original_hierarchy.append(view.id)
            view = view.inherit_id

        views_to_return = view

        node = etree.fromstring(view.arch)
        xpath = "//t[@t-call]"
        if bundles:
            xpath += "| //t[@t-call-assets]"
        for child in node.xpath(xpath):
            try:
                called_view = self._get_template_view(child.get('t-call', child.get('t-call-assets')))
            except MissingError:
                continue
            if called_view and called_view not in views_to_return and called_view.id not in visited:
                views_to_return += self._views_get(called_view, get_children=get_children, bundles=bundles, visited=visited + views_to_return.ids)

        if not get_children:
            return views_to_return

        extensions = self._view_get_inherited_children(view)

        # Keep children in a deterministic order regardless of their applicability
        for extension in extensions.sorted(key=lambda v: v.id):
            # only return optional grandchildren if this child is enabled
            if extension.id not in visited:
                for ext_view in self._views_get(extension, get_children=extension.active, root=False, visited=visited + views_to_return.ids):
                    if ext_view not in views_to_return:
                        views_to_return += ext_view
        return views_to_return

    @api.model
    def get_related_views(self, key, bundles=False):
        """ Get inherit view's informations of the template ``key``.
            returns templates info (which can be active or not)
            ``bundles=True`` returns also the asset bundles
        """
        user_groups = set(self.env.user.group_ids)
        new_context = {
            **self.env.context,
            'active_test': False,
        }
        new_context.pop('lang', None)
        View = self.with_context(new_context)
        views = View._views_get(key, bundles=bundles)
        return views.filtered(lambda v: not v.group_ids or len(user_groups.intersection(v.group_ids)))
