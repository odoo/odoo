from datetime import datetime
from operator import itemgetter

from odoo import _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.fields import Domain
from odoo.http import request, route
from odoo.tools import groupby as groupbyelem


class EventPortal(CustomerPortal):

    @route(['/my/events',
            '/my/events/page/<int:page>',
            ], type='http', auth='user', website=True)
    def portal_my_events(self, page=1, filterby=None, groupby='none', sortby='date', **kwargs):
        try:
            request.env['event.registration'].check_access('read')
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._prepare_portal_layout_values()
        domain = self._prepare_event_registrations_domain()
        Registration = request.env['event.registration']

        # Filter
        searchbar_filters = {
            'all': {'label': _("All"), 'domain': []},
            'upcoming': {'label': _("Upcoming"), 'domain': [('event_begin_date', '>=', datetime.today())]},
            'past': {'label': _("Past"), 'domain': [('event_begin_date', '<', datetime.today())]},
        }
        if not filterby:
            filterby = 'upcoming'
        domain = Domain.AND([domain, searchbar_filters[filterby]['domain']])

        # Groupby
        searchbar_groupby = {
            'none': {'label': _('None'), 'input': 'none'},
            'event_id': {'label': _('Event'), 'input': 'event_id'},
            'name': {'label': _('Attendee'), 'input': 'name'},
            'state': {'label': _('Status'), 'input': 'state'},
        }

        # Sort
        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'event_begin_date'},
            'name': {'label': _('Attendee'), 'order': 'name'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        sort_order = searchbar_sortings[sortby]['order']

        # Pager
        registration_count = Registration.search_count(domain)
        pager = portal_pager(
            url="/my/events",
            url_args={'filterby': filterby, 'groupby': groupby, 'sortby': sortby},
            total=registration_count,
            page=page,
            step=self._items_per_page
        )

        order = f'{groupby}, {sort_order}' if groupby != 'none' else sort_order
        registrations = Registration.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        # Sudo the registrations after search for template rendering (event/slot/ticket access).
        if not registrations:
            grouped_registrations = []
        elif groupby != 'none':
            grouped_registrations = [Registration.sudo().concat(g) for k, g in groupbyelem(registrations, itemgetter(groupby))]
        else:
            grouped_registrations = [registrations.sudo()]

        values.update({
            'default_url': '/my/events',
            'page_name': 'event',
            # display
            'pager': pager,
            'grouped_registrations': grouped_registrations,
            # search
            'filterby': filterby,
            'groupby': groupby,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_sortings': searchbar_sortings,
        })
        return request.render("event.portal_my_events", values)

    def _prepare_event_registrations_domain(self):
        """ Registrations booked by the current user / assigned to them are visible from portal. """
        return [('partner_id', '=', request.env.user.partner_id.id)]

    def _prepare_portal_counter_values(self, counter):
        if counter == 'event_registration_count':
            return 'event.registration', self._prepare_event_registrations_domain(), 'read'
        return super()._prepare_portal_counter_values(counter)
