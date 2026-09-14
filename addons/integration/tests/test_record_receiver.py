from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "integration")
class TestRecordReceiver(TransactionCase):
    def _for_record(self, name, purpose=None):
        with self.enter_registry_test_mode():
            return self.env["integration.receiver"]._for_record(
                self.env.company, name, purpose=purpose
            )

    def test_one_record_keeps_one_receiver_per_purpose(self):
        first = self._for_record("First flow", purpose="first_flow")
        second = self._for_record("Second flow", purpose="second_flow")

        self.assertNotEqual(first, second)
        self.assertEqual(self._for_record("Renamed", purpose="first_flow"), first)
        self.assertEqual(
            (first.res_model, first.res_id, first.res_purpose),
            ("res.company", self.env.company.id, "first_flow"),
        )
        self.assertNotEqual(first.code, second.code)
        self.assertEqual(first.auth_type, "caller_check")

    def test_a_receiver_without_purpose_is_not_a_purposed_one(self):
        plain = self._for_record("Plain")

        self.assertNotEqual(plain, self._for_record("Purposed", purpose="x"))
        self.assertFalse(plain.res_purpose)
