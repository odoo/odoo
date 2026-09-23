from odoo import http
from odoo.http import request


class PeppolWebhookController(http.Controller):
    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        "/peppol/webhook/new-message",
        type="http",
        auth="receiver",
        receiver="account_edi_proxy_client.user:_receiver_for_proxy_webhook",
        receiver_event="peppol_new_message",
        methods=["POST"],
        csrf=False,
        typed=True,
    )
    def webhook_new_message(self, token: str):
        return self._trigger("account_peppol.ir_cron_peppol_get_new_documents")

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        "/peppol/webhook/message-state-update",
        type="http",
        auth="receiver",
        receiver="account_edi_proxy_client.user:_receiver_for_proxy_webhook",
        receiver_event="peppol_message_state_update",
        methods=["POST"],
        csrf=False,
        typed=True,
    )
    def webhook_message_update(self, token: str):
        return self._trigger("account_peppol.ir_cron_peppol_get_message_status")

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        "/peppol/webhook/user-state-update",
        type="http",
        auth="receiver",
        receiver="account_edi_proxy_client.user:_receiver_for_proxy_webhook",
        receiver_event="peppol_user_state_update",
        methods=["POST"],
        csrf=False,
        typed=True,
    )
    def webhook_user_update(self, token: str):
        return self._trigger("account_peppol.ir_cron_peppol_get_participant_status")

    def _trigger(self, cron_xmlid):
        request.env["ir.cron"]._trigger_ref(cron_xmlid)
        return http.Response(status=204)
