from datetime import datetime, timezone
import random
from odoo import models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def payment_request_from_kiosk(self, order):
        if self.use_payment_terminal != 'adyen':
            return super().payment_request_from_kiosk(order)
        else:
            pos_config = order.session_id.config_id
            random_number = random.randrange(10**9, 10**10 - 1)

            # https://docs.adyen.com/point-of-sale/basic-tapi-integration/make-a-payment/#make-a-payment
            data = {
                'SaleToPOIRequest': {
                    'MessageHeader': {
                        'ProtocolVersion': "3.0",
                        'MessageClass': "Service",
                        'MessageType': "Request",
                        'MessageCategory': "Payment",
                        'SaleID': f'{pos_config.display_name} (ID:{pos_config.id})', #	Your unique ID for the POS system component to send this request from.
                        'ServiceID': str(random_number), # Your unique ID for this request, consisting of 1-10 alphanumeric characters.
                        'POIID': self.adyen_terminal_identifier, #	The unique ID of the terminal to send this request to.
                    },
                    'PaymentRequest': {
                        'SaleData': {
                            'SaleTransactionID': {
                                'TransactionID': order.pos_reference, # your reference to identify a payment.
                                'TimeStamp': datetime.now(tz=timezone.utc).isoformat(timespec='seconds'), # date and time of the request in UTC format.
                            },
                        },
                        'PaymentTransaction': {
                            'AmountsReq': {
                                'Currency': order.currency_id.name, # the transaction currency.
                                'RequestedAmount': order.amount_total, # The final transaction amount.
                            },
                        },
                    },
                },
            }

            req = self.proxy_adyen_request(data)

            if not req and req.get('error'):
                return False
            else:
                return True
