from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestEgressPolicy(TransactionCase):
    def _session(self, purpose):
        return self.env["ir.egress"].session(purpose=purpose, policy="private")

    def test_a_purpose_that_is_not_sensitive_goes_out(self):
        self.assertTrue(self._session("iap.olg.editor"))

    def test_a_sensitive_purpose_leaves_nothing_before_a_session_opens(self):
        self.env.ref("gateway_ml.purpose_iap_olg").sensitive = True
        with self.assertRaises(UserError) as caught:
            self._session("iap.olg.editor")
        self.assertIn("iap.olg.editor", str(caught.exception))

    def test_a_purpose_the_gateway_does_not_declare_is_not_governed(self):
        self.env.ref("gateway_ml.purpose_iap_olg").sensitive = True
        purposes = self.env["gateway.ml.purpose"].with_context(active_test=False)
        count = purposes.search_count([])
        self.assertTrue(self._session("iap"))
        self.assertEqual(purposes.search_count([]), count)
