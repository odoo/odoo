# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from operator import itemgetter

from odoo import http, _
from odoo.http import request
from odoo.osv import expression
from odoo.tools import groupby as groupbyelem

from odoo.addons.project.controllers.portal import ProjectCustomerPortal


class SaleProjectCustomerPortal(ProjectCustomerPortal):

    def _task_get_searchbar_groupby(self):
        values = super()._task_get_searchbar_groupby()
        values['sale_order'] = {'input': 'sale_order', 'label': _('Sales Order')}
        values['sale_line'] = {'input': 'sale_line', 'label': _('Sales Order Item')}
        return values

    def _task_get_groupby_mapping(self):
        groupby_mapping = super()._task_get_groupby_mapping()
        groupby_mapping.update(
            sale_order='sale_order_id',
            sale_line='sale_line_id')
        return groupby_mapping

    def _task_get_order(self, order, groupby):
        if groupby == 'sale_order':
            order = "sale_order_id, %s" % order
        elif groupby == 'sale_line':
            order = "sale_line_id, %s" % order
        else:
            order = super()._task_get_order(order, groupby)
        return order

    def _task_get_grouped_tasks(self, groupby, tasks):
        if groupby:
            grouped_tasks = [request.env['project.task'].concat(*g) for k, g in groupbyelem(tasks, itemgetter(groupby))]
        else:
            grouped_tasks = super()._task_get_grouped_tasks(groupby, tasks)
        return grouped_tasks

    def _task_get_searchbar_inputs(self):
        values = super()._task_get_searchbar_inputs()
        values['sale_order'] = {'input': 'sale_order', 'label': _('Search in Sales Order')}
        values['sale_line'] = {'input': 'sale_line', 'label': _('Search in Sales Order Item')}
        values['invoice'] = {'input': 'invoice', 'label': _('Search in Invoice')}
        return values

    def _task_get_search_domain(self, search_in, search):
        search_domain = super()._task_get_search_domain(search_in, search)
        if search_in in ('sale_order', 'all'):
            search_domain = expression.OR([search_domain, [('sale_order_id.name', 'ilike', search)]])
        if search_in in ('sale_line', 'all'):
            search_domain = expression.OR([search_domain, [('sale_line_id.name', 'ilike', search)]])
        if search_in in ('invoice', 'all'):
            search_domain = expression.OR([search_domain, [('sale_order_id.invoice_ids.name', 'ilike', search)]])
        return search_domain

    @http.route(['/my/tasks', '/my/tasks/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_tasks(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='content', groupby=None, **kw):
        return super().portal_my_tasks(page, date_begin, date_end, sortby, filterby, search, search_in, groupby, **kw)
