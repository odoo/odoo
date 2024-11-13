from odoo.addons.mail.tests.common_controllers import MailControllerCommon


class TestPortalControllerCommon(MailControllerCommon):
    def _get_sign_token_params(self, record):
        access_token = record._portal_ensure_token()
        partner = record.env["res.partner"].create({"name": "Sign Partner"})
        _hash = record._sign_token(partner.id)
        token = {"token": access_token}
        bad_token = {"token": "incorrect token"}
        sign = {"hash": _hash, "pid": partner.id}
        bad_sign = {"hash": "incorrect hash", "pid": partner.id}
        return token, bad_token, sign, bad_sign, partner
