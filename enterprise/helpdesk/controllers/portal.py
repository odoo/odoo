# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from operator import itemgetter

from markupsafe import Markup

from odoo import http
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.tools.translate import _
from odoo.tools import groupby as groupbyelem
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.osv.expression import AND, FALSE_DOMAIN


class CustomerPortal(portal.CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        return values

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'ticket_count' in counters:
            values['ticket_count'] = (
                request.env['helpdesk.ticket'].search_count(self._prepare_helpdesk_tickets_domain())
                if request.env['helpdesk.ticket'].has_access('read')
                else 0
            )
        return values

    def _prepare_helpdesk_tickets_domain(self):
        return []

    def _ticket_get_page_view_values(self, ticket, access_token, **kwargs):
        values = {
            'page_name': 'ticket',
            'ticket': ticket,
            'ticket_link_section': [],
            'ticket_closed': kwargs.get('ticket_closed', False),
            'preview_object': ticket,
            'res_company': ticket.company_id  # Used to display correct company logo
        }
        return self._get_page_view_values(ticket, access_token, values, 'my_tickets_history', False, **kwargs)

    def _ticket_get_searchbar_inputs(self):
        return {
            'name': {'input': 'name', 'label': _(
                'Search%(left)s Tickets%(right)s',
                left=Markup('<span class="nolabel">'),
                right=Markup('</span>'),
            ), 'sequence': 10},
            'user_id': {'input': 'user_id', 'label': _('Search in Assigned to'), 'sequence': 20},
            'partner_id': {'input': 'partner_id', 'label': _('Search in Customer'), 'sequence': 30},
            'team_id': {'input': 'team_id', 'label': _('Search in Helpdesk Team'), 'sequence': 40},
            'stage_id': {'input': 'stage_id', 'label': _('Search in Stage'), 'sequence': 50},
        }

    def _ticket_get_searchbar_groupby(self):
        return {
            'none': {'label': _('None'), 'sequence': 10},
            'user_id': {'label': _('Assigned to'), 'sequence': 20},
            'team_id': {'label': _('Helpdesk Team'), 'sequence': 30},
            'stage_id': {'label': _('Stage'), 'sequence': 40},
            'kanban_state': {'label': _('Status'), 'sequence': 50},
            'partner_id': {'label': _('Customer'), 'sequence': 60},
        }

    def _ticket_get_search_domain(self, search_in, search):
        if search_in == 'name':
            return ['|', ('name', 'ilike', search), ('ticket_ref', 'ilike', search)]
        elif search_in == 'user_id':
            assignees = request.env['res.users'].sudo()._search([('name', 'ilike', search)])
            return [('user_id', 'in', assignees)]
        elif search_in in self._ticket_get_searchbar_inputs():
            return [(search_in, 'ilike', search)]
        else:
            return ['|', ('name', 'ilike', search), ('ticket_ref', 'ilike', search)]

    def _prepare_my_tickets_values(self, page=1, date_begin=None, date_end=None, sortby=None, filterby='all', search=None, groupby='none', search_in='name'):
        values = self._prepare_portal_layout_values()
        domain = self._prepare_helpdesk_tickets_domain()

        searchbar_sortings = {
            'create_date desc': {'label': _('Newest')},
            'id desc': {'label': _('Reference')},
            'name': {'label': _('Subject')},
            'user_id': {'label': _('Assigned to')},
            'stage_id': {'label': _('Stage')},
            'date_last_stage_update desc': {'label': _('Last Stage Update')},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'assigned': {'label': _('Assigned'), 'domain': [('user_id', '!=', False)]},
            'unassigned': {'label': _('Unassigned'), 'domain': [('user_id', '=', False)]},
            'open': {'label': _('Open'), 'domain': [('close_date', '=', False)]},
            'closed': {'label': _('Closed'), 'domain': [('close_date', '!=', False)]},
        }
        searchbar_inputs = dict(sorted(self._ticket_get_searchbar_inputs().items(), key=lambda item: item[1]['sequence']))
        searchbar_groupby = dict(sorted(self._ticket_get_searchbar_groupby().items(), key=lambda item: item[1]['sequence']))

        # default sort by value
        if not sortby:
            sortby = 'create_date desc'

        domain = AND([domain, searchbar_filters[filterby]['domain']])

        if date_begin and date_end:
            domain = AND([domain, [('create_date', '>', date_begin), ('create_date', '<=', date_end)]])

        # search
        if search and search_in:
            domain = AND([domain, self._ticket_get_search_domain(search_in, search)])

        # pager
        tickets_count = request.env['helpdesk.ticket'].search_count(domain)
        pager = portal_pager(
            url="/my/tickets",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'search_in': search_in, 'search': search, 'groupby': groupby, 'filterby': filterby},
            total=tickets_count,
            page=page,
            step=self._items_per_page
        )

        order = f'{groupby}, {sortby}' if groupby != 'none' else sortby
        tickets = request.env['helpdesk.ticket'].search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_tickets_history'] = tickets.ids[:100]

        if not tickets:
            grouped_tickets = []
        elif groupby != 'none':
            grouped_tickets = [request.env['helpdesk.ticket'].concat(*g) for k, g in groupbyelem(tickets, itemgetter(groupby))]
        else:
            grouped_tickets = [tickets]

        values.update({
            'date': date_begin,
            'grouped_tickets': grouped_tickets,
            'page_name': 'ticket',
            'default_url': '/my/tickets',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'sortby': sortby,
            'groupby': groupby,
            'search_in': search_in,
            'search': search,
            'filterby': filterby,
        })
        return values

    @http.route(['/my/tickets', '/my/tickets/page/<int:page>'], type='http', auth="user", website=True)
    def my_helpdesk_tickets(self, page=1, date_begin=None, date_end=None, sortby=None, filterby='all', search=None, groupby='none', search_in='name', **kw):
        values = self._prepare_my_tickets_values(page, date_begin, date_end, sortby, filterby, search, groupby, search_in)
        return request.render("helpdesk.portal_helpdesk_ticket", values)

    @http.route([
        "/helpdesk/ticket/<int:ticket_id>",
        "/helpdesk/ticket/<int:ticket_id>/<access_token>",
        '/my/ticket/<int:ticket_id>',
        '/my/ticket/<int:ticket_id>/<access_token>'
    ], type='http', auth="public", website=True)
    def tickets_followup(self, ticket_id=None, access_token=None, **kw):
        try:
            ticket_sudo = self._document_check_access('helpdesk.ticket', ticket_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._ticket_get_page_view_values(ticket_sudo, access_token, **kw)
        return request.render("helpdesk.tickets_followup", values)

    @http.route([
        '/my/ticket/close/<int:ticket_id>',
        '/my/ticket/close/<int:ticket_id>/<access_token>',
    ], type='http', auth="public", website=True)
    def ticket_close(self, ticket_id=None, access_token=None, **kw):
        try:
            ticket_sudo = self._document_check_access('helpdesk.ticket', ticket_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if not ticket_sudo.team_id.allow_portal_ticket_closing:
            raise UserError(_("The team does not allow ticket closing through portal"))

        if not ticket_sudo.closed_by_partner and request.httprequest.method == 'GET':
            closing_stage = ticket_sudo.team_id._get_closing_stage()
            if ticket_sudo.stage_id != closing_stage:
                ticket_sudo.write({'stage_id': closing_stage[0].id, 'closed_by_partner': True})
            else:
                ticket_sudo.write({'closed_by_partner': True})
            body = _('Ticket closed by the customer')
            ticket_sudo.with_context(mail_create_nosubscribe=True).message_post(body=body, message_type='comment', subtype_xmlid='mail.mt_note')

        return request.redirect('/my/ticket/%s/%s?ticket_closed=1' % (ticket_id, access_token or ''))
