import odoo
from odoo.addons.web.tests.test_js import unit_test_error_checker


@odoo.tests.tagged("post_install", "-at_install")
class ExternalTestSuite(odoo.tests.HttpCase):
    def test_external_livechat(self):
        # webclient external test suite
        self.browser_js(
            "/web/tests/livechat?headless&loglevel=2&preset=desktop",
            "",
            "",
            login='admin',
            timeout=1800,
<<<<<<< b07f657e62e5978ea5c33f87e44aafc1a8b6d9c4
            success_signal="[HOOT] test suite succeeded",
            error_checker=unit_test_error_checker,
||||||| c5222a82887b6c5c781fe823865e2573c14e8b7b
            success_signal="[HOOT] test suite succeeded",
            error_checker=unit_test_error_checker
=======
            success_signal="[HOOT] Test suite succeeded",
            error_checker=unit_test_error_checker
>>>>>>> 1f1a4947d00f3e635af5a143a7509f7ee9daa042
        )
