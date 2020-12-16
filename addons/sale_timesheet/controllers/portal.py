# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.osv import expression

from odoo.addons.account.controllers import portal


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
