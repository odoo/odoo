from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestDonationProductTemplate(BaseCommon):
    def test_donation_product_can_be_archived(self):
        donation_product = self.env.ref("website_sale.product_donation")
        donation_product.write({"active": False})
        self.assertFalse(donation_product.active)

    def test_donation_product_can_not_be_deleted(self):
        donation_product = self.env.ref("website_sale.product_donation")
        self.assertRaises(UserError, donation_product.unlink)
