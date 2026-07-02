import logging

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


class PeppolAuthentication(http.Controller):

    @http.route('/peppol/authentication/callback', type='http', methods=['GET'], auth='user')
    def peppol_authentication_callback(self, auth_type, connect_token, auth_token=None):
        """ Route called by the Proxy Server after authentication."""
        def redirect(success=True, partner=None, error_message=None):
            if partner:
                # Notify the root/initial window of the authentication result. See JS service "peppol_auth_service".
                partner._bus_send("peppol_auth_channel", {'auth_result': 'success' if success else 'failure', 'error_message': error_message})
                # Action to close the window opened for authentication
            return request.redirect_query('/odoo/peppol-auth-callback-action', query={'success': success})

        connect_data = request.env['peppol.registration']._decode_connect_token(connect_token)
        if not connect_data:
            _logger.warning("Invalid request token auth_type=%s connect_token=%s auth_token=%s", auth_type, connect_token, auth_token)
            return redirect(success=False)

        partner = connect_data['partner']
        if not auth_token:
            _logger.warning("Invalid auth token auth_type=%s connect_token=%s auth_token=%s", auth_type, connect_token, auth_token)
            return redirect(success=False, partner=partner)

        peppol_identifier = connect_data['peppol_identifier']
        db_uuid = request.env['ir.config_parameter'].get_str('database.uuid')
        company = connect_data['company']
        try:
            request.env['peppol.registration'].sudo()._create_connection(peppol_identifier, db_uuid, company, auth_token=auth_token)
        except UserError as e:
            _logger.warning("Could not create proxy user auth_type=%s connect_token=%s auth_token=%s", auth_type, connect_token, auth_token)
            return redirect(success=False, partner=partner, error_message=str(e))

        return redirect(success=True, partner=partner)

    @http.route('/peppol/authentication/webhook', type='http', methods=['POST'], auth='public', csrf=False, save_session=False)
    def peppol_authentication_webhook(self, auth_type, connect_token, auth_token=None):
        """webhook called by IAP on KYC decision.

        Finalizes the registration automatically so the user does not have to return to
        their browser.
        """
        connect_data = request.env['peppol.registration'].sudo()._decode_connect_token(connect_token)
        if not connect_data or not auth_token:
            _logger.warning("Invalid peppol auth webhook auth_type=%s connect_token=%s", auth_type, connect_token)
            return request.make_json_response({'error': 'invalid_request'}, status=400)

        company = connect_data['company']
        # connection may already have been finalized from the browser callback
        if company.sudo().account_peppol_edi_user:
            return request.make_json_response({'status': 'already_connected'})

        db_uuid = request.env['ir.config_parameter'].sudo().get_str('database.uuid')
        try:
            request.env['peppol.registration'].sudo()._create_connection(
                connect_data['peppol_identifier'], db_uuid, company, auth_token=auth_token,
            )
        except UserError as e:
            _logger.warning("Peppol auth webhook could not create proxy user connect_token=%s error=%s", connect_token, e)
            # the user can still finalize from the emailed callback link.
            return request.make_json_response({'status': 'failed'})

        connect_data['partner']._bus_send("peppol_auth_channel", {'auth_result': 'success'})
        return request.make_json_response({'status': 'connected'})
