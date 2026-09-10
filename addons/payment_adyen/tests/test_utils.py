# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment_adyen import utils as adyen_utils
from odoo.addons.payment_adyen.tests.common import AdyenCommon


@tagged("post_install", "-at_install")
class TestAdyenUtils(AdyenCommon):
    @mute_logger("odoo.addons.payment_adyen.models.payment_transaction")
    def test_no_information_missing_from_partner_address(self):
        test_partner = self.env["res.partner"].create({
            "name": "Dummy Partner",
            "email": "norbert.buyer@example.com",
            "phone": "0032 12 34 56 78",
        })
        test_address = adyen_utils.format_partner_address(test_partner)
        for key in ("city", "country", "stateOrProvince", "street"):
            self.assertTrue(test_address.get(key))
