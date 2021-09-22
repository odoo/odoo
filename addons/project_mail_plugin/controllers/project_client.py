
from odoo import Command, http, _
from odoo.http import request


class ProjectClient(http.Controller):
    @http.route('/mail_plugin/project/search', type='json', auth='outlook', cors="*")
    def projects_search(self, search_term, limit=5):
        """
        Used in the plugin side when searching for projects.
        Fetches projects that have names containing the search_term.
        """
        projects = request.env['project.project'].search([('name', 'ilike', search_term)], limit=limit)

        return [
            {
                'project_id': project.id,
                'name': project.name,
                'partner_name': project.partner_id.name,
                'company_id': project.company_id.id
            }
            for project in projects.sudo()
        ]

    @http.route('/mail_plugin/task/create', type='json', auth='outlook', cors="*")
    def task_create(self, email_subject, email_body, project_id, partner_id):
        partner = request.env['res.partner'].browse(partner_id).exists()
        if not partner:
            return {'error': 'partner_not_found'}

        if not request.env['project.project'].browse(project_id).exists():
            return {'error': 'project_not_found'}

        if not email_subject:
            email_subject = _('Task for %s', partner.name)

        record = request.env['project.task'].create({
            'name': email_subject,
            'partner_id': partner_id,
            'description': email_body,
            'project_id': project_id,
            'user_ids': [Command.link(request.env.uid)],
        })

        return {'task_id': record.id, 'name': record.name}

    @http.route('/mail_plugin/project/create', type='json', auth='outlook', cors="*")
    def project_create(self, name):
        record = request.env['project.project'].create({'name': name})
        return {"project_id": record.id, "name": record.name}
