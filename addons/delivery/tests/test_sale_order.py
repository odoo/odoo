import logging

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestSaleOrder(SaleCommon):
    def test_avoid_setting_pickup_location_as_default_delivery_address(self):
        self._create_partner(
            type="delivery", parent_id=self.partner.id, is_pickup_location=True
        )
        so = self.env["sale.order"].create({"partner_id": self.partner.id})
        self.assertFalse(so.partner_shipping_id.is_pickup_location)

    def test_remove_delivery_line_resets_pickup_location_data(self):
        """A stale pickup location must not survive a carrier change.

        Nothing else in this module keeps `pickup_location_data` in sync with
        `carrier_id`, so `_remove_delivery_line` -- the method every carrier
        change goes through via `set_delivery_line` -- must reset it itself.
        """
        so = self.env["sale.order"].create({"partner_id": self.partner.id})
        so.pickup_location_data = {"name": "Stale pickup point"}
        so._remove_delivery_line()
        self.assertFalse(so.pickup_location_data)

    def test_pickup_confirmation_keeps_customer_phone_preference(self):
        primary = self.env["phone.number"].create(
            {"number": "+32000444001", "primary": True}
        )
        preferred = self.env["phone.number"].create(
            {"number": "+32000444002", "sequence": 100}
        )
        self.partner.write(
            {
                "phone_ids": [Command.set((primary | preferred).ids)],
                "preferred_phone_id": preferred.id,
            }
        )
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        order.pickup_location_data = {
            "name": "Pickup preference",
            "street": "Pickup street",
            "city": "Brussels",
            "zip_code": "1000",
            "country_code": "BE",
        }
        order._action_confirm()
        _logger.debug(
            "Pickup phone: source=%s selected=%s",
            preferred.id,
            order.partner_shipping_id._phone_get_number().id,
        )
        self.assertTrue(order.partner_shipping_id.is_pickup_location)
        self.assertEqual(order.partner_shipping_id._phone_get_number(), preferred)
        self.assertEqual(self.partner.phone_ids, primary | preferred)

        pickup = order.partner_shipping_id
        target = self.env["phone.number"].create(
            {"number": "+32000444013", "sequence": 200}
        )
        self.partner.write(self.partner._prepare_phone_replacement_vals(target))
        second_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "partner_shipping_id": self.partner.id,
                "pickup_location_data": order.pickup_location_data,
            }
        )
        second_order._action_confirm()
        self.assertEqual(second_order.partner_shipping_id, pickup)
        self.assertEqual(pickup._phone_get_number(), target)

    def test_pickup_does_not_reuse_an_ordinary_or_different_postcode_address(self):
        ordinary = self._create_partner(
            name="Pickup identity",
            type="delivery",
            parent_id=self.partner.id,
            street="Same street",
            city="Brussels",
            zip="1000",
            country_id=self.env.ref("base.be").id,
        )
        wrong_zip = ordinary.copy(
            {"name": ordinary.name, "zip": "2000", "is_pickup_location": True}
        )
        order = self.env["sale.order"].create(
            {"partner_id": self.partner.id, "partner_shipping_id": self.partner.id}
        )
        order.pickup_location_data = {
            "name": ordinary.name,
            "street": "Same street",
            "city": "Brussels",
            "zip_code": "1000",
            "country_code": "BE",
        }
        order._action_confirm()
        _logger.debug(
            "Pickup identity: selected=%s ordinary=%s other_postcode=%s",
            order.partner_shipping_id.id,
            ordinary.id,
            wrong_zip.id,
        )
        self.assertNotIn(order.partner_shipping_id, ordinary | wrong_zip)
        self.assertTrue(order.partner_shipping_id.is_pickup_location)
        self.assertEqual(order.partner_shipping_id.zip, "1000")
        self.assertFalse(ordinary.is_pickup_location)

    def test_pickup_country_and_payload_shape_are_validated(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        original = order.partner_shipping_id
        for payload in (
            ["invalid shape"],
            {
                "street": "Pickup street",
                "city": "Brussels",
                "zip_code": "1000",
                "country_code": "ZZ",
            },
        ):
            with self.subTest(payload=payload):
                order.pickup_location_data = payload
                _logger.debug("Pickup invalid payload: type=%s", type(payload).__name__)
                with self.assertRaises(UserError):
                    order._action_confirm()
                self.assertEqual(order.partner_shipping_id, original)

    def test_pickup_reconfirmation_does_not_nest_recipient_addresses(self):
        order = self._create_so()
        order.pickup_location_data = {
            "name": "Reconfirmed pickup",
            "street": "Pickup street",
            "city": "Brussels",
            "zip_code": "1000",
            "country_code": "BE",
        }
        order.action_confirm()
        pickup = order.partner_shipping_id
        order.action_cancel()
        order.action_draft()
        order.action_confirm()
        _logger.debug(
            "Pickup reconfirm: original=%s current=%s parent=%s",
            pickup.id,
            order.partner_shipping_id.id,
            order.partner_shipping_id.parent_id.id,
        )
        self.assertEqual(order.partner_shipping_id, pickup)
        self.assertEqual(pickup.parent_id, self.partner)

    def test_pickup_optional_fields_reject_malformed_values(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        for field in ("name", "state"):
            with self.subTest(field=field):
                payload = {
                    "name": "Pickup",
                    "street": "Pickup street",
                    "city": "Brussels",
                    "zip_code": "1000",
                    "country_code": "BE",
                    field: {"bad": "shape"},
                }
                _logger.debug("Pickup optional input: field=%s", field)
                with self.assertRaises(UserError):
                    order._get_pickup_address_values(payload)
