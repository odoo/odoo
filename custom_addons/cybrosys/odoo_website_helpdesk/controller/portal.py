# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Arshad Ali Pottengal (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo import http
from odoo.addons.portal.controllers import portal
from odoo.http import request


class TicketPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """
        Prepare values for the home portal, including ticket count. Args:
        counters (dict): A dictionary containing counters for various portal
        information. Returns: dict: A dictionary of values for the home portal.
        """
        values = super()._prepare_home_portal_values(counters)
        if 'ticket_count' in counters:
            ticket_count = request.env['ticket.helpdesk'].search_count(
                self._get_tickets_domain()) if request.env[
                'ticket.helpdesk'].check_access(
                'read', raise_exception=False) else 0
            values['ticket_count'] = ticket_count
        return values

    def _get_tickets_domain(self):
        """
        Define the domain for searching tickets related to the current customer.
        Returns:
            list: A list representing the domain for ticket search.
        """
        return [('customer_id', '=', request.env.user.partner_id.id)]

    @http.route(['/my/tickets'], type='http', auth="user", website=True)
    def portal_my_tickets(self):
        """
        Route to display the tickets associated with the current customer.
        Returns:
            http.Response: The HTTP response rendering the tickets page.
        """
        domain = self._get_tickets_domain()
        tickets = request.env['ticket.helpdesk'].sudo().search(domain)
        values = {
            'default_url': "/my/tickets",
            'tickets': tickets,
            'page_name': 'ticket',
        }
        return request.render("odoo_website_helpdesk.portal_my_tickets",
                              values)

    @http.route(['/my/tickets/<int:id>'], type='http', auth="public",
                website=True)
    def portal_tickets_details(self, **kwargs):
        """
        Route to display the details of a specific ticket.
        Args:
            ticket_id (int): The ID of the ticket to be displayed.
        Returns:
            http.Response: The HTTP response rendering the ticket details page.
        """
        ticket_id = kwargs.get("id")
        details = request.env['ticket.helpdesk'].sudo().browse(ticket_id)
        data = {
            'page_name': 'ticket',
            'ticket': True,
            'details': details,
        }
        return request.render("odoo_website_helpdesk.portal_ticket_details",
                              data)

    @http.route('/my/tickets/download/<id>', auth='public',
                type='http',
                website=True)
    def ticket_download_portal(self, **kwargs):
        """
        Route to download a PDF version of a specific ticket.
        Args:
            ticket (str): The ID of the ticket to be downloaded.
        Returns:
            http.Response: The HTTP response with the PDF file for download.
        """
        ticket_id = int(kwargs.get('id'))
        data = {
            'help': request.env['ticket.helpdesk'].sudo().browse(ticket_id)}
        report = request.env.ref(
            'odoo_website_helpdesk.report_ticket')
        pdf, _ = report.sudo()._render_qweb_pdf(
            report, res_ids=ticket_id, data=data)
        pdf_http_headers = [('Content-Type', 'application/pdf'),
                            ('Content-Length', len(pdf)),
                            ('Content-Disposition',
                             'attachment; filename="Helpdesk Ticket.pdf"')]
        return request.make_response(pdf, headers=pdf_http_headers)
