# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.estate.tests.common import EstateCommon


@tagged("post_install", "-at_install")
class TestEstateProperty(EstateCommon):
    def test_total_area_adds_living_and_garden_areas(self):
        self.property.garden_area = 20
        self.assertEqual(self.property.total_area, 100)

    def test_best_price_is_the_highest_offer(self):
        self._create_offer(91000)
        self._create_offer(95000, partner=self.other_buyer)
        self.assertEqual(self.property.best_price, 95000)

    def test_property_without_accepted_offer_cannot_be_sold(self):
        self._create_offer(95000)
        with self.assertRaises(UserError):
            self.property.action_sold()

    def test_cancelled_property_cannot_be_sold(self):
        self.property.action_cancel()
        with self.assertRaises(UserError):
            self.property.action_sold()

    def test_sold_property_cannot_be_cancelled(self):
        self._create_offer(95000).action_accept()
        self.property.action_sold()
        with self.assertRaises(UserError):
            self.property.action_cancel()

    def test_offer_below_90_percent_of_expected_price_cannot_be_accepted(self):
        offer = self._create_offer(89000)
        with self.assertRaises(ValidationError):
            offer.action_accept()

    def test_expected_price_cannot_exceed_accepted_price_by_more_than_10_percent(self):
        self._create_offer(95000).action_accept()
        with self.assertRaises(ValidationError):
            self.property.expected_price = 110000

    def test_property_with_offers_cannot_be_deleted(self):
        self._create_offer(95000)
        with self.assertRaises(UserError):
            self.property.unlink()

    def test_cancelled_property_can_be_deleted(self):
        self.property.action_cancel()
        self.property.unlink()
        self.assertFalse(self.property.exists())
