import json
import logging

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import hash_sign

_logger = logging.getLogger(__name__)


class PeppolAuthentication(http.Controller):

    @http.route('/peppol/authentication/callback', type='http', methods=['GET'], auth='user')
    def peppol_authentication_callback(self, auth_type, connect_token, auth_token=None, err=None):
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

        # if the auth_token is unauthorized, it means the user doesn't have the correct credentials to activate peppol for that company,
        # or there is an issue with the company's data on the CBE
        if auth_token == 'unauthorized':
            try:
                err = json.loads(err)
            except json.JSONDecodeError:
                err = {}
                _logger.error("Failed to decode error json")

            base_url = self.env['ir.config_parameter'].sudo().get_str('web.base.url')
            payload = {
                'company_id': connect_data['company'].id,
                'err_msg': err.get('message', "Failed to Verify your company's data"),
                'state': auth_token,
                'reason': err.get('reason'),
            }

            url_hash = hash_sign(
                env=self.env(su=True),
                scope='peppol_activation',
                message_values=payload,
                expiration_hours=24,
            )

            return request.redirect(f"{base_url}/peppol/activate/{auth_type}/{url_hash}/1")

        peppol_identifier = connect_data['peppol_identifier']
        db_uuid = request.env['ir.config_parameter'].get_str('database.uuid')
        company = connect_data['company']
        try:
            request.env['peppol.registration'].sudo()._create_connection(peppol_identifier, db_uuid, company, auth_token=auth_token)
        except UserError as e:
            _logger.warning("Could not create proxy user auth_type=%s connect_token=%s auth_token=%s", auth_type, connect_token, auth_token)
            return redirect(success=False, partner=partner, error_message=str(e))

        return redirect(success=True, partner=partner)
