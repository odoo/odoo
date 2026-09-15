import logging

from odoo import Command
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo.http import root
from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon
from odoo.addons.website_sale_mondialrelay.controllers.controllers import MondialRelay

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestMondialRelayShipping(WebsiteSaleCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.relay_data = {
            "id": "R123",
            "name": "Relay preference",
            "street": "Pickup street",
            "street2": "",
            "zip": "1000",
            "city": "Brussels",
            "country_code": "be",
        }

    def test_pickup_address_uses_contact_preference(self):
        primary = self.env["phone.number"].create(
            {"number": "+32000444006", "primary": True}
        )
        preferred = self.env["phone.number"].create(
            {"number": "+32000444007", "sequence": 100}
        )
        self.partner.write(
            {
                "phone_ids": [Command.set((primary | preferred).ids)],
                "preferred_phone_id": preferred.id,
            }
        )
        pickup = self.partner._mondialrelay_search_or_create(self.relay_data)
        _logger.debug(
            "Mondial pickup: source=%s selected=%s",
            preferred.id,
            pickup._phone_get_number().id,
        )
        self.assertEqual(pickup._phone_get_number(), preferred)

    def test_anonymous_cart_is_denied(self):
        self.cart.partner_id = self.website.user_id.partner_id
        with MockRequest(self.env, website=self.website) as req:
            req.cart = self.cart
            self.assertTrue(self.cart._is_anonymous_cart())
            _logger.debug("Mondial anonymous cart: order=%s", self.cart.id)
            with self.assertRaises(AccessDenied):
                MondialRelay().mondial_relay_update_shipping()

    def _relay_payload(self):
        return {
            "ID": self.relay_data["id"],
            "Nom": self.relay_data["name"],
            "Adresse1": self.relay_data["street"],
            "Adresse2": self.relay_data["street2"],
            "CP": self.relay_data["zip"],
            "Ville": self.relay_data["city"],
            "Pays": "BE",
        }

    def test_pickup_selection_over_http(self):
        preferred = self.env["phone.number"].create(
            {"number": "+32000444008", "sequence": 100}
        )
        self.partner.write(
            {
                "phone_ids": [
                    Command.create({"number": "+32000444009", "primary": True}),
                    Command.link(preferred.id),
                ],
                "preferred_phone_id": preferred.id,
            }
        )
        self.cart.carrier_id = self.env.ref(
            "delivery_mondialrelay.delivery_carrier_mondialrelay_be_lu"
        )
        session = self.authenticate(None, None)
        session["sale_order_id"] = self.cart.id
        root.session_store.save(session)
        result = self.call_jsonrpc(
            "/website_sale_mondialrelay/update_shipping", params=self._relay_payload()
        )
        self.cart.invalidate_recordset()
        shipping = self.cart.partner_shipping_id
        _logger.debug(
            "Mondial HTTP: pickup=%s phone=%s",
            shipping.id,
            shipping._phone_get_number().id,
        )
        self.assertEqual(result["new_partner_shipping_id"], shipping.id)
        self.assertEqual(shipping._phone_get_number(), preferred)
        self.assertEqual(shipping.ref, "MR#R123")
        self.assertIn("Relay preference", str(result["address"]))
        wizard = self.env["choose.delivery.carrier"].create(
            {"order_id": self.cart.id, "carrier_id": self.cart.carrier_id.id}
        )
        self.assertEqual(wizard.mondialrelay_last_selected_id, "BE-R123")

    def test_invalid_payload_and_carrier_cannot_change_address(self):
        original = self.cart.partner_shipping_id
        with MockRequest(self.env, website=self.website) as req:
            req.cart = self.cart
            self.cart.carrier_id = False
            with self.assertRaises(UserError):
                MondialRelay().mondial_relay_update_shipping(**self._relay_payload())
            self.cart.carrier_id = self.env.ref(
                "delivery_mondialrelay.delivery_carrier_mondialrelay_be_lu"
            )
            invalid = [
                {},
                {"ID": []},
                {"Pays": "FR"},
                {"Pays": None},
                {"Ville": " "},
                {"Adresse2": ["unsafe"]},
                {"CP": {"invalid": "shape"}},
            ]
            for changes in invalid:
                payload = {**self._relay_payload(), **changes} if changes else {}
                with self.subTest(changes=changes), self.assertRaises(UserError):
                    MondialRelay().mondial_relay_update_shipping(**payload)
                self.assertEqual(self.cart.partner_shipping_id, original)
            req.cart = self.env["sale.order"]
            with self.assertRaises(AccessDenied):
                MondialRelay().mondial_relay_update_shipping(**self._relay_payload())
            _logger.debug("Mondial invalid payloads: rejected=%s", len(invalid))

    def test_pickup_reuse_refreshes_phone_and_preserves_secondary(self):
        first = self.env["phone.number"].create({"number": "+32000444010"})
        self.partner.phone_ids = first
        pickup = self.partner._mondialrelay_search_or_create(self.relay_data)
        secondary = self.env["phone.number"].create(
            {"number": "+32000444011", "type": "emergency"}
        )
        pickup.phone_ids = [Command.link(secondary.id)]
        target = self.env["phone.number"].create(
            {"number": "+32000444012", "sequence": 100}
        )
        self.partner.write(self.partner._prepare_phone_replacement_vals(target))
        reused = self.partner._mondialrelay_search_or_create(self.relay_data)
        self.env.flush_all()
        self.env.invalidate_all()
        _logger.debug(
            "Mondial reused: pickup=%s selected=%s",
            reused.id,
            reused._phone_get_number().id,
        )
        self.assertEqual(reused, pickup)
        self.assertEqual(reused._phone_get_number(), target)
        self.assertIn(secondary, reused.phone_ids)
        self.assertNotIn(first, reused.phone_ids)

    def test_pickup_identity_includes_recipient_and_country(self):
        first = self.partner._mondialrelay_search_or_create(self.relay_data)
        sibling = self.env["res.partner"].create(
            {"name": "Sibling recipient", "parent_id": self.partner.id}
        )
        other = sibling._mondialrelay_search_or_create(self.relay_data)
        foreign = self.partner._mondialrelay_search_or_create(
            {**self.relay_data, "country_code": "fr"}
        )
        self.assertNotEqual(first, other)
        self.assertEqual(other.parent_id, sibling)
        self.assertNotEqual(first, foreign)
        self.assertEqual(foreign.country_id.code, "FR")
        duplicate = first.copy({"name": first.name})
        self.assertIn(
            self.partner._mondialrelay_search_or_create(self.relay_data),
            first | duplicate,
        )
        with self.assertRaises(ValidationError):
            self.partner._mondialrelay_search_or_create(
                {**self.relay_data, "country_code": "zz"}
            )
        _logger.debug(
            "Mondial identity: first=%s sibling=%s foreign=%s",
            first.id,
            other.id,
            foreign.id,
        )

    def test_numeric_identifiers_and_postcodes_remain_supported(self):
        payload = {**self._relay_payload(), "ID": 123, "CP": 1000}
        parsed = MondialRelay()._parse_relay_address(payload)
        _logger.debug(
            "Relay scalar normalization: id=%s postcode=%s", parsed["id"], parsed["zip"]
        )
        self.assertEqual(parsed["id"], "123")
        self.assertEqual(parsed["zip"], "1000")
        self.assertEqual(payload["ID"], 123)
