from odoo import http
from odoo.http import request


class PeppolWebhookController(http.Controller):

    @http.route(
        '/peppol/webhook/new-message',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def webhook_new_message(self, token):
        edi_client = request.env['account_edi_proxy_client.user']._get_user_from_token(token, url=request.httprequest.url)

        cron = request.env.ref(
            'account_peppol.ir_cron_peppol_get_new_documents',
            raise_if_not_found=False,
        )
        if edi_client and cron:
            cron.sudo()._trigger()

        return http.Response(status=204)

    @http.route(
        '/peppol/webhook/message-state-update',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def webhook_message_update(self, token):
        edi_client = request.env['account_edi_proxy_client.user']._get_user_from_token(token, url=request.httprequest.url)

        cron = request.env.ref(
            'account_peppol.ir_cron_peppol_get_message_status',
            raise_if_not_found=False,
        )
        if edi_client and cron:
            cron.sudo()._trigger()

        return http.Response(status=204)

    @http.route(
        '/peppol/webhook/user-state-update',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def webhook_user_update(self, token):
        edi_client = request.env['account_edi_proxy_client.user']._get_user_from_token(token, url=request.httprequest.url)

        cron = request.env.ref(
            'account_peppol.ir_cron_peppol_get_participant_status',
            raise_if_not_found=False,
        )
        if edi_client and cron:
            cron.sudo()._trigger()

        return http.Response(status=204)
