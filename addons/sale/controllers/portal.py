import binascii

from odoo import SUPERUSER_ID, _, fields, http
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.fields import Command
from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.base_order.controllers.portal import OrderPortalMixin
from odoo.addons.payment.controllers import portal as payment_portal

_debug = DebugLog(__name__)


class CustomerPortal(payment_portal.PaymentPortal, OrderPortalMixin):
    def _sale_get_order_model(self):
        return "sale.order"

    def _sale_get_portal_counters(self):
        return [
            ("quotation_count", self._sale_get_page_state_domain("quote")),
            ("order_count", self._sale_get_page_state_domain("order")),
        ]

    def _sale_get_page_config(self, page_key):
        if page_key == "quote":
            return {
                "url": "/my/quotes",
                "template": "sale.portal_my_quotations",
                "session_key": "my_quotations_history",
                "page_name": "quote",
                "values_key": "quotations",
            }
        return {
            "url": "/my/orders",
            "template": "sale.portal_my_orders",
            "session_key": "my_orders_history",
            "page_name": "order",
            "values_key": "orders",
            "default_filter": "all",
        }

    def _sale_get_page_state_domain(self, page_key):
        if page_key == "quote":
            return [("state", "=", "draft"), ("sent", "=", True)]
        return [("state", "in", ("done", "cancel"))]

    def _sale_get_order_searchbar_sortings(self):
        return self._order_portal_default_sortings()

    def _sale_get_order_searchbar_filters(self, page_key):
        if page_key != "order":
            return {}
        return {
            "all": {
                "label": _("All"),
                "domain": [("state", "in", ("done", "cancel"))],
            },
            "order": {
                "label": _("Sales Order"),
                "domain": [("state", "=", "done")],
            },
            "cancel": {
                "label": _("Cancelled"),
                "domain": [("state", "=", "cancel")],
            },
        }

    def _sale_get_detail_history_session_key(self, order):
        if order.state in ("draft", "cancel"):
            return "my_quotations_history"
        return "my_orders_history"

    def _sale_prepare_orders_domain(self, partner, page_key):
        return list(self._sale_get_page_state_domain(page_key))

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        return self._order_portal_home_counters(
            values,
            counters,
            self._sale_get_order_model(),
            self._sale_get_portal_counters(),
        )

    def _sale_prepare_order_portal_rendering_values(self, page_key, **kwargs):
        partner = request.env.user.partner_id
        return self._order_portal_rendering_values(
            model_name=self._sale_get_order_model(),
            cfg=self._sale_get_page_config(page_key),
            base_domain=self._sale_prepare_orders_domain(partner, page_key),
            searchbar_sortings=self._sale_get_order_searchbar_sortings(),
            searchbar_filters=self._sale_get_order_searchbar_filters(page_key),
            **kwargs,
        )

    @http.route(
        ["/my/quotes", "/my/quotes/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_quotes(self, **kw):
        values = self._sale_prepare_order_portal_rendering_values("quote", **kw)
        _debug.pipeline("portal_list", page="quote", orders=values.get("quotations"))
        return request.render("sale.portal_my_quotations", values)

    @http.route(
        ["/my/orders", "/my/orders/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_orders(self, **kw):
        values = self._sale_prepare_order_portal_rendering_values("order", **kw)
        _debug.pipeline("portal_list", page="order", orders=values.get("orders"))
        return request.render("sale.portal_my_orders", values)

    def _sale_order_get_page_view_values(
        self, order_sudo, access_token, values, history_session_key, /, **kwargs
    ):
        return self._get_page_view_values(
            order_sudo, access_token, values, history_session_key, False, **kwargs
        )

    @http.route(
        ["/my/orders/<int:order_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_my_order(
        self,
        order_id,
        report_type=None,
        access_token=None,
        message=False,
        download=False,
        payment_amount=None,
        amount_selection=None,
        **kw,
    ):
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except AccessError, MissingError:
            _debug.logic("portal_access_denied", route="order_page", order=order_id)
            return request.redirect("/my")

        payment_amount = self._cast_as_float(payment_amount)
        prepayment_amount = order_sudo._get_prepayment_required_amount()
        if (
            payment_amount
            and payment_amount < prepayment_amount
            and order_sudo.state != "done"
        ):
            _debug.logic(
                "portal_payment_amount_refused",
                order=order_sudo,
                requested=payment_amount,
                prepayment=prepayment_amount,
            )
            raise MissingError(_("The amount is lower than the prepayment amount."))

        if report_type in ("html", "pdf", "text"):
            _debug.pipeline("portal_report", order=order_sudo, kind=report_type)
            return self._show_report(
                model=order_sudo,
                report_type=report_type,
                report_ref="sale.action_report_saleorder",
                download=download,
            )

        is_link_preview = request.httprequest.headers.get("Odoo-Link-Preview")
        if (
            order_sudo.state == "draft"
            and request.env.user.share
            and access_token
            and is_link_preview != "True"
        ):
            today = fields.Date.today().isoformat()
            session_obj_date = request.session.get("view_quote_%s" % order_sudo.id)
            if session_obj_date != today:
                request.session["view_quote_%s" % order_sudo.id] = today
                lang = (
                    order_sudo.user_id.partner_id.lang
                    or order_sudo.company_id.partner_id.lang
                )
                author = (
                    order_sudo.partner_id
                    if request.env.user._is_public()
                    else request.env.user.partner_id
                )
                msg = (
                    request.env["sale.order"]
                    .with_context(lang=lang)
                    .env._("Quotation viewed by customer %s", author.name)
                )
                _debug.lifecycle(
                    "quotation_viewed_by_customer", order=order_sudo, author=author
                )
                order_sudo.with_user(SUPERUSER_ID).message_post(
                    body=msg,
                    message_type="notification",
                    subtype_xmlid="sale.mt_order_viewed",
                )

        backend_url = (
            f"/odoo/action-{order_sudo._get_portal_return_action().id}/{order_sudo.id}"
        )
        values = {
            "sale_order": order_sudo,
            "product_documents": order_sudo._get_product_documents(),
            "message": message,
            "report_type": "html",
            "backend_url": backend_url,
            "res_company": order_sudo.company_id,
            "payment_amount": payment_amount,
        }

        _debug.logic("portal_order_page", order=order_sudo, state=order_sudo.state)
        if order_sudo._has_to_be_paid() or (
            payment_amount and not order_sudo.is_expired
        ):
            values.update(
                self._prepare_payment_form_context(
                    order_sudo,
                    is_down_payment=self._is_down_payment(
                        order_sudo, amount_selection, payment_amount
                    ),
                    payment_amount=payment_amount,
                )
            )
        else:
            values["payment_amount"] = None

        values = self._sale_order_get_page_view_values(
            order_sudo,
            access_token,
            values,
            self._sale_get_detail_history_session_key(order_sudo),
            **kw,
        )

        return request.render("sale.sale_order_portal_template", values)

    def _is_down_payment(self, order_sudo, amount_selection, payment_amount):
        if amount_selection == "down_payment":
            is_down_payment = True
        elif amount_selection == "full_amount":
            is_down_payment = False
        else:
            is_down_payment = (
                order_sudo.prepayment_percent < 1.0
                if payment_amount is None
                else payment_amount < order_sudo.amount_total
            )
        _debug.logic(
            "down_payment_decision",
            order=order_sudo,
            down_payment=is_down_payment,
            selection=amount_selection or "implicit",
        )
        return is_down_payment

    def _prepare_payment_form_context(
        self, order_sudo, is_down_payment=False, payment_amount=None, **kwargs
    ):
        company = order_sudo.company_id
        logged_in = not request.env.user._is_public()
        partner_sudo = (
            request.env.user.partner_id if logged_in else order_sudo.partner_invoice_id
        )
        currency = order_sudo.currency_id

        if is_down_payment:
            if payment_amount and payment_amount < order_sudo.amount_total:
                amount = payment_amount
            else:
                amount = order_sudo._get_prepayment_required_amount()
        elif order_sudo.state == "done":
            amount = payment_amount or order_sudo.amount_total
        else:
            amount = order_sudo.amount_total

        availability_report = {}
        with _debug.perf(
            "payment_options", cr=request.env.cr, order=order_sudo
        ) as span:
            providers_sudo = (
                request.env["payment.provider"]
                .sudo()
                ._get_compatible_providers(
                    company.id,
                    partner_sudo.id,
                    amount,
                    currency_id=currency.id,
                    sale_order_id=order_sudo.id,
                    report=availability_report,
                    **kwargs,
                )
            )
            payment_methods_sudo = (
                request.env["payment.method"]
                .sudo()
                ._get_compatible_payment_methods(
                    providers_sudo.ids,
                    partner_sudo.id,
                    currency_id=currency.id,
                    sale_order_id=order_sudo.id,
                    report=availability_report,
                    **kwargs,
                )
            )
            tokens_sudo = (
                request.env["payment.token"]
                .sudo()
                ._get_available_tokens(providers_sudo.ids, partner_sudo.id, **kwargs)
            )
            span.set(amount=amount, providers=providers_sudo, tokens=tokens_sudo)

        company_mismatch = not payment_portal.PaymentPortal._can_partner_pay_in_company(
            partner_sudo, company
        )

        portal_page_values = {
            "company_mismatch": company_mismatch,
            "expected_company": company,
            "payment_amount": payment_amount,
        }
        payment_form_values = {
            "show_tokenize_input_mapping": payment_portal.PaymentPortal._get_show_tokenize_input_mapping(
                providers_sudo, sale_order_id=order_sudo.id
            ),
        }
        payment_context = {
            "amount": amount,
            "currency": currency,
            "partner_id": partner_sudo.id,
            "providers_sudo": providers_sudo,
            "payment_methods_sudo": payment_methods_sudo,
            "tokens_sudo": tokens_sudo,
            "availability_report": availability_report,
            "transaction_route": order_sudo.get_portal_url(suffix="/transaction"),
            "landing_route": order_sudo.get_portal_url(),
            "access_token": order_sudo._portal_get_or_create_token(),
        }
        return {
            **portal_page_values,
            **payment_form_values,
            **payment_context,
            **self._prepare_extra_payment_form_context(**kwargs),
        }

    @http.route(
        ["/my/orders/<int:order_id>/accept"],
        type="jsonrpc",
        auth="public",
        website=True,
    )
    def portal_my_order_accept(
        self, order_id, access_token=None, name=None, signature=None
    ):
        access_token = access_token or request.httprequest.args.get("access_token")
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except AccessError, MissingError:
            _debug.logic("portal_access_denied", route="accept", order=order_id)
            return {"error": _("Invalid order.")}

        if not order_sudo._has_to_be_signed():
            _debug.logic(
                "portal_sign_refused", order=order_sudo, reason="not_awaiting_signature"
            )
            return {
                "error": _("The order is not in a state requiring customer signature.")
            }
        if not signature:
            _debug.logic(
                "portal_sign_refused", order=order_sudo, reason="missing_signature"
            )
            return {"error": _("Signature is missing.")}

        try:
            order_sudo.write(
                {
                    "signed_by": name,
                    "signed_on": fields.Datetime.now(),
                    "signature": signature,
                }
            )
            request.env.cr.flush()
        except TypeError, binascii.Error:
            _debug.logic(
                "portal_sign_refused", order=order_sudo, reason="undecodable_signature"
            )
            return {"error": _("Invalid signature data.")}

        _debug.lifecycle("portal_order_signed", order=order_sudo, signed_by=bool(name))
        if not order_sudo._has_to_be_paid():
            _debug.pipeline("portal_confirm_after_sign", order=order_sudo)
            order_sudo.with_context(sale_include_signature=True)._confirm_order()

        pdf = (
            request.env["ir.actions.report"]
            .sudo()
            .with_context(sale_include_signature=True)
            ._render_qweb_pdf("sale.action_report_saleorder", [order_sudo.id])[0]
        )

        order_sudo.message_post(
            attachments=[("%s.pdf" % order_sudo.name, pdf)],
            author_id=(
                order_sudo.partner_id.id
                if request.env.user._is_public()
                else request.env.user.partner_id.id
            ),
            body=_("Order signed by %s", name),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )

        query_string = "&message=sign_ok"
        if order_sudo._has_to_be_paid():
            query_string += "&allow_payment=yes"
        return {
            "force_refresh": True,
            "redirect_url": order_sudo.get_portal_url(query_string=query_string),
        }

    @http.route(
        ["/my/orders/<int:order_id>/decline"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def portal_my_order_decline(
        self, order_id, access_token=None, decline_message=None, **kw
    ):
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except AccessError, MissingError:
            _debug.logic("portal_access_denied", route="decline", order=order_id)
            return request.redirect("/my")

        if order_sudo._has_to_be_signed() and decline_message:
            _debug.lifecycle("portal_order_declined", order=order_sudo)
            order_sudo._action_cancel()
            order_sudo.line_ids.currency_id  # noqa: B018 (intentional: primes the currency cache)

            order_sudo.message_post(
                author_id=(
                    order_sudo.partner_id.id
                    if request.env.user._is_public()
                    else request.env.user.partner_id.id
                ),
                body=decline_message,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
            redirect_url = order_sudo.get_portal_url()
        else:
            _debug.logic(
                "portal_decline_refused",
                order=order_sudo,
                has_message=bool(decline_message),
            )
            redirect_url = order_sudo.get_portal_url(
                query_string="&message=cant_reject"
            )

        return request.redirect(redirect_url)

    @http.route(
        "/my/orders/<int:order_id>/document/<int:document_id>",
        type="http",
        auth="public",
        readonly=True,
    )
    def portal_my_order_document(self, order_id, document_id, access_token):
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except AccessError, MissingError:
            _debug.logic("portal_access_denied", route="document", order=order_id)
            return request.redirect("/my")

        document = request.env["document.document"].browse(document_id).sudo().exists()
        if not document or not document.active:
            _debug.logic(
                "portal_document_refused",
                order=order_sudo,
                reason="missing_or_archived",
            )
            return request.redirect("/my")

        if document not in order_sudo._get_product_documents():
            _debug.logic(
                "portal_document_refused", order=order_sudo, reason="not_on_order"
            )
            return request.redirect("/my")

        _debug.pipeline("portal_document_served", order=order_sudo, document=document)

        return (
            request.env["ir.binary"]
            ._get_stream_from_record(
                document.attachment_id,
            )
            .prepare_response(as_attachment=True)
        )

    @http.route(
        ["/my/orders/<int:order_id>/download_edi"],
        auth="public",
        website=True,
    )
    def portal_my_order_download_edi(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except AccessError, MissingError:
            _debug.logic("portal_access_denied", route="download_edi", order=order_id)
            return request.redirect("/my")

        _debug.pipeline("portal_edi_download", order=order_sudo)
        return self._order_portal_edi_response(order_sudo) or request.redirect("/my")

    @http.route(
        ["/my/orders/<int:order_id>/update_line_dict"],
        type="jsonrpc",
        auth="public",
        website=True,
    )
    def portal_quote_option_update(
        self,
        order_id,
        line_id,
        access_token=None,
        remove=False,
        input_quantity=False,
        **kwargs,
    ):
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except AccessError, MissingError:
            _debug.logic("portal_access_denied", route="update_line", order=order_id)
            return request.redirect("/my")

        if not order_sudo._can_be_edited_on_portal():
            _debug.logic(
                "portal_line_update_refused", order=order_sudo, reason="order_readonly"
            )
            return None

        order_line = request.env["sale.order.line"].sudo().browse(int(line_id)).exists()
        if (
            not order_line
            or order_line.order_id != order_sudo
            or not order_line._can_be_edited_on_portal()
        ):
            _debug.logic(
                "portal_line_update_refused", order=order_sudo, reason="line_readonly"
            )
            return None

        if input_quantity is not False:
            quantity = max(input_quantity, 0)
        else:
            number = -1 if remove else 1
            quantity = max((order_line.product_qty + number), 0)

        if order_line.product_type == "combo":
            combo_item_lines = order_line._get_lines_linked().filtered("combo_item_id")
            combo_item_lines.update({"product_qty": quantity})

        _debug.lifecycle(
            "portal_line_quantity_set",
            order=order_sudo,
            line=order_line,
            quantity=quantity,
        )
        order_line.product_qty = quantity
        return None


class PaymentPortal(payment_portal.PaymentPortal):
    @http.route(
        "/my/orders/<int:order_id>/transaction",
        type="jsonrpc",
        auth="public",
    )
    def portal_order_transaction(self, order_id, access_token, **kwargs):
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token
            )
        except MissingError:
            raise
        except AccessError:
            _debug.logic("portal_access_denied", route="transaction", order=order_id)
            raise ValidationError(_("The access token is invalid.")) from None

        logged_in = not request.env.user._is_public()
        partner_sudo = (
            request.env.user.partner_id if logged_in else order_sudo.partner_invoice_id
        )
        self._check_transaction_kwargs(kwargs)
        kwargs.update(
            {
                "partner_id": partner_sudo.id,
                "currency_id": order_sudo.currency_id.id,
                "sale_order_id": order_id,
            }
        )
        tx_sudo = self._create_transaction(
            custom_create_values={"sale_order_ids": [Command.set([order_id])]},
            **kwargs,
        )
        _debug.lifecycle(
            "portal_transaction_created", order=order_sudo, transaction=tx_sudo
        )

        return tx_sudo._prepare_processing_values()
