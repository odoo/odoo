# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import BaseCommon


class EstateCommon(BaseCommon):
    """Shared fixtures; BaseCommon runs each test as an internal user (`base.group_user`)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.buyer = cls.env["res.partner"].create({"name": "Buyer"})
        cls.other_buyer = cls.env["res.partner"].create({"name": "Other Buyer"})
        cls.property = cls.env["estate.property"].create({
            "name": "Test House",
            "expected_price": 100000,
            "living_area": 80,
        })

    def _create_offer(self, price, partner=None, estate_property=None):
        return self.env["estate.property.offer"].create({
            "property_id": (estate_property or self.property).id,
            "partner_id": (partner or self.buyer).id,
            "price": price,
        })
