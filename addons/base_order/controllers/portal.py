from collections import OrderedDict

from odoo import _
from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.portal.controllers.portal import pager as portal_pager

_debug = DebugLog(__name__)


class OrderPortalMixin:
    """Shared portal behavior for order-like models (sale/purchase quotes).

    Expects to be mixed in alongside a host controller that provides
    `_items_per_page`, `_prepare_portal_layout_values()`, and
    `_resolve_searchbar_option()` -- as `portal.controllers.portal.
    CustomerPortal` does. A host missing one of these fails with a runtime
    `AttributeError`, not at class-definition time.
    """

    def _order_portal_default_sortings(self):
        return {
            "date": {"label": _("Newest"), "order": "create_date desc, id desc"},
            "name": {"label": _("Name"), "order": "name asc, id asc"},
            "amount_total": {
                "label": _("Total"),
                "order": "amount_total desc, id desc",
            },
        }

    def _order_portal_home_counters(self, values, counters, model_name, counter_specs):
        Order = request.env[model_name]
        can_read = Order.has_access("read")
        for counter_key, domain in counter_specs:
            if counter_key in counters:
                values[counter_key] = Order.search_count(domain) if can_read else 0  # noqa: E8507 - one count per portal counter
                _debug.perf.count(
                    "portal_counter",
                    model=model_name,
                    key=counter_key,
                    value=values[counter_key],
                )
        return values

    def _order_portal_rendering_values(
        self,
        model_name,
        cfg,
        base_domain,
        searchbar_sortings,
        searchbar_filters,
        page=1,
        date_begin=None,
        date_end=None,
        sortby=None,
        filterby=None,
        **kwargs,
    ):
        Order = request.env[model_name]
        values = self._prepare_portal_layout_values()

        domain = list(base_domain)
        if date_begin and date_end:
            domain += [
                ("create_date", ">", date_begin),
                ("create_date", "<=", date_end),
            ]

        sortby = self._resolve_searchbar_option(searchbar_sortings, sortby, "date")
        order = searchbar_sortings[sortby]["order"]

        if searchbar_filters:
            if not filterby:
                filterby = cfg.get("default_filter")
            if filterby in searchbar_filters:
                domain += searchbar_filters[filterby]["domain"]

        can_read = Order.has_access("read")
        total = Order.search_count(domain) if can_read else 0
        pager = portal_pager(
            url=cfg["url"],
            url_args={
                "date_begin": date_begin,
                "date_end": date_end,
                "sortby": sortby,
                "filterby": filterby,
            },
            total=total,
            page=page,
            step=self._items_per_page,
        )

        orders = (
            Order.search(
                domain,
                order=order,
                limit=self._items_per_page,
                offset=pager["offset"],
            )
            if can_read
            else Order
        )

        request.session[cfg["session_key"]] = orders.ids
        _debug.pipeline(
            "portal_order_list",
            model=model_name,
            page=cfg["page_name"],
            total=total,
            shown=len(orders),
            sortby=sortby,
            filterby=filterby or "none",
            readable=can_read,
        )

        values.update(
            {
                "date": date_begin,
                cfg["values_key"]: orders,
                "page_name": cfg["page_name"],
                "pager": pager,
                "default_url": cfg["url"],
                "searchbar_sortings": searchbar_sortings,
                "sortby": sortby,
                "searchbar_filters": OrderedDict(sorted(searchbar_filters.items())),
                "filterby": filterby,
            }
        )
        return values

    def _order_portal_edi_response(self, order_sudo):
        builders = order_sudo._get_edi_builders()

        if len(builders) == 0:
            _debug.logic("edi_download_skipped", order=order_sudo, reason="no_builder")
            return None
        builder = builders[0]

        xml_content = builder._export_order(order_sudo)

        download_name = order_sudo._get_edi_filename(builder)

        http_headers = [
            ("Content-Type", "text/xml"),
            ("Content-Length", len(xml_content)),
            ("Content-Disposition", f"attachment; filename={download_name}"),
        ]
        _debug.pipeline(
            "edi_document_served",
            order=order_sudo,
            builders=len(builders),
            bytes=len(xml_content),
        )
        return request.prepare_response(xml_content, headers=http_headers)
