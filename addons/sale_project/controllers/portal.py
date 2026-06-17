# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from operator import itemgetter

from odoo.addons.project.controllers.portal import ProjectCustomerPortal
from odoo.tools import groupby as groupbyelem


class SaleProjectCustomerPortal(ProjectCustomerPortal):

    def _task_get_searchbar_groupby(self, milestones_allowed, project=False):
        values = super()._task_get_searchbar_groupby(milestones_allowed, project)
        if project and not project.sudo()._get_hide_partner():
            del values['partner_id']
        if not project or project.sudo().allow_billable:
            values |= {
                'sale_line_id': {'label': _('Sales Order Item'), 'sequence': 80},
            }
        return values

    def _task_get_searchbar_inputs(self, milestones_allowed, project=False):
        values = super()._task_get_searchbar_inputs(milestones_allowed, project)
        if project and not project.sudo()._get_hide_partner():
            del values['partner_id']
        if not project or project.sudo().allow_billable:
            values |= {
                'sale_order':  {'input': 'sale_order', 'label': _('Search in Sales Order Item'), 'sequence': 90},
                'invoice': {'input': 'invoice', 'label': _('Search in Invoice'), 'sequence': 100},
            }
        return values

    def _task_get_search_domain(self, search_in, search, milestones_allowed, project):
        if search_in == 'sale_order':
            return ['|', ('sale_order_id.name', 'ilike', search), ('sale_line_id.name', 'ilike', search)]
        elif search_in == 'invoice':
            return [('sale_order_id.invoice_ids.name', 'ilike', search)]
        else:
            return super()._task_get_search_domain(search_in, search, milestones_allowed, project)

    def _prepare_project_sharing_session_info(self, project):
        session_info = super()._prepare_project_sharing_session_info(project)
        session_info['user_context'].update({
            'allow_billable': project.allow_billable,
        })
        return session_info

    def _concat_tasks(self, task_sudo, groupby, tasks):
        if groupby == 'sale_line_id':
            tasks_no_sol = tasks.filtered(lambda task: task.sale_line_id.state != 'sale' or not task.sale_line_id)
            tasks_sol = tasks - tasks_no_sol
            grouped_tasks = [task_sudo.concat(g) for k, g in groupbyelem(tasks_sol, itemgetter(groupby))]
            if not grouped_tasks:
                if tasks_no_sol:
                    grouped_tasks = [tasks_no_sol]
            else:
                grouped_tasks.append(tasks_no_sol)

            return grouped_tasks

        return super()._concat_tasks(task_sudo, groupby, tasks)
