# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import SQL


class Document(models.Model):
    _inherit = 'documents.document'

    is_shared = fields.Boolean(compute='_compute_is_shared', search='_search_is_shared')
    project_id = fields.Many2one('project.project', compute='_compute_project_id', search='_search_project_id')
    task_id = fields.Many2one('project.task', compute='_compute_task_id', search='_search_task_id')

    def _compute_is_shared(self):
        search_domain = [
            '&',
                '|',
                    ('date_deadline', '=', False),
                    ('date_deadline', '>', fields.Date.today()),
                '&',
                    ('type', '=', 'ids'),
                    ('document_ids', 'in', self.ids),
        ]

        doc_share_read_group = self.env['documents.share']._read_group(
            search_domain,
            ['document_ids'],
            ['__count'],
        )
        doc_share_count_per_doc_id = {document.id: count for document, count in doc_share_read_group}

        for document in self:
            document.is_shared = doc_share_count_per_doc_id.get(document.id) or document.folder_id.is_shared

    @api.model
    def _search_is_shared(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise NotImplementedError(f'The search does not support the {operator} operator or {value} value.')

        share_links = self.env['documents.share'].search_read(
            ['|', ('date_deadline', '=', False), ('date_deadline', '>', fields.Date.today())],
            ['document_ids', 'folder_id', 'include_sub_folders', 'type'],
        )

        shared_folder_ids = set()
        shared_folder_with_descendants_ids = set()
        shared_document_ids = set()

        for link in share_links:
            if link['type'] == 'domain':
                if link['include_sub_folders']:
                    shared_folder_with_descendants_ids.add(link['folder_id'][0])
                else:
                    shared_folder_ids.add(link['folder_id'][0])
            else:
                shared_document_ids |= set(link['document_ids'])

        domain = [
            '|',
                '|',
                    ('folder_id', 'in', list(shared_folder_ids)),
                    ('folder_id', 'child_of', list(shared_folder_with_descendants_ids)),
                ('id', 'in', list(shared_document_ids)),
        ]

        if (operator == '=') ^ value:
            domain.insert(0, '!')
        return domain

    @api.depends('res_id', 'res_model')
    def _compute_project_id(self):
        for record in self:
            if record.res_model == 'project.project':
                record.project_id = self.env['project.project'].browse(record.res_id)
            elif record.res_model == 'project.task':
                record.project_id = self.env['project.task'].browse(record.res_id).project_id
            else:
                record.project_id = False

    @api.model
    def _search_project_id(self, operator, value):
        if operator in ('=', '!=') and isinstance(value, bool): # needs to be the first condition as True and False are instances of int
            if not value:
                operator = operator == "=" and "!=" or "="
            comparator = operator == "=" and "|" or "&"
            return [
                comparator, ("res_model", operator, "project.project"), ("res_model", operator, "project.task"),
            ]
        elif operator in ('=', '!=', "in", "not in") and (isinstance(value, int) or isinstance(value, list)):
            return [
                "|", "&", ("res_model", "=", "project.project"), ("res_id", operator, value),
                     "&", ("res_model", "=", "project.task"),
                          ("res_id", "in", self.env["project.task"]._search([("project_id", operator, value)])),
            ]
        elif operator in ("ilike", "not ilike", "=", "!=") and isinstance(value, str):
            query_project = self.env["project.project"]._search([(self.env["project.project"]._rec_name, operator, value)])
            project_select, project_where_params = query_project.select()
            # We may need to flush `res_model` `res_id` if we ever get a flow that assigns + search at the same time..
            # We only apply security rules to projects as security rules on documents will be applied prior
            # to this leaf. Not applying security rules on tasks might give more result than expected but it would not allow
            # access to an unauthorized document.
            return [
                ("id", "inselect", (f"""
                    WITH helper as (
                        {project_select}
                    )
                    SELECT document.id
                    FROM documents_document document
                    LEFT JOIN project_project project ON project.id=document.res_id AND document.res_model = 'project.project'
                    LEFT JOIN project_task task ON task.id=document.res_id AND document.res_model = 'project.task'
                    WHERE COALESCE(task.project_id, project.id) IN (SELECT id FROM helper)
                """, project_where_params))
            ]
        else:
            raise ValidationError(_("Invalid project search"))

    @api.depends('res_id', 'res_model')
    def _compute_task_id(self):
        for record in self:
            record.task_id = record.res_model == 'project.task' and self.env['project.task'].browse(record.res_id)

    @api.model
    def _search_task_id(self, operator, value):
        if operator in ('=', '!=') and isinstance(value, bool):
            if not value:
                operator = operator == "=" and "!=" or "="
            return [
                ("res_model", operator, "project.task"),
            ]
        elif operator in ('=', '!=', "in", "not in") and (isinstance(value, int) or isinstance(value, list)):
            return [
                "&", ("res_model", "=", "project.task"), ("res_id", operator, value),
            ]
        elif operator in ("ilike", "not ilike", "=", "!=") and isinstance(value, str):
            query_task = self.env["project.task"]._search([(self.env["project.task"]._rec_name, operator, value)])
            document_task_alias = query_task.make_alias('project_task', 'document')
            query_task.add_join("JOIN", document_task_alias, 'documents_document', SQL(
                "%s = %s AND %s = %s",
                SQL.identifier('project_task', 'id'),
                SQL.identifier(document_task_alias, 'res_id'),
                SQL.identifier(document_task_alias, 'res_model'),
                'project.task',
            ))
            return [
                ("id", "inselect", query_task.select(f"{document_task_alias}.id")),
            ]
        else:
            raise ValidationError(_("Invalid task search"))

    @api.model
    def search_panel_select_range(self, field_name, **kwargs):
        if field_name != 'folder_id' or not self._context.get('limit_folders_to_project'):
            return super().search_panel_select_range(field_name, **kwargs)

        res_model = self._context.get('active_model')
        if res_model not in ('project.project', 'project.task'):
            return super().search_panel_select_range(field_name, **kwargs)

        res_id = self._context.get('active_id')
        fields = ['display_name', 'description', 'parent_folder_id', 'has_write_access']

        active_record = self.env[res_model].browse(res_id)
        if not active_record.exists():
            return super().search_panel_select_range(field_name, **kwargs)
        project = active_record if res_model == 'project.project' else active_record.sudo().project_id

        document_read_group = self.env['documents.document']._read_group(kwargs.get('search_domain', []), [], ['folder_id:array_agg'])
        folder_ids = document_read_group[0][0]
        records = self.env['documents.folder'].with_context(hierarchical_naming=False).search_read([
            '|',
                ('id', 'child_of', project.documents_folder_id.id),
                ('id', 'in', folder_ids),
        ], fields)
        available_folder_ids = set(record['id'] for record in records)

        values_range = OrderedDict()
        for record in records:
            record_id = record['id']
            if record['parent_folder_id'] and record['parent_folder_id'][0] not in available_folder_ids:
                record['parent_folder_id'] = False
            value = record['parent_folder_id']
            record['parent_folder_id'] = value and value[0]
            values_range[record_id] = record

        return {
            'parent_field': 'parent_folder_id',
            'values': list(values_range.values()),
        }
