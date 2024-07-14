# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import _
from odoo.http import request, route
from odoo.addons.helpdesk.controllers.portal import CustomerPortal as HelpdeskCustomerPortal
from odoo.addons.account.controllers.portal import CustomerPortal as AccountCustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager


class CustomerPortal(HelpdeskCustomerPortal, AccountCustomerPortal):
    def _ticket_get_page_view_values(self, ticket, access_token, **kwargs):
        values = super()._ticket_get_page_view_values(ticket, access_token, **kwargs)
        if ticket.invoice_ids and ticket.use_credit_notes:
            moves = request.env['account.move'].search([('id', 'in', ticket.invoice_ids.ids)])
            if moves:
                if len(moves) == 1:
                    ticket_invoice_url = f'/my/invoices/{moves.id}'
                    title = _('Credit Note')
                else:
                    ticket_invoice_url = f'/my/tickets/{ticket.id}/invoices'
                    title = _('Credit Notes')
                values['ticket_link_section'].append({
                    'access_url': ticket_invoice_url,
                    'title': title,
                    'sequence': 2,
                })
        return values

    @route([
        '/my/tickets/<ticket_id>/invoices',
        '/my/tickets/<ticket_id>/invoices/page/<int:page>'
    ], type='http', auth="user", website=True)
    def portal_my_tickets_invoices(self, ticket_id=None, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        ticket = request.env['helpdesk.ticket'].search([('id', '=', ticket_id)])
        if not ticket:
            return NotFound()
        domain = [('id', 'in', ticket.invoice_ids.ids)]
        values = self._prepare_my_invoices_values(page, date_begin, date_end, sortby, filterby, domain=domain)

        # pager
        pager = portal_pager(**values['pager'])

        # content according to pager and archive selected
        invoices = values['invoices'](pager['offset'])
        request.session['my_invoices_history'] = invoices.ids[:100]

        values.update({
            'invoices': invoices,
            'pager': pager,
        })
        return request.render("account.portal_my_invoices", values)
