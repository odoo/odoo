# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from collections import defaultdict

from odoo import api, fields, models, _, _lt
from odoo.exceptions import UserError
from odoo.tools import frozendict


class ProjectProject(models.Model):
    _name = 'project.project'
    _inherit = ['project.project', 'documents.mixin']

    use_documents = fields.Boolean("Use Documents", default=True)
    documents_folder_id = fields.Many2one('documents.folder', string="Workspace", domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", copy=False,
        help="Workspace in which all of the documents of this project will be categorized. All of the attachments of your tasks will be automatically added as documents in this workspace as well.")
    documents_tag_ids = fields.Many2many('documents.tag', 'project_documents_tag_rel', string="Default Tags", domain="[('folder_id', 'parent_of', documents_folder_id)]", copy=True)
    document_count = fields.Integer(compute='_compute_attached_document_count', string="Number of documents in Project", groups='documents.group_documents_user')
    shared_document_ids = fields.One2many('documents.document', string='Shared Documents', compute='_compute_shared_document_ids')
    shared_document_count = fields.Integer("Shared Documents Count", compute='_compute_shared_document_ids')

    @api.constrains('documents_folder_id')
    def _check_company_is_folder_company(self):
        for project in self:
            if project.documents_folder_id and project.documents_folder_id.company_id and project.company_id != project.documents_folder_id.company_id:
                raise UserError(_('The "%s" workspace should either be in the "%s" company like this project or be open to all companies.', project.documents_folder_id.name, project.company_id.name))

    def _compute_attached_document_count(self):
        Task = self.env['project.task']
        task_read_group = Task._read_group(
            [('project_id', 'in', self.ids)],
            ['project_id'],
            ['id:array_agg'],
        )
        task_ids = []
        task_ids_per_project_id = {}
        for project, ids in task_read_group:
            task_ids += ids
            task_ids_per_project_id[project.id] = ids
        Document = self.env['documents.document']
        project_document_read_group = Document._read_group(
            [('res_model', '=', 'project.project'), ('res_id', 'in', self.ids)],
            ['res_id'],
            ['__count'],
        )
        document_count_per_project_id = dict(project_document_read_group)
        document_count_per_task_id = Task.browse(task_ids)._get_task_document_data()
        for project in self:
            task_ids = task_ids_per_project_id.get(project.id, [])
            project.document_count = document_count_per_project_id.get(project.id, 0) \
                + sum(
                    document_count_per_task_id.get(task_id, 0)
                    for task_id in task_ids
                )

    def _compute_shared_document_ids(self):
        tasks_read_group = self.env['project.task']._read_group(
            [('project_id', 'in', self.ids)],
            ['project_id'],
            ['id:array_agg'],
        )

        project_id_per_task_id = {}
        task_ids = []

        for project, ids in tasks_read_group:
            task_ids += ids
            for task_id in ids:
                project_id_per_task_id[task_id] = project.id

        documents_read_group = self.env['documents.document']._read_group(
            [
                '&',
                    ('is_shared', '=', True),
                    '|',
                        '&',
                            ('res_model', '=', 'project.project'),
                            ('res_id', 'in', self.ids),
                        '&',
                            ('res_model', '=', 'project.task'),
                            ('res_id', 'in', task_ids),
            ],
            ['res_model', 'res_id'],
            ['id:array_agg'],
        )

        document_ids_per_project_id = defaultdict(list)
        for res_model, res_id, ids in documents_read_group:
            if res_model == 'project.project':
                document_ids_per_project_id[res_id] += ids
            else:
                project_id = project_id_per_task_id[res_id]
                document_ids_per_project_id[project_id] += ids

        for project in self:
            shared_document_ids = self.env['documents.document'] \
                .browse(document_ids_per_project_id[project.id])
            project.shared_document_ids = shared_document_ids
            project.shared_document_count = len(shared_document_ids)

    @api.onchange('documents_folder_id')
    def _onchange_documents_folder_id(self):
        self.env['documents.document'].search([
            ('res_model', '=', 'project.task'),
            ('res_id', 'in', self.task_ids.ids),
            ('folder_id', '=', self._origin.documents_folder_id.id),
        ]).folder_id = self.documents_folder_id
        self.documents_tag_ids = False

    def _create_missing_folders(self):
        folders_to_create_vals = []
        projects_with_folder_to_create = []
        documents_project_folder_id = self.env.ref('documents_project.documents_project_folder').id

        for project in self:
            if not project.documents_folder_id:
                folder_vals = {
                    'name': project.name,
                    'parent_folder_id': documents_project_folder_id,
                    'company_id': project.company_id.id,
                }
                folders_to_create_vals.append(folder_vals)
                projects_with_folder_to_create.append(project)

        created_folders = self.env['documents.folder'].sudo().create(folders_to_create_vals)
        for project, folder in zip(projects_with_folder_to_create, created_folders):
            project.sudo().documents_folder_id = folder

    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        if not self.env.context.get('no_create_folder'):
            projects.filtered(lambda project: project.use_documents)._create_missing_folders()
        return projects

    def write(self, vals):
        if 'company_id' in vals:
            for project in self:
                if project.documents_folder_id and project.documents_folder_id.company_id and len(project.documents_folder_id.project_ids) > 1:
                    other_projects = project.documents_folder_id.project_ids - self
                    if other_projects and other_projects.company_id.id != vals['company_id']:
                        lines = [f"- {project.name}" for project in other_projects]
                        raise UserError(_(
                            'You cannot change the company of this project, because its workspace is linked to the other following projects that are still in the "%s" company:\n%s\n\n'
                            'Please update the company of all projects so that they remain in the same company as their workspace, or leave the company of the "%s" workspace blank.',
                            other_projects.company_id.name, '\n'.join(lines), project.documents_folder_id.name))

        if 'name' in vals and len(self.documents_folder_id.project_ids) == 1 and self.name == self.documents_folder_id.name:
            self.documents_folder_id.sudo().name = vals['name']
        res = super().write(vals)
        if 'company_id' in vals:
            for project in self:
                if project.documents_folder_id and project.documents_folder_id.company_id:
                    project.documents_folder_id.company_id = project.company_id
        if not self.env.context.get('no_create_folder'):
            self.filtered('use_documents')._create_missing_folders()
        return res

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        # We have to add no_create_folder=True to the context, otherwise a folder
        # will be automatically created during the call to create.
        # However, we cannot use with_context, as it intanciates a new recordset,
        # and this copy would call itself infinitely.
        previous_context = self.env.context
        self.env.context = frozendict(self.env.context, no_create_folder=True)
        project = super().copy(default)
        self.env.context = previous_context

        if not self.env.context.get('no_create_folder') and project.use_documents and self.documents_folder_id:
            project.documents_folder_id = self.documents_folder_id.copy({'name': project.name})
        return project

    def _get_stat_buttons(self):
        buttons = super(ProjectProject, self)._get_stat_buttons()
        if self.use_documents:
            buttons.append({
                'icon': 'file-text-o',
                'text': _lt('Documents'),
                'number': self.document_count,
                'action_type': 'object',
                'action': 'action_view_documents_project',
                'additional_context': json.dumps({
                    'active_id': self.id,
                }),
                'show': self.use_documents,
                'sequence': 20,
            })
        return buttons

    def action_view_documents_project(self):
        self.ensure_one()
        return {
            'res_model': 'documents.document',
            'type': 'ir.actions.act_window',
            'name': _("%(project_name)s's Documents", project_name=self.name),
            'domain': [
            '|',
                '&',
                ('res_model', '=', 'project.project'), ('res_id', '=', self.id),
                '&',
                ('res_model', '=', 'project.task'), ('res_id', 'in', self.tasks.ids),
            ],
            'view_mode': 'kanban,tree,form',
            'context': {'default_res_model': 'project.project', 'default_res_id': self.id, 'limit_folders_to_project': True, 'default_tag_ids': self.documents_tag_ids.ids},
        }

    def _get_document_tags(self):
        return self.documents_tag_ids

    def _get_document_folder(self):
        return self.documents_folder_id

    def _check_create_documents(self):
        return self.use_documents and super()._check_create_documents()
