import json
from base64 import urlsafe_b64encode

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home, CREDENTIAL_PARAMS

from ..lib.duo_labs.webauthn import options_to_json


CREDENTIAL_PARAMS.append('webauthn_response')


class WebauthnController(http.Controller):
    @http.route(['/auth/passkey/start-auth'], type='json', auth='public')
    def json_start_authentication(self):
        auth_options = request.env['auth.passkey.key']._start_auth()
        request.session.webauthn_challenge = auth_options.challenge
        return json.loads(options_to_json(auth_options))
