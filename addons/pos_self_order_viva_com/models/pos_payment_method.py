import logging
import math
import uuid
from odoo import models, api, fields
from odoo.fields import Domain


_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _payment_request_from_kiosk(self, order):
        if self.use_payment_terminal != "viva_com":
            return super()._payment_request_from_kiosk(order)

        pos_config = order.session_id.config_id
        viva_session_id = order.uuid + " - " + uuid.uuid4().hex
        if order.partner_id:
            customer_ref = order.partner_id.name + " - " + order.partner_id.email
        else:
            customer_ref = " "

        payment_request = {
            "sessionId": viva_session_id,
            "terminalId": self.viva_com_terminal_id,
            "cashRegisterId": pos_config.uuid,
            "amount": round(order.amount_total * math.pow(10, pos_config.currency_id.decimal_places)),
            "currencyCode": str(pos_config.currency_id.iso_numeric),
            "merchantReference": viva_session_id + "/" + str(order.session_id.id),
            "customerTrns": customer_ref,
            "preauth": False,
            "maxInstalments": 0,
            "tipAmount": 0,
        }

        payment_response = self.viva_com_send_payment_request(payment_request)
        if payment_response.get("success") != 200:
            return False
        return viva_session_id

    def _send_notification(self, data):
        if not data.get("pos_session_id"):
            return super()._send_notification(data)
        pos_session = self.env["pos.session"].browse(int(data["pos_session_id"]))
        if not pos_session or pos_session.config_id.self_ordering_mode != "kiosk":
            return super()._send_notification(data)

        order_uuid = data["sessionId"].split(" ")[0]
        order = pos_session.order_ids.search([("uuid", "=", order_uuid)])
        if not order:
            _logger.warning("Received Viva notification for unknown kiosk order %s", order_uuid)
            return
        if order.state == 'paid':
            _logger.warning("Received Viva notification for already paid kiosk order %s", order_uuid)
            return

        if data["success"]:
            currency = pos_session.config_id.currency_id
            payment_amount = currency.round(data["amount"] / math.pow(10, currency.decimal_places))
            order.add_payment({
                "amount": payment_amount,
                "payment_date": fields.Datetime.now(),
                "payment_method_id": self.id,
                "card_type": data.get("applicationLabel"),
                "cardholder_name": data.get("FullName", ""),
                "transaction_id": data.get("transactionId"),
                "payment_status": "done",
                "pos_order_id": order.id
            })
            order.action_pos_order_paid()
            order._send_payment_result("Success")
        else:
            order._send_payment_result("fail")

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        domain = super()._load_pos_self_data_domain(data, config)
        if config.self_ordering_mode == "kiosk":
            domain = Domain.OR([
                [("use_payment_terminal", "=", "viva_com"), ("id", "in", config.payment_method_ids.ids)],
                domain
            ])
        return domain
