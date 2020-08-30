# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.osv import expression

from odoo.addons.account.controllers.portal import PortalAccount


class PortalAccount(PortalAccount):

    def _invoice_get_page_view_values(self, invoice, access_token, **kwargs):
        values = super(PortalAccount, self)._invoice_get_page_view_values(invoice, access_token, **kwargs)
        domain = request.env['account.analytic.line']._timesheet_get_portal_domain()
        domain = expression.AND([domain, [('timesheet_invoice_id', '=', invoice.id)]])
        values['timesheets'] = request.env['account.analytic.line'].sudo().search(domain)
        values['is_uom_day'] = request.env['account.analytic.line'].sudo()._is_timesheet_encode_uom_day()
        return values
