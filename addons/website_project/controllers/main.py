# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import http, _
from odoo.http import request

from odoo.addons.website_portal.controllers.main import website_account


class WebsiteAccount(website_account):

    def _prepare_portal_layout_values(self):
        values = super(WebsiteAccount, self)._prepare_portal_layout_values()
        project_count = request.env['project.project'].search_count([('privacy_visibility','=','portal')])
        task_count = request.env['project.task'].search_count([('project_id.privacy_visibility','=','portal')])
        values.update({
            'project_count': project_count,
            'task_count': task_count,
        })
        return values

    @http.route(['/my/projects', '/my/projects/page/<int:page>'], type='http', auth="user", website=True)
    def my_projects(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        Project = request.env['project.project']

        sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }

        domain = [('privacy_visibility','=','portal')]
        order = sortings.get(sortby, sortings['date'])['order']

        # archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups('project.project', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        # pager
        pager = request.website.pager(
            url="/my/projects",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=values['project_count'],
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        projects = Project.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'sortings': sortings,
            'sortby': sortby,
            'projects': projects,
            'page_name': 'project',
            'archive_groups': archive_groups,
            'default_url': '/my/projects',
            'pager': pager
        })
        return request.render("website_project.my_projects", values)

    @http.route(['/my/project/<model("project.project"):project>'], type='http', auth="user", website=True)
    def my_project(self, project=None, **kw):
        return request.render("website_project.my_project", {'project': project})

    @http.route(['/my/tasks', '/my/tasks/page/<int:page>'], type='http', auth="user", website=True)
    def my_tasks(self, page=1, date_begin=None, date_end=None, project=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()

        sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'stage_id'},
            'update': {'label': _('Last Stage Update'), 'order': 'date_last_stage_update desc'},
        }

        projects = request.env['project.project'].search([('privacy_visibility', '=', 'portal')])

        project_filters = {
            'all': {'label': _('All'), 'domain': []},
        }

        for proj in projects:
            project_filters.update({
                str(proj.id): {'label': proj.name, 'domain': [('project_id', '=', proj.id)]}
            })

        domain = [('project_id.privacy_visibility', '=', 'portal')]
        domain += project_filters.get(project, project_filters['all'])['domain']
        order = sortings.get(sortby, sortings['date'])['order']

        # archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups('project.task', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # pager
        count = request.env['project.task'].search_count(domain)
        pager = request.website.pager(
            url="/my/tasks",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'project': project},
            total=count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        tasks = request.env['project.task'].search(domain, order=order, limit=self._items_per_page, offset=(page - 1) * self._items_per_page)

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'project_filters': OrderedDict(sorted(project_filters.items())),
            'projects': projects,
            'project': project,
            'sortings': sortings,
            'sortby': sortby,
            'tasks': tasks,
            'page_name': 'task',
            'archive_groups': archive_groups,
            'default_url': '/my/tasks',
            'pager': pager
        })
        return request.render("website_project.my_tasks", values)

    @http.route(['/my/task/<model("project.task"):task>'], type='http', auth="user", website=True)
    def my_task(self, task=None, **kw):
        return request.render("website_project.my_task", {'task': task, 'user': request.env.user})
