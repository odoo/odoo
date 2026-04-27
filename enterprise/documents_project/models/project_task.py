# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import api, Command, fields, models, _
from odoo.osv import expression


class ProjectTask(models.Model):
    _name = 'project.task'
    _inherit = ['project.task', 'documents.mixin']

    project_use_documents = fields.Boolean("Use Documents", related='project_id.use_documents', export_string_translation=False)
    documents_folder_id = fields.Many2one(related='project_id.documents_folder_id', export_string_translation=False)
    folder_user_permission = fields.Selection(related='documents_folder_id.user_permission')
    document_ids = fields.One2many('documents.document', 'res_id', string='Documents',
                                   domain=[('res_model', '=', 'project.task'), ('shortcut_document_id', '=', False)])
    document_count = fields.Integer(compute='_compute_document_count', export_string_translation=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS | {'project_use_documents', 'folder_user_permission', 'document_ids', 'document_count'}

    def _get_task_document_data(self):
        domain = expression.AND([
            [('type', '!=', 'folder')], [('shortcut_document_id', '=', False)],
            [('res_model', '=', 'project.task')], [('res_id', 'in', self.ids)],
        ])
        return dict(self.env['documents.document']._read_group(domain, ['res_id'], ['__count']))

    @api.depends('project_use_documents', 'document_ids')
    def _compute_document_count(self):
        project_using_documents = self.filtered('project_use_documents')
        for task in project_using_documents:
            task.document_count = len(task.document_ids)
        (self - project_using_documents).document_count = 0

    def unlink(self):
        # unlink documents.document directly so mail.activity.mixin().unlink is called
        self.env['documents.document'].sudo().search([('attachment_id', 'in', self.attachment_ids.ids)]).unlink()
        return super(ProjectTask, self).unlink()

    def _get_document_access_ids(self):
        return False

    def _get_document_tags(self):
        return self.project_id.documents_tag_ids

    def _get_document_owner(self):
        return self.env.user if not self.env.user._is_public() else super()._get_document_owner()

    def _get_document_vals_access_rights(self):
        return {
            'access_internal': 'edit' if self.project_id.privacy_visibility != 'followers' else 'none',
            'access_via_link': 'view',
            'is_access_via_link_hidden': False,
        }

    def _get_document_folder(self):
        return self.project_id.documents_folder_id

    def _get_document_partner(self):
        return self.partner_id

    def _check_create_documents(self):
        return self.project_use_documents and super()._check_create_documents()

    def _get_attachments_search_domain(self):
        self.ensure_one()
        return expression.AND([
            super()._get_attachments_search_domain(),
            [('document_ids', '=', False)],
        ])

    def action_view_documents_project_task(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("documents_project.action_view_documents_project_task")
        return action | {
            'context': {
                **ast.literal_eval(action['context'].replace('active_id', str(self.id))),
                'active_model': 'project.task',
                'default_res_id': self.id,
                'default_res_model': 'project.task',
                'no_documents_unique_folder_id': True,
                'searchpanel_default_folder_id': self.documents_folder_id.id,
            }
        }

    def action_open_documents_portal(self):
        self.ensure_one()
        return {
            'name': _("Task's Documents"),
            'type': 'ir.actions.act_url',
            'url': f"/my/tasks/{self.id}/documents/",
        }

    def write(self, vals):
        if 'project_id' in vals:
            documents_to_move = self.env['documents.document']
            for task in self:
                documents_to_move |= task.document_ids.filtered(
                    lambda d: d.folder_id == task.documents_folder_id
                )
        res = super().write(vals)

        if 'project_id' in vals:
            for task in self:
                if not task.document_ids:
                    continue
                if not (vals.get('project_id') and task.project_use_documents):
                    task.document_ids = [Command.clear()]
                elif task.project_use_documents:
                    (task.document_ids & documents_to_move).folder_id = task.documents_folder_id.id
        return res
