# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup, escape

from odoo import Command, fields, models, _
from odoo import api
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import SQL


class Document(models.Model):
    _inherit = 'documents.document'

    project_id = fields.Many2one('project.project', compute='_compute_project_id', search='_search_project_id', export_string_translation=False)
    task_id = fields.Many2one('project.task', compute='_compute_task_id', search='_search_task_id', export_string_translation=False)

    # for folders
    project_ids = fields.One2many('project.project', 'documents_folder_id', string="Projects")

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
            # We may need to flush `res_model` `res_id` if we ever get a flow that assigns + search at the same time..
            # We only apply security rules to projects as security rules on documents will be applied prior
            # to this leaf. Not applying security rules on tasks might give more result than expected but it would not allow
            # access to an unauthorized document.
            return [
                ("id", "in", SQL("""(
                    WITH helper as (
                        %s
                    )
                    SELECT document.id
                    FROM documents_document document
                    LEFT JOIN project_project project ON project.id=document.res_id AND document.res_model = 'project.project'
                    LEFT JOIN project_task task ON task.id=document.res_id AND document.res_model = 'project.task'
                    WHERE COALESCE(task.project_id, project.id) IN (SELECT id FROM helper)
                )""", query_project.subselect()))
            ]
        else:
            raise ValidationError(_("Invalid project search"))

    def _prepare_create_values(self, vals_list):
        vals_list = super()._prepare_create_values(vals_list)
        folder_ids = {folder_id for v in vals_list if (folder_id := v.get('folder_id')) and not v.get('res_id')}
        folder_id_values = {
            folder_id: self.browse(folder_id)._get_link_to_project_values()
            for folder_id in folder_ids
        }
        for vals in vals_list:
            if (folder_id := vals.get('folder_id')) and vals.get('type') != 'folder' and not vals.get('res_id'):
                vals.update(folder_id_values[folder_id])
        return vals_list

    @api.depends('res_id', 'res_model')
    def _compute_task_id(self):
        for record in self:
            record.task_id = record.res_model == 'project.task' and self.env['project.task'].browse(record.res_id)

    def write(self, vals):
        if (project_or_task_id := vals.get('res_id')) and 'access_internal' not in vals:
            res_model = vals.get('res_model')
            if res_model is None:
                res_models = set(self.mapped('res_model'))
                if len(res_models) == 1:
                    res_model = self[0].res_model
                elif res_models & {'project.project', 'project.task'}:
                    raise UserError(_(
                        "Impossible to update write `res_id` without `access_internal` for records "
                        "with different `res_models` when some are linked to projects or tasks."))

            if res_model in {'project.project', 'project.task'}:
                project_or_task = self.env[res_model].browse(project_or_task_id)
                project = project_or_task if res_model == 'project.project' else project_or_task.project_id
                vals['access_internal'] = 'none' if project.privacy_visibility == 'followers' else 'edit'
        project_folder = self.env.ref('documents_project.document_project_folder')
        if not vals.get('active', True) and self._project_folder_in_self_or_ancestors(project_folder):
            raise UserError(_('The "%s" workspace is required by the Project application and cannot be archived.', project_folder.name))
        return super().write(vals)

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
            query_task = self.env['project.task']._search([(self.env["project.task"]._rec_name, operator, value)])
            document_task_alias = query_task.make_alias('project_task', 'document')
            query_task.add_join("JOIN", document_task_alias, 'documents_document', SQL(
                "%s = %s AND %s = %s",
                SQL.identifier('project_task', 'id'),
                self._field_to_sql(document_task_alias, 'res_id'),
                self._field_to_sql(document_task_alias, 'res_model'),
                'project.task',
            ))
            return [
                ("id", "in", query_task.subselect(f"{document_task_alias}.id")),
            ]
        else:
            raise ValidationError(_("Invalid task search"))

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if (template_folder_id := self.env.context.get('project_documents_template_folder')) \
                and [('type', '=', 'folder')] in domain:
            domain = expression.AND([
                domain,
                ['!', ('id', 'child_of', template_folder_id)],
            ])
        return domain

    def _project_folder_in_self_or_ancestors(self, project_folder):
        project_folder_ancestors = {int(ancestor_id) for ancestor_id in project_folder.sudo().parent_path.split('/')[:-1]}
        return project_folder_ancestors & set(self.ids)

    @api.ondelete(at_uninstall=False)
    def unlink_except_project_folder(self):
        project_folder = self.env.ref('documents_project.document_project_folder')
        if self._project_folder_in_self_or_ancestors(project_folder):
            raise UserError(_('The "%s" workspace is required by the Project application and cannot be deleted.', project_folder.name))
        projects_with_folder = self.env['project.project'].search([('use_documents', '=', True), ('documents_folder_id', 'child_of', self.ids)])
        if projects_with_folder:
            raise UserError(_(
                "This action can't be performed, as it would remove the workspaces used by the following projects:\n%(projects)s\nTo continue, choose different workspaces or turn off the Documents feature for these projects.",
                projects="\n".join(f"- {project.name}" for project in projects_with_folder),
            ))

    @api.constrains('company_id')
    def _check_no_company_on_projects_folder(self):
        if not self.company_id:
            return
        projects_folder = self.env.ref('documents_project.document_project_folder')
        if projects_folder in self:
            raise UserError(_("You cannot set a company on the %s folder.", projects_folder.name))

    @api.constrains('company_id')
    def _check_company_is_projects_company(self):
        for folder in self.filtered(lambda d: d.type == 'folder'):
            if folder.project_ids and folder.project_ids.company_id:
                different_company_projects = folder.project_ids.filtered(lambda project: project.company_id != self.company_id)
                if not different_company_projects:
                    continue
                if len(different_company_projects) == 1:
                    project = different_company_projects[0]
                    message = _('This folder should remain in the same company as the "%(project)s" project to which it is linked. Please update the company of the "%(project)s" project, or leave the company of this workspace empty.', project=project.name)
                else:
                    lines = [f"- {project.name}" for project in different_company_projects]
                    message = _('This folder should remain in the same company as the following projects to which it is linked:\n%s\n\nPlease update the company of those projects, or leave the company of this workspace empty.', '\n'.join(lines))
                raise UserError(message)

    def action_move_documents(self, folder_id):
        res = super().action_move_documents(folder_id)
        if not self.folder_id:
            return res
        if unlinked_documents := self.filtered(
            lambda d: d.res_model in ['documents.document', False] and d.res_id in [False, d.id]
        ):
            values = self.folder_id._get_link_to_project_values()
            unlinked_documents.write(values)
        return res

    def action_create_project_task(self):
        if not self.ids:
            return
        if any(document.type == 'folder' for document in self):
            raise UserError(_('You cannot create a task from a folder.'))
        deprecated_tag = self.env.ref('documents.documents_tag_deprecated', raise_if_not_found=False)
        if deprecated_tag and deprecated_tag in self.tag_ids:
            raise (_("Impossible to create a task on a deprecated document"))

        if self.res_model == 'project.task':
            raise UserError(_("Documents already linked to a task."))
        project = self._get_project_from_closest_ancestor() if len(self.folder_id) == 1 else self.env['project.project']
        new_obj = self.env['project.task'].create({
            'name': " / ".join(self.mapped('name')) or _("New task from Documents"),
            'user_ids': [Command.set(self.env.user.ids)],
            'partner_id': self.partner_id.id if len(self.partner_id) == 1 else False,
            'project_id': project.id,
        })
        task_action = {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'res_id': new_obj.id,
            'name': _("new %(model)s from %(new_record)s", model='project.task', new_record=new_obj.name),
            'view_mode': 'form',
            'views': [(False, "form")],
            'context': self._context,
        }
        if len(self) == 1:
            document_msg = _('Task created from document %s', self._get_html_link())
        else:
            document_msg = escape(_('Task created from documents'))
            document_msg += Markup("<ul>%s</ul>") % Markup().join(Markup("<li>%s</li>") % document._get_html_link()
                                                                  for document in self)
        for document in self:
            this_document = document
            if (document.res_model or document.res_id) and document.res_model != 'documents.document' \
                    and not (project and document.res_model == 'project.project' and document.res_id == project.id):
                this_document = document.copy()
                attachment_id_copy = document.attachment_id.with_context(no_document=True).copy()
                this_document.write({'attachment_id': attachment_id_copy.id})

            # the 'no_document' key in the context indicates that this ir_attachment has already a
            # documents.document and a new document shouldn't be automatically generated.
            this_document.attachment_id.with_context(no_document=True).write({
                'res_model': 'project.task',
                'res_id': new_obj.id
            })
        new_obj.message_post(body=document_msg)
        return task_action

    def _get_link_to_project_values(self):
        self.ensure_one()
        values = {}
        if project := self._get_project_from_closest_ancestor():
            if self.type == 'folder' and not self.shortcut_document_id:
                values.update({
                    'res_model': 'project.project',
                    'res_id': project.id,
                })
                project = project.sudo()
                if project.partner_id and not self.partner_id.id:
                    values['partner_id'] = project.partner_id.id
        return values

    def _get_project_from_closest_ancestor(self):
        """
        If the current folder is linked to exactly one project, this method returns
        that project.

        If the current folder doesn't match the criteria, but one of its ancestors
        does, this method will return the project linked to the closest ancestor
        matching the criteria.

        :return: The project linked to the closest valid ancestor, or an empty
        recordset if no project is found.
        """
        self.ensure_one()
        eligible_projects = self.env['project.project'].sudo()._read_group(
            [('documents_folder_id', 'parent_of', self.id)],
            ['documents_folder_id'],
            having=[('__count', '=', 1)],
        )
        if not eligible_projects:
            return self.env['project.project']

        # dict {folder_id: position}, where position is a value used to sort projects by their folder_id
        folder_id_order = {int(folder_id): i for i, folder_id in enumerate(reversed(self.parent_path[:-1].split('/')))}
        eligible_projects.sort(key=lambda project_group: folder_id_order[project_group[0].id])
        return self.env['project.project'].sudo().search(
            [('documents_folder_id', '=', eligible_projects[0][0].id)], limit=1).sudo(False)
