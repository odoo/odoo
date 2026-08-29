from psycopg.errors import UniqueViolation

from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestAddressExtendedOnchanges(TransactionCase):
    """res.city display name and res.partner city/country onchanges."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country = cls.env.ref("base.us")
        cls.state = cls.env["res.country.state"].search(
            [("country_id", "=", cls.country.id)], limit=1
        )
        cls.city = cls.env["res.city"].create(
            {
                "name": "Springfield",
                "zipcode": "62701",
                "country_id": cls.country.id,
                "state_id": cls.state.id,
            }
        )

    def test_city_display_name_with_zip(self):
        """A city with a zip shows "name (zip)"."""
        self.assertIn("Springfield (62701)", str(self.city.display_name))

    def test_city_display_name_without_zip(self):
        """A city without a zip shows only the name (boundary)."""
        city = self.env["res.city"].create(
            {"name": "Nozip", "country_id": self.country.id}
        )
        self.assertIn("Nozip", str(city.display_name))
        self.assertNotIn("(", str(city.display_name))

    def test_onchange_city_id_populates_address(self):
        """Selecting a city_id fills city, zip and state on the partner."""
        partner = self.env["res.partner"].new({"city_id": self.city.id})
        partner._onchange_city_id()
        self.assertEqual(partner.city, "Springfield")
        self.assertEqual(partner.zip, "62701")
        self.assertEqual(partner.state_id, self.state)

    def test_onchange_country_clears_mismatched_city(self):
        """Changing country to one that mismatches the city clears city_id."""
        other = self.env["res.country"].search([("id", "!=", self.country.id)], limit=1)
        partner = self.env["res.partner"].new(
            {"city_id": self.city.id, "country_id": other.id}
        )
        partner._onchange_country_id()
        self.assertFalse(partner.city_id)

    def test_onchange_country_clears_stale_city_zip_state(self):
        """Clearing a mismatched city_id also clears city/zip/state_id."""
        other = self.env["res.country"].search([("id", "!=", self.country.id)], limit=1)
        partner = self.env["res.partner"].new({"city_id": self.city.id})
        partner._onchange_city_id()
        self.assertEqual(partner.city, "Springfield")
        self.assertEqual(partner.zip, "62701")

        partner.country_id = other
        partner._onchange_country_id()
        self.assertFalse(partner.city_id)
        self.assertFalse(partner.city)
        self.assertFalse(partner.zip)
        self.assertFalse(partner.state_id)

    def test_duplicate_city_name_zip_state_country_rejected(self):
        """A second city with the same name/zip/state/country is rejected."""
        with self.assertRaises(UniqueViolation), mute_logger("odoo.db.cursor"):
            self.env["res.city"].create(
                {
                    "name": "Springfield",
                    "zipcode": "62701",
                    "country_id": self.country.id,
                    "state_id": self.state.id,
                }
            )

    def test_same_city_name_in_another_state_is_allowed(self):
        """A city name is unique within a state, not within a country.

        Four Mexican municipalities are named Benito Juarez and 273 Brazilian
        ones repeat a name across states; scoping the index by country alone
        made those datasets impossible to load.
        """
        other_state = self.env["res.country.state"].search(
            [("country_id", "=", self.country.id), ("id", "!=", self.state.id)],
            limit=1,
        )
        twin = self.env["res.city"].create(
            {
                "name": "Springfield",
                "zipcode": "62701",
                "country_id": self.country.id,
                "state_id": other_state.id,
            }
        )
        self.assertNotEqual(twin, self.city)

    def test_same_city_name_without_zip_in_another_state_is_allowed(self):
        """The zip-less shape every localization ships must survive too."""
        other_state = self.env["res.country.state"].search(
            [("country_id", "=", self.country.id), ("id", "!=", self.state.id)],
            limit=1,
        )
        first = self.env["res.city"].create(
            {
                "name": "Benito Juarez",
                "country_id": self.country.id,
                "state_id": self.state.id,
            }
        )
        second = self.env["res.city"].create(
            {
                "name": "Benito Juarez",
                "country_id": self.country.id,
                "state_id": other_state.id,
            }
        )
        self.assertNotEqual(first, second)

    def test_duplicate_city_name_in_the_same_state_without_zip_rejected(self):
        """Within one state the name is still unique, which is the point."""
        self.env["res.city"].create(
            {
                "name": "Twinsville",
                "country_id": self.country.id,
                "state_id": self.state.id,
            }
        )
        with self.assertRaises(UniqueViolation), mute_logger("odoo.db.cursor"):
            self.env["res.city"].create(
                {
                    "name": "Twinsville",
                    "country_id": self.country.id,
                    "state_id": self.state.id,
                }
            )

    def test_duplicate_city_name_country_without_zip_rejected(self):
        """A second city with no zip still collides on name/country."""
        self.env["res.city"].create({"name": "Nozip", "country_id": self.country.id})
        with self.assertRaises(UniqueViolation), mute_logger("odoo.db.cursor"):
            self.env["res.city"].create(
                {"name": "Nozip", "country_id": self.country.id}
            )

    def test_onchange_city_id_clears_on_new_record(self):
        """Unselecting city_id clears city/zip/state on a new, unsaved record too."""
        partner = self.env["res.partner"].new({})
        partner.city_id = self.city
        partner._onchange_city_id()
        self.assertEqual(partner.city, "Springfield")
        self.assertEqual(partner.zip, "62701")

        partner.city_id = False
        partner._onchange_city_id()
        self.assertFalse(partner.city)
        self.assertFalse(partner.zip)
        self.assertFalse(partner.state_id)

    def test_onchange_city_id_keeps_typed_zip_when_city_has_none(self):
        """A city with no zip must not wipe a zip the user already typed."""
        city = self.env["res.city"].create(
            {"name": "Nozipkeep", "country_id": self.country.id}
        )
        partner = self.env["res.partner"].new({"zip": "99999"})
        partner.city_id = city
        partner._onchange_city_id()
        self.assertEqual(partner.city, "Nozipkeep")
        self.assertEqual(partner.zip, "99999")

    def test_onchange_city_id_keeps_state_when_city_has_none(self):
        """A city with no state must not wipe the state already on the partner."""
        city = self.env["res.city"].create(
            {"name": "Nostatekeep", "zipcode": "12345", "country_id": self.country.id}
        )
        partner = self.env["res.partner"].new({"state_id": self.state.id})
        partner.city_id = city
        partner._onchange_city_id()
        self.assertEqual(partner.zip, "12345")
        self.assertEqual(partner.state_id, self.state)

    def test_city_formatted_display_name_shows_state(self):
        """The formatted display name appends the state, to tell homonyms apart."""
        formatted = self.city.with_context(formatted_display_name=True).display_name
        self.assertEqual(formatted, f"Springfield (62701) \t --{self.state.name}--")
        self.assertEqual(self.city.display_name, "Springfield (62701)")
