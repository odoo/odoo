# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.exceptions import AccessError, MissingError
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

class SaleTimesheetCustomerPortal(TimesheetCustomerPortal):

    def _get_searchbar_inputs(self):
        searchbar_inputs = super()._get_searchbar_inputs()
        searchbar_inputs.update(
            so={'input': 'so', 'label': _('Search in Sales Order')},
            sol={'input': 'sol', 'label': _('Search in Sales Order Item')},
            invoice={'input': 'invoice', 'label': _('Search in Invoice')})
        return searchbar_inputs

    def _get_searchbar_groupby(self):
        searchbar_groupby = super()._get_searchbar_groupby()
        searchbar_groupby.update(
            so={'input': 'so', 'label': _('Sales Order')},
            sol={'input': 'sol', 'label': _('Sales Order Item')},
            invoice={'input': 'invoice', 'label': _('Invoice')})
        return searchbar_groupby

    def _get_search_domain(self, search_in, search):
        search_domain = super()._get_search_domain(search_in, search)
        if search_in in ('sol', 'all'):
            search_domain = expression.OR([search_domain, [('so_line', 'ilike', search)]])
        if search_in in ('so', 'all'):
            search_domain = expression.OR([search_domain, [('so_line.order_id.name', 'ilike', search)]])
        if search_in in ('invoice', 'all'):
            invoices = request.env['account.move'].sudo().search([('name', 'ilike', search)])
            domain = request.env['account.analytic.line']._timesheet_get_sale_domain(invoices.mapped('invoice_line_ids.sale_line_ids'), invoices)
            search_domain = expression.OR([search_domain, domain])
        return search_domain

    def _get_groupby_mapping(self):
        groupby_mapping = super()._get_groupby_mapping()
        groupby_mapping.update(
            sol='so_line',
            so='order_id',
            invoice='timesheet_invoice_id')
        return groupby_mapping

    def _get_searchbar_sortings(self):
        searchbar_sortings = super()._get_searchbar_sortings()
        searchbar_sortings.update(
            sol={'label': _('Sales Order Item'), 'order': 'so_line'})
        return searchbar_sortings

    def _task_get_page_view_values(self, task, access_token, **kwargs):
        values = super()._task_get_page_view_values(task, access_token, **kwargs)
        values['so_accessible'] = False
        try:
            if task.sale_order_id and self._document_check_access('sale.order', task.sale_order_id.id):
                values['so_accessible'] = True
        except (AccessError, MissingError):
            pass

        values['invoices_accessible'] = []
        for invoice in task.sale_order_id.invoice_ids:
            try:
                if self._document_check_access('account.move', invoice.id):
                    values['invoices_accessible'].append(invoice.id)
            except (AccessError, MissingError):
                pass
        return values

    @http.route(['/my/timesheets', '/my/timesheets/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_timesheets(self, page=1, sortby=None, filterby=None, search=None, search_in='all', groupby='sol', **kw):
        return super().portal_my_timesheets(page, sortby, filterby, search, search_in, groupby, **kw)
