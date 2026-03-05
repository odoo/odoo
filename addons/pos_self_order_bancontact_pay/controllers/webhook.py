from odoo.addons.pos_bancontact_pay.controllers.webhook import BancontactPayController


class SelfOrderBancontactPayController(BancontactPayController):
    def _notify_pos(self, pos_config, bancontact_id, bancontact_status):
        super()._notify_pos(pos_config, bancontact_id, bancontact_status)

        if pos_config.self_ordering_mode == "kiosk":
            error = self._get_bancontact_error_message(bancontact_status)
            pos_config._notify(
                "FINALIZE_KIOSK_PAYMENT",
                {
                    "status": "success" if bancontact_status == "SUCCEEDED" else "fail",
                    "error": error,
                    "bancontact_id": bancontact_id,
                },
            )

    def _get_bancontact_error_message(self, bancontact_status):
        if bancontact_status == "CANCELLED":
            return "Payment cancelled"
        if bancontact_status == "EXPIRED":
            return "Payment expired"
        return None
