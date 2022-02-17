# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict
from operator import itemgetter
from markupsafe import Markup

from odoo import conf, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.tools import groupby as groupbyelem

from odoo.osv.expression import OR, AND

from odoo.addons.web.controllers.main import HomeStaticTemplateHelpers


class ProjectCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'project_count' in counters:
            values['project_count'] = request.env['project.project'].search_count([])
        if 'task_count' in counters:
            values['task_count'] = request.env['project.task'].search_count([])
        return values

    # ------------------------------------------------------------
    # My Project
    # ------------------------------------------------------------
    def _project_get_page_view_values(self, project, access_token, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='content', groupby=None, **kwargs):
        # TODO: refactor this because most of this code is duplicated from portal_my_tasks method
        values = self._prepare_portal_layout_values()
        searchbar_sortings = self._task_get_searchbar_sortings()

        searchbar_inputs = self._task_get_searchbar_inputs()
        searchbar_groupby = self._task_get_searchbar_groupby()

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # default filter by value
        domain = [('project_id', '=', project.id)]

        # default group by value
        if not groupby:
            groupby = 'project'

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # search
        if search and search_in:
            domain += self._task_get_search_domain(search_in, search)

        Task = request.env['project.task']
        if access_token:
            Task = Task.sudo()
        elif not request.env.user._is_public():
            domain = AND([domain, request.env['ir.rule']._compute_domain(Task._name, 'read')])
            Task = Task.sudo()

        # task count
        task_count = Task.search_count(domain)
        # pager
        url = "/my/project/%s" % project.id
        pager = portal_pager(
            url=url,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'groupby': groupby, 'search_in': search_in, 'search': search},
            total=task_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        order = self._task_get_order(order, groupby)

        tasks = Task.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_project_tasks_history'] = tasks.ids[:100]

        groupby_mapping = self._task_get_groupby_mapping()
        group = groupby_mapping.get(groupby)
        if group:
            grouped_tasks = [Task.concat(*g) for k, g in groupbyelem(tasks, itemgetter(group))]
        else:
            grouped_tasks = [tasks]

        values.update(
            date=date_begin,
            date_end=date_end,
            grouped_tasks=grouped_tasks,
            page_name='project',
            default_url=url,
            pager=pager,
            searchbar_sortings=searchbar_sortings,
            searchbar_groupby=searchbar_groupby,
            searchbar_inputs=searchbar_inputs,
            search_in=search_in,
            search=search,
            sortby=sortby,
            groupby=groupby,
            project=project,
        )
        return self._get_page_view_values(project, access_token, values, 'my_projects_history', False, **kwargs)

    @http.route(['/my/projects', '/my/projects/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_projects(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        Project = request.env['project.project']
        domain = []

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # projects count
        project_count = Project.search_count(domain)
        # pager
        pager = portal_pager(
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
            'default_url': '/my/projects',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby
        })
        return request.render("project.portal_my_projects", values)

    @http.route(['/my/project/<int:project_id>'], type='http', auth="public", website=True)
    def portal_my_project(self, project_id=None, access_token=None, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='content', groupby=None, **kw):
        try:
            project_sudo = self._document_check_access('project.project', project_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        if project_sudo.with_user(request.env.user)._check_project_sharing_access():
            return request.render("project.project_sharing_portal", {'project_id': project_id})
        project_sudo = project_sudo if access_token else project_sudo.with_user(request.env.user)
        values = self._project_get_page_view_values(project_sudo, access_token, page, date_begin, date_end, sortby, search, search_in, groupby, **kw)
        values['task_url'] = 'project/%s/task' % project_id
        return request.render("project.portal_my_project", values)

    def _prepare_project_sharing_session_info(self, project):
        session_info = request.env['ir.http'].session_info()
        user_context = request.session.get_context() if request.session.uid else {}
        mods = conf.server_wide_modules or []
        qweb_checksum = HomeStaticTemplateHelpers.get_qweb_templates_checksum(debug=request.session.debug, bundle="project.assets_qweb")
        lang = user_context.get("lang")
        translation_hash = request.env['ir.translation'].get_web_translations_hash(mods, lang)
        cache_hashes = {
            "qweb": qweb_checksum,
            "translations": translation_hash,
        }

        project_company = project.company_id
        session_info.update(
            cache_hashes=cache_hashes,
            action_name='project.project_sharing_project_task_action',
            project_id=project.id,
            user_companies={
                'current_company': project_company.id,
                'allowed_companies': {
                    project_company.id: {
                        'id': project_company.id,
                        'name': project_company.name,
                    },
                },
            },
            # FIXME: See if we prefer to give only the currency that the portal user just need to see the correct information in project sharing
            currencies=request.env['ir.http'].get_currencies(),
        )
        return session_info

    @http.route("/my/project/<int:project_id>/project_sharing", type="http", auth="user", methods=['GET'])
    def render_project_backend_view(self, project_id):
        project = request.env['project.project'].sudo().browse(project_id)
        if not project.exists() or not project.with_user(request.env.user)._check_project_sharing_access():
            return request.not_found()

        return request.render(
            'project.project_sharing_embed',
            {'session_info': self._prepare_project_sharing_session_info(project)},
        )

    @http.route('/my/project/<int:project_id>/task/<int:task_id>', type='http', auth='public', website=True)
    def portal_my_project_task(self, project_id=None, task_id=None, access_token=None, **kw):
        try:
            project_sudo = self._document_check_access('project.project', project_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        Task = request.env['project.task']
        if access_token:
            Task = Task.sudo()
        task_sudo = Task.search([('project_id', '=', project_id), ('id', '=', task_id)], limit=1).sudo()
        task_sudo.attachment_ids.generate_access_token()
        values = self._task_get_page_view_values(task_sudo, access_token, project=project_sudo, **kw)
        values['project'] = project_sudo
        return request.render("project.portal_my_task", values)

    # ------------------------------------------------------------
    # My Task
    # ------------------------------------------------------------
    def _task_get_page_view_values(self, task, access_token, **kwargs):
        project = kwargs.get('project')
        if project:
            project_accessible = True
            page_name = 'project_task'
            history = 'my_project_tasks_history'
        else:
            page_name = 'task'
            history = 'my_tasks_history'
            try:
                project_accessible = bool(task.project_id.id and self._document_check_access('project.project', task.project_id.id))
            except (AccessError, MissingError):
                project_accessible = False
        values = {
            'page_name': page_name,
            'task': task,
            'user': request.env.user,
            'project_accessible': project_accessible,
        }
        return self._get_page_view_values(task, access_token, values, history, False, **kwargs)

    def _task_get_searchbar_sortings(self):
        return {
            'date': {'label': _('Newest'), 'order': 'create_date desc', 'sequence': 1},
            'name': {'label': _('Title'), 'order': 'name', 'sequence': 2},
            'project': {'label': _('Project'), 'order': 'project_id, stage_id', 'sequence': 3},
            'users': {'label': _('Assignees'), 'order': 'user_ids', 'sequence': 4},
            'stage': {'label': _('Stage'), 'order': 'stage_id, project_id', 'sequence': 5},
            'status': {'label': _('Status'), 'order': 'kanban_state', 'sequence': 6},
            'priority': {'label': _('Priority'), 'order': 'priority desc', 'sequence': 7},
            'date_deadline': {'label': _('Deadline'), 'order': 'date_deadline asc', 'sequence': 8},
            'update': {'label': _('Last Stage Update'), 'order': 'date_last_stage_update desc', 'sequence': 10},
        }

    def _task_get_searchbar_groupby(self):
        values = {
            'none': {'input': 'none', 'label': _('None'), 'order': 1},
            'project': {'input': 'project', 'label': _('Project'), 'order': 2},
            'stage': {'input': 'stage', 'label': _('Stage'), 'order': 4},
            'status': {'input': 'status', 'label': _('Status'), 'order': 5},
            'priority': {'input': 'priority', 'label': _('Priority'), 'order': 6},
            'customer': {'input': 'customer', 'label': _('Customer'), 'order': 9},
        }
        return dict(sorted(values.items(), key=lambda item: item[1]["order"]))

    def _task_get_groupby_mapping(self):
        return {
            'project': 'project_id',
            'stage': 'stage_id',
            'customer': 'partner_id',
            'priority': 'priority',
            'status': 'kanban_state',
        }

    def _task_get_order(self, order, groupby):
        groupby_mapping = self._task_get_groupby_mapping()
        field_name = groupby_mapping.get(groupby, '')
        if not field_name:
            return order
        return '%s, %s' % (field_name, order)

    def _task_get_searchbar_inputs(self):
        values = {
            'all': {'input': 'all', 'label': _('Search in All'), 'order': 1},
            'content': {'input': 'content', 'label': Markup(_('Search <span class="nolabel"> (in Content)</span>')), 'order': 1},
            'ref': {'input': 'ref', 'label': _('Search in Ref'), 'order': 1},
            'project': {'input': 'project', 'label': _('Search in Project'), 'order': 2},
            'users': {'input': 'users', 'label': _('Search in Assignees'), 'order': 3},
            'stage': {'input': 'stage', 'label': _('Search in Stages'), 'order': 4},
            'status': {'input': 'status', 'label': _('Search in Status'), 'order': 5},
            'priority': {'input': 'priority', 'label': _('Search in Priority'), 'order': 6},
            'message': {'input': 'message', 'label': _('Search in Messages'), 'order': 10},
        }
        return dict(sorted(values.items(), key=lambda item: item[1]["order"]))

    def _task_get_search_domain(self, search_in, search):
        search_domain = []
        if search_in in ('content', 'all'):
            search_domain.append([('name', 'ilike', search)])
            search_domain.append([('description', 'ilike', search)])
        if search_in in ('customer', 'all'):
            search_domain.append([('partner_id', 'ilike', search)])
        if search_in in ('message', 'all'):
            search_domain.append([('message_ids.body', 'ilike', search)])
        if search_in in ('stage', 'all'):
            search_domain.append([('stage_id', 'ilike', search)])
        if search_in in ('project', 'all'):
            search_domain.append([('project_id', 'ilike', search)])
        if search_in in ('ref', 'all'):
            search_domain.append([('id', 'ilike', search)])
        if search_in in ('users', 'all'):
            user_ids = request.env['res.users'].sudo().search([('name', 'ilike', search)])
            search_domain.append([('user_ids', 'in', user_ids.ids)])
        if search_in in ('priority', 'all'):
            search_domain.append([('priority', 'ilike', search == 'normal' and '0' or '1')])
        if search_in in ('status', 'all'):
            search_domain.append([
                ('kanban_state', 'ilike', 'normal' if search == 'In Progress' else 'done' if search == 'Ready' else 'blocked' if search == 'Blocked' else search)
            ])
        return OR(search_domain)

    @http.route(['/my/tasks', '/my/tasks/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_tasks(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='content', groupby=None, **kw):
        values = self._prepare_portal_layout_values()
        searchbar_sortings = self._task_get_searchbar_sortings()
        searchbar_sortings = dict(sorted(self._task_get_searchbar_sortings().items(),
                                         key=lambda item: item[1]["sequence"]))

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
        }

        searchbar_inputs = self._task_get_searchbar_inputs()
        searchbar_groupby = self._task_get_searchbar_groupby()

        # extends filterby criteria with project the customer has access to
        projects = request.env['project.project'].search([])
        for project in projects:
            searchbar_filters.update({
                str(project.id): {'label': project.name, 'domain': [('project_id', '=', project.id)]}
            })

        # extends filterby criteria with project (criteria name is the project id)
        # Note: portal users can't view projects they don't follow
        project_groups = request.env['project.task'].read_group([('project_id', 'not in', projects.ids)],
                                                                ['project_id'], ['project_id'])
        for group in project_groups:
            proj_id = group['project_id'][0] if group['project_id'] else False
            proj_name = group['project_id'][1] if group['project_id'] else _('Others')
            searchbar_filters.update({
                str(proj_id): {'label': proj_name, 'domain': [('project_id', '=', proj_id)]}
            })

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # default filter by value
        if not filterby:
            filterby = 'all'
        domain = searchbar_filters.get(filterby, searchbar_filters.get('all'))['domain']

        # default group by value
        if not groupby:
            groupby = 'project'

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # search
        if search and search_in:
            domain += self._task_get_search_domain(search_in, search)

        TaskSudo = request.env['project.task'].sudo()
        domain = AND([domain, request.env['ir.rule']._compute_domain(TaskSudo._name, 'read')])

        # task count
        task_count = TaskSudo.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/tasks",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby, 'groupby': groupby, 'search_in': search_in, 'search': search},
            total=task_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        order = self._task_get_order(order, groupby)

        tasks = TaskSudo.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_tasks_history'] = tasks.ids[:100]

        groupby_mapping = self._task_get_groupby_mapping()
        group = groupby_mapping.get(groupby)
        if group:
            grouped_tasks = [request.env['project.task'].concat(*g) for k, g in groupbyelem(tasks, itemgetter(group))]
        else:
            grouped_tasks = [tasks]

        task_states = dict(request.env['project.task']._fields['kanban_state']._description_selection(request.env))
        if sortby == 'status':
            if groupby == 'none' and grouped_tasks:
                grouped_tasks[0] = grouped_tasks[0].sorted(lambda tasks: task_states.get(tasks.kanban_state))
            else:
                grouped_tasks.sort(key=lambda tasks: task_states.get(tasks[0].kanban_state))

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'grouped_tasks': grouped_tasks,
            'page_name': 'task',
            'default_url': '/my/tasks',
            'task_url': 'task',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        return request.render("project.portal_my_tasks", values)

    @http.route(['/my/task/<int:task_id>'], type='http', auth="public", website=True)
    def portal_my_task(self, task_id, access_token=None, **kw):
        try:
            task_sudo = self._document_check_access('project.task', task_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # ensure attachment are accessible with access token inside template
        for attachment in task_sudo.attachment_ids:
            attachment.generate_access_token()
        values = self._task_get_page_view_values(task_sudo, access_token, **kw)
        return request.render("project.portal_my_task", values)
