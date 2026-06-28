# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon


@tagged("-at_install", "post_install")
class TestPaymentMethod(PaymentCommon):
    def test_prevent_unlinking_payment_method_unknown(self):
        pm_unknown = self.env["payment.method"].create({
            "name": "Unknown",
            "code": "unknown",
            "provider_id": self.provider.id,
        })
        with self.assertRaises(UserError):
            pm_unknown.unlink()

    def test_brand_compatible_with_manual_capture(self):
        """Test that a "brand" can be enabled for providers which support manual capture."""
        self.provider.update({"capture_manually": True, "support_manual_capture": "partial"})
        self.payment_method.support_manual_capture = "partial"
        brand_payment_method = self.env["payment.method"].create({
            "name": "Dummy Brand",
            "code": "dumbrand",
            "primary_payment_method_id": self.payment_method.id,
            "active": False,
            "provider_id": self.provider.id,
        })
        self._assert_does_not_raise(ValidationError, brand_payment_method.action_unarchive)
        self.assertTrue(brand_payment_method.active)
