# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
import pprint
import re
from urllib.parse import parse_qs, quote_plus

import requests

from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo.release import major_version
from odoo.tools import hmac

_logger = logging.getLogger(__name__)

UNPREDICTABLE_ADYEN_DATA = object()  # sentinel


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [
            ("adyen", "Adyen"),
        ]

    # Adyen
    ADYEN_REGION_SELECTION = [
        ("eu", "Europe"),
        ("au", "Australia"),
        ("apse", "South East Asia"),
        ("us", "United States"),
    ]
    APPLICATION_INFO_PARAMS = [
        ("applicationInfo.externalPlatform.name", "Odoo"),
        ("applicationInfo.externalPlatform.version", major_version),
        ("applicationInfo.externalPlatform.integrator", "Odoo"),
        ("applicationInfo.merchantApplication.name", "Odoo POS"),
    ]

    adyen_api_key = fields.Char(
        string="Adyen API key",
        help="Used when connecting to Adyen: https://docs.adyen.com/user-management/how-to-get-the-api-key/#description",
        copy=False,
        groups="base.group_erp_manager",
    )
    adyen_terminal_identifier = fields.Char(
        help="[Terminal model]-[Serial number], for example: P400Plus-123456789",
        copy=False,
    )
    adyen_test_mode = fields.Boolean(
        help="Run transactions in the test environment.",
        groups="base.group_erp_manager",
    )
    adyen_region = fields.Selection(
        selection=ADYEN_REGION_SELECTION,
        string="Adyen Region",
        default="eu",
        help="Select the region for Adyen Terminal API endpoints.",
    )
    adyen_api_url_prefix = fields.Char(
        string="API URL Prefix",
        help="The base URL for the API endpoints",
        copy=False,
    )

    adyen_latest_response = fields.Char(
        copy=False,
        groups="base.group_erp_manager",
    )  # used to buffer the latest asynchronous notification from Adyen.
    adyen_event_url = fields.Char(
        string="Event URL",
        help="This URL needs to be pasted on Adyen's portal terminal settings.",
        readonly=True,
        store=False,
        default=lambda self: f"{self.get_base_url()}/pos_adyen/notification",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ["adyen_terminal_identifier", "adyen_region", "adyen_api_url_prefix"]
        return params

    @api.constrains("adyen_terminal_identifier")
    def _check_adyen_terminal_identifier(self):
        for payment_method in self:
            if not payment_method.adyen_terminal_identifier:
                continue
            # sudo() to search all companies
            existing_payment_method = self.env[self._name].sudo().search(
                [
                    ("id", "!=", payment_method.id),
                    (
                        "adyen_terminal_identifier",
                        "=",
                        payment_method.adyen_terminal_identifier,
                    ),
                ],
                limit=1,
            )
            if existing_payment_method:
                if existing_payment_method.company_id == payment_method.company_id:
                    raise ValidationError(
                        _(
                            "Terminal %(terminal)s is already used on payment method %(payment_method)s.",
                            terminal=payment_method.adyen_terminal_identifier,
                            payment_method=existing_payment_method.display_name,
                        ),
                    )
                raise ValidationError(
                    _(
                        "Terminal %(terminal)s is already used in company %(company)s on payment method %(payment_method)s.",
                        terminal=payment_method.adyen_terminal_identifier,
                        company=existing_payment_method.company_id.name,
                        payment_method=existing_payment_method.display_name,
                    ),
                )

    @api.model
    def _adyen_normalize_api_url_prefix(self, prefix):
        if not prefix:
            return ""
        return re.sub(r"(?:https://)?(\w+-\w+).*", r"\1", prefix.strip())

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "adyen_api_url_prefix" in vals:
                vals["adyen_api_url_prefix"] = self._adyen_normalize_api_url_prefix(
                    vals["adyen_api_url_prefix"],
                )
        return super().create(vals_list)

    def write(self, vals):
        if "adyen_api_url_prefix" in vals:
            vals = dict(vals)
            vals["adyen_api_url_prefix"] = self._adyen_normalize_api_url_prefix(
                vals["adyen_api_url_prefix"],
            )
        return super().write(vals)

    def _get_adyen_endpoints(self):
        return {
            "terminal_request": "https://terminal-api-%s.adyen.com/async",
            "payment_status": "https://terminal-api-%s.adyen.com/sync",
        }

    def _is_write_forbidden(self, fields):
        return super()._is_write_forbidden(
            fields - {"adyen_latest_response"},
        )

    def get_latest_adyen_status(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group(
            "point_of_sale.group_pos_user",
        ):
            raise AccessDenied()

        latest_response = self.sudo().adyen_latest_response
        latest_response = json.loads(latest_response) if latest_response else False
        return latest_response

    def proxy_adyen_request(self, data, operation=False):
        """Necessary because Adyen's endpoints don't have CORS enabled"""
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group(
            "point_of_sale.group_pos_user",
        ):
            raise AccessDenied()
        if not data:
            raise UserError(_("Invalid Adyen request"))

        if (
            "SaleToPOIRequest" in data
            and data["SaleToPOIRequest"]["MessageHeader"]["MessageCategory"]
            == "Payment"
            and "PaymentRequest" in data["SaleToPOIRequest"]
        ):  # Clear only if it is a payment request
            self.sudo().adyen_latest_response = (
                ""  # avoid handling old responses multiple times
            )

        if not operation:
            operation = "terminal_request"

        # These checks are not optimal. This RPC method should be changed.

        is_capture_data = (
            operation == "capture"
            and hasattr(self, "adyen_merchant_account")
            and self._is_valid_adyen_request_data(
                data,
                {
                    "paymentPspReference": UNPREDICTABLE_ADYEN_DATA,
                    "amount": {
                        "value": UNPREDICTABLE_ADYEN_DATA,
                        "currency": UNPREDICTABLE_ADYEN_DATA,
                    },
                    "merchantAccount": self.adyen_merchant_account,
                },
            )
        )

        is_adjust_data = (
            operation == "adjust"
            and hasattr(self, "adyen_merchant_account")
            and self._is_valid_adyen_request_data(
                data,
                {
                    "paymentPspReference": UNPREDICTABLE_ADYEN_DATA,
                    "amount": {
                        "value": UNPREDICTABLE_ADYEN_DATA,
                        "currency": UNPREDICTABLE_ADYEN_DATA,
                    },
                    "merchantAccount": self.adyen_merchant_account,
                    "industryUsage": "delayedCharge",
                },
            )
        )

        is_cancel_data = (
            operation == "terminal_request"
            and self._is_valid_adyen_request_data(
                data,
                {
                    "SaleToPOIRequest": {
                        "MessageHeader": self._get_expected_message_header("Abort"),
                        "AbortRequest": {
                            "AbortReason": "MerchantAbort",
                            "MessageReference": {
                                "MessageCategory": "Payment",
                                "SaleID": UNPREDICTABLE_ADYEN_DATA,
                                "ServiceID": UNPREDICTABLE_ADYEN_DATA,
                            },
                        },
                    },
                },
            )
        )

        is_payment_status_data = (
            operation == "payment_status"
            and self._is_valid_adyen_request_data(
                data,
                {
                    "SaleToPOIRequest": {
                        "MessageHeader": self._get_expected_message_header(
                            "TransactionStatus",
                        ),
                        "TransactionStatusRequest": {
                            "ReceiptReprintFlag": True,
                            "DocumentQualifier": ["CustomerReceipt", "CashierReceipt"],
                        },
                    },
                },
            )
        )

        is_payment_request_with_acquirer_data = (
            operation == "terminal_request"
            and self._is_valid_adyen_request_data(
                data,
                self._get_expected_payment_request(True),
            )
        )

        if is_payment_request_with_acquirer_data:
            parsed_sale_to_acquirer_data = parse_qs(
                data["SaleToPOIRequest"]["PaymentRequest"]["SaleData"][
                    "SaleToAcquirerData"
                ],
            )
            valid_acquirer_data = self._get_valid_acquirer_data()
            is_payment_request_with_acquirer_data = len(
                parsed_sale_to_acquirer_data.keys(),
            ) <= len(valid_acquirer_data.keys())
            if is_payment_request_with_acquirer_data:
                for key, values in parsed_sale_to_acquirer_data.items():
                    if len(values) != 1:
                        is_payment_request_with_acquirer_data = False
                        break
                    value = values[0]
                    valid_value = valid_acquirer_data.get(key)
                    if valid_value == UNPREDICTABLE_ADYEN_DATA:
                        continue
                    if value != valid_value:
                        is_payment_request_with_acquirer_data = False
                        break

        is_payment_request_without_acquirer_data = (
            operation == "terminal_request"
            and self._is_valid_adyen_request_data(
                data,
                self._get_expected_payment_request(False),
            )
        )

        if (
            not is_payment_request_without_acquirer_data
            and not is_payment_request_with_acquirer_data
            and not is_adjust_data
            and not is_cancel_data
            and not is_capture_data
            and not is_payment_status_data
        ):
            raise UserError(_("Invalid Adyen request"))

        if (
            is_payment_request_with_acquirer_data
            or is_payment_request_without_acquirer_data
        ):
            acquirer_data = data["SaleToPOIRequest"]["PaymentRequest"]["SaleData"].get(
                "SaleToAcquirerData",
            )
            msg_header = data["SaleToPOIRequest"]["MessageHeader"]
            metadata = "metadata.pos_hmac=" + self._get_hmac(
                msg_header["SaleID"],
                msg_header["ServiceID"],
                msg_header["POIID"],
                data["SaleToPOIRequest"]["PaymentRequest"]["SaleData"][
                    "SaleTransactionID"
                ]["TransactionID"],
            )

            application_keys = {key for key, _value in self.APPLICATION_INFO_PARAMS}
            filtered_fragments = []
            if acquirer_data:
                for fragment in acquirer_data.split("&"):
                    if not fragment:
                        continue
                    key = fragment.split("=", 1)[0]
                    if key in application_keys or key == "metadata.pos_hmac":
                        continue
                    filtered_fragments.append(fragment)

            fragments = filtered_fragments
            fragments.extend(
                f"{key}={quote_plus(value)}"
                for key, value in self.APPLICATION_INFO_PARAMS
            )
            fragments.append(metadata)

            data["SaleToPOIRequest"]["PaymentRequest"]["SaleData"][
                "SaleToAcquirerData"
            ] = "&".join(fragments)

        return self._proxy_adyen_request_direct(data, operation)

    @api.model
    def _is_valid_adyen_request_data(self, provided_data, expected_data):
        if not isinstance(provided_data, dict) or set(provided_data.keys()) != set(
            expected_data.keys(),
        ):
            return False

        for provided_key, provided_value in provided_data.items():
            expected_value = expected_data[provided_key]
            if expected_value == UNPREDICTABLE_ADYEN_DATA:
                continue
            if isinstance(expected_value, dict):
                if not self._is_valid_adyen_request_data(
                    provided_value,
                    expected_value,
                ):
                    return False
            else:
                if provided_value != expected_value:
                    return False
        return True

    def _get_expected_message_header(self, expected_message_category):
        return {
            "ProtocolVersion": "3.0",
            "MessageClass": "Service",
            "MessageType": "Request",
            "MessageCategory": expected_message_category,
            "SaleID": UNPREDICTABLE_ADYEN_DATA,
            "ServiceID": UNPREDICTABLE_ADYEN_DATA,
            "POIID": self.adyen_terminal_identifier,
        }

    def _get_expected_payment_request(self, with_acquirer_data):
        res = {
            "SaleToPOIRequest": {
                "MessageHeader": self._get_expected_message_header("Payment"),
                "PaymentRequest": {
                    "SaleData": {
                        "SaleTransactionID": {
                            "TransactionID": UNPREDICTABLE_ADYEN_DATA,
                            "TimeStamp": UNPREDICTABLE_ADYEN_DATA,
                        },
                    },
                    "PaymentTransaction": {
                        "AmountsReq": {
                            "Currency": UNPREDICTABLE_ADYEN_DATA,
                            "RequestedAmount": UNPREDICTABLE_ADYEN_DATA,
                        },
                    },
                },
            },
        }

        if with_acquirer_data:
            res["SaleToPOIRequest"]["PaymentRequest"]["SaleData"][
                "SaleToAcquirerData"
            ] = UNPREDICTABLE_ADYEN_DATA
        return res

    @api.model
    def _get_valid_acquirer_data(self):
        return {
            "tenderOption": "AskGratuity",
            "authorisationType": "PreAuth",
            **dict(self.APPLICATION_INFO_PARAMS),
        }

    @api.model
    def _get_hmac(self, sale_id, service_id, poi_id, sale_transaction_id):
        return hmac(
            env=self.env(su=True),
            scope="pos_adyen_payment",
            message=(sale_id, service_id, poi_id, sale_transaction_id),
        )

    def _proxy_adyen_request_direct(self, data, operation):
        self.ensure_one()
        TIMEOUT = 10

        _logger.info(
            "Request to Adyen by user #%d:\n%s",
            self.env.uid,
            pprint.pformat(data),
        )

        endpoints = self._get_adyen_endpoints()
        endpoint = False
        payload = data
        region = self.sudo().adyen_region or "eu"

        if operation == "terminal_request":
            environment = "test" if self.sudo().adyen_test_mode else "live"
            if region != "eu" and environment == "live":
                environment = f"{environment}-{region}"
            endpoint = endpoints[operation] % environment
        elif operation in ("capture", "adjust"):
            payment_psp_reference = data.get("paymentPspReference")
            if not payment_psp_reference:
                raise UserError(
                    _("Missing paymentPspReference for Adyen %(operation)s request", operation=operation),
                )
            environment = "test" if self.sudo().adyen_test_mode else "live"
            if environment == "test":
                base_url = "https://checkout-test.adyen.com/checkout/v71"
            else:
                prefix = self._adyen_normalize_api_url_prefix(
                    self.sudo().adyen_api_url_prefix,
                )
                if not prefix:
                    raise UserError(
                        _(
                            "Configure the API URL prefix on the payment method to perform the Adyen '%s' operation."
                        ) % operation,
                    )
                base_url = (
                    f"https://{prefix}-checkout-live.adyenpayments.com/checkout/v71"
                )
            payload = dict(data)
            payload.pop("paymentPspReference", None)
            resource = "captures" if operation == "capture" else "amountUpdates"
            template = endpoints.get(operation)
            endpoint_path = (
                template.format(
                    paymentPspReference=payment_psp_reference,
                    resource=resource,
                )
                if template
                else f"/payments/{payment_psp_reference}/{resource}"
            )
            if not endpoint_path.startswith("/"):
                endpoint_path = f"/{endpoint_path}"
            endpoint = f"{base_url}{endpoint_path}"
        else:
            raise UserError(_("Unsupported Adyen operation."))

        headers = {
            "x-api-key": self.sudo().adyen_api_key,
        }
        req = requests.post(endpoint, json=payload, headers=headers, timeout=TIMEOUT)

        # Authentication error doesn't return JSON
        if req.status_code == 401:
            return {"error": {"status_code": req.status_code, "message": req.text}}

        if req.text == "ok":
            return True

        return req.json()
