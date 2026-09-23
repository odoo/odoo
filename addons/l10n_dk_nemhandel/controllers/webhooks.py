from odoo import http
from odoo.http import request


class NemhandelWebhookController(http.Controller):
    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        "/nemhandel/webhook/new-message",
        type="http",
        auth="receiver",
        receiver="account_edi_proxy_client.user:_receiver_for_proxy_webhook",
        receiver_event="nemhandel_new_message",
        methods=["POST"],
        csrf=False,
        typed=True,
    )
    def webhook_nemhandel_new_message(self, token: str):
        return self._trigger("l10n_dk_nemhandel.ir_cron_nemhandel_get_new_documents")

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        "/nemhandel/webhook/message-state-update",
        type="http",
        auth="receiver",
        receiver="account_edi_proxy_client.user:_receiver_for_proxy_webhook",
        receiver_event="nemhandel_message_state_update",
        methods=["POST"],
        csrf=False,
        typed=True,
    )
    def webhook_nemhandel_message_update(self, token: str):
        return self._trigger("l10n_dk_nemhandel.ir_cron_nemhandel_get_message_status")

    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        "/nemhandel/webhook/user-state-update",
        type="http",
        auth="receiver",
        receiver="account_edi_proxy_client.user:_receiver_for_proxy_webhook",
        receiver_event="nemhandel_user_state_update",
        methods=["POST"],
        csrf=False,
        typed=True,
    )
    def webhook_nemhandel_user_update(self, token: str):
        return self._trigger(
            "l10n_dk_nemhandel.ir_cron_nemhandel_get_participant_status"
        )

    def _trigger(self, cron_xmlid):
        request.env["ir.cron"]._trigger_ref(cron_xmlid)
        return http.Response(status=204)
