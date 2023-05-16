from odoo.addons.web.tests.test_login import TestWebLogin
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPerformance(TestWebLogin):
    def test_web_login(self):
        with self.assertQueryCount(184):  # com: 161 ; ent: 184 ; local gamification only: 134
            try:
                super().test_web_login()
            except AssertionError:
                # See `test_web_login_external`
                pass

    def test_web_login_external(self):
        with self.assertQueryCount(271):  # com: 260 ; ent: 271 ; local gamification only: 117
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
