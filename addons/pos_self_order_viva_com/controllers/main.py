from werkzeug.exceptions import NotFound

from odoo import http
from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController


class PosSelfOrderVivaComController(PosSelfOrderController):
    @http.route('/pos_self_order_viva_com/poll_payment', type='jsonrpc', auth='public')
    def poll_payment(self, access_token, viva_session_id, payment_method_id):
        pos_config = self._verify_pos_config(access_token)
        payment_method_sudo = pos_config.env["pos.payment.method"].browse(payment_method_id)
        if not payment_method_sudo or payment_method_sudo not in pos_config.payment_method_ids:
            raise NotFound("Payment method not found")

        payment_status = payment_method_sudo.viva_com_get_payment_status(viva_session_id)
        if "error" in payment_status:
            return False

        pos_session_id = payment_status["merchantReference"].split("/")[1]
        payment_status["pos_session_id"] = pos_session_id
        payment_method_sudo._send_notification(payment_status)

        return True
