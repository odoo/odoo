# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectCollaborator(models.Model):
    _name = 'project.collaborator'
    _description = 'Collaborators in project shared'

    project_id = fields.Many2one('project.project', 'Project Shared', domain=[('privacy_visibility', '=', 'portal')], required=True)
    partner_id = fields.Many2one('res.partner', 'Collaborator', required=True)

    _sql_constraints = [
        ('unique_collaborator', 'UNIQUE(project_id, partner_id)', 'A collaborator cannot be selected more than once in the project sharing access. Please remove duplicate(s) and try again.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        project_collaborators = super().create(vals_list)
        non_authenticated_collaborator = project_collaborators.partner_id.filtered(lambda partner: not partner.user_ids)
        non_authenticated_collaborator._create_portal_users()
        return project_collaborators
