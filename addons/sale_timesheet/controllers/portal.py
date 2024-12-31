# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.osv import expression

from odoo.addons.account.controllers.portal import PortalAccount
from odoo.addons.hr_timesheet.controllers.portal import TimesheetCustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.project.controllers.portal import ProjectCustomerPortal


class PortalProjectAccount(PortalAccount, ProjectCustomerPortal):

    def _invoice_get_page_view_values(self, invoice, access_token, **kwargs):
        values = super()._invoice_get_page_view_values(invoice, access_token, **kwargs)
        domain = request.env['account.analytic.line']._timesheet_get_portal_domain()
        domain = expression.AND([
            domain,
            request.env['account.analytic.line']._timesheet_get_sale_domain(
                invoice.line_ids.sale_line_ids,
                request.env['account.move'].browse([invoice.id])
            )
        ])
        values['timesheets'] = request.env['account.analytic.line'].sudo().search(domain)
        values['is_uom_day'] = request.env['account.analytic.line'].sudo()._is_timesheet_encode_uom_day()
        return values

    @http.route([
        '/my/tasks/<task_id>/orders/invoices',
        '/my/tasks/<task_id>/orders/invoices/page/<int:page>'],
        type='http', auth="user", website=True)
    def portal_my_tasks_invoices(self, task_id=None, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        task = request.env['project.task'].search([('id', '=', task_id)])
        if not task:
            return NotFound()

        domain = [('id', 'in', task.sale_order_id.invoice_ids.ids)]
        values = self._prepare_my_invoices_values(page, date_begin, date_end, sortby, filterby, domain=domain)

        # pager
        pager = portal_pager(**values['pager'])

        # content according to pager and archive selected
        invoices = values['invoices'](pager['offset'])
        request.session['my_invoices_history'] = [i['invoice'].id for i in invoices[:100]]

        values.update({
            'invoices': invoices,
            'pager': pager,
        })

        return request.render("account.portal_my_invoices", values)


class SaleTimesheetCustomerPortal(TimesheetCustomerPortal):

    def _get_searchbar_inputs(self):
        return super()._get_searchbar_inputs() | {
            'so': {'input': 'so', 'label': _('Search in Sales Order'), 'sequence': 50},
            'invoice': {'input': 'invoice', 'label': _('Search in Invoice'), 'sequence': 80},
        }

    def _get_searchbar_groupby(self):
        return super()._get_searchbar_groupby() | {
            'so_line': {'label': _('Sales Order Item'), 'sequence': 80},
            'timesheet_invoice_id': {'label': _('Invoice'), 'sequence': 90},
        }

    def _get_search_domain(self, search_in, search):
        if search_in == 'so':
            return ['|', ('so_line', 'ilike', search), ('so_line.order_id.name', 'ilike', search)]
        elif search_in == 'invoice':
            invoices = request.env['account.move'].sudo().search(['|', ('name', 'ilike', search), ('id', 'ilike', search)])
            return request.env['account.analytic.line']._timesheet_get_sale_domain(invoices.invoice_line_ids.sale_line_ids, invoices)
        else:
            return super()._get_search_domain(search_in, search)

    def _get_searchbar_sortings(self):
        return super()._get_searchbar_sortings() | {
            'so_line': {'label': _('Sales Order Item')},
            'timesheet_invoice_id': {'label': _('Invoice')},
        }

    def _task_get_page_view_values(self, task, access_token, **kwargs):
        values = super()._task_get_page_view_values(task, access_token, **kwargs)
        values['so_accessible'] = False
        try:
            if task.sale_order_id and self._document_check_access('sale.order', task.sale_order_id.id):
                values['so_accessible'] = True
                title = _('Quotation') if task.sale_order_id.state in ['draft', 'sent'] else _('Sales Order')
                values['task_link_section'].append({
                    'access_url': task.sale_order_id.get_portal_url(),
                    'title': title,
                })
        except (AccessError, MissingError):
            pass

        moves = request.env['account.move']
        invoice_ids = task.sale_order_id.invoice_ids
        if invoice_ids and request.env['account.move'].has_access('read'):
            moves = request.env['account.move'].search([('id', 'in', invoice_ids.ids)])
            values['invoices_accessible'] = moves.ids
            if moves:
                if len(moves) == 1:
                    task_invoice_url = moves.get_portal_url()
                    title = _('Invoice')
                else:
                    task_invoice_url = f'/my/tasks/{task.id}/orders/invoices'
                    title = _('Invoices')
                values['task_link_section'].append({
                    'access_url': task_invoice_url,
                    'title': title,
                })
        return values

    @http.route()
    def portal_my_timesheets(self, *args, groupby='so_line', **kw):
        return super().portal_my_timesheets(*args, groupby=groupby, **kw)
