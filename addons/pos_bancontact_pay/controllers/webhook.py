from odoo import http
from odoo.http import request

from odoo.addons.pos_bancontact_pay.controllers.signature import (
    BancontactSignatureValidation,
)
from odoo.addons.pos_bancontact_pay.errors.exceptions import (
    BancontactSignatureValidationError,
)


class BancontactPayController(http.Controller):

    @http.route(["/bancontact_pay/webhook"], type="http", auth="public", methods=["POST"], csrf=False)
    def bancontact_pay_webhook(self, config_id=None, ppid=None, mode=None):
        bancontact_signature_validation = BancontactSignatureValidation(request.httprequest, mode == "test")
        try:
            bancontact_signature_validation.verify_signature(ppid)
        except BancontactSignatureValidationError as e:
            return http.Response(str(e), status=403)

        try:
            config_id = int(config_id)
        except (TypeError, ValueError):
            return http.Response("Invalid or missing config_id parameter", status=400)

        pos_config = self.env['pos.config'].sudo().browse(config_id)
        if not pos_config.exists():
            return http.Response("Invalid POS configuration ID", status=400)

        data = request.get_json_data()
        bancontact_id = data.get("paymentId")
        bancontact_status = data.get("status")
        if bancontact_status not in ["SUCCEEDED", "AUTHORIZATION_FAILED", "FAILED", "EXPIRED", "CANCELLED"]:
            return http.Response(status=204)

        self._notify_pos(pos_config, bancontact_id, bancontact_status)

        return http.Response(status=200)

    def _notify_pos(self, pos_config, bancontact_id, bancontact_status):
        pos_config._notify(
            "BANCONTACT_PAY_PAYMENTS_NOTIFICATION",
            {
                "bancontact_id": bancontact_id,
                "bancontact_status": bancontact_status,
            },
        )
