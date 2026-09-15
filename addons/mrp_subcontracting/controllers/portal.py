from collections import OrderedDict

import werkzeug

from odoo import _, http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager

_debug = DebugLog(__name__)


class CustomerPortal(portal.CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "production_count" in counters:
            commercial_partner = request.env.user.partner_id.commercial_partner_id
            values["production_count"] = request.env["stock.picking"].search_count(
                [
                    ("partner_id.commercial_partner_id", "=", commercial_partner.id),
                    ("move_ids.is_subcontract", "=", True),
                ]
            )
        return values

    @http.route(
        ["/my/productions", "/my/productions/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_productions(
        self, page=1, date_begin=None, date_end=None, sortby="date", filterby="all"
    ):
        commercial_partner = request.env.user.partner_id.commercial_partner_id
        StockPicking = request.env["stock.picking"]
        domain = [
            ("partner_id.commercial_partner_id", "=", commercial_partner.id),
            ("move_ids.is_subcontract", "=", True),
        ]

        if date_begin and date_end:
            domain += [
                ("create_date", ">", date_begin),
                ("create_date", "<=", date_end),
            ]

        searchbar_filters = {
            "all": {"label": _("All"), "domain": []},
            "done": {"label": _("Done"), "domain": [("state", "=", "done")]},
            "ready": {"label": _("Ready"), "domain": [("state", "=", "assigned")]},
        }
        filterby = self._resolve_searchbar_option(searchbar_filters, filterby, "all")
        domain += searchbar_filters[filterby]["domain"]

        searchbar_sortings = {
            "date": {"label": _("Newest"), "order": "create_date desc, id desc"},
            "name": {"label": _("Name"), "order": "name asc, id asc"},
        }
        sortby = self._resolve_searchbar_option(searchbar_sortings, sortby, "date")
        order = searchbar_sortings[sortby]["order"]
        count = StockPicking.search_count(domain)
        pager = portal_pager(
            url="/my/productions",
            url_args={"date_begin": date_begin, "date_end": date_end, "sortby": sortby},
            total=count,
            page=page,
            step=self._items_per_page,
        )
        pickings = StockPicking.search(
            domain, order=order, limit=self._items_per_page, offset=pager["offset"]
        )
        _debug.pipeline(
            "portal_productions_listed",
            partner=commercial_partner.id,
            filterby=filterby,
            sortby=sortby,
            total=count,
            shown=len(pickings),
        )

        values = {
            "date": date_begin,
            "pickings": pickings,
            "page_name": "production",
            "pager": pager,
            "searchbar_sortings": searchbar_sortings,
            "sortby": sortby,
            "searchbar_filters": OrderedDict(sorted(searchbar_filters.items())),
            "filterby": filterby,
            "default_url": "/my/productions",
        }

        return http.request.render("mrp_subcontracting.portal_my_productions", values)

    @http.route(
        "/my/productions/<int:picking_id>",
        type="http",
        auth="user",
        methods=["GET"],
        website=True,
    )
    def portal_my_production(self, picking_id):
        try:
            self._document_check_access("stock.picking", picking_id)
        except AccessError, MissingError:
            _debug.logic("portal_refused", route="my_production", picking=picking_id)
            raise werkzeug.exceptions.NotFound from None
        picking = request.env["stock.picking"].browse(picking_id)
        return request.render(
            "mrp_subcontracting.subcontracting_portal", {"picking": picking}
        )

    @http.route(
        "/my/productions/<int:picking_id>/subcontracting_portal",
        type="http",
        auth="user",
        methods=["GET"],
    )
    def render_production_backend_view(self, picking_id):
        try:
            picking = self._document_check_access("stock.picking", picking_id)
        except AccessError, MissingError:
            _debug.logic("portal_refused", route="backend_view", picking=picking_id)
            raise werkzeug.exceptions.NotFound from None
        session_info = request.env["ir.http"].session_info()
        production_company = picking.company_id
        session_info.update(
            action_name="mrp_subcontracting.subcontracting_portal_view_production_action",
            picking_id=picking.id,
            user_companies={
                "current_company": production_company.id,
                "allowed_companies": {
                    production_company.id: {
                        "id": production_company.id,
                        "name": production_company.name,
                    },
                },
            },
        )

        return request.render(
            "mrp_subcontracting.subcontracting_portal_embed",
            {"session_info": session_info},
        )
