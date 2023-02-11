# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from operator import itemgetter

from odoo import _
from odoo.http import request
from odoo.tools import groupby as groupbyelem

from odoo.osv.expression import OR

from odoo.addons.project.controllers.portal import ProjectCustomerPortal


class SaleProjectCustomerPortal(ProjectCustomerPortal):

    def _task_get_searchbar_groupby(self):
        values = super()._task_get_searchbar_groupby()
        values['sale_order'] = {'input': 'sale_order', 'label': _('Sales Order'), 'order': 7}
        values['sale_line'] = {'input': 'sale_line', 'label': _('Sales Order Item'), 'order': 8}
        return dict(sorted(values.items(), key=lambda item: item[1]["order"]))

    def _task_get_groupby_mapping(self):
        groupby_mapping = super()._task_get_groupby_mapping()
        groupby_mapping.update(sale_order='sale_order_id', sale_line='sale_line_id')
        return groupby_mapping

    def _task_get_searchbar_inputs(self):
        values = super()._task_get_searchbar_inputs()
        values['sale_order'] = {'input': 'sale_order', 'label': _('Search in Sales Order'), 'order': 7}
        values['sale_line'] = {'input': 'sale_line', 'label': _('Search in Sales Order Item'), 'order': 8}
        values['invoice'] = {'input': 'invoice', 'label': _('Search in Invoice'), 'order': 9}
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
