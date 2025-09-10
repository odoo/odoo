# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from collections import OrderedDict
from operator import itemgetter
from markupsafe import Markup

from odoo import http, _
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.fields import Domain
from odoo.http import request
from odoo.tools import groupby as groupbyelem

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class ProjectCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'project_count' in counters:
            values['project_count'] = request.env['project.project'].search_count([]) \
                if request.env['project.project'].has_access('read') else 0
        if 'task_count' in counters:
            values['task_count'] = request.env['project.task'].search_count([('project_id', '!=', False)])\
                if request.env['project.task'].has_access('read') else 0
        return values

    # ------------------------------------------------------------
    # My Project
    # ------------------------------------------------------------
    def _project_get_page_view_values(self, project, access_token, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='content', groupby=None, **kwargs):
        # default filter by value
        domain = [('project_id', '=', project.id)]
        # pager
        url = "/my/projects/%s" % project.id
        values = self._prepare_tasks_values(page, date_begin, date_end, sortby, search, search_in, groupby, url, domain, su=bool(access_token) and request.env.user.has_group('base.group_public'), project=project)
        # adding the access_token to the pager's url args,
        # so we are not prompted for loging when switching pages
        # if access_token is None, the arg is not present in the URL
        values['pager']['url_args']['access_token'] = access_token
        pager = portal_pager(**values['pager'])

        values.update(
            grouped_tasks=values['grouped_tasks'](pager['offset']),
            page_name='project',
            pager=pager,
            project=project,
            multiple_projects=False,
            task_url=f'projects/{project.id}/task',
            preview_object=project,
        )
        # default value is set to 'project' in _prepare_tasks_values, so we have to set it to 'none' here.
        if not groupby:
            values['groupby'] = 'none'

        return self._get_page_view_values(project, access_token, values, 'my_projects_history', False, **kwargs)

    def _prepare_project_domain(self):
        return [('is_template', '=', False)]

    def _prepare_searchbar_sortings(self):
        return {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }

    @http.route(['/my/projects', '/my/projects/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_projects(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        Project = request.env['project.project']
        domain = self._prepare_project_domain()

        searchbar_sortings = self._prepare_searchbar_sortings()
        if not sortby:
            sortby = 'name'
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

    @http.route(['/my/projects/<int:project_id>', '/my/projects/<int:project_id>/page/<int:page>'], type='http', auth="public", website=True)
    def portal_my_project(self, project_id=None, access_token=None, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='content', groupby=None, task_id=None, **kw):
        try:
            project_sudo = self._document_check_access('project.project', project_id, access_token)
            if project_sudo.is_template:
                return request.redirect('/my')
        except (AccessError, MissingError):
            return request.redirect('/my')
        if project_sudo.collaborator_count and project_sudo.with_user(request.env.user)._check_project_sharing_access():
            return request.redirect(f'/my/projects/{project_id}/project_sharing')
        project_sudo = project_sudo if access_token else project_sudo.with_user(request.env.user)
        if not groupby:
            groupby = 'stage_id'
        values = self._project_get_page_view_values(project_sudo, access_token, page, date_begin, date_end, sortby, search, search_in, groupby, **kw)
        return request.render("project.portal_my_project", values)

    def _get_project_sharing_company(self, project):
        return project.company_id or request.env.user.company_id

    def _prepare_project_sharing_session_info(self, project):
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        if request.env.lang:
            lang = request.env.lang
            session_info['user_context']['lang'] = lang
            # Update Cache
            user_context['lang'] = lang
        lang = user_context.get("lang")

        project_company = self._get_project_sharing_company(project)

        session_info.update(
            action_name="project.project_sharing_project_task_action",
            project_id=project.id,
            project_name=project.name,
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
            currencies=request.env['res.currency'].get_all_currencies(),
        )
        session_info['user_context'].update({
            'allow_milestones': project.allow_milestones,
            'allow_task_dependencies': project.allow_task_dependencies,
        })
        return session_info

    @http.route(['/my/projects/<int:project_id>/project_sharing', '/my/projects/<int:project_id>/project_sharing/<path:subpath>'], type='http', auth='user', methods=['GET'])
    def render_project_backend_view(self, project_id, subpath=None):
        project = request.env['project.project'].sudo().browse(project_id)
        if not (
            project.exists()
            and project.with_user(request.env.user)._check_project_sharing_access()
        ):
            return request.not_found()
        return request.render(
            'project.project_sharing_portal',
            {'session_info': self._prepare_project_sharing_session_info(project)},
        )

    @http.route('/my/projects/<int:project_id>/task/<int:task_id>', type='http', auth='public', website=True)
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

    @http.route('/my/projects/<int:project_id>/task/<int:task_id>/subtasks', type='http', auth='user', methods=['GET'], website=True)
    def portal_my_project_subtasks(self, project_id, task_id, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='content', groupby=None, **kw):
        try:
            project_sudo = self._document_check_access('project.project', project_id)
            task_sudo = request.env['project.task'].search([('project_id', '=', project_id), ('id', '=', task_id)]).sudo()
            task_domain = Domain('id', 'child_of', task_id) & Domain('id', '!=', task_id)
            searchbar_filters = self._get_my_tasks_searchbar_filters(Domain('id', '=', task_sudo.project_id.id), task_domain)

            if not filterby:
                filterby = 'all'
            domain = Domain(searchbar_filters.get(filterby, searchbar_filters.get('all'))['domain'])

            values = self._prepare_tasks_values(page, date_begin, date_end, sortby, search, search_in, groupby,
                url=f'/my/projects/{project_id}/task/{task_id}/subtasks', domain=task_domain & domain)
            values['page_name'] = 'project_subtasks'

            # pager
            pager_vals = values['pager']
            pager_vals['url_args'].update(filterby=filterby)
            pager = portal_pager(**pager_vals)

            values.update({
                'project': project_sudo,
                'show_project': True,
                'task': task_sudo,
                'grouped_tasks': values['grouped_tasks'](pager['offset']),
                'pager': pager,
                'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
                'filterby': filterby,
            })
            return request.render("project.portal_my_tasks", values)
        except (AccessError, MissingError):
            return request.not_found()

    @http.route('/my/projects/<int:project_id>/task/<int:task_id>/recurrent_tasks', type='http', auth='user', methods=['GET'], website=True)
    def portal_my_project_recurrent_tasks(self, project_id, task_id, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='content', groupby=None, **kw):
        try:
            project_sudo = self._document_check_access('project.project', project_id)
            task_sudo = request.env['project.task'].search([('project_id', '=', project_id), ('id', '=', task_id)], limit=1).sudo()
            task_domain = Domain('id', 'in', task_sudo.recurrence_id.task_ids.ids)
            searchbar_filters = self._get_my_tasks_searchbar_filters(Domain('id', '=', project_id), task_domain)

            if not filterby:
                filterby = 'all'
            domain = Domain(searchbar_filters.get(filterby, searchbar_filters.get('all'))['domain'])

            values = self._prepare_tasks_values(
                page, date_begin, date_end, sortby, search, search_in, groupby,
                url=f'/my/projects/{project_id}/task/{task_id}/recurrent_tasks',
                domain=task_domain & domain,
            )
            values['page_name'] = 'project_recurrent_tasks'
            pager = portal_pager(**values['pager'])

            values.update({
                'project': project_sudo,
                'task': task_sudo,
                'grouped_tasks': values['grouped_tasks'](pager['offset']),
                'pager': pager,
                'searchbar_filters': dict(sorted(searchbar_filters.items())),
                'filterby': filterby,
            })
            return request.render("project.portal_my_tasks", values)
        except (AccessError, MissingError):
            return request.not_found()

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
            'priority_labels': dict(task._fields['priority']._description_selection(request.env)),
            'task': task,
            'user': request.env.user,
            'project_accessible': project_accessible,
            'task_link_section': [],
            'preview_object': task,
        }

        values = self._get_page_view_values(task, access_token, values, history, False, **kwargs)
        if project:
            values['project_id'] = project.id
            history = request.session.get('my_project_tasks_history', [])
            try:
                current_task_index = history.index(task.id)
            except ValueError:
                return values

            total_task = len(history)
            task_url = f"{task.project_id.access_url}/task/%s?model=project.project&res_id={values['user'].id}&access_token={access_token}"

            values['prev_record'] = current_task_index != 0 and task_url % history[current_task_index - 1]
            values['next_record'] = current_task_index < total_task - 1 and task_url % history[current_task_index + 1]

        return values

    def _task_get_searchbar_sortings(self, milestones_allowed, project=False):
        values = {
            'id desc': {'label': _('Newest'), 'order': 'id desc', 'sequence': 10},
            'name': {'label': _('Title'), 'order': 'name', 'sequence': 20},
            'stage_id, project_id': {'label': _('Stage'), 'order': 'stage_id, project_id', 'sequence': 50},
            'state': {'label': _('Status'), 'order': 'state', 'sequence': 60},
            'priority desc': {'label': _('Priority'), 'order': 'priority desc', 'sequence': 80},
            'date_deadline asc': {'label': _('Deadline'), 'order': 'date_deadline asc', 'sequence': 90},
            'date_last_stage_update desc': {'label': _('Last Stage Update'), 'order': 'date_last_stage_update desc', 'sequence': 110},
        }
        if not project:
            values['project_id, stage_id'] = {'label': _('Project'), 'order': 'project_id, stage_id', 'sequence': 30}
        if milestones_allowed:
            values['milestone_id'] = {'label': _('Milestone'), 'order': 'milestone_id', 'sequence': 70}
        return values

    def _task_get_searchbar_groupby(self, milestones_allowed, project=False):
        values = {
            'none': {'label': _('None'), 'sequence': 10},
            'stage_id': {'label': _('Stage'), 'sequence': 20},
            'state': {'label': _('Status'), 'sequence': 40},
            'priority': {'label': _('Priority'), 'sequence': 60},
            'partner_id': {'label': _('Customer'), 'sequence': 70},
        }
        if not project:
            values['project_id'] = {'label': _('Project'), 'sequence': 30}
        if milestones_allowed:
            values['milestone_id'] = {'label': _('Milestone'), 'sequence': 50}
        return values

    def _task_get_searchbar_inputs(self, milestones_allowed, project=False):
        values = {
            'name': {'input': 'name', 'label': _(
                'Search%(left)s Tasks%(right)s',
                left=Markup('<span class="nolabel">'),
                right=Markup('</span>'),
            ), 'sequence': 10},
            'users': {'input': 'user_ids', 'label': _('Search in Assignees'), 'sequence': 20},
            'stage_id': {'input': 'stage_id', 'label': _('Search in Stages'), 'sequence': 30},
            'status': {'input': 'status', 'label': _('Search in Status'), 'sequence': 40},
            'priority': {'input': 'priority', 'label': _('Search in Priority'), 'sequence': 60},
            'partner_id': {'input': 'partner_id', 'label': _('Search in Customer'), 'sequence': 80},
        }
        if not project:
            values['project_id'] = {'input': 'project_id', 'label': _('Search in Project'), 'sequence': 50}
        if milestones_allowed:
            values['milestone_id'] = {'input': 'milestone_id', 'label': _('Search in Milestone'), 'sequence': 70}

        return values

    def _task_get_search_domain(self, search_in, search, milestones_allowed, project):
        if not search_in or search_in == 'name':
            return ['|', ('name', 'ilike', search), ('id', 'ilike', search)]
        elif search_in == 'users':
            user_ids = request.env['res.users'].sudo().search([('name', 'ilike', search)])
            return [('user_ids', 'in', user_ids.ids)]
        elif search_in == 'priority':
            priority_selections = request.env['ir.model.fields.selection'].sudo().search([
                ('field_id.model', '=', 'project.task'),
                ('field_id.name', '=', 'priority'),
                ('name', 'ilike', search),
            ])
            if priority_selections:
                return [('priority', 'in', priority_selections.mapped('value'))]
            return Domain.FALSE
        elif search_in == 'status':
            state_selections = request.env['ir.model.fields.selection'].sudo().search([
                ('field_id.model', '=', 'project.task'),
                ('field_id.name', '=', 'state'),
                ('name', 'ilike', search),
            ])
            if state_selections:
                return [('state', 'in', state_selections.mapped('value'))]
            return Domain.FALSE
        elif search_in in self._task_get_searchbar_inputs(milestones_allowed, project):
            return [(search_in, 'ilike', search)]
        else:
            return ['|', ('name', 'ilike', search), ('id', 'ilike', search)]

    def _prepare_tasks_values(self, page, date_begin, date_end, sortby, search, search_in, groupby, url="/my/tasks", domain=None, su=False, project=False):
        values = self._prepare_portal_layout_values()

        Task = request.env['project.task']

        domain = Domain.AND([domain or [], [('has_template_ancestor', '=', False)]])
        if not su and Task.has_access('read'):
            domain &= Domain(request.env['ir.rule']._compute_domain(Task._name, 'read'))
        Task_sudo = Task.sudo()
        milestone_domain = domain & Domain('allow_milestones', '=', True) & Domain('milestone_id', '!=', False)
        milestones_allowed = Task_sudo.search_count(milestone_domain, limit=1) == 1
        searchbar_sortings = dict(sorted(self._task_get_searchbar_sortings(milestones_allowed, project).items(),
                                         key=lambda item: item[1]["sequence"]))
        searchbar_inputs = dict(sorted(self._task_get_searchbar_inputs(milestones_allowed, project).items(), key=lambda item: item[1]['sequence']))
        searchbar_groupby = dict(sorted(self._task_get_searchbar_groupby(milestones_allowed, project).items(), key=lambda item: item[1]['sequence']))

        # default sort by value
        if not sortby or (sortby == 'milestone_id' and not milestones_allowed):
            sortby = next(iter(searchbar_sortings))

        # default group by value
        if not groupby or (groupby == 'milestone_id' and not milestones_allowed):
            groupby = 'project_id'

        if date_begin and date_end:
            domain &= Domain('create_date', '>', date_begin) & Domain('create_date', '<=', date_end)

        # search reset if needed
        if not milestones_allowed and search_in == 'milestone_id':
            search_in = 'all'
        # search
        if search and search_in:
            domain &= Domain(self._task_get_search_domain(search_in, search, milestones_allowed, project))

        # content according to pager and archive selected
        if groupby == 'none':
            group_field = None
        elif groupby == 'priority':
            group_field = 'priority desc'
        else:
            group_field = groupby
        order = '%s, %s' % (group_field, sortby) if group_field else sortby

        def get_grouped_tasks(pager_offset):
            tasks = Task_sudo.search(domain, order=order, limit=self._items_per_page, offset=pager_offset)
            request.session['my_project_tasks_history' if url.startswith('/my/projects') else 'my_tasks_history'] = tasks.ids[:100]

            tasks_project_allow_milestone = tasks.filtered(lambda t: t.allow_milestones)
            tasks_no_milestone = tasks - tasks_project_allow_milestone

            if groupby != 'none':
                if groupby == 'milestone_id':
                    grouped_tasks = [Task_sudo.concat(*g) for k, g in groupbyelem(tasks_project_allow_milestone, itemgetter(groupby))]

                    if not grouped_tasks:
                        if tasks_no_milestone:
                            grouped_tasks = [tasks_no_milestone]
                    else:
                        if grouped_tasks[len(grouped_tasks) - 1][0].milestone_id and tasks_no_milestone:
                            grouped_tasks.append(tasks_no_milestone)
                        else:
                            grouped_tasks[len(grouped_tasks) - 1] |= tasks_no_milestone

                else:
                    grouped_tasks = [Task_sudo.concat(*g) for k, g in groupbyelem(tasks, itemgetter(groupby))]
            else:
                grouped_tasks = [tasks] if tasks else []

            task_states = dict(Task_sudo._fields['state']._description_selection(request.env))
            if sortby == 'state':
                if groupby == 'none' and grouped_tasks:
                    grouped_tasks[0] = grouped_tasks[0].sorted(lambda tasks: task_states.get(tasks.state))
                else:
                    grouped_tasks.sort(key=lambda tasks: task_states.get(tasks[0].state))
            return grouped_tasks

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'grouped_tasks': get_grouped_tasks,
            'allow_milestone': milestones_allowed,
            'multiple_projects': True,
            'priority_labels': dict(Task_sudo._fields['priority']._description_selection(request.env)),
            'page_name': 'task',
            'default_url': url,
            'task_url': 'tasks',
            'pager': {
                "url": url,
                "url_args": {'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'groupby': groupby, 'search_in': search_in, 'search': search},
                "total": Task_sudo.search_count(domain),
                "page": page,
                "step": self._items_per_page
            },
            'searchbar_sortings': searchbar_sortings,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
            'sortby': sortby,
            'groupby': groupby,
        })
        return values

    def _get_my_tasks_searchbar_filters(self, project_domain=None, task_domain=None):
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': [('project_id', '!=', False), ('is_template', '=', False)]},
        }

        # extends filterby criteria with project the customer has access to
        projects = request.env['project.project'].search(project_domain or [], order="id")
        for project in projects:
            searchbar_filters.update({
                str(project.id): {'label': project.name, 'domain': [('project_id', '=', project.id)]}
            })

        # extends filterby criteria with project (criteria name is the project id)
        # Note: portal users can't view projects they don't follow
        project_groups = request.env['project.task']._read_group(
            Domain.AND([[('project_id', 'not in', projects.ids), ('is_template', '=', False), ('project_id', '!=', False)], task_domain or []]),
            ['project_id'])
        for [project] in project_groups:
            searchbar_filters.update({
                str(project.id): {'label': project.sudo().display_name, 'domain': [('project_id', '=', project.id)]}
            })
        return searchbar_filters

    @http.route(['/my/tasks', '/my/tasks/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_tasks(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='name', groupby=None, **kw):
        searchbar_filters = self._get_my_tasks_searchbar_filters([('is_template', '=', False)])

        if not filterby:
            filterby = 'all'
        domain = searchbar_filters.get(filterby, searchbar_filters.get('all'))['domain']

        values = self._prepare_tasks_values(page, date_begin, date_end, sortby, search, search_in, groupby, domain=domain)

        # pager
        pager_vals = values['pager']
        pager_vals['url_args'].update(filterby=filterby)
        pager = portal_pager(**pager_vals)

        grouped_tasks = values['grouped_tasks'](pager['offset'])
        values.update({
            'grouped_tasks': grouped_tasks,
            'show_project': True,
            'pager': pager,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
        })
        return request.render("project.portal_my_tasks", values)

    def _show_task_report(self, task_sudo, report_type, download):
        # This method is to be overriden to report timesheets if the module is installed.
        # The route should not be called if at least hr_timesheet is not installed
        raise MissingError(_('There is nothing to report.'))

    @http.route(['/my/tasks/<int:task_id>'], type='http', auth="public", website=True)
    def portal_my_task(self, task_id, report_type=None, access_token=None, project_sharing=False, **kw):
        try:
            task_sudo = self._document_check_access('project.task', task_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('pdf', 'html', 'text'):
            return self._show_task_report(task_sudo, report_type, download=kw.get('download'))

        # ensure attachment are accessible with access token inside template
        for attachment in task_sudo.attachment_ids:
            attachment.generate_access_token()
        if project_sharing is True:
            # Then the user arrives to the stat button shown in form view of project.task and the portal user can see only 1 task
            # so the history should be reset.
            request.session['my_tasks_history'] = task_sudo.ids
        values = self._task_get_page_view_values(task_sudo, access_token, **kw)
        return request.render("project.portal_my_task", values)

    @http.route('/project_sharing/attachment/add_image', type='http', auth='user', methods=['POST'], website=True)
    def add_image(self, name, data, res_id, access_token=None, **kwargs):
        try:
            task_sudo = self._document_check_access('project.task', int(res_id), access_token=access_token)
            if not task_sudo.with_user(request.env.uid).project_id._check_project_sharing_access():
                return request.not_found()
        except (AccessError, MissingError):
            raise UserError(_("The document does not exist or you do not have the rights to access it."))

        IrAttachment = request.env['ir.attachment']

        # Avoid using sudo when not necessary: internal users can create attachments,
        # as opposed to public and portal users.
        if not request.env.user._is_internal():
            IrAttachment = IrAttachment.sudo()

        values = IrAttachment._check_contents({
            'name': name,
            'datas': data,
            'res_model': 'project.task',
            'res_id': res_id,
            'access_token': IrAttachment._generate_access_token(),
        })

        valid_image_mime_types = ['image/jpeg', 'image/png', 'image/bmp', 'image/tiff']

        if values.get('mimetype', False) not in valid_image_mime_types:
            return request.make_response(
                data=json.dumps({'error': _('Only jpeg, png, bmp and tiff images are allowed as attachments.')}),
                headers=[('Content-Type', 'application/json')],
                status=400
            )

        attachment = IrAttachment.create(values)
        return request.make_response(
            data=json.dumps(attachment.read(['id', 'name', 'mimetype', 'file_size', 'access_token'])[0]),
            headers=[('Content-Type', 'application/json')]
        )
