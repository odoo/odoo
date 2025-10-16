from odoo import http
from odoo.http import request

from odoo.addons.pos_bancontact_pay.controllers.signature import BancontactSignatureValidation
from odoo.addons.pos_bancontact_pay.errors.exceptions import BancontactSignatureValidationError


class BancontactPayController(http.Controller):

    @http.route(["/bancontact_pay/webhook"], type="http", auth="public", methods=["POST"], csrf=False)
    def bancontact_pay_webhook(self, mode=None):
        bancontact_signature_validation = BancontactSignatureValidation(request.httprequest, mode == "test")
        try:
            bancontact_signature_validation.verify_signature()
        except BancontactSignatureValidationError as e:
            return http.Response(str(e), status=403)

        data = request.get_json_data()
        bancontact_payment_id = data.get("paymentId")

        pos_payment = None
        if bancontact_payment_id:
            pos_payment = self.env["pos.payment"].sudo().search([("bancontact_id", "=", bancontact_payment_id)], limit=1)
        if not pos_payment or not pos_payment.exists():
            return http.Response("Payment not found.", status=404)

        try:
            bancontact_signature_validation.verify_subject(pos_payment.payment_method_id.bancontact_ppid)
        except BancontactSignatureValidationError as e:
            return http.Response(str(e), status=403)

        bancontact_status = data.get("status")

        def _notify_pos():
            pos_order = pos_payment.pos_order_id
            pos_order.config_id._notify(
                "BANCONTACT_PAY_PAYMENTS_NOTIFICATION",
                {
                    "order_id": pos_order.id,
                    "payment_id": pos_payment.id,
                    "bancontact_status": bancontact_status,
                },
            )

        if pos_payment.payment_status != "done":
            if bancontact_status == "SUCCEEDED":
                pos_payment.payment_status = "done"
                pos_payment.qr_code = False
                _notify_pos()
            elif bancontact_status in ("AUTHORIZATION_FAILED", "FAILED", "EXPIRED", "CANCELLED") and pos_payment.payment_status != "retry":
                pos_payment.payment_status = "retry"
                pos_payment.qr_code = False
                pos_payment.bancontact_id = False
                _notify_pos()

            # PENDING, IDENTIFIED, AUTHORIZED, PENDING_MERCHANT_ACKNOWLEDGEMENT, VOIDED --> no action
            # https://docs.payconiq.be/guides/general/callback052025

        return http.Response(status=200)
