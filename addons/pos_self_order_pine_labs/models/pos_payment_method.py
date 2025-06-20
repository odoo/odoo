# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from werkzeug.exceptions import NotFound

import logging
import pytz
import uuid

from odoo import api, models
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _payment_request_from_kiosk(self, order):
        if self.use_payment_terminal != 'pine_labs':
            return super()._payment_request_from_kiosk(order)
        reference_prefix = order.config_id.name.replace(' ', '')
        # We need to provide the amount in paisa since Pine Labs processes amounts in paisa.
        # The conversion rate between INR and paisa is set as 1 INR = 100 paisa.
        data = {
            'amount': order.amount_total * 100,
            'transactionNumber': f'{reference_prefix}/Order/{order.id}/{uuid.uuid4().hex}',
            'sequenceNumber': '1'
        }
        payment_response = self.pine_labs_make_payment_request(data)
        payment_response['payment_ref_no'] = data.get('transactionNumber')
        return payment_response

    def handle_pine_labs_payment_response(self, order_id, payment_response):
        """
        Handles Pine Labs payment response for a POS order by parsing local transaction datetime
        with the provided time zone and converting it to UTC.
        Builds payment data from the response and registers the payment on the order.
        Marks the order as paid and triggers the bus service for updates.
        """
        order = self.env['pos.order'].browse(order_id)
        if not order.exists():
            _logger.warning('Order with ID %s does not exist.', order_id)
            raise NotFound()
        # We receive 'Transaction Date' and 'Transaction Time' values from Pine Labs in local system time.
        # To accurately convert this local time to UTC in Python:
        # - The system's timezone (from the client) is passed along with the Pine Labs response.
        # - This timezone is used to localize the naive datetime in Python.
        # - The localized datetime is then converted to UTC for standardized processing and storage.
        local_dt = datetime.strptime(payment_response['Transaction Date'] + payment_response['Transaction Time'], '%d%m%Y%H%M%S')
        local_tz = pytz.timezone(payment_response['time_zone'])
        localized_dt = local_tz.localize(local_dt)
        payment_data = {
            'amount': order.amount_total,
            'pos_order_id': order.id,
            'payment_method_id': self.id,
            'payment_method_issuer_bank': payment_response.get('Acquirer Name'),
            'payment_method_authcode': payment_response.get('ApprovalCode'),
            'cardholder_name': payment_response.get('Card Holder Name'),
            'payment_status': "done",
            'card_no': payment_response.get('Card Number') and payment_response.get('Card Number')[-4:],
            'card_brand': payment_response.get('Card Type'),
            'payment_method_payment_mode': payment_response.get('PaymentMode'),
            'transaction_id': payment_response.get('TransactionLogId'),
            'payment_ref_no': payment_response.get('payment_ref_no'),
            'pine_labs_plutus_transaction_ref': payment_response.get('pine_labs_plutus_transaction_ref'),
            'payment_date': localized_dt.astimezone(pytz.utc).replace(tzinfo=None),
        }
        order.add_payment(payment_data)
        order.action_pos_order_paid()
        self.call_bus_service(order)

    def call_bus_service(self, order):
        order.config_id._notify('PAYMENT_STATUS', {
            'payment_result': 'Success',
            'data': {
                'pos.order': order.read(order._load_pos_self_data_fields(order.config_id.id), load=False),
                'pos.order.line': order.lines.read(order._load_pos_self_data_fields(order.config_id.id), load=False),
            }
        })

    @api.model
    def _load_pos_self_data_domain(self, data):
        domain = super()._load_pos_self_data_domain(data)
        if data['pos.config'][0]['self_ordering_mode'] == 'kiosk':
            domain = expression.OR([[('use_payment_terminal', '=', 'pine_labs')], domain])
        return domain
