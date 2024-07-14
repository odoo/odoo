# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.project.controllers.portal import ProjectCustomerPortal


class DocumentsProjectCustomerPortal(ProjectCustomerPortal):
    def _display_project_groupby(self, project):
        return super()._display_project_groupby(project) or project.use_documents and project.sudo().shared_document_count

    def _project_get_page_view_values(self, project, access_token, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='content', groupby=None, **kwargs):
        if not groupby and project.use_documents and project.sudo().shared_document_count:
            groupby = 'project'
        return super()._project_get_page_view_values(project, access_token, page=page, date_begin=date_begin, date_end=date_end, sortby=sortby, search=search, search_in=search_in, groupby=groupby, **kwargs)
