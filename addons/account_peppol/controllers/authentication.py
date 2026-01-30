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
        db_uuid = request.env['ir.config_parameter'].get_param('database.uuid')
        company = connect_data['company']
        try:
            request.env['peppol.registration'].sudo()._create_connection(peppol_identifier, db_uuid, company, auth_token=auth_token)
        except UserError as e:
            _logger.warning("Could not create proxy user auth_type=%s connect_token=%s auth_token=%s", auth_type, connect_token, auth_token)
            return redirect(success=False, partner=partner, error_message=str(e))

        return redirect(success=True, partner=partner)
