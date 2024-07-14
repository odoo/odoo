# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import fields, models, _
from odoo.osv import expression


class ProjectTask(models.Model):
    _name = 'project.task'
    _inherit = ['project.task', 'documents.mixin']

    project_use_documents = fields.Boolean("Use Documents", related='project_id.use_documents')
    documents_folder_id = fields.Many2one('documents.folder', related='project_id.documents_folder_id')
    document_ids = fields.One2many('documents.document', 'res_id', string='Documents', domain=[('res_model', '=', 'project.task')])
    shared_document_ids = fields.One2many('documents.document', string='Shared Documents', compute='_compute_shared_document_ids')
    document_count = fields.Integer(compute='_compute_attached_document_count', string="Number of documents in Task", groups='documents.group_documents_user')
    shared_document_count = fields.Integer("Shared Documents Count", compute='_compute_shared_document_ids')

    def _get_task_document_data(self):
        domain = [('res_model', '=', 'project.task'), ('res_id', 'in', self.ids)]
        return dict(self.env['documents.document']._read_group(domain, ['res_id'], ['__count']))

    def _compute_attached_document_count(self):
        tasks_data = self._get_task_document_data()
        for task in self:
            task.document_count = tasks_data.get(task.id, 0)

    def _compute_shared_document_ids(self):
        documents_read_group = self.env['documents.document']._read_group(
            [
                '&',
                    ('is_shared', '=', True),
                    '&',
                        ('res_model', '=', 'project.task'),
                        ('res_id', 'in', self.ids),
            ],
            ['res_id'],
            ['id:array_agg', '__count'],
        )
        document_ids_and_count_per_task_id = {res_id: ids_count for res_id, *ids_count in documents_read_group}
        for task in self:
            task.shared_document_ids, task.shared_document_count = document_ids_and_count_per_task_id.get(task.id, (False, 0))

    def unlink(self):
        # unlink documents.document directly so mail.activity.mixin().unlink is called
        self.env['documents.document'].sudo().search([('attachment_id', 'in', self.attachment_ids.ids)]).unlink()
        return super(ProjectTask, self).unlink()

    def _get_document_tags(self):
        return self.project_id.documents_tag_ids

    def _get_document_folder(self):
        return self.project_id.documents_folder_id

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
        action = self.env['ir.actions.act_window']._for_xml_id('documents_project.action_view_documents_project_task')
        action['context'] = {
            **ast.literal_eval(action['context'].replace('active_id', str(self.id))),
            'default_tag_ids': self.project_id.documents_tag_ids.ids,
        }
        return action

    def action_open_shared_documents(self):
        self.ensure_one()
        return {
            'name': _("Task's Documents"),
            'type': 'ir.actions.act_url',
            'url': f"/my/tasks/{self.id}/documents/",
        }
