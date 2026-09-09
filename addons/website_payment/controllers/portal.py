from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.tools.json import scriptsafe as json_safe
from odoo.tools.translate import LazyTranslate

from odoo.addons.account_payment_provider.controllers import (
    portal as account_payment_portal,
)
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers import portal as payment_portal

_debug = DebugLog(__name__)

_lt = LazyTranslate(__name__)


class PaymentPortal(payment_portal.PaymentPortal):
    @http.route(
        "/donation/pay",
        type="http",
        methods=["GET", "POST"],
        auth="public",
        website=True,
        sitemap=False,
        list_as_website_content=_lt("Donation Payment"),
    )
    def donation_pay(self, **kwargs):
        kwargs["is_donation"] = True
        kwargs["currency_id"] = (
            self._cast_as_int(kwargs.get("currency_id"))
            or request.env.company.currency_id.id
        )
        kwargs["amount"] = self._cast_as_float(kwargs.get("amount")) or 25.0
        kwargs["donation_options"] = kwargs.get(
            "donation_options", json_safe.dumps({"customAmount": "freeAmount"})
        )

        if request.env.user._is_public():
            kwargs["partner_id"] = request.env.user.partner_id.id
            kwargs["access_token"] = payment_utils.generate_access_token(
                kwargs["partner_id"], kwargs["amount"], kwargs["currency_id"]
            )

        return self.payment_pay(**kwargs)

    @http.route(
        "/donation/transaction/<minimum_amount>",
        type="jsonrpc",
        auth="public",
        website=True,
        sitemap=False,
    )
    def donation_transaction(
        self, amount, currency_id, partner_id, access_token, minimum_amount=0, **kwargs
    ):
        if float(amount) < float(minimum_amount):
            _debug.logic(
                "donation_refused",
                reason="below_minimum",
                amount=float(amount),
                minimum=float(minimum_amount),
            )
            raise ValidationError(
                _("Donation amount must be at least %.2f.", float(minimum_amount))
            )
        use_public_partner = request.env.user._is_public() or not partner_id
        if use_public_partner:
            details = kwargs.get("partner_details") or {}
            if not details.get("name"):
                _debug.logic("donation_refused", reason="no_name")
                raise ValidationError(_("Name is required."))
            if not details.get("email"):
                _debug.logic("donation_refused", reason="no_email")
                raise ValidationError(_("Email is required."))
            if not details.get("country_id"):
                _debug.logic("donation_refused", reason="no_country")
                raise ValidationError(_("Country is required."))
            partner_id = request.website.user_id.partner_id.id
            del kwargs["partner_details"]
        else:
            partner_id = request.env.user.partner_id.id

        self._check_transaction_kwargs(
            kwargs,
            additional_allowed_keys=(
                "donation_comment",
                "donation_recipient_email",
                "partner_details",
                "reference_prefix",
            ),
        )
        if use_public_partner:
            kwargs["custom_create_values"] = {"tokenize": False}
        tx_sudo = self._create_transaction(
            amount=amount, currency_id=currency_id, partner_id=partner_id, **kwargs
        )
        tx_sudo.is_donation = True
        if use_public_partner:
            tx_sudo.update(
                {
                    "partner_name": details["name"],
                    "partner_email": details["email"],
                    "partner_country_id": int(details["country_id"]),
                }
            )
        elif not tx_sudo.partner_country_id:
            country_id = kwargs.get("partner_details", {}).get("country_id")
            if not country_id:
                raise ValidationError(_("Country is required."))
            tx_sudo.partner_country_id = int(country_id)
        access_token = payment_utils.generate_access_token(
            tx_sudo.partner_id.id, tx_sudo.amount, tx_sudo.currency_id.id
        )
        self._update_landing_route(tx_sudo, access_token)

        recipient_email = kwargs["donation_recipient_email"]
        comment = kwargs["donation_comment"]
        tx_sudo._send_donation_email(True, comment, recipient_email)

        return tx_sudo._prepare_processing_values()

    def _prepare_extra_payment_form_context(
        self,
        donation_options=None,
        donation_descriptions=None,
        is_donation=False,
        **kwargs,
    ):
        rendering_context = super()._prepare_extra_payment_form_context(
            donation_options=donation_options,
            donation_descriptions=donation_descriptions,
            is_donation=is_donation,
            **kwargs,
        )
        if is_donation:
            user_sudo = request.env.user
            logged_in = not user_sudo._is_public()
            partner_sudo = user_sudo.partner_id
            partner_details = {}
            if logged_in:
                partner_details = {
                    "name": partner_sudo.name,
                    "email": partner_sudo.email,
                    "country_id": partner_sudo.country_id.id,
                }

            countries = request.env["res.country"].sudo().search([])
            descriptions = request.httprequest.form.getlist("donation_descriptions")

            donation_options = (
                json_safe.loads(donation_options) if donation_options else {}
            )
            donation_amounts = json_safe.loads(
                donation_options.get("donationAmounts", "[]")
            )

            rendering_context.update(
                {
                    "is_donation": True,
                    "partner": partner_sudo,
                    "submit_button_label": _("Donate"),
                    "transaction_route": "/donation/transaction/%s"
                    % donation_options.get("minimumAmount", 0),
                    "partner_details": partner_details,
                    "error": {},
                    "countries": countries,
                    "donation_options": donation_options,
                    "donation_amounts": donation_amounts,
                    "donation_descriptions": descriptions,
                }
            )
        return rendering_context

    def _get_payment_page_template_xmlid(self, **kwargs):
        if kwargs.get("is_donation"):
            return "website_payment.donation_pay"
        return super()._get_payment_page_template_xmlid(**kwargs)

    @staticmethod
    def _get_show_tokenize_input_mapping(providers_sudo, **kwargs):
        res = super(PaymentPortal, PaymentPortal)._get_show_tokenize_input_mapping(
            providers_sudo, **kwargs
        )
        if kwargs.get("is_donation") and request.env.user._is_public():
            for provider_sudo in providers_sudo:
                res[provider_sudo.id] = False
        return res

    @http.route(
        "/website_payment/snippet/supported_payment_methods",
        type="http",
        methods=["GET"],
        auth="public",
        website=True,
        sitemap=False,
        readonly=True,
    )
    def get_supported_payment_methods(self, limit=None):
        limit = self._cast_as_int(limit)
        website = request.website

        compatible_providers_sudo = (
            request.env["payment.provider"]
            .with_user(website.user_id)
            .sudo()
            ._get_compatible_providers(
                website.company_id.id, None, 0, website_id=website.id
            )
        )
        brands_domain = Domain(
            [
                ("is_primary", "=", False),
                (
                    "primary_payment_method_id.provider_ids",
                    "in",
                    compatible_providers_sudo.ids,
                ),
                ("primary_payment_method_id.active", "=", True),
            ]
        )
        primary_without_brands_domain = Domain(
            [
                ("is_primary", "=", True),
                ("brand_ids", "=", False),
                ("provider_ids", "in", compatible_providers_sudo.ids),
            ]
        )

        supported_pms = (
            request.env["payment.method"]
            .search(
                Domain.OR([brands_domain, primary_without_brands_domain]),
                limit=limit,
            )
            .mapped(
                lambda pm: {
                    "name": pm.name,
                    "image_url": request.env["website"].image_url(pm, "image"),
                }
            )
        )

        if request.env.user._is_internal():
            cache_control = "no-cache"
        else:
            cache_control = "public, max-age=604800, stale-while-revalidate=86400"

        return request.prepare_json_response(
            supported_pms,
            headers=[("Cache-Control", cache_control)],
        )


class PortalAccount(account_payment_portal.PortalAccount):
    def _invoice_get_page_view_values(self, *args, **kwargs):
        return super()._invoice_get_page_view_values(
            *args, website_id=request.website.id, **kwargs
        )
