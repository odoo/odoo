# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.http import request

from odoo.addons.project.controllers.portal import ProjectCustomerPortal


class DocumentsProjectCustomerPortal(ProjectCustomerPortal):

    def _project_get_page_view_values(self, project, access_token, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='content', groupby=None, **kwargs):
        if not groupby and project.use_documents and project.sudo().document_count:
            groupby = 'project'
        return super()._project_get_page_view_values(project, access_token, page=page, date_begin=date_begin, date_end=date_end, sortby=sortby, search=search, search_in=search_in, groupby=groupby, **kwargs)

    def _task_get_page_view_values(self, task, access_token, **kwargs):
        values = super()._task_get_page_view_values(task, access_token, **kwargs)
        if request.env['documents.document'].has_access('read') and task.project_use_documents:
            is_shared_document = request.env['documents.document'].search_count([
                ('res_model', '=', 'project.task'),
                ('res_id', '=', task.id),
            ], limit=1)
            if is_shared_document:
                project_id = values.get('project_id')
                url = "/my/tasks/%s/documents" % (task.id)
                if project_id:
                    url = "/my/projects/%s/task/%s/documents" % (project_id, task.id)
                values['task_link_section'].append({
                    'access_url': url,
                    'title': _('Documents'),
                    'target': '_blank'
                })

        return values
