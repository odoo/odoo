import logging

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


class PeppolAuthentication(http.Controller):

    @http.route('/peppol/authentication/callback', type='http', methods=['GET'], auth='user')
    def peppol_authentication_callback(self, auth_type, connect_token, auth_token=None, state=None):
        """ Route called by the Proxy Server after authentication."""
        def redirect(auth_result='success', partner=None, error_message=None):
            if partner:
                partner._bus_send("peppol_auth_channel", {'auth_result': auth_result, 'error_message': error_message})
            # to avoid showing the accounting settings again (otherwise user will just be redirected
            # to not completed "Register with Peppol" page and will be confused)
            if auth_result == 'pending':
                return request.redirect('/odoo')
            else:
                return request.redirect('/odoo/settings/#account')

        state = state or 'success'
        connect_data = request.env['peppol.registration']._decode_connect_token(connect_token)
        if not connect_data:
            _logger.warning("Invalid request token auth_type=%s connect_token=%s auth_token=%s", auth_type, connect_token, auth_token)
            return redirect('failure')

        partner = connect_data['partner']

        # The user aborted the authentication on the IAP side with back button
        if state == 'canceled':
            return redirect('canceled', partner=partner)

        # The manual KYC/KYB decision is asynchronous, this is the "redirection" from IAP when KYC is not yet validated
        if state == 'pending':
            return redirect('pending', partner=partner)

        if not auth_token:
            _logger.warning("Invalid auth token auth_type=%s connect_token=%s auth_token=%s", auth_type, connect_token, auth_token)
            return redirect('failure', partner=partner)

        peppol_identifier = connect_data['peppol_identifier']
        db_uuid = request.env['ir.config_parameter'].get_str('database.uuid')
        company = connect_data['company']
        try:
            request.env['peppol.registration'].sudo()._create_connection(peppol_identifier, db_uuid, company, auth_token=auth_token)
        except UserError as e:
            _logger.warning("Could not create proxy user auth_type=%s connect_token=%s auth_token=%s", auth_type, connect_token, auth_token)
            return redirect('failure', partner=partner, error_message=str(e))

        return redirect('success', partner=partner)

    @http.route('/peppol/authentication/webhook', type='http', methods=['POST'], auth='public', csrf=False, save_session=False)
    def peppol_authentication_webhook(self, auth_type, connect_token, auth_token=None):
        """webhook called by IAP on positive KYC decision.

        Finalizes the registration automatically
        """
        connect_data = request.env['peppol.registration'].sudo()._decode_connect_token(connect_token)
        if not connect_data or not auth_token:
            _logger.warning("Invalid peppol auth webhook auth_type=%s connect_token=%s", auth_type, connect_token)
            return request.make_json_response({'error': 'invalid_request'}, status=400)

        company = connect_data['company']
        # connection may already have been finalized from the browser callback
        if company.sudo().account_peppol_edi_user:
            return request.make_json_response({'status': 'already_connected'})

        db_uuid = request.env['ir.config_parameter'].sudo().get_param('database.uuid')
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
