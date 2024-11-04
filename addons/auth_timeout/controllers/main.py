from odoo import http
from odoo.http import request


class AuthTimeOutController(http.Controller):
    @http.route(
        "/auth-timeout/check-identity", type="http", auth="user", website=True, sitemap=False, check_identity=False
    )
    def check_identity(self, redirect=None):
        """Display the authentication form in a page. Used when an HTTP call raises a `CheckIdentityException`."""
        return request.render("auth_timeout.check_identity", {"redirect": redirect})

    # Cannot be readonly because checking the identity can lead to some data being written
    # e.g. totp rate limit during a totp by mail
    @http.route("/auth-timeout/session/check-identity", type="jsonrpc", auth="user", check_identity=False)
    def check_identity_session(self, **kwargs):
        """JSON route used to receive the authentication form sent by the user."""
        return request.env["ir.http"]._check_identity(kwargs)

    @http.route("/auth-timeout/send-totp-mail-code", type="jsonrpc", auth="user", check_identity=False)
    def send_totp_mail_code(self):
        """JSON route to trigger the sending of the TOTP code by email when requested by the user in the interface."""
        self.env.user._send_totp_mail_code()
