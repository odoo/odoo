from odoo import http


class AuthTOTPMailController(http.Controller):

    @http.route("/auth-timeout/send-totp-mail-code", type="jsonrpc", auth="user", check_identity=False)
    def send_totp_mail_code(self):
        """JSON route to trigger the sending of the TOTP code by email when requested by the user in the interface."""
        self.env.user._send_totp_mail_code()
