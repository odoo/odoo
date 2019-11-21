# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import json
import logging
import pprint
import random
import re
import requests
import string
import uuid
from unicodedata import normalize
from werkzeug import urls

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.addons.payment_payfort.controllers.main import PayfortController
from odoo.http import request
from odoo.tools.pycompat import to_text
from .payfort_const import PAYFORT_ERROR, PAYFORT_SUCCESS, CURRENCY_DEC_MAP

_logger = logging.getLogger(__name__)


class AcquirerPayfort(models.Model):
    _inherit = "payment.acquirer"

    provider = fields.Selection(selection_add=[("payfort", "Payfort")])
    payfort_merchant_identifier = fields.Char(
        "Merchant Identifier", required_if_provider="payfort", groups="base.group_user"
    )
    payfort_access_code = fields.Char(
        "Access Code", required_if_provider="payfort", groups="base.group_user"
    )
    payfort_request_sha = fields.Char(
        "SHA Request Phrase", required_if_provider="payfort", groups="base.group_user"
    )
    payfort_response_sha = fields.Char(
        "SHA Response Phrase", required_if_provider="payfort", groups="base.group_user"
    )

    def _get_feature_support(self):
        """Add advanced feature support description for Payfort. """
        res = super(AcquirerPayfort, self)._get_feature_support()
        res["tokenize"].append("payfort")
        res["authorize"].append("payfort")
        return res

    @api.model
    def _payfort_convert_amount(self, amount, currency):
        """
        Convert an amount to payfort-compatible representation.

        Payfort requires the amount to be multiplied by 10^k,
        where k depends on the currency code (ISO-4217).
        """
        k = CURRENCY_DEC_MAP.get(currency.name, 2)
        paymentAmount = int(tools.float_round(amount, k) * (10 ** k))
        return paymentAmount

    @api.model
    def _get_payfort_urls(self, environment):
        return {
            "payfort_form_url": "https://%s.payfort.com/FortAPI/paymentPage"
            % ("checkout" if environment == "prod" else "sbcheckout"),
            "payfort_recurring_url": "https://%s.payfort.com/FortAPI/paymentApi"
            % ("paymentservices" if environment == "prod" else "sbpaymentservices"),
        }

    @api.model
    def _payfort_sanitize_values(self, values):
        """Sanitize sensible fields to avoid errors.
        
        Sanitize email, reference and customer name to match the requirements detailed at
        https://docs.payfort.com/docs/api/build/index.html#authorization-purchase-request.
        
        Most of these field must be alphanumeric with some special characters allowed.
        
        Special case for language: payfort only accept 'en' or 'ar', default to 'en' unless
        the partner has an arabic language variant.
        
        :param values (dict): dictionnary of values that should be sent to payfort
        :return: copy of the submitted dict with sanitized values
        :rtype: dict"""
        sanitized_values = values.copy()
        if values.get("customer_email"):
            sanitized_values["customer_email"] = re.sub(
                r"[^A-Za-z0-9\.\-_@+]+", "", values["customer_email"]
            )
        if values.get("merchant_reference"):
            sanitized_values["merchant_reference"] = re.sub(
                r"[^A-Za-z0-9\.\-_]+", "-", values["merchant_reference"]
            )
        if values.get("customer_name"):
            sanitized_values["customer_name"] = re.sub(
                r"[^A-Za-z0-9_\/\\\-\.'\s]+",
                "",
                normalize("NFKD", values["customer_name"]),
            )
        # Payfort only has en/ar, let's default to EN
        if values.get("language"):
            partner_lang = values.get("language", "en")
            sanitized_values["language"] = (
                "ar"
                if (len(partner_lang) > 1 and partner_lang[:1].lower() == "ar")
                else "en"
            )
        return sanitized_values

    def _payfort_generate_signature(self, sha_type, values):
        """ Generate the shasign for incoming or outgoing communications using the SHA-256 signature.
        
        The signature is generated as described at https://docs.payfort.com/docs/api/build/index.html#signature
        1/ Sort all params alphabetically
        1b/ (For response signatures) Remove the 'signature' param from the payload otherwise **cue inception boom**
        2/ Concat param and value with '=' char
        3/ Concat everything without separator
        4/ Add passphrase at beginning and end of string
        5/ Apply hash method on string (SHA-256)

        :param string sha_type: 'request' (odoo contacting payfort) or 'response' (payfort
                                contacting odoo).
        :param dict values: transaction values
        :return: shasign of the provided payload
        :rtype: string
        """
        if self.provider != "payfort":
            raise ValidationError(
                "Trying to generate SHA signature using Payfort method for a non-Payfort payment"
            )
        if sha_type not in ("request", "response"):
            raise ValidationError("'sha_type' should be 'request' or 'response'")
        if sha_type == "request":
            sha_phrase = self.payfort_request_sha
        else:
            sha_phrase = self.payfort_response_sha

        sig_string = sha_phrase
        # partner_id is not sent to payfort (so not part of signature computation)
        # but must be present in dict for processing in our code
        fields_to_ignore = ["signature", "partner_id"]
        for key in filter(lambda k: k not in fields_to_ignore, sorted(values.keys())):
            sig_string += "%s=%s" % (key, values[key])
        sig_string += sha_phrase
        return hashlib.sha256(sig_string.encode()).hexdigest()

    def payfort_form_generate_values(self, values):
        base_url = self.get_base_url()

        amount = self._payfort_convert_amount(values["amount"], values["currency"])

        if (
            not values.get("currency")
            or not values.get("partner_lang")
            or not (values.get("partner_email") or values.get("billing_partner_email"))
        ):
            raise ValidationError(
                _(
                    "Mandatory fields missing for Payfort payment (currency/language/email)"
                )
            )

        payfort_values = {
            "command": "PURCHASE" if not self.capture_manually else "AUTHORIZATION",
            "access_code": self.payfort_access_code,
            "merchant_identifier": self.payfort_merchant_identifier,
            "merchant_reference": values["reference"],
            "amount": str(amount),
            "currency": values["currency"].name,
            "language": values["partner_lang"],
            "customer_email": values.get("partner_email")
            or values.get("billing_partner_email"),
            "customer_name": values.get("partner_name") or "",
            "eci": "ECOMMERCE",
            "return_url": urls.url_join(base_url, PayfortController._return_url),
            # payfort is rather strict regarding the reference, which means that the merchant_reference
            # might not match the one we have for the tx
            # pass the original reference as an extra param that they will send back with the response
            "merchant_extra": values["reference"],
        }
        if self.save_token in ["ask", "always"]:
            payfort_values.update(token_name=self._payfort_generate_token_reference())
        payfort_values = self._payfort_sanitize_values(payfort_values)
        payfort_values["signature"] = self._payfort_generate_signature(
            "request", payfort_values
        )
        values.update(payfort_values)
        return values

    def payfort_get_form_action_url(self):
        self.ensure_one()
        environment = "prod" if self.state == "enabled" else "test"
        return self._get_payfort_urls(environment)["payfort_form_url"]

    def _payfort_generate_token_reference(self):
        """Generate a unique token reference for Payfort."""
        return "Odoo-token-%s" % uuid.uuid4()

    def _payfort_generate_s2s_values(self, partner_id):
        self.ensure_one()
        if not self.provider == "payfort":
            raise ValidationError("This provider does not use Payfort")
        if not partner_id:
            raise ValidationError(
                _("A partner must be specified for recurring transactions.")
            )
        partner = self.env["res.partner"].sudo().browse(partner_id)
        base_url = self.get_base_url()
        # I would have used a uuid4, but Payfort only accepts 40 letters in
        # the merchant_reference field; using a 10-char long random string
        # offer enough randomness to avoid collision, especially since this
        # is *per partner*
        rand_string = "".join(random.choices(string.ascii_letters, k=10))
        payfort_values = {
            "service_command": "TOKENIZATION",
            "access_code": self.payfort_access_code,
            "merchant_identifier": self.payfort_merchant_identifier,
            # note: this string is parsed in the return controller, its structure cannot be changed
            # without changing the controller as well
            "merchant_reference": "ODOO-PARTNER-%s-%s" % (rand_string, partner.id),
            "language": partner.lang,
            "token_name": self._payfort_generate_token_reference(),
            "return_url": urls.url_join(
                base_url, "/payment/payfort/merchant_page_return"
            ),
        }
        payfort_values = self._payfort_sanitize_values(payfort_values)
        payfort_values["signature"] = self._payfort_generate_signature(
            "request", payfort_values
        )
        # not part of signature & not sent to Payfort, needed for rendering only
        payfort_values.update(
            {"acquirer_id": self.id, "form_action": self.payfort_get_form_action_url(),}
        )
        return payfort_values

    def payfort_s2s_form_process(self, data):
        self.ensure_one()
        shasign_check = self._payfort_generate_signature("response", data)
        if not hmac.compare_digest(
            to_text(shasign_check), to_text(data.get("signature"))
        ):
            error_msg = _("Payfort: invalid signature, received %s, computed %s") % (
                data.get("signature"),
                shasign_check,
            )
            _logger.warning(error_msg)
            raise ValidationError(error_msg)
        status = data.get("status")
        if status in PAYFORT_SUCCESS:
            token = (
                self.env["payment.token"]
                .sudo()
                .create(
                    {
                        "acquirer_ref": data.get("token_name"),
                        "acquirer_id": self.id,
                        "name": "%s - %s"
                        % (data.get("card_number"), data.get("card_holder_name")),
                        "partner_id": data.get("partner_id"),
                    }
                )
            )
        else:
            token = self.env["payment.token"]
        return token


