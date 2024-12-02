import base64
import logging

import requests
from odoo import fields, models
from odoo.exceptions import UserError
from requests import request

from .. import const

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    # fields
    code = fields.Selection(
        selection_add=[("paymob", "Paymob")], ondelete={"paymob": "set default"}
    )
    paymob_public_key = fields.Char("Public Key", required_if_provider="paymob")
    paymob_secret_key = fields.Char("Secret Key", required_if_provider="paymob")
    paymob_api_key = fields.Char("API Key", required_if_provider="paymob")
    paymob_hmac = fields.Char("HMAC")

    payment_method_ids = fields.Many2many(
        "payment.method",
        string="Payment Methods",
        help="Payment methods available for this provider based on the keys provided",
    )

    available_currency_ids = fields.Many2many(
        "res.currency",
        string="Available Currencies",
        help="Currencies supported by this provider.",
    )

    available_country_ids = fields.Many2many(
        "res.country",
        string="Available Countries",
        help="Countries supported by this provider.",
    )

    # methods
    def _compute_feature_support_fields(self):
        """Override of `payment` to enable additional features."""
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == "paymob").update(
            {
                "support_manual_capture": "full_only",
                "support_refund": "partial",
            }
        )

    def _paymob_get_api_url(self, country=None):
        """
        Returns the base URL for the payment provider based on the mode and country
        :param country: The country code
        :return: The base URL
        """

        BASE_URL = const.BASE_URL

        if not country:
            country = self.match_countries(
                self.paymob_public_key, self.paymob_secret_key
            )
        return BASE_URL.get(country)

    def validate_keys(self):
        """
        Validates the keys provided by the user.
        """

        try:
            pk_parts = self.paymob_public_key.split("_")
            sk_parts = self.paymob_secret_key.split("_")
            country_code, pk_key, pk_mode = pk_parts[:3]
            _, sk_key, sk_mode = sk_parts[:3]
        except ValueError:
            raise UserError("Please enter valid keys")

        expected_mode = "live" if self.state == "enabled" else "test"
        errors = []
        if pk_key != "pk" or pk_mode != expected_mode:
            errors.append(f"Please enter a valid {expected_mode.upper()} public key.")
        if sk_key != "sk" or sk_mode != expected_mode:
            errors.append(f"Please enter a valid {expected_mode.upper()} secret key.")
        if errors:
            raise UserError("\n".join(errors))

        country = self.match_countries(self.paymob_public_key, self.paymob_secret_key)
        url = self._paymob_get_api_url(country=country)

        auth_url = url + "api/auth/tokens"
        response = request("POST", auth_url, json={"api_key": self.paymob_api_key})
        token = response.json().get("token")
        if response.status_code == 403 or not token:
            raise UserError(
                "Sorry, We could not authenticate you. Please enter valid key."
            )

        hmac_url = url + "api/auth/hmac_secret/get_hmac"
        self.set_hmac(token, hmac_url)

        payment_integrations_url = (
            url
            + "api/ecommerce/integrations?is_plugin=true&page_size=500&is_deprecated=false&is_standalone=false&is_next=yes"
        )
        gateways_url = url + "api/ecommerce/gateways"
        self.get_integration_ids(
            token,
            {
                "integrations_url": payment_integrations_url,
                "gateways_url": gateways_url,
            },
        )
        self.update_available_currencies_and_countries()

        _logger.info("Keys validated successfully")
        _logger.info("Hmac set successfully with the value: %s", self.paymob_hmac)
        _logger.info(
            "Integration IDs retrieved with the values: %s", self.payment_method_ids
        )
        return True

    def match_countries(self, public_key, secret_key):
        """
        Matches the country code in the public and secret keys
        :param public_key: The public key
        :param secret_key: The secret key
        :return: The country code
        """
        public_key_parts = public_key.split("_")
        secret_key_parts = secret_key.split("_")

        if len(public_key_parts) < 4 or len(secret_key_parts) < 4:
            raise UserError("Invalid Key Format")

        if public_key_parts[0] not in ["egy", "omn", "are", "sau"] or secret_key_parts[
            0
        ] not in ["egy", "omn", "are", "sau"]:
            raise UserError("Invalid Country Code")

        if public_key_parts[0] != secret_key_parts[0]:
            raise UserError("Keys do not match")

        return public_key_parts[0]

    def set_hmac(self, token, url):
        """
        Sets the HMAC for the payment provider
        :param token: The token to authenticate the request
        :param url: The URL to retrieve the HMAC
        """
        response = request("GET", url, headers={"Authorization": f"Bearer {token}"})
        hmac_secret = response.json().get("hmac_secret")
        if hmac_secret:
            self.paymob_hmac = hmac_secret
            self.write({"paymob_hmac": hmac_secret})
        else:
            _logger.error("Failed to retrieve HMAC from the response")
            raise UserError("Failed to retrieve HMAC from the response")

        return True

    def get_integration_ids(self, token, url):
        """
        Retrieves integration IDs from the Paymob API.
        :param token: The token to authenticate the request
        :param url: The URL to retrieve the integrations
        """
        response = request(
            "GET", url["integrations_url"], headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code != 200:
            raise UserError("Failed to retrieve integrations")
        integrations = response.json().get("results", [])
        valid_integrations = [
            integration
            for integration in integrations
            if self.is_valid_integration(integration)
        ]

        gateways_response = request(
            "GET", url["gateways_url"], headers={"Authorization": f"Bearer {token}"}
        )
        if gateways_response.status_code != 200:
            raise UserError("Failed to retrieve gateways")
        gateways = gateways_response.json().get("result", [])

        gateway_dict = {
            gateway.get("code"): {
                "label": gateway.get("label"),
                "description": gateway.get("description"),
                "logo": gateway.get("logo"),
                "code": gateway.get("code"),
            }
            for gateway in gateways
        }

        payment_methods_details = []
        for integration in valid_integrations:
            gateway_type = integration.get("gateway_type")
            matched_gateway = gateway_dict.get(gateway_type)

            if matched_gateway:
                payment_method_details = {
                    "name": matched_gateway.get("label"),
                    "description": matched_gateway.get("description"),
                    "logo": matched_gateway.get("logo"),
                    "currency": integration.get("currency"),
                    "gateway_type": gateway_type,
                    "integration_name": integration.get("integration_name"),
                    "integration_id": integration.get("id"),
                    "is_live": integration.get("is_live"),
                    "code": matched_gateway.get("code"),
                }
                payment_methods_details.append(payment_method_details)
        self.create_payment_methods(payment_methods_details)

    def is_valid_integration(self, integration):
        """
        Checks if the integration is valid based on the live/test mode.
        :param integration: The integration object
        :return: True if the integration is valid, False otherwise
        """
        if self.state == "enabled" and integration.get("is_live"):
            return True
        elif self.state == "test" and not integration.get("is_live"):
            return True
        return False

    def create_payment_methods(self, payment_methods_details):
        """
        Creates payment methods based on the details provided.
        :param payment_methods_details: The details of the payment methods
        """
        PaymentMethod = self.env["payment.method"]
        provider = self
        payment_method_ids = []

        for method_detail in payment_methods_details:
            existing_payment_method = self.env["payment.method"].search(
                [("integration_id", "=", method_detail["integration_id"])], limit=1
            )

            if existing_payment_method:

                existing_payment_method.write(
                    {
                        "code": method_detail["code"],
                        "supported_country_ids": [(6, 0, self.get_country_ids())],
                        "supported_currency_ids": [
                            (6, 0, self.get_currency_ids(method_detail["currency"]))
                        ],
                        "support_tokenization": True,
                        "support_refund": "partial",
                    }
                )
                payment_method_ids.append(existing_payment_method.id)
                continue

            image_base64 = False
            if "logo" in method_detail:
                response = requests.get(method_detail["logo"])
                if response.status_code == 200:
                    image_base64 = base64.b64encode(response.content).decode("utf-8")

            new_payment_method = PaymentMethod.create(
                {
                    "name": method_detail["name"],
                    "code": method_detail["code"],
                    "image": image_base64,
                    "supported_currency_ids": [
                        (6, 0, self.get_currency_ids(method_detail["currency"]))
                    ],
                    "supported_country_ids": [(6, 0, self.get_country_ids())],
                    "description": method_detail["description"],
                    "integration_id": method_detail["integration_id"],
                    "support_tokenization": True,
                    "support_refund": "partial",
                }
            )
            payment_method_ids.append(new_payment_method.id)

        provider.payment_method_ids = [(6, 0, payment_method_ids)]

    def get_currency_ids(self, currency_code):
        """
        Retrieves currency IDs based on the currency code.
        :param currency_code: The currency code
        :return: The currency IDs
        """
        currency_ids = []
        currencies = self.env["res.currency"].search(
            [
                ("name", "=", currency_code),
                "|",
                ("active", "=", False),
                ("active", "=", True),
            ]
        )
        for currency in currencies:
            currency_ids.append(currency.id)
        return currency_ids

    def get_country_ids(self):
        """
        Retrieves the country record with the specified name based on predefined country codes.
        :return: The country ID
        """
        COUNTRIES_NAMES = const.COUNTRIES_NAMES

        country_code = self.match_countries(
            self.paymob_public_key, self.paymob_secret_key
        )
        country_name = COUNTRIES_NAMES.get(country_code)
        country = self.env["res.country"].search([("name", "=", country_name)], limit=1)
        if country:
            return [country.id]
        else:
            return False

    def update_available_currencies_and_countries(self):
        """
        Populate the available_currency_ids and available_country_ids fields
        based on the payment methods' currencies and countries, only for active methods.
        """
        currency_ids = set()
        country_ids = set()

        supports_all_currencies = False
        supports_all_countries = False

        for method in self.payment_method_ids:
            if not method.supported_currency_ids:
                supports_all_currencies = True
            if not method.supported_country_ids:
                supports_all_countries = True
            currency_ids.update(method.supported_currency_ids.ids)
            country_ids.update(method.supported_country_ids.ids)

        self.available_currency_ids = (
            [(6, 0, list(currency_ids))] if not supports_all_currencies else [(5, 0, 0)]
        )
        self.available_country_ids = (
            [(6, 0, list(country_ids))] if not supports_all_countries else [(5, 0, 0)]
        )
