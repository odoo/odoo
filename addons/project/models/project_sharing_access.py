# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


PROJECT_SHARING_ACCESS_MODE = [
    ('read', 'Read'),
    ('comment', 'Comment'),
    ('edit', 'Edit'),
]


class ProjectSharingAccess(models.Model):
    _name = 'project.sharing.access'
    _description = 'Project Sharing Access'

    project_id = fields.Many2one('project.project', 'Project Shared', required=True)
    user_id = fields.Many2one('res.users', string='Portal Users', domain=lambda self: [('groups_id', 'in', self.env.ref('base.group_portal').id)], required=True)
    access_mode = fields.Selection(PROJECT_SHARING_ACCESS_MODE, string='Access Mode', required=True)

    _sql_constraints = [
        ('unique_user', 'UNIQUE(project_id, user_id)', 'A user cannot be selected more than once in the project sharing access. Please remove duplicate(s) and try again.'),
    ]
