# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, Command
from odoo.fields import Domain
from odoo.http import request, route
from odoo.tools import SQL
from odoo.tools.image import image_data_uri

from odoo.addons.mail_plugin.controllers import mail_plugin

_logger = logging.getLogger(__name__)


class MailPluginController(mail_plugin.MailPluginController):

    def _get_record_redirect_url(self, model, record_id):
        if model == 'project.task':
            return f'/odoo/all-tasks/{int(record_id)}'

        return super()._get_record_redirect_url(model, record_id)

    @route()
    def search_records(self, model, query, limit=30):
        """An empty search on project should return them all."""
        values, count = super().search_records(model, query, limit)
        if not query and model == 'project.project':
            # search all projects
            return self._search_and_format_projects([], limit=limit)
        return values, count

    def _search_records(self, model, terms, limit=30):
        if model == "project.project":
            return self._search_and_format_projects(terms, limit=limit)

        if model == "project.task":
            domain = Domain.OR([('name', 'ilike', term)] for term in terms)
            return self._search_and_format_tasks(domain, limit=limit)

        return super()._search_records(model, terms, limit)

    def _search_and_format_projects(self, queries, limit=30):
        group_project_stages = request.env.user.has_group('project.group_project_stages')

        # get the projects where the user is responsible first
        project_domain = (
            Domain.OR([('name', 'ilike', query)] for query in queries)
            if queries else Domain([])
        )

        project_domain &= Domain('is_template', '=', False)
        if group_project_stages:
            project_domain &= Domain('stage_id', '=', False) | Domain('stage_id.fold', '=', False)

        request.env.cr.execute(SQL(
            """
            SELECT project.id,
                   project.user_id = %(user_id)s AS is_current_user
              FROM project_project project
         LEFT JOIN project_favorite_user_rel AS is_favorite
                ON is_favorite.project_id = project.id
               AND is_favorite.user_id = %(user_id)s
             WHERE id IN (%(query)s)
             ORDER BY (is_favorite IS NOT NULL) DESC, is_current_user DESC
             LIMIT %(limit)s
            """,
            user_id=request.env.user.id,
            # search with access rules, active domain, etc
            query=request.env['project.project']._search(project_domain).select('id'),
            limit=limit,
        ))

        projects = request.env['project.project'].sudo().browse([
            v['id'] for v in request.env.cr.dictfetchall()
        ])
        project_count = request.env['project.project'].search_count(project_domain)

        return [
            {
                'id': project.id,
                'name': project.name,
                'partner_name': project.partner_id.name,
                'company_name': project.company_id.name,
                'stage_name': group_project_stages and project.stage_id.name,
                'company_id': project.company_id.id,
            }
            for project in projects
        ], project_count

    def _search_and_format_tasks(self, domain, limit=30):
        task_count = request.env['project.task'].search_count(domain)
        partner_tasks = request.env['project.task'].search(
            domain,
            limit=limit,
            # state start with number to be able to sort based on their value
            order='state DESC',
        )
        accessible_projects = partner_tasks.project_id._filtered_access('read').ids

        return [
            self._format_task(task)
            for task in partner_tasks
            if task.project_id.id in accessible_projects
        ], task_count

    def _get_contact_data(self, partner, email):
        """
        Overrides the base module's get_contact_data method by Adding the "tasks" key within the initial contact
        information dict loaded when opening an email on Outlook.
        This is structured this way to enable the "project" feature on the Outlook side only if the Odoo version
        supports it.

        Return the tasks key only if the current user can create tasks. So, if they can not
        create tasks, the section won't be visible on the addin side (like if the project
        module was not installed on the database).
        """
        contact_values = super()._get_contact_data(partner, email)

        if not request.env['project.task'].has_access('create'):
            return contact_values

        if not partner:
            contact_values['tasks'] = []
            contact_values['task_count'] = 0
        else:
            contact_values['tasks'], contact_values['task_count'] = self._search_and_format_tasks([
                ('state', 'not in', ('1_done', '1_canceled')),
                ('partner_id', '=', partner.id),
            ])

        contact_values['can_create_project'] = request.env['project.project'].has_access('create')
        return contact_values

    def _mail_models_access_whitelist(self, access):
        models_whitelist = super()._mail_models_access_whitelist(access)
        if request.env['project.project'].has_access(access):
            models_whitelist.append('project.project')
        if request.env['project.task'].has_access(access):
            models_whitelist.append('project.task')
        return models_whitelist

    def _translation_modules_whitelist(self):
        modules_whitelist = super()._translation_modules_whitelist()
        if not request.env['project.task'].has_access('create'):
            return modules_whitelist
        return modules_whitelist + ['project_mail_plugin']

    @route('/mail_plugin/task/create', type='jsonrpc', auth='outlook', cors="*")
    def task_create(
        self, email_subject, email_body, project_id, partner_id,
        partner_name, partner_email, attachments=None):
        if not request.env['project.project'].browse(project_id).exists():
            return {'error': 'project_not_found'}

        if partner_id:
            partner = request.env['res.partner'].browse(partner_id).exists()
            if not partner:
                return {'error': 'partner_not_found'}
        else:
            partner = self._search_or_create_partner(partner_email, partner_name)

        if not email_subject:
            email_subject = _('Task for %s', partner.name)

        task = request.env['project.task'].with_company(partner.company_id).create({
            'name': email_subject,
            'partner_id': partner.id,
            'description': email_body,
            'project_id': project_id,
            'user_ids': [Command.link(request.env.uid)],
        })

        if attachments:
            request.env["ir.attachment"].create([{
                "name": name,
                "datas": content,
                "res_model": task._name,
                "res_id": task.id,
            } for name, content in attachments])

        values = self._format_task(task)
        values['partner_id'] = task.partner_id.id
        values['partner_image'] = image_data_uri(partner.avatar_128)
        return values

    def _format_task(self, task):
        return {
            'id': task.id,
            'name': task.name,
            'project_name': task.project_id.name,
            'partner_id': task.partner_id.id,
        }

    @route('/mail_plugin/project/create', type='jsonrpc', auth='outlook', cors="*")
    def project_create(self, name):
        record = request.env['project.project'].create({'name': name})
        return {"id": record.id, "name": record.name}
