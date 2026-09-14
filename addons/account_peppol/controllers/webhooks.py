from odoo import http
from odoo.http import request


class PeppolWebhookController(http.Controller):
    @http.route(
        "/peppol/webhook/new-message",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def webhook_new_message(self, token):
        return self._admit_and_trigger(
            token,
            "peppol_new_message",
            "account_peppol.ir_cron_peppol_get_new_documents",
        )

    @http.route(
        "/peppol/webhook/message-state-update",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def webhook_message_update(self, token):
        return self._admit_and_trigger(
            token,
            "peppol_message_state_update",
            "account_peppol.ir_cron_peppol_get_message_status",
        )

    @http.route(
        "/peppol/webhook/user-state-update",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def webhook_user_update(self, token):
        return self._admit_and_trigger(
            token,
            "peppol_user_state_update",
            "account_peppol.ir_cron_peppol_get_participant_status",
        )

    def _admit_and_trigger(self, token, event_type, cron_xmlid):
        ProxyUser = request.env["account_edi_proxy_client.user"]
        edi_client = ProxyUser._get_user_from_token(token, url=request.httprequest.url)
        if ProxyUser._admit_proxy_webhook(edi_client, event_type):
            cron = request.env.ref(cron_xmlid, raise_if_not_found=False)
            if cron:
                cron.sudo()._trigger()
        return http.Response(status=204)
