# coding: utf-8

# Copyright 2015 Eezee-It
import datetime
from dateutil import parser
import json
import logging
import pytz
import re
import time
from hashlib import sha256

from werkzeug import urls

from odoo import models, fields, api
from odoo.tools.float_utils import float_compare
from odoo.tools.translate import _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment.utils import singularize_reference_prefix
from odoo.addons.payment_sips.controllers.main import SipsController

from .const import SIPS_SUPPORTED_CURRENCIES, SIPS_STATUS_CANCEL, SIPS_STATUS_PENDING, SIPS_STATUS_ERROR, SIPS_STATUS_REFUSED, SIPS_STATUS_VALID, SIPS_STATUS_WAIT

_logger = logging.getLogger(__name__)


class TxSips(models.Model):
    _inherit = "payment.transaction"

    @api.model
    def _compute_reference(self, provider, prefix=None, separator="-", **kwargs):
        if provider == 'sips':
            separator = 'x'
            prefix = singularize_reference_prefix(separator='')
        return super()._compute_reference(provider, prefix, separator, **kwargs)

    def _get_specific_processing_values(self, processing_values):
        self.ensure_one()
        if self.provider != "sips":
            return super()._get_specific_processing_values(processing_values)

        base_url = self.get_base_url()
        currency = self.env["res.currency"].sudo().browse(processing_values["currency_id"])
        sips_currency = SIPS_SUPPORTED_CURRENCIES.get(currency.name)
        if not sips_currency:
            raise ValidationError(
                _("Currency not supported by Wordline: %s") % currency.name
            )
        # rounded to its smallest unit, depends on the currency
        amount = round(processing_values["amount"] * (10 ** sips_currency.decimal))

        sips_tx_values = dict(processing_values)
        data = {
            "amount": amount,
            "currencyCode": sips_currency.iso_id,
            "merchantId": self.acquirer_id.sips_merchant_id,
            "normalReturnUrl": urls.url_join(base_url, SipsController._return_url),
            "automaticResponseUrl": urls.url_join(base_url, SipsController._notify_url),
            "transactionReference": processing_values["reference"],
            "statementReference": processing_values["reference"],
            "keyVersion": self.acquirer_id.sips_key_version,
        }
        sips_tx_values.update(
            {
                "Data": "|".join([f"{k}={v}" for k, v in data.items()]),
                "InterfaceVersion": self.acquirer_id.sips_version,
            }
        )

        return_context = {}
        if sips_tx_values.get("return_url"):
            return_context["return_url"] = urls.url_quote(
                sips_tx_values.get("return_url")
            )
        return_context["reference"] = sips_tx_values["reference"]
        sips_tx_values["Data"] += "|returnContext=%s" % (json.dumps(return_context))

        shasign = self.acquirer_id._sips_generate_shasign(sips_tx_values)
        sips_tx_values["Seal"] = shasign
        return sips_tx_values

    def _get_specific_rendering_values(self, processing_values):
        self.ensure_one()
        if self.provider != "sips":
            return super()._get_specific_rendering_values(processing_values)

        processing_values["tx_url"] = self._sips_get_redirect_action_url()
        processing_values["InterfaceVersion"] = processing_values["InterfaceVersion"]
        processing_values["Seal"] = processing_values["Seal"]
        return processing_values

    def _sips_get_redirect_action_url(self):
        self.ensure_one()
        return (
            self.acquirer_id.sips_prod_url
            if self.acquirer_id.state == "enabled"
            else self.acquirer_id.sips_test_url
        )

    def _sips_data_to_object(self, data):
        res = {}
        for element in data.split("|"):
            (key, value) = element.split("=")
            res[key] = value
        return res

    @api.model
    def _get_tx_from_data(self, provider, data):
        if provider != "sips":
            return super()._get_tx_from_data(provider, data)

        data = self._sips_data_to_object(data["Data"])
        reference = data.get("transactionReference")

        if not reference:
            return_context = json.loads(data.get("returnContext", "{}"))
            reference = return_context.get("reference")

        payment_tx = self.search([("reference", "=", reference)])
        if not payment_tx:
            error_msg = (
                _("Sips: received data for reference %s; no order found") % reference
            )
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return payment_tx

    def _get_invalid_parameters(self, data):
        if self.provider != "sips":
            return super()._get_invalid_parameters(data)
        invalid_parameters = []

        data = self._sips_data_to_object(data.get("Data"))

        # amounts should match
        # get currency decimals from const
        sips_currency = SIPS_SUPPORTED_CURRENCIES.get(self.currency_id.name)
        # convert from int to float using decimals from currency
        amount_converted = float(data.get("amount", "0.0")) / (
            10 ** sips_currency.decimal
        )
        if float_compare(amount_converted, self.amount, sips_currency.decimal) != 0:
            invalid_parameters['amount'] = (data.get("amount"), "%.2f" % self.amount)

        return invalid_parameters

    def _process_feedback_data(self, data):
        if self.provider != "sips":
            return super()._process_feedback_data(data)
        data = self._sips_data_to_object(data.get("Data"))
        status = data.get("responseCode")
        date = data.get("transactionDateTime")
        if date:
            try:
                # dateutil.parser 2.5.3 and up should handle dates formatted as
                # '2020-04-08T05:54:18+02:00', which strptime does not
                # (+02:00 does not work as %z expects +0200 before Python 3.7)
                # See odoo/odoo#49160
                date = parser.parse(date).astimezone(pytz.utc).replace(tzinfo=None)
            except Exception:
                # fallback on now to avoid failing to register the payment
                # because a provider formats their dates badly or because
                # some library is not behaving
                date = fields.Datetime.now()

        self.acquirer_reference = data.get("transactionReference")
        res = False
        if status in SIPS_STATUS_VALID:
            msg = f"ref: {self.reference}, got valid response [{status}], set as done."
            self._set_done()
            res = True
        elif status in SIPS_STATUS_ERROR:
            msg = f"ref: {self.reference}, got response [{status}], set as cancel."
            self._set_canceled()
        elif status in SIPS_STATUS_WAIT:
            msg = f"ref: {self.reference}, got wait response [{status}], set as cancel."
            self._set_canceled()
        elif status in SIPS_STATUS_REFUSED:
            msg = f"ref: {self.reference}, got refused response [{status}], set as cancel."
            self._set_canceled()
        elif status in SIPS_STATUS_PENDING:
            msg = f"ref: {self.reference}, got pending response [{status}], set as pending."
            self._set_pending()
        elif status in SIPS_STATUS_CANCEL:
            msg = (
                f"ref: {self.reference}, got cancel response [{status}], set as cancel."
            )
            self._set_canceled()
        else:
            msg = f"ref: {self.reference}, got unrecognized response [{status}], set as cancel."
            self._set_canceled()
        _logger.info(msg)
        return res
