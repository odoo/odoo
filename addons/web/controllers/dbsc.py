from __future__ import annotations

import logging
import secrets
import jwt
from http import HTTPStatus

from werkzeug.exceptions import BadRequest, Forbidden, Unauthorized
from werkzeug.http import quote_header_value

from odoo import http
from odoo.http import Controller, Response, request
from odoo.http.session import SESSION_LIFETIME, get_device, session_store
from odoo.tools.misc import frozendict
from .home import Home

_logger = logging.getLogger('odoo.dbsc')


def get_jwt_challenge(jw_token: str, jw_key: dict, alg: str) -> str | None:
    if not (jw_token and jw_key and alg):
        return

    try:
        public_key = jwt.PyJWK.from_dict(jw_key).key  # Check `kty`
        payload = jwt.decode(jw_token, key=public_key, algorithms=[alg])
        return payload.get('jti')
    except jwt.PyJWTError:
        _logger.warning("Cryptographic verification failed", exc_info=True)


class DBSCAuthController(Home):

    @http.route()
    def web_login(self, *args, **kw):
        response = super().web_login(*args, **kw)
        session = request.session
        if session.uid and request.env['ir.config_parameter'].sudo().get_bool('web.dbsc'):
            session['dbsc_challenge'] = challenge = secrets.token_urlsafe()
            path = quote_header_value('/dbsc/register')
            challenge = quote_header_value(challenge, allow_token=False)
            response.headers['Secure-Session-Registration'] = f'(ES256 RS256); path={path}; challenge={challenge}'
        return response


class DBSCController(Controller):

    # The required authentication to use DBSC API routes must be `'none'` to
    # prevent the HTTP stack from returning a response that would not be
    # interpreted correctly by the API.
    # A specific example is a redirect when the refresh route is accessed, which
    # would cause the deferred requests to remain pending and never be resolved.

    @http.route('/dbsc/register', type='http', auth='none', methods=['POST'], csrf=False)
    def dbsc_register(self, **kw):
        session = request.session
        if not session.uid:
            raise Unauthorized()

        token = request.httprequest.headers.get('Secure-Session-Response')
        if not token:
            raise BadRequest("Missing Secure-Session-Response header")

        jwt_header = jwt.get_unverified_header(token)
        jwk_dict = jwt_header.get('jwk') or frozendict()
        alg = jwt_header.get('alg', 'ES256')

        expected_challenge = session.get('dbsc_challenge')
        challenge = get_jwt_challenge(token, jwk_dict, alg)
        if not (
            expected_challenge and challenge
            and secrets.compare_digest(challenge, expected_challenge)
        ):
            raise Forbidden()

        session_store().make_dbsc_public_key(session, jwk=jwk_dict, alg=alg)

        response = request.make_json_response({
            'session_identifier': secrets.token_urlsafe(),
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
        response.set_cookie('dbsc', '1', max_age=SESSION_LIFETIME, secure=True, httponly=True)
        return response

    @http.route('/dbsc/refresh', type='http', auth='none', methods=['POST'], csrf=False)
    def dbsc_refresh(self, **kw):
        session = request.session
        if not session.uid:
            raise Unauthorized()

        if not request.env['ir.config_parameter'].sudo().get_bool('web.dbsc'):
            raise Forbidden()

        public_key = session_store().get_dbsc_public_key(session)
        if not public_key:
            raise Forbidden()

        dbsc_id = quote_header_value(request.httprequest.headers.get('Sec-Secure-Session-Id'), allow_token=False)
        token = request.httprequest.headers.get('Secure-Session-Response')
        if not token:
            session['dbsc_challenge'] = challenge = secrets.token_urlsafe()
            response = Response(status=HTTPStatus.FORBIDDEN)
            challenge = quote_header_value(session['_dbsc_challenge'], allow_token=False)
            response.headers['Secure-Session-Challenge'] = f'{challenge}; id={dbsc_id}'
            return response

        expected_challenge = session.get('dbsc_challenge')
        challenge = get_jwt_challenge(token, public_key['jwk'], public_key['alg'])
        if not (
            expected_challenge and challenge
            and secrets.compare_digest(challenge, expected_challenge)
        ):
            raise Forbidden()

        session.pop('dbsc_challenge')

        current_device = get_device(session, request)
        current_device['trusted'] = True

        response = Response(status=HTTPStatus.OK)
        response.set_cookie('dbsc', '1', max_age=SESSION_LIFETIME, secure=True, httponly=True)
        return response
