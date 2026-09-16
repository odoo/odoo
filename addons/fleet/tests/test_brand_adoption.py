from unittest.mock import patch

from lxml import etree

from odoo.tests import TransactionCase, tagged
from odoo.tools import file_path

from odoo.addons.fleet import hooks


@tagged("post_install", "-at_install")
class TestBrandAdoption(TransactionCase):
    def _adopt(self, declared):
        with patch.object(hooks, "_declared_brands", return_value=declared):
            return hooks.adopt_existing_manufacturers(self.env.cr)

    def test_an_existing_manufacturer_of_the_same_name_takes_the_brand_xmlid(self):
        partner = self.env["res.partner"].create(
            {"name": "Adopted Motors", "is_manufacturer": True}
        )
        self.assertEqual(self._adopt([("brand_adopted_probe", "adopted motors")]), 1)
        self.assertEqual(
            self.env.ref("fleet.brand_adopted_probe"),
            partner,
            "the data file must update this partner rather than create a twin",
        )

    def test_a_name_nobody_carries_is_left_to_the_data_file(self):
        self.assertEqual(self._adopt([("brand_absent_probe", "Absent Motors")]), 0)
        self.assertFalse(
            self.env.ref("fleet.brand_absent_probe", raise_if_not_found=False)
        )

    def test_a_partner_that_is_no_manufacturer_is_not_adopted(self):
        self.env["res.partner"].create({"name": "Customer Motors"})
        self.assertEqual(self._adopt([("brand_customer_probe", "Customer Motors")]), 0)

    def test_one_partner_answers_to_one_brand(self):
        self.env["res.partner"].create({"name": "Twin Motors", "is_manufacturer": True})
        declared = [
            ("brand_twin_one_probe", "Twin Motors"),
            ("brand_twin_two_probe", "Twin Motors"),
        ]
        self.assertEqual(self._adopt(declared), 1)
        self.assertFalse(
            self.env.ref("fleet.brand_twin_two_probe", raise_if_not_found=False)
        )

    def test_the_catalog_is_seed_data(self):
        root = etree.parse(file_path(hooks._BRAND_DATA)).getroot()
        self.assertEqual(
            root.get("noupdate"),
            "1",
            "an upgrade must not write the shipped logo and name back over the "
            "ones a database keeps for a brand it already had",
        )

    def test_every_shipped_brand_declares_a_name(self):
        declared = hooks._declared_brands()
        self.assertTrue(declared)
        self.assertFalse([xmlid for xmlid, name in declared if not name])
        self.assertEqual(
            len({xmlid for xmlid, _name in declared}),
            len(declared),
            "an xml id declared twice would adopt twice",
        )
