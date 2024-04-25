import json
from base64 import urlsafe_b64encode

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.utils import _get_login_redirect_url

from ..lib.duo_labs.webauthn import options_to_json


class WebauthnController(http.Controller):
    @http.route(['/auth/passkey/start-registration'], type='json', auth='user')
    def json_start_registration(self):
        registration_options = request.env['auth.passkey.key']._create_registration_options()
        request.session.webauthn_challenge = registration_options.challenge
        return json.loads(options_to_json(registration_options))

    @http.route(['/auth/passkey/verify-registration'], type='json', auth='user')
    def json_verify_registration(self, registration):
        verification = request.env['auth.passkey.key']._verify_registration_options(
            registration,
            request.session.pop('webauthn_challenge'),
        )
        return {'credentialId': urlsafe_b64encode(verification.credential_id),
                'credentialPublicKey': urlsafe_b64encode(verification.credential_public_key)}

    @http.route(['/auth/passkey/start-auth'], type='json', auth='public')
    def json_start_authentication(self):
        auth_options = request.env['auth.passkey.key']._start_auth()
        request.session.webauthn_challenge = auth_options.challenge
        return json.loads(options_to_json(auth_options))

    @http.route(['/auth/passkey/verify-auth'], type='json', auth='public')
    def json_verify_authentication(self, auth):
        auth_key = request.env['auth.passkey.key']._verify_auth(auth, request.session.pop('webauthn_challenge'))
        request.session.pre_login = auth_key.create_uid.login
        request.session.pre_uid = auth_key.create_uid.id
        request.session.finalize(request.env)
        return {
            'status': 'ok',
            'redirect_url': _get_login_redirect_url(auth_key.create_uid.id)
        }
