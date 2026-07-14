import logging

from odoo import http, SUPERUSER_ID
from odoo.http import request
from odoo.tools import verify_hash_signed

_logger = logging.getLogger(__name__)


class BaseVatWebhookController(http.Controller):
    @http.route('/base_vat/1/webhook_update_vies', type='http', csrf=False, save_session=False, auth='public')
    def webhook_update_vies(self, webhook_token, status):
        """
        Webhook called by IAP when it updates a status from the pending state.
        The webhook_token is computed by the Odoo db (in _compute_vies_valid) and stored
        on IAP such that only IAP can call this webhook.
        """
        if not (vat := verify_hash_signed(request.env(su=True), 'vies_check', webhook_token)):
            _logger.warning("VIES update failed: webhook_token does not match.")
            return

        partners = request.env["res.partner"].with_user(SUPERUSER_ID).search([("vat", "=", vat)])
        partners._update_vies_status(status)
