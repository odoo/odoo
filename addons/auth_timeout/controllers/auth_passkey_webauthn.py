from odoo import http
from odoo.addons.auth_passkey.controllers import main as auth_passkey_main


class WebauthnController(auth_passkey_main.WebauthnController):
    # `/auth/passkey/start-auth` must be `check_identity=False`
    # because it's used to start an authentication upon authentication with a passkey,
    # which is used when the user needs to check its identity using a passkey
    @http.route(check_identity=False)
    def json_start_authentication(self):
        return super().json_start_authentication()
