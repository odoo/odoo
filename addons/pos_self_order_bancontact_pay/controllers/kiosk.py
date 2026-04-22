from werkzeug.exceptions import Unauthorized

from odoo import _, http

from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController


class PosSelfOrderControllerBancontactPay(PosSelfOrderController):
    @http.route("/pos-self-order/create-bancontact-pay-payment", auth="public", type="jsonrpc", website=True)
    def bancontact_pay_create_payment_from_kiosk(self, access_token, payment_method_id, line_uuid, order_uuid):
        pos_config = self._verify_pos_config(access_token)
        order = pos_config.env["pos.order"].search([["uuid", "=", order_uuid]], limit=1)
        payment_method = pos_config.env["pos.payment.method"].browse(payment_method_id)

        if not order.exists or not payment_method.exists() or payment_method.payment_provider != 'bancontact_pay' or pos_config.id not in payment_method.config_ids.ids:
            raise Unauthorized()

        return payment_method.sudo().create_bancontact_payment({
            "uuid": line_uuid,
            "configId": pos_config.id,
            "amount": order.amount_total,
            "currency": order.currency_id.name,
            "description": _("Payment at %(company)s\nKiosk: %(config)s", company=pos_config.company_id.name, config=pos_config.name),
        })
