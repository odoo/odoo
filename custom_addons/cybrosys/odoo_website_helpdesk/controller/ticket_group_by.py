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
from odoo.http import request


class TicketGroupBy(http.Controller):
    """Controller for handling ticket grouping based on different criteria."""

    @http.route(['/ticketgroupby'], type='jsonrpc', auth="public", website=True)
    def ticket_group_by(self, **kwargs):
        """grouping tickets based on user-defined criteria.
        Args:
        - kwargs (dict): Keyword arguments received from the HTTP request.
        Returns:
        - http.Response: Rendered HTTP response containing grouped ticket information.
        """
        context = []
        group_value = kwargs.get("search_value")
        if group_value == '0':
            context = []
            tickets = request.env["ticket.helpdesk"].search(
                [('user_id', '=', request.env.user.id)])
            if tickets:
                context.append({
                    'name': '',
                    'data': tickets
                })
        if group_value == '1':
            context = []
            stage_ids = request.env['ticket.stage'].search([])
            for stage in stage_ids:
                ticket_ids = request.env['ticket.helpdesk'].search([
                    ('stage_id', '=', stage.id),
                    ('user_id', '=', request.env.user.id)
                ])
                if ticket_ids:
                    context.append({
                        'name': stage.name,
                        'data': ticket_ids
                    })
        if group_value == '2':
            context = []
            type_ids = request.env['helpdesk.type'].search([])
            for types in type_ids:
                ticket_ids_1 = request.env['ticket.helpdesk'].search([
                    ('ticket_type_id', '=', types.id),
                    ('user_id', '=', request.env.user.id)
                ])
                if ticket_ids_1:
                    context.append({
                        'name': types.name,
                        'data': ticket_ids_1
                    })
        values = {
            'tickets': context,
        }
        response = http.Response(
            template='odoo_website_helpdesk.ticket_group_by_table',
            qcontext=values)
        return response.render()
