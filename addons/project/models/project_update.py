# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models

class ProjectUpdateStatus(models.Model):
    _name = 'project.update.status'
    _description = 'Project Update Status'
    _order = 'sequence, id'

    def _get_default_project_ids(self):
        default_project_id = self.env.context.get('default_project_id')
        return [default_project_id] if default_project_id else None

    name = fields.Char()
    color = fields.Integer()
    default = fields.Boolean()
    project_ids = fields.Many2many('project.project', 'project_update_status_rel', 'update_status_id', 'project_id', string='Projects',
                                   default=_get_default_project_ids)

class ProjectUpdate(models.Model):
    _name = 'project.update'
    _description = 'Project Update'
    _order = 'create_date desc'

    def _get_default_name(self):
        return _("Status Update - %(date)s", date=fields.Date.to_string(fields.Date.today()))

    def _get_default_status(self):
        return self.env['project.update.status'].search([('default', '=', True)], limit=1)

    name = fields.Char("Title", default=_get_default_name, required=True)
    project_id = fields.Many2one("project.project", required=True)
    status_id = fields.Many2one("project.update.status", copy=False, default=_get_default_status, required=True)
    progress = fields.Integer()
    description = fields.Html()
