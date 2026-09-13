from __future__ import annotations

import secrets
from http import HTTPStatus

from werkzeug.exceptions import Forbidden
from werkzeug.http import quote_header_value

from odoo import http
from odoo.http import Controller, Response, request
from odoo.http.session import SESSION_LIFETIME, STORED_SESSION_BYTES, get_device


class DBSCController(Controller):

    # We should not update session information during the registration because
    # the browser controls the call to this endpoint, and there may be concurrent requests.
    @http.route('/dbsc/register', type='http', auth='user', methods=['POST'], csrf=False)
    def dbsc_register(self, **kw):
        session = request.session

        device_dbsc = request.env['res.device.dbsc']._dbsc_register(
            session.sid[:STORED_SESSION_BYTES],
            request.httprequest.headers.get('Secure-Session-Response'),
            session.get('dbsc_register_challenge'),
        )
        if not device_dbsc:
            raise Forbidden()

        response = request.make_json_response({
            'session_identifier': device_dbsc.session_identifier,
            'refresh_url': '/dbsc/refresh',
            'scope': {
                'origin': request.httprequest.host_url.rstrip('/'),
                'include_site': False,
                'scope_specification': [
                    {'type': 'include', 'path': '/'},
                    # Refresh url is automatically exclude to prevent infinite loop
                ],
            },
            'credentials': [
                {'type': 'cookie', 'name': 'dbsc', 'attributes': 'Path=/; Secure; HttpOnly'},
            ],
        })
        response.set_cookie('dbsc', '', max_age=0)  # Trigger a refresh directly to mark the session
        return response

    # We can update the session because there is no concurrent requests.
    # The browser defers and resolves them according to the response from that endpoint.
    @http.route('/dbsc/refresh', type='http', auth='user', methods=['POST'], csrf=False)
    def dbsc_refresh(self, **kw):
        session = request.session

        if not request.env['ir.config_parameter'].sudo().get_bool('web.dbsc'):
            raise Forbidden()

        session_identifier = request.httprequest.headers.get('Sec-Secure-Session-Id')
        if session.sid[:STORED_SESSION_BYTES] != session_identifier:
            raise Forbidden()

        device_dbsc = request.env['res.device.dbsc'].search([
            ('session_identifier', '=', session_identifier)
        ], limit=1)
        if not device_dbsc:
            raise Forbidden()

        session['dbsc'] = True  # Mark the session DBSC linked
        session.pop('dbsc_register_challenge', None)  # Consume register challenge

        jws = request.httprequest.headers.get('Secure-Session-Response')
        if not (jws and 'dbsc_refresh_challenge' in session):
            session['dbsc_refresh_challenge'] = challenge = secrets.token_urlsafe()
            response = Response(status=HTTPStatus.FORBIDDEN)
            challenge = quote_header_value(challenge, allow_token=False)
            session_identifier = quote_header_value(session_identifier, allow_token=False)
            response.headers['Secure-Session-Challenge'] = f'{challenge}; id={session_identifier}'
            return response

        if not device_dbsc._dbsc_refresh(jws, session['dbsc_refresh_challenge']):
            raise Forbidden()

        session.pop('dbsc_refresh_challenge')  # Single use challenge
        current_device = get_device(session, request)
        current_device['dbsc_trusted'] = True

        response = Response(status=HTTPStatus.OK)
        response.set_cookie('dbsc', '1', max_age=SESSION_LIFETIME, secure=True, httponly=True)
        return response
