# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import _, frozendict
from odoo.models import PREFETCH_MAX


class ProjectProject(models.Model):
    _name = 'project.project'
    _inherit = ['project.project', 'documents.mixin']

    use_documents = fields.Boolean("Documents", default=True)
    documents_folder_id = fields.Many2one(
        'documents.document', string="Folder", copy=False,
        domain="[('type', '=', 'folder'), ('shortcut_document_id', '=', False), "
               "'|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Folder in which all of the documents of this project will be categorized. All of the attachments of "
             "your tasks will be automatically added as documents in this workspace as well.")
    documents_tag_ids = fields.Many2many(
        'documents.tag', 'project_documents_tag_rel', string="Default Tags", copy=True)
    document_count = fields.Integer(
        compute='_compute_documents', export_string_translation=False)
    document_ids = fields.One2many('documents.document', compute='_compute_documents', export_string_translation=False)

    @api.ondelete(at_uninstall=False)
    def _archive_folder_on_projects_unlinked(self):
        """ Archives the project folder if all its related projects are unlinked. """
        self.env['documents.document'].sudo().search([
            ('project_ids', '!=', False),
            ('project_ids', 'not any', [('id', 'not in', self.ids)]
        )]).sudo(False)._filtered_access('unlink').action_archive()

    @api.constrains('documents_folder_id')
    def _check_company_is_folders_company(self):
        for project in self.filtered('documents_folder_id'):
            if folder := project['documents_folder_id']:
                if folder.company_id and project.company_id != folder.company_id:
                    raise UserError(_(
                        'The "%(folder)s" folder should either be in the "%(company)s" company like this'
                        ' project or be open to all companies.',
                        folder=folder.name, company=project.company_id.name)
                    )

    def _compute_documents(self):
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

        # perf optimization:
        # prefer a subquery when searching documents on too many tasks
        if len(task_ids) > PREFETCH_MAX:
            task_ids = self.env['project.task']._search([('project_id', 'in', self.ids)])

        documents_read_group = self.env['documents.document']._read_group(
            [
                ('user_permission', '!=', 'none'),
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
            document_ids = self.env['documents.document'] \
                .browse(document_ids_per_project_id[project.id])
            project.document_ids = document_ids
            project.document_count = len(document_ids)

    @api.onchange('documents_folder_id')
    def _onchange_documents_folder_id(self):
        self.env['documents.document'].search([
            ('res_model', '=', 'project.task'),
            ('res_id', 'in', self.task_ids.ids),
            ('folder_id', '=', self._origin.documents_folder_id.id),
        ]).folder_id = self.documents_folder_id

    def _create_missing_folders(self):
        folders_to_create_vals = []
        projects_with_folder_to_create = []
        documents_project_folder_id = self.env.ref('documents_project.document_project_folder').id

        for project in self:
            if not project.documents_folder_id:
                folder_vals = {
                    'access_internal': 'edit' if project.privacy_visibility != 'followers' else 'none',
                    'company_id': project.company_id.id,
                    'folder_id': documents_project_folder_id,
                    'name': project.name,
                    'type': 'folder',
                }
                folders_to_create_vals.append(folder_vals)
                projects_with_folder_to_create.append(project)

        if folders_to_create_vals:
            created_folders = self.env['documents.document'].sudo().create(folders_to_create_vals)
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
                            'You cannot change the company of this project, because its workspace is linked to the other following projects that are still in the "%(other_company)s" company:\n%(other_workspaces)s\n\n'
                            'Please update the company of all projects so that they remain in the same company as their workspace, or leave the company of the "%(workspace)s" workspace blank.',
                            other_company=other_projects.company_id.name, other_workspaces='\n'.join(lines), workspace=project.documents_folder_id.name))

        if 'name' in vals and len(self.documents_folder_id.sudo().project_ids) == 1 and self.name == self.documents_folder_id.sudo().name:
            self.documents_folder_id.sudo().name = vals['name']

        if new_visibility := vals.get('privacy_visibility'):
            (self.documents_folder_id | self.document_ids).action_update_access_rights(
                access_internal='none' if new_visibility == 'followers' else 'edit')

        res = super().write(vals)
        if 'company_id' in vals:
            for project in self:
                if project.documents_folder_id and project.documents_folder_id.company_id:
                    project.documents_folder_id.company_id = project.company_id
        if not self.env.context.get('no_create_folder'):
            self.filtered('use_documents')._create_missing_folders()
        return res

    def copy(self, default=None):
        # We have to add no_create_folder=True to the context, otherwise a folder
        # will be automatically created during the call to create.
        # However, we cannot use with_context, as it instantiates a new recordset,
        # and this copy would call itself infinitely.
        previous_context = self.env.context
        self.env.context = frozendict(self.env.context, no_create_folder=True)
        copied_projects = super().copy(default)
        self.env.context = previous_context

        for old_project, new_project in zip(self, copied_projects):
            if not self.env.context.get('no_create_folder') and new_project.use_documents and old_project.documents_folder_id:
                new_project.documents_folder_id = old_project.documents_folder_id.with_context(
                    documents_copy_folders_only=True).sudo().copy(
                        {'name': new_project.name, 'owner_id': self.env.ref('base.user_root').id}
                    )
        return copied_projects

    def _get_stat_buttons(self):
        buttons = super(ProjectProject, self)._get_stat_buttons()
        if self.use_documents:
            buttons.append({
                'icon': 'file-text-o',
                'text': self.env._('Documents'),
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
        action = self.env["ir.actions.actions"]._for_xml_id("documents.document_action")
        return action | {
            'view_mode': 'kanban,list',
            'context': {
                'active_id': self.id,
                'active_model':  'project.project',
                'default_res_id': self.id,
                'default_res_model': 'project.project',
                'no_documents_unique_folder_id': True,
                'searchpanel_default_folder_id': self._get_document_folder().id,
            }
        }

    def _get_document_access_ids(self):
        return False

    def _get_document_tags(self):
        return self.documents_tag_ids

    def _get_document_folder(self):
        if self.use_documents:
            if not self.documents_folder_id:
                self._create_missing_folders()
            return self.documents_folder_id
        return super()._get_document_folder()

    def _get_document_partner(self):
        return self.partner_id

    def _get_document_vals_access_rights(self):
        return {
            'access_internal': 'none' if self.privacy_visibility == 'followers' else 'edit',
            'access_via_link': 'view',
            'is_access_via_link_hidden': False,
        }

    def _check_create_documents(self):
        return self.use_documents and super()._check_create_documents()

    def _check_project_read_access(self):
        return self.has_access('read')
