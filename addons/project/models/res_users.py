# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_group_subtask_project = fields.Boolean(
        'Use Subtasks', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='project.group_subtask_project')

    has_group_project_rating = fields.Boolean(
        'Use Rating on Project', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='project.group_project_rating')

    group_project_user = fields.Selection(
        selection=lambda self: self._get_group_selection('base.module_category_project_management'),
        string='Project', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='base.module_category_project_management')
