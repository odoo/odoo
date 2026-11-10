from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import CREDENTIAL_PARAMS


CREDENTIAL_PARAMS.append('webauthn_response')


class WebauthnController(http.Controller):
    @http.route(['/auth/passkey/start-auth'], type='json', auth='public')
    def json_start_authentication(self):
        auth_options = request.env['auth.passkey.key']._start_auth()
        return auth_options

    @http.route(['/.well-known/webauthn'], type='http', auth='public')
    def web_well_known_webauthn(self):
        return request.make_json_response({
            "origins": request.env['auth.passkey.key']._get_allowed_origins()
        })
