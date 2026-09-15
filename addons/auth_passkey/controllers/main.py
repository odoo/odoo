from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import CREDENTIAL_PARAMS
from ..mobile_utils import _WEB_WELL_KNOW_ANDROID


CREDENTIAL_PARAMS.append('webauthn_response')


class WebauthnController(http.Controller):
    @http.route(['/auth/passkey/start-auth'], type='jsonrpc', auth='public')
    def json_start_authentication(self):
        auth_options = request.env['auth.passkey.key']._start_auth()
        return auth_options

    @http.route(['/.well-known/assetlinks.json'], type='http', auth='public')
    def web_well_known_android(self):
        return request.make_json_response(_WEB_WELL_KNOW_ANDROID, {
            'Content-Type': 'application/json'
        })
