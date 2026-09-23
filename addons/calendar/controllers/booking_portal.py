from datetime import datetime
from operator import itemgetter

from odoo import http
from odoo.fields import Domain
from odoo.http import request
from odoo.tools import groupby as groupbyelem

from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager


class AppointmentPortal(portal.CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)

        if "appointment_count" in counters:
            domain = self._get_domain_portal_default()
            values["appointment_count"] = request.env["calendar.event"].search_count(
                domain
            )

        return values

    def _get_domain_portal_default(self):
        my_user = request.env.user
        return [
            ("user_id", "!=", my_user.id),
            ("partner_ids", "in", my_user.partner_id.ids),
            ("appointment_type_id", "!=", False),
        ]

    def _get_domain_appointment_search(self, search_in, search):
        search_domains = []
        if search_in in ("all", "name"):
            search_domains.append([("name", "ilike", search)])
        if search_in in ("all", "responsible"):
            search_domains.append([("user_id", "ilike", search)])
        if search_in in ("all", "description"):
            search_domains.append([("description", "ilike", search)])
        return Domain.OR(search_domains) if search_domains else Domain.TRUE

    def _appointment_get_groupby_mapping(self):
        return {
            "responsible": "user_id",
        }

    @http.route(
        [
            "/my/appointments",
            "/my/appointments/page/<int:page>",
        ],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_appointments(
        self,
        page=1,
        sortby=None,
        filterby=None,
        search=None,
        search_in="all",
        groupby="none",
        **kwargs,
    ):
        values = self._prepare_portal_layout_values()
        # Sudo to access the appointment name and responsible for the groupby
        Event = request.env["calendar.event"].sudo()

        domain = self._get_domain_portal_default()

        searchbar_sortings = {
            "date": {"label": request.env._("Date"), "order": "start"},
            "name": {"label": request.env._("Name"), "order": "name"},
        }

        searchbar_inputs = {
            "all": {"label": request.env._("Search in All"), "input": "all"},
            "name": {"label": request.env._("Search in Name"), "input": "name"},
            "responsible": {
                "label": request.env._("Search in Responsible"),
                "input": "responsible",
            },
            "description": {
                "label": request.env._("Search in Description"),
                "input": "description",
            },
        }

        searchbar_groupby = {
            "none": {"label": request.env._("None"), "input": "none"},
            "responsible": {
                "label": request.env._("Responsible"),
                "input": "responsible",
            },
        }

        searchbar_filters = {
            "upcoming": {
                "label": request.env._("Upcoming"),
                "domain": [("start", ">=", datetime.today())],
            },
            "past": {
                "label": request.env._("Past"),
                "domain": [("start", "<", datetime.today())],
            },
            "all": {"label": request.env._("All"), "domain": []},
        }

        # Clamp to the declared vocabulary: `sortby` comes straight off the query
        # string, and indexing it unchecked answered `?sortby=anything-else` with
        # a KeyError (HTTP 500). `groupby` below already degrades via
        # `groupby_mapping.get(groupby, None)`.
        sortby = self._resolve_searchbar_option(searchbar_sortings, sortby, "date")
        sort_order = searchbar_sortings[sortby]["order"]
        groupby_mapping = self._appointment_get_groupby_mapping()
        groupby_field = groupby_mapping.get(groupby, None)
        if groupby_field is not None and groupby_field not in Event._fields:
            raise ValueError(
                f"The field {groupby_field!r} does not exist in the targeted model"
            )
        order = "%s, %s" % (groupby_field, sort_order) if groupby_field else sort_order

        filterby = self._resolve_searchbar_option(searchbar_filters, filterby, "all")
        domain = Domain.AND([domain, searchbar_filters[filterby]["domain"]])

        if (
            search
            and search_in
            and (
                search_domain := self._get_domain_appointment_search(search_in, search)
            )
        ):
            domain = Domain.AND([domain, search_domain])

        appointment_count = Event.search_count(domain)
        pager = portal_pager(
            url="/my/appointments",
            url_args={
                "sortby": sortby,
                "search_in": search_in,
                "search": search,
                "groupby": groupby,
                "filterby": filterby,
            },
            total=appointment_count,
            page=page,
            step=self._items_per_page,
        )
        appointments = Event.search(
            domain, order=order, limit=self._items_per_page, offset=pager["offset"]
        )

        grouped_appointments = False
        # If not False, this will contain a list of tuples (record of groupby, recordset of events):
        # [(res.users(2), calendar.event(1, 2)), (...), ...]
        if groupby_field:
            grouped_appointments = [
                (g, Event.concat(*events))
                for g, events in groupbyelem(appointments, itemgetter(groupby_field))
            ]

        values.update(
            {
                "appointments": appointments,
                "grouped_appointments": grouped_appointments,
                "page_name": "appointment",
                "pager": pager,
                "default_url": "/my/appointments",
                "searchbar_sortings": searchbar_sortings,
                "search_in": search_in,
                "search": search,
                "sortby": sortby,
                "groupby": groupby,
                "filterby": filterby,
                "searchbar_inputs": searchbar_inputs,
                "searchbar_groupby": searchbar_groupby,
                "searchbar_filters": searchbar_filters,
            }
        )
        return request.render("calendar.portal_my_appointments", values)
