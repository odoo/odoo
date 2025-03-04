from odoo import http
from odoo.http import request

class PeppolWebhookController(http.Controller):

    @http.route(
        '/peppol/webhook/<string(length=32):user_id>/<any("new-message", "message-state-update", "user-state-update"):event>',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def message_updated(self, user_id, event):
        user = request.env['account_edi_proxy_client.user'].sudo().search([('id_client', '=', user_id)], limit=1)

        cron_name = {
            'new-message': 'account_peppol.ir_cron_peppol_get_new_documents',
            'message-state-update': 'account_peppol.ir_cron_peppol_get_message_status',
            'user-state-update': 'account_peppol.ir_cron_peppol_get_participant_status',
        }.get(event)

        cron = request.env.ref(
            cron_name,
            raise_if_not_found=False,
        )
        if user and cron:
            cron.sudo()._trigger()

        return http.Response(status=204)
