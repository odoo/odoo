from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account_payment_provider.tests.common import AccountPaymentCommon


@tagged("-at_install", "post_install")
class TestPaymentProviderSetup(AccountPaymentCommon):
    def test_setup_payment_method_skips_none_and_custom(self):
        count_before = self.env["account.payment.method"].search_count([])

        self.env["payment.provider"]._setup_payment_method("none")
        self.env["payment.provider"]._setup_payment_method("custom")

        self.assertEqual(
            self.env["account.payment.method"].search_count([]),
            count_before,
            msg="_setup_payment_method should never create a method for 'none' or 'custom'.",
        )

    def test_setup_payment_method_creates_method_for_new_code(self):
        provider_model = self.env["payment.provider"]
        code_field = provider_model._fields["code"]
        with patch.object(
            code_field, "selection", [*code_field.selection, ("t2_dummy", "T2 Dummy")]
        ):
            provider_model._setup_payment_method("t2_dummy")

        method = self.env["account.payment.method"].search([("code", "=", "t2_dummy")])
        self.assertEqual(len(method), 1)
        self.assertEqual(method.payment_type, "inbound")
        self.assertEqual(method.name, "T2 Dummy")

    def test_setup_payment_method_is_idempotent(self):
        provider_model = self.env["payment.provider"]
        code_field = provider_model._fields["code"]
        with patch.object(
            code_field, "selection", [*code_field.selection, ("t2_dummy", "T2 Dummy")]
        ):
            provider_model._setup_payment_method("t2_dummy")
            provider_model._setup_payment_method("t2_dummy")

        self.assertEqual(
            self.env["account.payment.method"].search_count(
                [("code", "=", "t2_dummy")]
            ),
            1,
            msg="Calling _setup_payment_method twice for the same new code should not "
            "create a duplicate method.",
        )

    def test_has_existing_payment_false_when_method_unused(self):
        self.assertFalse(
            self.provider._has_existing_payment(self.dummy_provider_method)
        )

    def test_has_existing_payment_true_when_payment_uses_method(self):
        method_line = self.provider.journal_id.inbound_payment_channel_ids.filtered(
            lambda l: l.payment_provider_id == self.provider
        )
        self.env["account.payment"].create(
            {"payment_channel_id": method_line.id, "amount": 10}
        )

        self.assertTrue(
            self.provider._has_existing_payment(method_line.payment_method_id)
        )

    def test_remove_provider_blocked_when_payments_exist(self):
        method_line = self.provider.journal_id.inbound_payment_channel_ids.filtered(
            lambda l: l.payment_provider_id == self.provider
        )
        self.env["account.payment"].create(
            {"payment_channel_id": method_line.id, "amount": 10}
        )

        with self.assertRaises(UserError):
            self.env["payment.provider"]._remove_provider(self.provider.code)

    def test_remove_provider_unlinks_method_when_no_payments_exist(self):
        provider_model = self.env["payment.provider"]
        code_field = provider_model._fields["code"]
        with patch.object(
            code_field, "selection", [*code_field.selection, ("t2_dummy", "T2 Dummy")]
        ):
            provider_model._setup_payment_method("t2_dummy")
            method = self.env["account.payment.method"].search(
                [("code", "=", "t2_dummy")]
            )
            self.assertTrue(method)

            provider_model._remove_provider("t2_dummy")

        self.assertFalse(method.exists())
