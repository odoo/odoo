# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _

from odoo.addons.project.controllers.portal import ProjectCustomerPortal


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
                'sale_order':  {'input': 'sale_order', 'label': _('Search in Sales Order'), 'sequence': 90},
                'invoice': {'input': 'invoice', 'label': _('Search in Invoice'), 'sequence': 100},
            }
        return values

<<<<<<< saas-17.4
    def _task_get_search_domain(self, search_in, search, milestones_allowed, project):
        if search_in == 'sale_order':
            return ['|', ('sale_order_id.name', 'ilike', search), ('sale_line_id.name', 'ilike', search)]
        elif search_in == 'invoice':
            return [('sale_order_id.invoice_ids.name', 'ilike', search)]
        else:
            return super()._task_get_search_domain(search_in, search, milestones_allowed, project)

    def _prepare_project_sharing_session_info(self, project, task=None):
        session_info = super()._prepare_project_sharing_session_info(project, task)
        session_info['action_context'].update({
||||||| fe59408877823b1537a1734aba8306435a3d0912
    def _task_get_search_domain(self, search_in, search):
        search_domain = [super()._task_get_search_domain(search_in, search)]
        if search_in in ('sale_order', 'all'):
            search_domain.append(['|', ('sale_order_id.name', 'ilike', search), ('sale_line_id.name', 'ilike', search)])
        if search_in in ('invoice', 'all'):
            search_domain.append([('sale_order_id.invoice_ids.name', 'ilike', search)])
        return OR(search_domain)
=======
    def _task_get_search_domain(self, search_in, search):
        search_domain = [super()._task_get_search_domain(search_in, search)]
        if search_in in ('sale_order', 'all'):
            search_domain.append(['|', ('sale_order_id.name', 'ilike', search), ('sale_line_id.name', 'ilike', search)])
        if search_in in ('invoice', 'all'):
            search_domain.append([('sale_order_id.invoice_ids.name', 'ilike', search)])
        return OR(search_domain)

    def _prepare_project_sharing_session_info(self, project, task=None):
        session_info = super()._prepare_project_sharing_session_info(project, task)
        session_info['user_context'].update({
>>>>>>> b7e37d1fd24df46ad8f0759d7ef82871302baf46
            'allow_billable': project.allow_billable,
        })
        return session_info
