from odoo import _, http
from odoo.addons.mail_plugin.controllers import mail_plugin
from odoo.http import request


class MailPluginController(mail_plugin.MailPluginController):

    @http.route('/mail/plugin/tasks/refresh', type='json', auth='outlook', cors='*')
    def refresh_tasks(self, partner, **kwargs):
        partner = request.env['res.partner'].browse(partner['id'])
        partner_tasks = request.env['project.task'].search([('partner_id', '=', partner.id)], offset=0, limit=5)
        accessible_projects = partner_tasks.project_id._filtered_access('read').ids

        tasks_values = []
        for task in partner_tasks:
            if task.project_id.id in accessible_projects:
                record = {
                    'task_id': task.id,
                    'name': task.name,
                    'project_name': task.project_id.name,
                }
                tasks_values.append(record)

        return tasks_values

    @http.route('/mail/plugin/tasks/search', type='json', auth='outlook', cors='*')
    def get_tasks(self, query='', partner=None, **kwargs):
        if not partner:
            return {'error': _('Partner ID is required.')}

        partner = request.env['res.partner'].browse(partner['id']).exists()
        if not partner:
            return {'error': _('The Partner does not exist.')}
        if not query.strip():
            return {'error': _('Search query cannot be empty.')}

        partner_tasks = request.env['project.task'].search([
            '|', '|',
            ('name', 'ilike', query),
            ('partner_id.name', 'ilike', query),
            ('project_id.name', 'ilike', query)
        ], order='create_date')

        tasks = []
        for task in partner_tasks:
            record = {
                'task_id': task.id,
                'name': task.name,
                'project_name': task.project_id.name,
                'company_id': task.company_id,
            }
            tasks.append(record)

        return tasks
