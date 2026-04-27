# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.tools import format_list
from lxml import etree

GANTT_VALID_ATTRIBUTES = set([
    '__validate__',                     # ir.ui.view implementation detail
    'date_start',
    'date_stop',
    'default_scale',
    'default_range',
    'class',
    'js_class',
    'form_view_id',
    'progress',
    'consolidation',
    'consolidation_max',
    'consolidation_exclude',
    'string',
    'create',
    'on_create',
    'cell_create',
    'edit',
    'delete',
    'plan',
    'default_group_by',
    'dynamic_range',
    'display_mode',
    'display_unavailability',
    'disable_drag_drop',
    'total_row',
    'collapse_first_level',
    'offset',
    'scales',
    'thumbnails',
    'precision',
    'color',
    'decoration-secondary',
    'decoration-success',
    'decoration-info',
    'decoration-warning',
    'decoration-danger',
    'sample',
    'progress_bar',
    'dependency_field',
    'dependency_inverted_field',
    'pill_label',
    'groups_limit'
])

class View(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[('gantt', 'Gantt')])

    def _validate_tag_gantt(self, node, name_manager, node_info):
        if not node_info['validate']:
            return

        templates_count = 0
        for child in node.iterchildren(tag=etree.Element):
            if child.tag == 'templates':
                if not templates_count:
                    templates_count += 1
                else:
                    msg = _('Gantt view can contain only one templates tag')
                    self._raise_view_error(msg, child)
            elif child.tag != 'field':
                msg = _('Gantt child can only be field or template, got %s', child.tag)
                self._raise_view_error(msg, child)

        default_scale = node.get('default_scale')
        if default_scale:
            if default_scale not in ('day', 'week', 'week_2', 'month', 'month_3', 'year'):
                self._raise_view_error(_("Invalid default_scale '%s' in gantt", default_scale), node)
        default_range = node.get('default_range')
        if default_range:
            if default_range not in ('day', 'week', 'month', 'quarter', 'year'):
                self._raise_view_error(_("Invalid default_range '%s' in gantt", default_range), node)
        display_mode = node.get('display_mode')
        if display_mode:
            if display_mode not in ('dense', 'sparse'):
                self._raise_view_error(_("Invalid display_mode '%s' in gantt", display_mode), node)
        attrs = set(node.attrib)
        if 'date_start' not in attrs:
            msg = _("Gantt must have a 'date_start' attribute")
            self._raise_view_error(msg, node)

        if 'date_stop' not in attrs:
            msg = _("Gantt must have a 'date_stop' attribute")
            self._raise_view_error(msg, node)

        if 'dependency_field' in attrs and 'dependency_inverted_field' not in attrs:
            msg = _("Gantt must have a 'dependency_inverted_field' attribute once the 'dependency_field' is specified")
            self._raise_view_error(msg, node)

        remaining = attrs - GANTT_VALID_ATTRIBUTES
        if remaining:
            msg = _(
                "Invalid attributes (%(invalid_attributes)s) in gantt view. Attributes must be in (%(valid_attributes)s)",
                invalid_attributes=format_list(self.env, remaining),
                valid_attributes=format_list(self.env, GANTT_VALID_ATTRIBUTES),
            )
            self._raise_view_error(msg, node)

    def _get_view_fields(self, view_type, models):
        if view_type == 'gantt':
            models[self._name] = list(self._fields.keys())
            return models
        return super()._get_view_fields(view_type, models)

    def _get_view_info(self):
        return {'gantt': {'icon': 'fa fa-tasks'}} | super()._get_view_info()

    def _is_qweb_based_view(self, view_type):
        return view_type == 'gantt' or super()._is_qweb_based_view(view_type)
