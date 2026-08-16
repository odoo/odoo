import logging

from odoo import http

_logger = logging.getLogger(__name__)


class PeppolAuthentication(http.Controller):

    @http.route('/peppol/authentication/callback', type='http', methods=['GET'], auth='user', sitemap=False)
    def peppol_authentication_callback(self, auth_type=None, connect_token=None, auth_token=None, state=None, **kwargs):
        conn_data = http.request.env['res.company'].sudo()._peppol_decode_connect_token(connect_token)
        if not conn_data:
            _logger.warning("Invalid Peppol auth token (auth_type=%s)", auth_type)
        elif state in ('pending', 'canceled'):
            _logger.info("Peppol callback decision %s decision (auth_type=%s)", state, auth_type)
        elif not auth_token:
            _logger.warning("Peppol registration auth_token missing (auth_type=%s)", auth_type)
        else:
            try:
                conn_data['company'].sudo()._peppol_create_connection(conn_data['peppol_identifier'], auth_token=auth_token)
            except Exception as e:  # noqa: BLE001
                _logger.warning("Failed to cereate Peppol connection: %s", e)
        return http.request.redirect('/web')

    @http.route('/peppol/authentication/webhook', type='http', methods=['POST'], auth='public', csrf=False, save_session=False)
    def peppol_authentication_webhook(self, auth_type=None, connect_token=None, auth_token=None, **kwargs):
        connect_data = http.request.env['res.company'].sudo()._peppol_decode_connect_token(connect_token)
        if not connect_data or not auth_token:
            _logger.warning("Invalid peppol webhook request (auth_type=%s)", auth_type)
            return http.request.make_json_response({'error': 'invalid_request'}, status=400)
        company = connect_data['company']
        peppol_user = company.sudo().account_edi_proxy_client_ids.filtered(lambda u: u.edi_format_id.code == 'peppol')
        if peppol_user:
            return http.request.make_json_response({'status': 'already_connected'})
        try:
            company.sudo()._peppol_create_connection(connect_data['peppol_identifier'], auth_token=auth_token)
        except Exception as e:  # noqa: BLE001
            _logger.warning("Peppol webhook could not create the connection: %s", e)
            return http.request.make_json_response({'status': 'failed'})
        return http.request.make_json_response({'status': 'connected'})
