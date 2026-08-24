# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("phone_validation", "post_install", "-at_install")
class TestPartnerPhoneWriteFormat(TransactionCase):
    """Phone/mobile numbers must be formatted on every write path.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_de = cls.env.ref("base.de")
        cls.raw_phone = "030 1234567"
        cls.raw_mobile = "0151 23456789"

    def _expected(self, fname, raw):
        """Value the interactive form (onchange) would have produced."""
        partner = self.env["res.partner"].new(
            {"country_id": self.country_de.id, fname: raw}
        )
        if fname == "phone":
            partner._onchange_phone_validation()
        else:
            partner._onchange_mobile_validation()
        return partner[fname]

    def test_create_formats_phone(self):
        """A number set through create() is formatted, not stored raw."""
        partner = self.env["res.partner"].create(
            {
                "name": "Checkout Customer",
                "country_id": self.country_de.id,
                "phone": self.raw_phone,
            }
        )
        self.assertEqual(partner.phone, self._expected("phone", self.raw_phone))
        self.assertNotEqual(
            partner.phone,
            self.raw_phone,
            "Phone stored unformatted: create() bypassed phone formatting.",
        )

    def test_create_formats_mobile(self):
        """Mobile set through create() is formatted too."""
        partner = self.env["res.partner"].create(
            {
                "name": "Checkout Customer",
                "country_id": self.country_de.id,
                "mobile": self.raw_mobile,
            }
        )
        self.assertEqual(
            partner.mobile, self._expected("mobile", self.raw_mobile)
        )

    def test_write_formats_phone(self):
        """A number set through write() is formatted, not stored raw."""
        partner = self.env["res.partner"].create(
            {"name": "Checkout Customer", "country_id": self.country_de.id}
        )
        partner.write({"phone": self.raw_phone})
        self.assertEqual(partner.phone, self._expected("phone", self.raw_phone))

    def test_write_formats_mobile(self):
        """Mobile follows the same rule as phone on write()."""
        partner = self.env["res.partner"].create(
            {"name": "Checkout Customer", "country_id": self.country_de.id}
        )
        partner.write({"mobile": self.raw_mobile})
        self.assertEqual(
            partner.mobile, self._expected("mobile", self.raw_mobile)
        )

    def test_write_uses_country_from_vals(self):
        """When country is changed in the same write, it is used to format."""
        partner = self.env["res.partner"].create({"name": "Roaming Customer"})
        partner.write(
            {"country_id": self.country_de.id, "phone": self.raw_phone}
        )
        self.assertEqual(partner.phone, self._expected("phone", self.raw_phone))

    def test_orm_write_matches_onchange(self):
        """Programmatic write must match the interactive onchange result.
        """
        via_write = self.env["res.partner"].create(
            {
                "name": "Consistency",
                "country_id": self.country_de.id,
                "phone": self.raw_phone,
            }
        )
        self.assertEqual(
            via_write.phone,
            self._expected("phone", self.raw_phone),
            "Programmatic write and interactive onchange produced different "
            "phone formatting - the write path is inconsistent.",
        )

    def test_invalid_number_is_left_untouched(self):
        """Unparseable input must not raise and must be preserved as-is."""
        partner = self.env["res.partner"].create(
            {
                "name": "Bad Number",
                "country_id": self.country_de.id,
                "phone": "notaphone",
            }
        )
        self.assertEqual(partner.phone, "notaphone")

    def test_no_country_no_crash(self):
        """Without a record country, formatting must degrade gracefully."""
        partner = self.env["res.partner"].create(
            {"name": "No Country", "phone": "+49 30 1234567"}
        )
        self.assertTrue(partner.phone.startswith("+49"))

    def test_empty_phone_write_is_noop(self):
        """Clearing a number must not be turned into a formatted value."""
        partner = self.env["res.partner"].create(
            {
                "name": "Clear Me",
                "country_id": self.country_de.id,
                "phone": self.raw_phone,
            }
        )
        partner.write({"phone": False})
        self.assertFalse(partner.phone)
