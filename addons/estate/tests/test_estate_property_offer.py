# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.estate.tests.common import EstateCommon


@tagged("post_install", "-at_install")
class TestEstatePropertyOffer(EstateCommon):
    def test_first_offer_marks_property_as_offer_received(self):
        self._create_offer(95000)
        self.assertEqual(self.property.state, "offer_received")

    def test_offer_below_best_offer_is_refused(self):
        self._create_offer(95000)
        with self.assertRaises(UserError):
            self._create_offer(94000, partner=self.other_buyer)

    def test_property_with_accepted_offer_refuses_new_offers(self):
        self._create_offer(95000).action_accept()
        with self.assertRaises(UserError):
            self._create_offer(99000, partner=self.other_buyer)

    def test_accepting_offer_sets_buyer_and_selling_price(self):
        self._create_offer(95000).action_accept()
        self.assertEqual(
            (self.property.partner_id, self.property.selling_price), (self.buyer, 95000)
        )

    def test_second_offer_cannot_be_accepted(self):
        first_offer = self._create_offer(95000)
        second_offer = self._create_offer(96000, partner=self.other_buyer)
        first_offer.action_accept()
        with self.assertRaises(UserError):
            second_offer.action_accept()

    def test_accepted_offer_cannot_be_refused(self):
        offer = self._create_offer(95000)
        offer.action_accept()
        with self.assertRaises(UserError):
            offer.action_refuse()

    def test_deadline_is_validity_days_after_creation(self):
        offer = self._create_offer(95000)
        offer.validity = 10
        expected_deadline = fields.Date.add(fields.Date.to_date(offer.create_date), days=10)
        self.assertEqual(offer.date_deadline, expected_deadline)

    def test_editing_deadline_updates_validity(self):
        offer = self._create_offer(95000)
        offer.date_deadline = fields.Date.add(fields.Date.to_date(offer.create_date), days=30)
        self.assertEqual(offer.validity, 30)
