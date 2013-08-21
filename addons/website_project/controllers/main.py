# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.addons.web import http
from openerp.addons.web.http import request


class website(osv.osv):
    _inherit = "website"
    def get_rendering_context(self, additional_values=None):
        project_obj = request.registry['project.project']
        project_ids = project_obj.search(request.cr, request.uid, [('privacy_visibility', "=", "public")])
        values = {
            'project_ids': project_obj.browse(request.cr, request.uid, project_ids),
        }
        if additional_values:
            values.update(additional_values)
        return super(website, self).get_rendering_context(values)


class website_project(http.Controller):

    @http.route(['/project/<int:project_id>/'], type='http', auth="public")
    def blog(self, project_id=None, **post):
        website = request.registry['website']
        project_obj = request.registry['project.project']
        task_obj = request.registry['project.task']
        stage_obj = request.registry['project.task.type']

        project = project_obj.browse(request.cr, request.uid, project_id)

        domain = [('id', 'in', [task.id for task in project.tasks])]
        stages = task_obj.read_group(request.cr, request.uid, domain, ["id", "stage_id"], groupby="stage_id")
        for stage in stages:
            stage['stage_id'] = stage_obj.browse(request.cr, request.uid, stage['stage_id'][0])
            task_ids = task_obj.search(request.cr, request.uid, stage['__domain'])
            stage['task_ids'] = task_obj.browse(request.cr, request.uid, task_ids)

        values = website.get_rendering_context({
            'project_id': project,
            'stages': stages,
        })
        return website.render("website_project.index", values)
