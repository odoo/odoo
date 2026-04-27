# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import OrderedDict
from werkzeug.exceptions import NotFound

from odoo import _
from odoo.http import request, route
from odoo.exceptions import AccessError, MissingError
from odoo.osv.expression import AND

from odoo.addons.helpdesk.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.project.controllers.portal import ProjectCustomerPortal


class ProjectHelpdeskPortal(ProjectCustomerPortal, CustomerPortal):

    def _task_get_page_view_values(self, task, access_token, **kwargs):
        values = super()._task_get_page_view_values(task, access_token, **kwargs)
        try:
            if task.helpdesk_ticket_id and self._document_check_access('helpdesk.ticket', task.helpdesk_ticket_id.id):
                values['task_link_section'].append({
                    'access_url': task.helpdesk_ticket_id.get_portal_url(),
                    'title': _('Ticket'),
                })
        except (AccessError, MissingError):
            pass

        return values

    def _ticket_get_page_view_values(self, ticket, access_token, **kwargs):
        values = super()._ticket_get_page_view_values(ticket, access_token, **kwargs)
        if ticket.fsm_task_count and request.env['project.task'].has_access('read'):
            tasks = request.env['project.task'].search([('id', 'in', ticket.fsm_task_ids.ids)])
            if tasks:
                if len(tasks) == 1:
                    ticket_fsm_task_url = f'/my/tasks/{tasks.id}'
                    title = _('Task')
                else:
                    ticket_fsm_task_url = f'/my/tickets/{ticket.id}/tasks'
                    title = _('Tasks')
                values['ticket_link_section'].append({
                    'access_url': ticket_fsm_task_url,
                    'title': title,
                    'sequence': 3,
                })
        return values

    @route([
        '/my/tickets/<ticket_id>/tasks',
        '/my/tickets/<ticket_id>/tasks/page/<int:page>'
    ], type='http', auth="user", website=True)
    def portal_my_tickets_task(self, ticket_id=None, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='content', groupby=None, **kw):
        ticket = request.env['helpdesk.ticket'].search([('id', '=', ticket_id)])
        if not ticket.exists():
            return NotFound()
        searchbar_filters = self._get_my_tasks_searchbar_filters()

        if not filterby:
            filterby = 'all'

        domain = searchbar_filters.get(filterby, searchbar_filters.get('all'))['domain']

        domain = AND([[('id', 'in', ticket.fsm_task_ids.ids)], domain])
        values = self._prepare_tasks_values(page, date_begin, date_end, sortby, search, search_in, groupby, domain=domain)

        # pager
        pager_vals = values['pager']
        pager_vals['url_args'].update(filterby=filterby)
        pager = portal_pager(**pager_vals)

        values.update({
            'grouped_tasks': values['grouped_tasks'](pager['offset']),
            'pager': pager,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        return request.render("project.portal_my_tasks", values)
