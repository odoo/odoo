import base64
from datetime import datetime

from odoo import fields, http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.tools.image import image_process

from odoo.addons.base_order.controllers.portal import OrderPortalMixin
from odoo.addons.portal.controllers import portal


class CustomerPortal(portal.CustomerPortal, OrderPortalMixin):
    def _purchase_get_order_model(self):
        return "purchase.order"

    def _purchase_get_portal_counters(self):
        return [
            ("rfq_count", self._purchase_get_page_state_domain("rfq")),
            ("purchase_count", [("state", "in", ("done", "cancel"))]),
        ]

    def _purchase_get_page_config(self, page_key):
        if page_key == "rfq":
            return {
                "url": "/my/rfq",
                "template": "purchase.portal_my_purchase_rfqs",
                "session_key": "my_rfqs_history",
                "page_name": "rfq",
                "values_key": "rfqs",
            }
        return {
            "url": "/my/purchase",
            "template": "purchase.portal_my_purchase_orders",
            "session_key": "my_purchases_history",
            "page_name": "purchase",
            "values_key": "orders",
            "default_filter": "all",
        }

    def _purchase_get_page_state_domain(self, page_key):
        if page_key == "rfq":
            return [("state", "=", "draft")]
        return []

    def _purchase_get_order_searchbar_sortings(self):
        return self._order_portal_default_sortings()

    def _purchase_get_order_searchbar_filters(self, page_key):
        if page_key != "purchase":
            return {}
        return {
            "all": {
                "label": request.env._("All"),
                "domain": [("state", "in", ("done", "cancel"))],
            },
            "purchase": {
                "label": request.env._("Purchase Order"),
                "domain": [("state", "=", "done")],
            },
            "cancel": {
                "label": request.env._("Cancelled"),
                "domain": [("state", "=", "cancel")],
            },
        }

    def _purchase_get_detail_history_session_key(self, order):
        if order.state == "draft":
            return "my_rfqs_history"
        return "my_purchases_history"

    @staticmethod
    def _purchase_detail_report_ref(order_sudo):
        if order_sudo.state == "draft":
            return "purchase.report_purchase_quotation"
        return "purchase.action_report_purchase_order"

    def _purchase_prepare_orders_domain(self, partner, page_key):
        return list(self._purchase_get_page_state_domain(page_key))

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        return self._order_portal_home_counters(
            values,
            counters,
            self._purchase_get_order_model(),
            self._purchase_get_portal_counters(),
        )

    def _purchase_prepare_order_portal_rendering_values(self, page_key, **kwargs):
        partner = request.env.user.partner_id
        return self._order_portal_rendering_values(
            model_name=self._purchase_get_order_model(),
            cfg=self._purchase_get_page_config(page_key),
            base_domain=self._purchase_prepare_orders_domain(partner, page_key),
            searchbar_sortings=self._purchase_get_order_searchbar_sortings(),
            searchbar_filters=self._purchase_get_order_searchbar_filters(page_key),
            **kwargs,
        )

    def _purchase_resize_to_48(self, source):
        if not source:
            source = request.env["ir.binary"]._get_placeholder_bytes()
        else:
            source = base64.b64decode(source)
        return base64.b64encode(image_process(source, size=(48, 48)))

    def _purchase_prepare_order_page_view_values(self, order, access_token, **kwargs):
        values = {
            "order": order,
            "resize_to_48": self._purchase_resize_to_48,
            "report_type": "html",
        }
        return self._get_page_view_values(
            order,
            access_token,
            values,
            self._purchase_get_detail_history_session_key(order),
            False,
            **kwargs,
        )

    @http.route(
        ["/my/rfq", "/my/rfq/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_purchase_rfqs(self, **kw):
        values = self._purchase_prepare_order_portal_rendering_values("rfq", **kw)
        return request.render("purchase.portal_my_purchase_rfqs", values)

    @http.route(
        ["/my/purchase", "/my/purchase/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_purchase_orders(self, **kw):
        values = self._purchase_prepare_order_portal_rendering_values("purchase", **kw)
        return request.render("purchase.portal_my_purchase_orders", values)

    @http.route(
        ["/my/purchase/<int:order_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_my_purchase_order(
        self, order_id=None, access_token=None, message=False, **kw
    ):
        try:
            order_sudo = self._document_check_access(
                "purchase.order", order_id, access_token=access_token
            )
        except AccessError, MissingError:
            return request.redirect("/my")

        report_type = kw.get("report_type")
        if report_type in ("html", "pdf", "text"):
            return self._show_report(
                model=order_sudo,
                report_type=report_type,
                report_ref=self._purchase_detail_report_ref(order_sudo),
                download=kw.get("download"),
            )

        if kw.get("acknowledge"):
            order_sudo.action_acknowledge()
            return request.redirect(
                order_sudo.get_portal_url(query_string="&message=ack_ok")
            )

        values = self._purchase_prepare_order_page_view_values(
            order_sudo, access_token, **kw
        )
        values["message"] = message
        if order_sudo.company_id:
            values["res_company"] = order_sudo.company_id

        if kw.get("update") == "True":
            return request.render(
                "purchase.portal_my_purchase_order_update_date", values
            )
        return request.render("purchase.portal_my_purchase_order", values)

    @http.route(
        ["/my/purchase/<int:order_id>/update"],
        type="jsonrpc",
        auth="public",
        website=True,
    )
    def portal_my_purchase_order_update_dates(
        self, order_id=None, access_token=None, **kw
    ):
        try:
            order_sudo = self._document_check_access(
                "purchase.order", order_id, access_token=access_token
            )
        except AccessError, MissingError:
            return {
                "success": False,
                "error": request.env._(
                    "You are not allowed to update this purchase order."
                ),
            }

        if not order_sudo._is_date_commitment_updatable():
            return {
                "success": False,
                "error": request.env._("This purchase order can no longer be updated."),
            }

        today = fields.Date.context_today(order_sudo)
        updated_dates = []
        for id_str, date_str in kw.items():
            try:
                line_id = int(id_str)
            except TypeError, ValueError:
                return {"success": False, "error": request.env._("Invalid order line.")}
            line = order_sudo.line_ids.filtered_domain([("id", "=", line_id)])
            if not line:
                return {"success": False, "error": request.env._("Invalid order line.")}

            try:
                parsed = datetime.strptime(date_str, "%Y-%m-%d")
            except TypeError, ValueError:
                return {"success": False, "error": request.env._("Invalid date.")}
            if parsed.date() < today:
                return {
                    "success": False,
                    "error": request.env._(
                        "The expected arrival date cannot be in the past."
                    ),
                }

            updated_dates.append((line, line._convert_to_middle_of_day(parsed)))

        if updated_dates:
            order_sudo._update_order_lines_date_commitment(updated_dates)
        return {"success": True}

    @http.route(
        ["/my/purchase/<int:order_id>/download_edi"],
        auth="public",
        website=True,
    )
    def portal_my_purchase_order_download_edi(
        self, order_id=None, access_token=None, **kw
    ):
        try:
            order_sudo = self._document_check_access(
                "purchase.order", order_id, access_token=access_token
            )
        except AccessError, MissingError:
            return request.redirect("/my")

        return self._order_portal_edi_response(order_sudo) or request.redirect("/my")
