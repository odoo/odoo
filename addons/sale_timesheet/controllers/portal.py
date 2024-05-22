# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request
from odoo.osv import expression

from odoo.addons.account.controllers import portal
from odoo.addons.hr_timesheet.controllers.portal import TimesheetCustomerPortal


class PortalAccount(portal.PortalAccount):

    def _invoice_get_page_view_values(self, invoice, access_token, **kwargs):
        values = super(PortalAccount, self)._invoice_get_page_view_values(invoice, access_token, **kwargs)
        domain = request.env['account.analytic.line']._timesheet_get_portal_domain()
        domain = expression.AND([
            domain,
            request.env['account.analytic.line']._timesheet_get_sale_domain(
                invoice.mapped('line_ids.sale_line_ids'),
                request.env['account.move'].browse([invoice.id])
            )
        ])
        values['timesheets'] = request.env['account.analytic.line'].sudo().search(domain)
        values['is_uom_day'] = request.env['account.analytic.line'].sudo()._is_timesheet_encode_uom_day()
        return values


class CustomerPortal(portal.CustomerPortal):
    def _order_get_page_view_values(self, order, access_token, **kwargs):
        values = super(CustomerPortal, self)._order_get_page_view_values(order, access_token, **kwargs)
        domain = request.env['account.analytic.line']._timesheet_get_portal_domain()
        domain = expression.AND([
            domain,
            request.env['account.analytic.line']._timesheet_get_sale_domain(
                order.mapped('order_line'),
                order.invoice_ids
            )
        ])
        values['timesheets'] = request.env['account.analytic.line'].sudo().search(domain)
        values['is_uom_day'] = request.env['account.analytic.line'].sudo()._is_timesheet_encode_uom_day()
        return values


class SaleTimesheetCustomerPortal(TimesheetCustomerPortal):

    def _get_searchbar_inputs(self):
        searchbar_inputs = super()._get_searchbar_inputs()
        searchbar_inputs.update(
            sol={'input': 'sol', 'label': _('Search in Sales Order Item')},
            sol_id={'input': 'sol_id', 'label': _('Search in Sales Order Item ID')},
            invoice={'input': 'invoice_id', 'label': _('Search in Invoice ID')})
        return searchbar_inputs

    def _get_searchbar_groupby(self):
        searchbar_groupby = super()._get_searchbar_groupby()
        searchbar_groupby.update(sol={'input': 'sol', 'label': _('Sales Order Item')})
        return searchbar_groupby

    def _get_search_domain(self, search_in, search):
        search_domain = super()._get_search_domain(search_in, search)
        if search_in in ('sol', 'all'):
            search_domain = expression.OR([search_domain, [('so_line', 'ilike', search)]])
        if search_in in ('sol_id', 'invoice_id'):
            search = int(search) if search.isdigit() else 0
        if search_in == 'sol_id':
            search_domain = expression.OR([search_domain, [('so_line.id', '=', search)]])
        if search_in == 'invoice_id':
            invoice = request.env['account.move'].browse(search)
            domain = request.env['account.analytic.line']._timesheet_get_sale_domain(invoice.mapped('invoice_line_ids.sale_line_ids'), invoice)
            search_domain = expression.OR([search_domain, domain])
        return search_domain

    def _get_groupby_mapping(self):
        groupby_mapping = super()._get_groupby_mapping()
        groupby_mapping.update(sol='so_line')
        return groupby_mapping

    @http.route(['/my/timesheets', '/my/timesheets/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_timesheets(self, page=1, sortby=None, filterby=None, search=None, search_in='all', groupby='sol', **kw):
        if search and search_in and search_in in ('sol_id', 'invoice_id') and not search.isdigit():
            search = '0'
        return super().portal_my_timesheets(page, sortby, filterby, search, search_in, groupby, **kw)
