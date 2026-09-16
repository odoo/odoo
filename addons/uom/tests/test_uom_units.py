from odoo.addons.uom.tests.common import UomCommon


class TestPowerAndFuelEfficiency(UomCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.watt = cls.quick_ref("uom.product_uom_wat")
        cls.kw = cls.quick_ref("uom.product_uom_kw")
        cls.mw = cls.quick_ref("uom.product_uom_mw")
        cls.hp = cls.quick_ref("uom.product_uom_hp")
        cls.kmpl = cls.quick_ref("uom.product_uom_km_per_liter")
        cls.mpg = cls.quick_ref("uom.product_uom_miles_per_galon")

    def test_one_mpg_is_the_metric_ratio_not_its_reciprocal(self):
        self.assertAlmostEqual(
            self.mpg._get_quantity_in_unit(1.0, self.kmpl, round=False),
            1.609344 / 3.785411784,
            places=9,
        )

    def test_one_km_per_liter_in_mpg(self):
        self.assertAlmostEqual(
            self.kmpl._get_quantity_in_unit(1.0, self.mpg, round=False),
            3.785411784 / 1.609344,
            places=9,
        )

    def test_one_horsepower_in_kilowatts(self):
        self.assertAlmostEqual(
            self.hp._get_quantity_in_unit(1.0, self.kw, round=False),
            0.74569987158227,
            places=9,
        )

    def test_the_power_units_are_decimal_multiples_of_the_watt(self):
        self.assertAlmostEqual(
            self.kw._get_quantity_in_unit(1.0, self.watt, round=False), 1000.0
        )
        self.assertAlmostEqual(
            self.mw._get_quantity_in_unit(1.0, self.watt, round=False), 1000000.0
        )

    def test_the_power_units_use_si_symbols(self):
        """The seeded names are what users read in every dropdown and report.

        They shipped as `w`, `Kw`, `Mw` and `Km/l`, none of which is the SI
        symbol, and the fuel-efficiency setting offered a third spelling again.
        """
        expected = {
            "uom.product_uom_wat": "W",
            "uom.product_uom_kw": "kW",
            "uom.product_uom_mw": "MW",
            "uom.product_uom_km_per_liter": "km/L",
        }
        for xml_id, name in expected.items():
            with self.subTest(xml_id=xml_id):
                unit = self.quick_ref(xml_id).with_context(lang="en_US")
                self.assertEqual(unit.name, name)
