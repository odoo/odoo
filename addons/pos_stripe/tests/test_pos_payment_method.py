from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon

SEND_API_REQUEST = "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request"


@tagged("post_install", "-at_install")
class TestStripePaymentMethod(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["payment.provider"].create({"name": "Stripe Test", "code": "stripe", "company_id": cls.env.company.id})
        cls.stripe_payment_method = cls.env["pos.payment.method"].create({
            "name": "Stripe",
            "payment_provider": "stripe",
            "stripe_serial_number": "WSC513105011295",
            "payment_method_type": "terminal",
            "journal_id": cls.bank_journal.id,
        })

    def test_account_mcc(self):
        for account, mcc in [
            ({"business_profile": {"mcc": "5812"}}, "5812"),
            ({"business_profile": {"mcc": None}}, False),
            ({"business_profile": None}, False),
        ]:
            with self.subTest(account=account), patch(SEND_API_REQUEST, return_value=account) as mock_request:
                self.assertEqual(self.stripe_payment_method.stripe_account_mcc(), mcc)
                self.assertEqual(mock_request.call_args.args, ("GET", "account"))

    def test_access_requires_pos_user(self):
        user = new_test_user(self.env, login="no_pos_user", groups="base.group_user")
        with patch(SEND_API_REQUEST) as mock_request, self.assertRaises(AccessError):
            self.stripe_payment_method.with_user(user).stripe_account_mcc()
        mock_request.assert_not_called()
