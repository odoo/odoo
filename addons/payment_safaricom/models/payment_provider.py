# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.urls import urljoin

from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_safaricom import const

_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("safaricom", "Safaricom M-PESA")], ondelete={"safaricom": "set default"}
    )
    safaricom_consumer_key = fields.Char(
        string="Consumer Key", required_if_provider="safaricom", groups="base.group_system"
    )
    safaricom_consumer_secret = fields.Char(
        string="Consumer Secret", required_if_provider="safaricom", groups="base.group_system"
    )
    safaricom_passkey = fields.Char(
        string="Passkey", required_if_provider="safaricom", groups="base.group_system"
    )
    safaricom_shortcode = fields.Char(
        string="Shortcode",
        help="The 5 to 6-digit M-PESA shortcode assigned to the business.",
        required_if_provider="safaricom",
    )
    safaricom_till_number = fields.Char(
        string="Till Number",
        help="The 6 or 7-digit till number. Required if the Transaction Type is set to BuyGoods.",
    )
    safaricom_transaction_type = fields.Selection(
        [("CustomerPayBillOnline", "PayBill"), ("CustomerBuyGoodsOnline", "BuyGoods (Till)")],
        string="Transaction Type",
        default="CustomerPayBillOnline",
        required_if_provider="safaricom",
    )

    # OAuth fields
    safaricom_access_token = fields.Char(
        string="Safaricom M-PESA Access Token", copy=False, groups="base.group_system"
    )
    safaricom_access_token_expiry = fields.Datetime(
        string="Safaricom M-PESA Access Token Expiry", copy=False, groups="base.group_system"
    )

    # === COMPUTE METHODS === #

    def _get_supported_currencies(self):
        """Override of `payment` to return the supported currencies."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == "safaricom":
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name == const.SUPPORTED_CURRENCY
            )
        return supported_currencies

    # === CONSTRAINT METHODS === #

    @api.constrains("safaricom_transaction_type", "safaricom_till_number")
    def _check_safaricom_till_number_required(self):
        """Ensure a Till Number is provided if BuyGoods is selected."""
        for provider in self.filtered(lambda p: p.code == "safaricom"):
            if (
                provider.safaricom_transaction_type == "CustomerBuyGoodsOnline"
                and not provider.safaricom_till_number
            ):
                raise ValidationError(
                    self.env._(
                        "Safaricom M-PESA: A Till Number is required when the "
                        "transaction type is set to 'BuyGoods (Till)'."
                    )
                )

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.ensure_one()
        if self.code != "safaricom":
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === BUSINESS METHODS === #

    def _get_amount_precision(self, currency, **kwargs):
        """Override of `payment` to return the amount precision for Safaricom.

        :param recordset currency: The currency of the transaction, as a `res.currency` record.
        :return: The number of decimal places.
        :rtype: int
        """
        precision = super()._get_amount_precision(currency, **kwargs)
        if self.code != "safaricom":
            return precision

        return 0  # Safaricom only supports whole numbers

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, **kwargs):
        """Override of `payment` to build the request URL."""
        if self.code != "safaricom":
            return super()._build_request_url(endpoint, **kwargs)

        if self.is_live:
            base_url = "https://api.safaricom.co.ke"
        else:
            base_url = "https://sandbox.safaricom.co.ke"

        return urljoin(base_url, endpoint)

    def _build_request_headers(
        self, method, endpoint, payload, *, is_refresh_token_request=False, **kwargs
    ):
        """Override of `payment` to build the request headers."""
        if self.code != "safaricom":
            return super()._build_request_headers(
                method,
                endpoint,
                payload,
                is_refresh_token_request=is_refresh_token_request,
                **kwargs,
            )

        if is_refresh_token_request:  # The token request authenticates with basic auth
            return {}
        return {"Authorization": f"Bearer {self._safaricom_fetch_access_token()}"}

    def _safaricom_fetch_access_token(self):
        """Generate a new access token if it's expired, otherwise return the existing access token.

        Note: `self.ensure_one()`

        :return: A valid access token.
        :rtype: str
        :raise ValidationError: If the access token can not be fetched.
        """
        self.ensure_one()

        # Refresh slightly before the expiry to avoid sending tokens expiring in transit
        refresh_margin = timedelta(seconds=60)
        if (
            self.safaricom_access_token
            and self.safaricom_access_token_expiry - refresh_margin >= fields.Datetime.now()
        ):
            return self.safaricom_access_token

        response_content = self._send_api_request(
            "GET",
            "/oauth/v1/generate",
            params={"grant_type": "client_credentials"},
            is_refresh_token_request=True,
        )
        access_token = response_content.get("access_token")
        try:
            expiry_delay = int(response_content.get("expires_in", 0))
        except (TypeError, ValueError):
            expiry_delay = 0
        if not access_token or not expiry_delay:
            _logger.error("Safaricom returned an invalid access token response.")
            raise ValidationError(self.env._("Could not fetch the access token from Safaricom."))

        self.write({
            "safaricom_access_token": access_token,
            "safaricom_access_token_expiry": (
                fields.Datetime.now() + timedelta(seconds=expiry_delay)
            ),
        })
        return self.safaricom_access_token

    def _build_request_auth(self, *, is_refresh_token_request=False, **kwargs):
        """Override of `payment` to build the basic auth of OAuth token requests."""
        if self.code != "safaricom" or not is_refresh_token_request:
            return super()._build_request_auth(
                is_refresh_token_request=is_refresh_token_request, **kwargs
            )
        return self.safaricom_consumer_key, self.safaricom_consumer_secret

    def _safaricom_get_password(self, timestamp):
        """Generate the password for M-Pesa API requests."""
        passkey = self.safaricom_passkey
        shortcode = self.safaricom_shortcode

        password = f"{shortcode}{passkey}{timestamp}"
        return base64.b64encode(password.encode("utf-8")).decode("utf-8")
