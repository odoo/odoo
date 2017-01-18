# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import http, _
from odoo.http import request

from odoo.addons.website_portal.controllers.main import website_account, get_records_pager


class WebsiteAccount(website_account):

    @http.route()
    def account(self, **kw):
        response = super(WebsiteAccount, self).account(**kw)
        response.qcontext.update({
            'project_count': request.env['project.project'].search_count([('privacy_visibility', '=', 'portal')]),
            'task_count': request.env['project.task'].search_count([('project_id.privacy_visibility', '=', 'portal')])
        })
        return response

    @http.route(['/my/projects', '/my/projects/page/<int:page>'], type='http', auth="user", website=True)
    def my_projects(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        Project = request.env['project.project']
        domain = [('privacy_visibility', '=', 'portal')]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups('project.project', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        # projects count
        project_count = Project.search_count(domain)
        # pager
        pager = request.website.pager(
            url="/my/projects",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=project_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        projects = Project.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_projects_history'] = projects.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'projects': projects,
            'page_name': 'project',
            'archive_groups': archive_groups,
            'default_url': '/my/projects',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby
        })
        return request.render("website_project.my_projects", values)

    @http.route(['/my/project/<model("project.project"):project>'], type='http', auth="user", website=True)
    def my_project(self, project=None, **kw):
        vals = {'project': project, }
        history = request.session.get('my_projects_history', [])
        vals.update(get_records_pager(history, project))
        return request.render("website_project.my_project", vals)

    @http.route(['/my/tasks', '/my/tasks/page/<int:page>'], type='http', auth="user", website=True)
    def my_tasks(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        domain = [('project_id.privacy_visibility', '=', 'portal')]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'stage_id'},
            'update': {'label': _('Last Stage Update'), 'order': 'date_last_stage_update desc'},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
        }
        # extends filterby criteria with project (criteria name is the project id)
        projects = request.env['project.project'].search([('privacy_visibility', '=', 'portal')])
        for proj in projects:
            searchbar_filters.update({
                str(proj.id): {'label': proj.name, 'domain': [('project_id', '=', proj.id)]}
            })

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups('project.task', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # task count
        task_count = request.env['project.task'].search_count(domain)
        # pager
        pager = request.website.pager(
            url="/my/tasks",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=task_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        tasks = request.env['project.task'].search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_tasks_history'] = tasks.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'projects': projects,
            'tasks': tasks,
            'page_name': 'task',
            'archive_groups': archive_groups,
            'default_url': '/my/tasks',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        return request.render("website_project.my_tasks", values)

    @http.route(['/my/task/<model("project.task"):task>'], type='http', auth="user", website=True)
    def my_task(self, task=None, **kw):
        vals = {'task': task, 'user': request.env.user}
        history = request.session.get('my_tasks_history', [])
        vals.update(get_records_pager(history, task))
        return request.render("website_project.my_task", vals)
