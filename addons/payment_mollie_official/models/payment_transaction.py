# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import pytz
import dateutil.parser
from odoo.addons.payment.models.payment_acquirer import ValidationError

import logging
_logger = logging.getLogger(__name__)
import pprint
from mollie.api.client import Client


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _mollie_form_get_tx_from_data(self, data):
        reference = data.get('reference')
        payment_tx = self.search([('reference', '=', reference)])

        if not payment_tx or len(payment_tx) > 1:
            error_msg = _('received data for reference %s') % (
                pprint.pformat(reference))
            if not payment_tx:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        return payment_tx

    def _mollie_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        return invalid_parameters

    def _mollie_form_validate(self, data):
        reference = data.get('reference')
        acquirer = self.acquirer_id
        if self.state == 'done':
            _logger.info(
                'Mollie: trying to validate an already validated tx (ref %s)',
                reference)
            return True

        mollie_client = Client()
        tx = self._mollie_form_get_tx_from_data(data)
        transactionId = tx['acquirer_reference']
        _logger.info("Validated transfer payment forTx %s: set as pending" % (
            reference))

        mollie_api_key = acquirer._get_mollie_api_keys(
            acquirer.state)['mollie_api_key']
        mollie_client.set_api_key(mollie_api_key)
        mollie_response = mollie_client.payments.get(transactionId)
        try:
            # dateutil and pytz don't recognize abbreviations PDT/PST
            tzinfos = {
                'PST': -8 * 3600,
                'PDT': -7 * 3600,
            }
            date = dateutil.parser.parse(data.get('createdAt'),
                                         tzinfos=tzinfos).astimezone(pytz.utc)
        except:
            date = fields.Datetime.now()
        res = {
            'acquirer_reference': mollie_response.get('id', ''),
        }

        status = mollie_response.get("status", "undefined")

        if status in ["paid", "authorized"]:
            res.update(date=date)
            self._set_transaction_done()
            return self.write(res)

        elif status in ["cancelled", "expired", "failed"]:
            self._set_transaction_cancel()
            return self.write(res)

        elif status in ["open", "pending"]:
            self._set_transaction_pending()
            return self.write(res)

        else:
            msg = "Error/%s/%s" % (transactionId, reference)
            self._set_transaction_error(msg)
            return self.write(res)