# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from odoo.addons.helpdesk.controllers import portal


class CustomerPortal(portal.CustomerPortal):
    def _ticket_get_page_view_values(self, ticket, access_token, **kwargs):
        values = super()._ticket_get_page_view_values(ticket, access_token, **kwargs)
        if ticket.use_helpdesk_sale_timesheet and ticket.sale_order_id:
            try:
                self._document_check_access('sale.order', ticket.sale_order_id.id)
                values['ticket_link_section'].append({
                    'access_url': ticket.sale_order_id.get_portal_url(),
                    'title': _('Sales Order'),
                    'sequence': 1,
                })
            except (AccessError, MissingError):
                pass
        if ticket.use_helpdesk_sale_timesheet:
            Timesheet = request.env['account.analytic.line']
            values['timesheets'] = ticket.timesheet_ids._get_portal_helpdesk_timesheet()
            is_encode_uom_day = Timesheet._is_timesheet_encode_uom_day()
            values['is_uom_day'] = is_encode_uom_day
            if is_encode_uom_day:
                values['convert_hours_to_days'] = Timesheet._convert_hours_to_days
        return values

    def _prepare_my_tickets_values(self, page=1, date_begin=None, date_end=None, sortby=None, filterby='all', search=None, groupby='none', search_in='content'):
        values = super()._prepare_my_tickets_values(page, date_begin, date_end, sortby, filterby, search, groupby, search_in)
        Timesheet = request.env['account.analytic.line']
        is_encode_uom_day = Timesheet._is_timesheet_encode_uom_day()
        values['is_uom_day'] = is_encode_uom_day
        if is_encode_uom_day:
            values['convert_hours_to_days'] = Timesheet._convert_hours_to_days
        return values
