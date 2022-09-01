# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _lt
from odoo.osv.expression import OR

from odoo.addons.project.controllers.portal import ProjectCustomerPortal


class SaleProjectCustomerPortal(ProjectCustomerPortal):

    def _task_get_searchbar_groupby(self, milestones_allowed):
        values = super()._task_get_searchbar_groupby(milestones_allowed)
        values['sale_order'] = {'input': 'sale_order', 'label': _lt('Sales Order'), 'order': 8}
        values['sale_line'] = {'input': 'sale_line', 'label': _lt('Sales Order Item'), 'order': 9}
        return dict(sorted(values.items(), key=lambda item: item[1]["order"]))

    def _task_get_groupby_mapping(self):
        groupby_mapping = super()._task_get_groupby_mapping()
        groupby_mapping.update(sale_order='sale_order_id', sale_line='sale_line_id')
        return groupby_mapping

    def _task_get_searchbar_inputs(self, milestones_allowed):
        values = super()._task_get_searchbar_inputs(milestones_allowed)
        values['sale_order'] = {'input': 'sale_order', 'label': _lt('Search in Sales Order'), 'order': 8}
        values['sale_line'] = {'input': 'sale_line', 'label': _lt('Search in Sales Order Item'), 'order': 9}
        values['invoice'] = {'input': 'invoice', 'label': _lt('Search in Invoice'), 'order': 10}
        return dict(sorted(values.items(), key=lambda item: item[1]["order"]))

    def _task_get_search_domain(self, search_in, search):
        search_domain = [super()._task_get_search_domain(search_in, search)]
        if search_in in ('sale_order', 'all'):
            search_domain.append([('sale_order_id.name', 'ilike', search)])
        if search_in in ('sale_line', 'all'):
            search_domain.append([('sale_line_id.name', 'ilike', search)])
        if search_in in ('invoice', 'all'):
            search_domain.append([('sale_order_id.invoice_ids.name', 'ilike', search)])
        return OR(search_domain)
