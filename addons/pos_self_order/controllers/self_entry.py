# -*- coding: utf-8 -*-
import werkzeug

from odoo import http, fields
from odoo.http import request
from .utils import is_pairing_required, check_kiosk_access


class PosSelfKiosk(http.Controller):
    @http.route(["/pos-self/<config_id>", "/pos-self/<config_id>/<path:subpath>"], auth="public", website=True, sitemap=True)
    def start_self_ordering(self, config_id=None, access_token=None, table_identifier=None, order_identifier=None, subpath=None):
        pos_config, _, config_access_token = self._verify_index_access(config_id, access_token, table_identifier)
        display_pairing_mode = self._is_pairing_mode(pos_config)
        return request.render(
                'pos_self_order.index',
                {
                    'access_token': config_access_token,
                    'session_info': {
                        **request.env["ir.http"].get_frontend_session_info(),
                        'bus_info': request.env["ir.http"]._get_bus_session_info(),
                        'currencies': request.env["res.currency"].get_all_currencies(),
                        'data': {
                            'config_id': pos_config.id,
                            'self_ordering_mode': pos_config.self_ordering_mode,
                        },
                        "base_url": request.env['pos.session'].get_base_url(),
                        "db": request.env.cr.dbname,
                    },
                    'pos_config_id': pos_config.id,
                    'pos_session_id': pos_config.current_session_id.id if pos_config.has_active_session else 0,  # Use 0 when there's no active session; False becomes empty when rendered via t-out
                    "pairing_mode": display_pairing_mode,
                },
        )

    @http.route("/pos-self/data/<config_id>", type='jsonrpc', auth='public', website=True)
    def get_self_ordering_data(self, config_id=None, access_token=None, table_identifier=None):
        pos_config, _, config_access_token = self._verify_data_access(config_id, access_token, table_identifier)
        data = pos_config.load_self_data()
        data['pos.config']['records'][0]['access_token'] = config_access_token
        return data

    @http.route('/pos-self-kiosk/pairing/<config_id>', type='jsonrpc', auth='public')
    def kiosk_pairing_request_code(self, config_id, access_token, **kwargs):
        """Request a pairing code for a kiosk device."""
        pos_config = self._verify_pairing_access(config_id, access_token)

        if not is_pairing_required(pos_config, request):
            return {'already_paired': True}

        pairing_request, pairing_session_key = self._get_current_pairing_request(pos_config)
        if not pairing_request:
            ip = request.httprequest.remote_addr
            user_agent = request.httprequest.user_agent.string
            pairing_request = pos_config.env['pos_self_order.kiosk.pairing.request'].sudo()._create_request(config_id=pos_config, ip_address=ip, user_agent=user_agent)
            self._setup_pairing_request(pairing_request, **kwargs)
            request.session[pairing_session_key] = pairing_request.id

        return {
            'pairing_code': pairing_request.pairing_code,
            'expires_in': int((pairing_request.expiration_date - fields.Datetime.now()).total_seconds()),
        }

    def _setup_pairing_request(self, pairing_request, **kwargs):
        # Setup additional fields on the pairing request if needed.
        pass

    @http.route('/pos-self-kiosk/pairing/<config_id>/status', type='jsonrpc', auth='public', methods=['POST'])
    def kiosk_pairing_request_status(self, config_id, access_token):
        """Polled by the kiosk device while waiting for an admin to approve the pairing code."""
        pos_config = self._verify_pairing_access(config_id, access_token)
        pairing_request, _ = self._get_current_pairing_request(pos_config)

        if not pairing_request:
            return {'status': 'invalid'}

        if pairing_request.approved:
            pairing_request.device_id._set_auth_cookie(request)
            # Don't clear the session, as multiple tabs can try to fetch the status (to avoid creating a new code)
            return {'status': 'approved'}

        return {'status': 'waiting'}

    def _verify_pairing_access(self, config_id, access_token):
        pos_config, _, config_access_token = self._verify_index_access(config_id, access_token, None)
        if not config_access_token or pos_config.self_ordering_mode != 'kiosk':
            raise werkzeug.exceptions.Forbidden()

        return pos_config

    def _get_current_pairing_request(self, pos_config):
        session_key = f'kiosk_pairing_{pos_config.id}_id'
        pairing_request_id = request.session.get(session_key)
        if not pairing_request_id:
            return None, session_key

        pairing_request = pos_config.env['pos_self_order.kiosk.pairing.request'].sudo().browse(pairing_request_id).exists()
        if not pairing_request or pairing_request.is_expired():
            return None, session_key

        if pairing_request.approved:
            pairing_request.device_id._set_auth_cookie(request)

        return pairing_request, session_key

    def _is_pairing_mode(self, pos_config):
        """Determine whether the initial page render should show the pairing screen instead of the default UI."""
        is_pairing_mode = is_pairing_required(pos_config, request)
        if is_pairing_mode:
            # If the user refreshes the page before receiving the pairing status,
            # set the auth cookie if the pairing has already been approved.
            pairing_request, _ = self._get_current_pairing_request(pos_config)
            if pairing_request and pairing_request.approved:
                is_pairing_mode = False
        return is_pairing_mode

    def _verify_index_access(self, config_id=None, access_token=None, table_identifier=None):
        table_sudo = False

        if not config_id or not config_id.isnumeric():
            raise werkzeug.exceptions.NotFound()

        if access_token:
            config_access_token = True
            pos_config_sudo = request.env["pos.config"].sudo().search([
                ("id", "=", config_id), ('access_token', '=', access_token)], limit=1)
        else:
            config_access_token = False
            pos_config_sudo = request.env["pos.config"].sudo().search([
                ("id", "=", config_id)], limit=1)

        if not pos_config_sudo or pos_config_sudo.self_ordering_mode == 'nothing':
            raise werkzeug.exceptions.NotFound()

        company = pos_config_sudo.company_id
        user = pos_config_sudo.self_ordering_default_user_id
        pos_config = pos_config_sudo.sudo(False).with_company(company).with_user(user).with_context(allowed_company_ids=company.ids, lang=request.cookies.get('frontend_lang'))

        if not pos_config:
            raise werkzeug.exceptions.NotFound()

        if pos_config and pos_config.self_ordering_mode == 'mobile':
            table_sudo = table_identifier and (
                request.env["restaurant.table"]
                .sudo()
                .search([("identifier", "=", table_identifier), ("active", "=", True)], limit=1)
            )
            if table_sudo and table_sudo.parent_id:
                table_sudo = table_sudo.parent_id
        # In mobile mode, always set config_access_token (needed for notification), even without an active session
        if config_access_token and pos_config.self_ordering_mode in ['kiosk', 'mobile']:
            config_access_token = pos_config.access_token
        else:
            config_access_token = ''

        table = table_sudo.sudo(False).with_company(company).with_user(user) if table_sudo else False
        return pos_config, table, config_access_token

    def _verify_data_access(self, config_id=None, access_token=None, table_identifier=None):
        pos_config, table, config_access_token = self._verify_index_access(config_id, access_token, table_identifier)
        check_kiosk_access(pos_config, request)
        return pos_config, table, config_access_token
