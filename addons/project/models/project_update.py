# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import _, api, fields, models

class ProjectUpdateStatus(models.Model):
    _name = 'project.update.status'
    _description = 'Project Update Status'
    _order = 'default desc, sequence, id'

    def _get_default_project_ids(self):
        default_project_id = self.env.context.get('default_project_id')
        return [default_project_id] if default_project_id else None

    name = fields.Char()
    color = fields.Integer()
    default = fields.Boolean()
    sequence = fields.Integer()
    project_ids = fields.Many2many('project.project', 'project_update_status_rel', 'update_status_id', 'project_id', string='Projects',
                                   default=_get_default_project_ids)

class ProjectUpdate(models.Model):
    _name = 'project.update'
    _description = 'Project Update'
    _order = 'create_date desc'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']

    def _get_default_status(self):
        project_id = self.env.context.get('default_project_id')
        if not project_id:
            return False
        return self.env['project.update.status'].search([('project_ids', '=', project_id)], limit=1)

    def _get_default_description(self):
        return self.env['project.project'].browse(self.env.context.get('default_project_id')).status_updates_template or \
            self.env.company.project_status_updates_template

    name = fields.Char("Title", required=True)
    status_id = fields.Many2one("project.update.status", copy=False, default=_get_default_status, required=True)
    color = fields.Integer(related="status_id.color")
    progress = fields.Integer()
    user_id = fields.Many2one('res.users', string="Author", required=True, default=lambda self: self.env.user)
    description = fields.Html(default=_get_default_description)
    date = fields.Date(default=fields.Date.today)
    project_id = fields.Many2one("project.project", required=True)
    project_user_id = fields.Many2one(related='project_id.user_id', readonly=True)
    project_date_deadline = fields.Date(related='project_id.date_deadline', readonly=True)
    project_description = fields.Html(related='project_id.description', readonly=True, string='Project Description')
    previous_status_update_ids = fields.One2many(related='project_id.update_ids')

    # ----- ORM Override
    @api.model
    def create(self, vals):
        update = super(ProjectUpdate, self).create(vals)
        return update

    def action_open_update_status(self):
        last_draft = self.search_read([
            ('project_id', '=', self.project_id.id),
            ('user_id', '=', self.env.uid)
        ], ['id'], limit=1)
        action = self.env["ir.actions.actions"]._for_xml_id("project.open_project_update_form")
        if last_draft:
            action['res_id'] = last_draft[0]['id']
        return action
