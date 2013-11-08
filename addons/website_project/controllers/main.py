# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website
from openerp.osv import osv


class Website(osv.Model):
    _inherit = "website"

    def preprocess_request(self, cr, uid, ids, request, context=None):
        project_obj = request.registry['project.project']
        project_ids = project_obj.search(cr, uid, [('privacy_visibility', "=", "public")], context=request.context)

        request.context['website_project_ids'] = project_obj.browse(cr, uid, project_ids, request.context)

        return super(Website, self).preprocess_request(cr, uid, ids, request, context)


class website_project(http.Controller):

    @website.route(['/project/<int:project_id>/'], type='http', auth="public", multilang=True)
    def project(self, project_id=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        project_obj = request.registry['project.project']

        project = project_obj.browse(request.cr, request.uid, project_id, request.context)

        render_values = {
            'project': project,
            'main_object': project,
        }
        return request.website.render("website_project.index", render_values)

    @website.route(['/project/task/<int:task_id>'], type='http', auth="public", multilang=True)
    def task(self, task_id=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        task_obj = request.registry['project.task']

        task = task_obj.browse(cr, uid, task_id, context=context)

        render_values = {
            'task': task,
            'main_object': task,
        }
        return request.website.render("website_project.task", render_values)
