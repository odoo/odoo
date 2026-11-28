# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon


@tagged("-at_install", "post_install")
class TestPaymentMethod(PaymentCommon):
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
