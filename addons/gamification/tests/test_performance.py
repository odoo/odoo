from odoo.addons.web.tests.test_login import TestWebLogin
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPerformance(TestWebLogin):
    def test_web_login(self):
        with self.assertQueryCount(174):  # com: 151 ; ent: 174 ; local gamification only: 126
            try:
                super().test_web_login()
            except AssertionError:
                # See `test_web_login_external`
                pass

    def test_web_login_external(self):
        with self.assertQueryCount(262):  # com: 250 ; ent: 262 ; local gamification only: 110
            try:
                super().test_web_login_external()
            except AssertionError:
                # Running this test in post_install is best practice for performance evaluation.
                # In a full installation of Odoo, other modules may alter the flow of loging in
                # (see portal's version of the test).
                # As gamification is only dependent on `base` and `mail`, we have to re-run the
                # base version of the test, with stale assertions. It doesn't matter because we
                # only care to track the number of queries necessary to reach the end.
                pass
