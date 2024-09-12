# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.mail.tests.common import MailCommon


@odoo.tests.tagged("-at_install", "post_install")
class TestControllerCommon(HttpCaseWithUserDemo, MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_portal_user()
        cls.user_public = cls.env.ref("base.public_user")
        cls.guest = cls.env["mail.guest"].create({"name": "Guest"})

    def _authenticate_user(self, user, guest):
        if not user or user == self.user_public:
            self.authenticate(None, None)
        else:
            self.authenticate(user.login, user.login)
        if guest:
            self.opener.cookies[guest._cookie_name] = guest._format_auth_cookie()