class PaymentTransactionPayfort(models.Model):
    _inherit = "payment.transaction"

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _payfort_form_get_tx_from_data(self, data):
        # merchant_extra will contain the exact `reference` field we have on the tx record,
        # so we should always use it by default; however some notifications will not contain
        # it. In that case, search on the merchant_reference and hope it gets found...
        reference = data.get("merchant_extra") or data.get("merchant_reference")
        if not reference:
            error_msg = _(
                "Payfort: received data with missing merchant_extra/merchant_reference"
            )
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        tx = self.env["payment.transaction"].search([("reference", "=", reference)])
        if len(tx) != 1:
            error_msg = _("Payfort: received data for reference %s") % (reference)
            if not tx:
                error_msg += _("; no order found")
            else:
                error_msg += _("; multiple order found")
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # verify shasign
        shasign_check = tx.acquirer_id._payfort_generate_signature("response", data)
        if to_text(shasign_check) != to_text(data.get("signature")):
            error_msg = _("Payfort: invalid signature, received %s, computed %s") % (
                data.get("signature"),
                shasign_check,
            )
            _logger.warning(error_msg)
            raise ValidationError(error_msg)

        return tx

    def _payfort_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        # reference at acquirer: fort_id
        if self.acquirer_reference and data.get("fort_id") != self.acquirer_reference:
            invalid_parameters.append(
                ("fort_id", data.get("fort_id"), self.acquirer_reference)
            )
        # seller
        if (
            data.get("merchant_identifier")
            != self.acquirer_id.payfort_merchant_identifier
        ):
            invalid_parameters.append(
                (
                    "merchant_identifier",
                    data.get("merchant_identifier"),
                    self.acquirer_id.payfort_merchant_identifier,
                )
            )
        # result
        if not data.get("status"):
            invalid_parameters.append(("status", data.get("status"), "status"))

        return invalid_parameters

    def _payfort_form_validate(self, data):
        status = data["status"]
        token = data.get("token_name")
        command = data.get("command")
        init_state = self.state  # state before processing the response
        if command in ("AUTHORIZATION", "PURCHASE", "CAPTURE"):
            # normal transaction
            # save token if asked
            if token and self.type == "form_save":
                Token = self.env["payment.token"]
                domain = [("acquirer_ref", "=", token)]
                if not Token.search_count(domain):
                    _logger.info(
                        "Payfort: saving alias %s for partner %s"
                        % (data.get("card_number"), self.partner_id)
                    )
                    ref = Token.create(
                        {
                            "name": "%s - %s"
                            % (data.get("card_number"), data.get("card_holder_name")),
                            "partner_id": self.partner_id.id,
                            "acquirer_id": self.acquirer_id.id,
                            "acquirer_ref": token,
                            "verified": True,
                        }
                    )
                    self.write({"payment_token_id": ref.id})
            self.write(
                {
                    "acquirer_reference": data.get("fort_id"),
                    "state_message": data.get("response_message"),
                    "html_3ds": data.get("3ds_url"),
                }
            )
            if status in PAYFORT_SUCCESS:
                if self.payment_token_id:
                    self.payment_token_id.verified = True
                if command == "AUTHORIZATION":
                    self._set_transaction_authorized()
                else:
                    self._set_transaction_done()
                # only execute callback if previous state is draft
                # as we might be processing a capture confirmation and the
                # callback would then already have been called at the auth step
                if init_state == "draft":
                    self.execute_callback()
                return True
            elif status in PAYFORT_ERROR:
                error_msg = data.get("response_message")
                self._set_transaction_error(error_msg)
                return False
            else:
                self._set_transaction_pending()
                return True
        elif command == "VOID_AUTHORIZATION":
            # refund of a tokenization authorization tx ('validation tx')
            # no need to get values to write on tx, was done previously
            # just set the tx to the correct status
            if status in PAYFORT_SUCCESS:
                self._set_transaction_cancel()
                return True
            elif status in PAYFORT_ERROR:
                error_msg = data.get("response_message")
                self._set_transaction_error(error_msg)
                return False
            else:
                self._set_transaction_pending()
                return True

    # --------------------------------------------------
    # S2S RELATED METHODS
    # --------------------------------------------------

    def payfort_s2s_do_transaction(self, **kwargs):
        environment = "prod" if self.acquirer_id.state == "enabled" else "test"
        endpoint = self.acquirer_id._get_payfort_urls(environment)[
            "payfort_recurring_url"
        ]
        is_payfort_validation_tx = self.env.context.get("payfort_validation")
        if is_payfort_validation_tx:
            # we need to override the currency because it most probably picked the wrong one
            # the authorization tx must use a currency supported by the provider
            # assume (hopefully) that the provider's journal's currency is
            journal = self.acquirer_id.journal_id
            journal_currency = journal.currency_id or journal.company_id.currency_id
            self.currency_id = journal_currency
        amount = self.acquirer_id._payfort_convert_amount(self.amount, self.currency_id)
        payment_values = {
            "command": "PURCHASE",
            "access_code": self.acquirer_id.payfort_access_code,
            "merchant_identifier": self.acquirer_id.payfort_merchant_identifier,
            "merchant_reference": self.reference,
            "amount": amount,
            "currency": self.currency_id.name,
            "language": self.partner_lang,
            "customer_email": self.partner_email,
            "eci": "RECURRING",
            "token_name": self.payment_token_id.acquirer_ref,
            "customer_name": self.partner_name,
            "merchant_extra": self.reference,
        }
        if is_payfort_validation_tx:
            base_url = self.acquirer_id.get_base_url()
            payment_values.update(
                {
                    "command": "AUTHORIZATION",  # always AUTH for token validation
                    # that way, if something goes wrong there is nothing to refund to the customer
                    "remember_me": "YES",
                    # if no request, the call CAME FROM INSIDE THE HOUSE!
                    "customer_ip": request
                    and request.httprequest.remote_addr
                    or "127.0.0.1",
                    # for multi-website, we need to make sure that we come back on the same url
                    # otherwise iframe & pop-up cross-communication will be blocked by same-origin
                    "return_url": urls.url_join(
                        base_url, "/payment/payfort/secure_merchant_page_return"
                    ),
                }
            )
            payment_values.pop("eci")
        payment_values = self.acquirer_id._payfort_sanitize_values(payment_values)
        payment_values["signature"] = self.acquirer_id._payfort_generate_signature(
            "request", payment_values
        )
        _logger.info(
            "Payfort: sending s2s payment request with values:\n%s"
            % pprint.pformat(payment_values)
        )
        response = requests.post(endpoint, json=payment_values)
        _logger.info(
            "Payfort: received s2s payment response with values:\n%s"
            % pprint.pformat(response.json())
        )
        return self._payfort_form_validate(response.json())

    def payfort_s2s_do_refund(self, **kwargs):
        if self.type == "validation":
            # a validation tx in payfort is done with an AUTHORIZATION command
            # to avoid problems in case of an interrupted flow
            # the validation process does not support this OoB and will always
            # call the refund method (this one) during the validation flow
            # refunding an authorized tx does not work, instead reroute the
            # call to the voiding method, which is appropriate for an authorized tx
            return self.payfort_s2s_void_transaction(**kwargs)
        environment = "prod" if self.acquirer_id.state == "enabled" else "test"
        endpoint = self.acquirer_id._get_payfort_urls(environment)[
            "payfort_recurring_url"
        ]
        amount = self.acquirer_id._payfort_convert_amount(self.amount, self.currency_id)
        payment_values = {
            "command": "REFUND",
            "access_code": self.acquirer_id.payfort_access_code,
            "merchant_identifier": self.acquirer_id.payfort_merchant_identifier,
            "merchant_reference": self.reference,
            "fort_id": self.acquirer_reference,
            "amount": amount,
            "currency": self.currency_id.name,
            "language": self.partner_lang,
        }
        payment_values = self.acquirer_id._payfort_sanitize_values(payment_values)
        payment_values["signature"] = self.acquirer_id._payfort_generate_signature(
            "request", payment_values
        )
        _logger.info(
            "Payfort: sending s2s refund request with values:\n%s"
            % pprint.pformat(payment_values)
        )
        response = requests.post(endpoint, json=payment_values)
        _logger.info(
            "Payfort: received s2s refund response with values:\n%s"
            % pprint.pformat(response.json())
        )
        return self._payfort_form_validate(response.json())

    def payfort_s2s_capture_transaction(self, **kwargs):
        environment = "prod" if self.acquirer_id.state == "enabled" else "test"
        endpoint = self.acquirer_id._get_payfort_urls(environment)[
            "payfort_recurring_url"
        ]
        amount = self.acquirer_id._payfort_convert_amount(self.amount, self.currency_id)
        payment_values = {
            "command": "CAPTURE",
            "access_code": self.acquirer_id.payfort_access_code,
            "merchant_identifier": self.acquirer_id.payfort_merchant_identifier,
            "merchant_reference": self.reference,
            "fort_id": self.acquirer_reference,
            "amount": amount,
            "currency": self.currency_id.name,
            "language": self.partner_lang,
        }
        payment_values = self.acquirer_id._payfort_sanitize_values(payment_values)
        payment_values["signature"] = self.acquirer_id._payfort_generate_signature(
            "request", payment_values
        )
        _logger.info(
            "Payfort: sending s2s capture request with values:\n%s"
            % pprint.pformat(payment_values)
        )
        response = requests.post(endpoint, json=payment_values)
        _logger.info(
            "Payfort: received s2s capture response with values:\n%s"
            % pprint.pformat(response.json())
        )
        return self._payfort_form_validate(response.json())

    def payfort_s2s_void_transaction(self, **kwargs):
        environment = "prod" if self.acquirer_id.state == "enabled" else "test"
        endpoint = self.acquirer_id._get_payfort_urls(environment)[
            "payfort_recurring_url"
        ]
        payment_values = {
            "command": "VOID_AUTHORIZATION",
            "access_code": self.acquirer_id.payfort_access_code,
            "merchant_identifier": self.acquirer_id.payfort_merchant_identifier,
            "merchant_reference": self.reference,
            "fort_id": self.acquirer_reference,
            "language": self.partner_lang,
        }
        payment_values = self.acquirer_id._payfort_sanitize_values(payment_values)
        payment_values["signature"] = self.acquirer_id._payfort_generate_signature(
            "request", payment_values
        )
        _logger.info(
            "Payfort: sending s2s void request with values:\n%s"
            % pprint.pformat(payment_values)
        )
        response = requests.post(endpoint, json=payment_values)
        _logger.info(
            "Payfort: received s2s void response with values:\n%s"
            % pprint.pformat(response.json())
        )
        return self._payfort_form_validate(response.json())
