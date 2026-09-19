from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import common


class TestFiscalPosition(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fp = cls.env["account.fiscal.position"]

        cls.fp.search([]).write({"auto_apply": False})

        cls.res_partner = cls.env["res.partner"]
        cls.be = be = cls.env.ref("base.be")
        cls.fr = fr = cls.env.ref("base.fr")
        cls.mx = mx = cls.env.ref("base.mx")
        cls.eu = cls.env.ref("base.europe")
        cls.nl = cls.env.ref("base.nl")
        cls.us = cls.env.ref("base.us")
        cls.state_fr = cls.env["res.country.state"].create(
            {"name": "State", "code": "ST", "country_id": fr.id}
        )
        cls.jc = cls.res_partner.create(
            {"name": "JCVD", "vat": "BE0477472701", "country_id": be.id}
        )
        cls.ben = cls.res_partner.create({"name": "BP", "country_id": be.id})
        cls.george = cls.res_partner.create(
            {"name": "George", "vat": "BE0477472701", "country_id": fr.id}
        )
        cls.alberto = cls.res_partner.create(
            {"name": "Alberto", "vat": "ZUÑ920208KL4", "country_id": mx.id}
        )
        cls.be_nat = cls.fp.create(
            {"name": "BE-NAT", "auto_apply": True, "country_id": be.id, "sequence": 10}
        )
        cls.fr_b2b = cls.fp.create(
            {
                "name": "EU-VAT-FR-B2B",
                "auto_apply": True,
                "country_id": fr.id,
                "vat_required": True,
                "sequence": 40,
            }
        )
        cls.fr_b2c = cls.fp.create(
            {
                "name": "EU-VAT-FR-B2C",
                "auto_apply": True,
                "country_id": fr.id,
                "sequence": 50,
            }
        )

    def test_10_fp_country(self):
        def assert_fp(partner, expected_pos, message):
            self.assertEqual(
                self.fp._get_fiscal_position(partner).id, expected_pos.id, message
            )

        self.assertFalse(self.ben.vat)
        assert_fp(
            self.ben,
            self.be_nat,
            "BE-NAT should match before EU-INTRA due to lower sequence",
        )

        fr_b2b_zip100 = self.fr_b2b.copy({"zip_from": 0, "zip_to": 5000, "sequence": 1})
        self.george.zip = 6000
        assert_fp(
            self.george, self.fr_b2b, "FR-B2B with wrong zip range should not match"
        )
        self.george.zip = 1234
        assert_fp(self.george, fr_b2b_zip100, "FR-B2B with ok zip range should match")
        self.george.zip = None

        fr_b2b_state = self.fr_b2b.copy(
            {"state_ids": [(4, self.state_fr.id)], "sequence": 1}
        )
        assert_fp(self.george, self.fr_b2b, "FR-B2B with states should not match")
        self.george.state_id = self.state_fr
        assert_fp(self.george, fr_b2b_state, "FR-B2B with states should match")

        self.george.property_account_position_id = self.be_nat
        assert_fp(self.george, self.be_nat, "Forced position has max precedence")

    def _create_tax_group_for_company(self, country):
        self.env.company.country_id = country
        return self.env["account.tax.group"].create(
            {
                "name": "Test Tax Group",
                "company_ids": [Command.set(self.env.company.ids)],
            }
        )

    def test_20_fp_one_tax_2m(self):
        self._create_tax_group_for_company(self.us)

        self.src_tax = self.env["account.tax"].create({"name": "SRC", "amount": 0.0})

        self.fp2m = self.fp.create(
            {
                "name": "FP-TAX2TAXES",
            }
        )

        self.dst1_tax = self.env["account.tax"].create(
            {
                "name": "DST1",
                "amount": 0.0,
                "fiscal_position_ids": [Command.set(self.fp2m.ids)],
                "original_tax_ids": [Command.set(self.src_tax.ids)],
                "sequence": 10,
            }
        )
        self.dst2_tax = self.env["account.tax"].create(
            {
                "name": "DST2",
                "amount": 0.0,
                "fiscal_position_ids": [Command.set(self.fp2m.ids)],
                "original_tax_ids": [Command.set(self.src_tax.ids)],
                "sequence": 5,
            }
        )
        mapped_taxes = self.fp2m.map_tax(self.src_tax)

        self.assertEqual(mapped_taxes, self.dst1_tax | self.dst2_tax)

    def test_map_tax_and_account_from_an_onchange_record(self):
        self._create_tax_group_for_company(self.us)
        src_tax = self.env["account.tax"].create({"name": "SRC-NEW", "amount": 7.0})
        fpos = self.fp.create({"name": "FP-NEWID"})
        dst_tax = self.env["account.tax"].create(
            {
                "name": "DST-NEW",
                "amount": 9.0,
                "fiscal_position_ids": [Command.set(fpos.ids)],
                "original_tax_ids": [Command.set(src_tax.ids)],
            }
        )
        self.assertEqual(fpos.map_tax(src_tax), dst_tax)

        draft_tax = self.env["account.tax"].new(origin=src_tax)
        self.assertFalse(draft_tax.id, "the probe must be a NewId record")
        self.assertEqual(
            fpos.map_tax(draft_tax),
            dst_tax,
            msg="a NewId tax must map like the record it originates from",
        )

        src_account, dst_account = self.env["account.account"].create(
            [
                {"name": "SRC-ACC", "code": "FPNEW1", "account_type": "income"},
                {"name": "DST-ACC", "code": "FPNEW2", "account_type": "income"},
            ]
        )
        fpos.account_ids = [
            Command.create(
                {"account_src_id": src_account.id, "account_dest_id": dst_account.id}
            )
        ]
        self.assertEqual(fpos.map_account(src_account), dst_account)

        draft_account = self.env["account.account"].new(origin=src_account)
        self.assertEqual(
            fpos.map_account(draft_account),
            dst_account,
            msg="a NewId account must map like the record it originates from",
        )

    def test_30_fp_delivery_address(self):
        self.env.company.vat = "BE0477472701"
        self.env.company.country_id = self.be

        self.env["account.fiscal.position"].search([]).auto_apply = False

        fp_be_nat = self.env["account.fiscal.position"].create(
            {
                "name": "Régime National",
                "auto_apply": True,
                "country_id": self.be.id,
                "vat_required": True,
                "sequence": 10,
            }
        )
        fp_eu_intra = self.env["account.fiscal.position"].create(
            {
                "name": "Régime Intra-Communautaire",
                "auto_apply": True,
                "country_group_id": self.eu.id,
                "vat_required": True,
                "sequence": 20,
            }
        )
        fp_eu_priv = self.env["account.fiscal.position"].create(
            {
                "name": "EU privé",
                "auto_apply": True,
                "country_group_id": self.eu.id,
                "sequence": 30,
            }
        )
        fp_eu_extra = self.env["account.fiscal.position"].create(
            {
                "name": "Régime Extra-Communautaire",
                "auto_apply": True,
                "sequence": 40,
            }
        )

        partner_be_vat = self.env["res.partner"].create(
            {
                "name": "BE VAT",
                "vat": "BE0477472701",
                "country_id": self.be.id,
            }
        )
        partner_nl_vat = self.env["res.partner"].create(
            {
                "name": "NL VAT",
                "vat": "NL123456782B90",
                "country_id": self.nl.id,
            }
        )
        partner_nl_no_vat = self.env["res.partner"].create(
            {
                "name": "NL NO VAT",
                "country_id": self.nl.id,
            }
        )
        partner_us_no_vat = self.env["res.partner"].create(
            {
                "name": "US NO VAT",
                "country_id": self.us.id,
            }
        )

        self.assertEqual(
            self.env["account.fiscal.position"]._get_fiscal_position(
                partner_be_vat, partner_nl_vat
            ),
            fp_be_nat,
        )

        self.assertEqual(
            self.env["account.fiscal.position"]._get_fiscal_position(
                partner_nl_vat, partner_be_vat
            ),
            fp_be_nat,
        )

        self.assertEqual(
            self.env["account.fiscal.position"]._get_fiscal_position(
                partner_be_vat, partner_nl_no_vat
            ),
            fp_be_nat,
        )

        self.assertEqual(
            self.env["account.fiscal.position"]._get_fiscal_position(
                partner_nl_vat, partner_nl_vat
            ),
            fp_eu_intra,
        )

        self.assertEqual(
            self.env["account.fiscal.position"]._get_fiscal_position(
                partner_nl_no_vat, partner_nl_no_vat
            ),
            fp_eu_priv,
        )

        self.assertEqual(
            self.env["account.fiscal.position"]._get_fiscal_position(
                partner_us_no_vat, partner_us_no_vat
            ),
            fp_eu_extra,
        )

    def test_domestic_fp_map_self(self):
        self._create_tax_group_for_company(self.us)
        fp = self.env["account.fiscal.position"].create(
            {
                "name": "FP Self",
            }
        )
        tax = self.env["account.tax"].create(
            {
                "name": "Source Dest Tax",
                "amount": 10,
                "fiscal_position_ids": [Command.link(fp.id)],
            }
        )
        self.assertEqual(fp.map_tax(tax), tax)

    def test_domestic_fp(self):
        country_group, a_country_group = self.env["res.country.group"].create(
            [
                {
                    "name": "One country group",
                },
                {
                    "name": "Alphabetically first country_group",
                },
            ]
        )
        my_country = self.env["res.country"].create(
            {
                "name": "Neverland",
                "code": "PP",
                "country_group_ids": [
                    Command.set(country_group.ids + a_country_group.ids)
                ],
            }
        )
        self.env.company.country_id = my_country

        fp_1, fp_2, fp_3 = self.env["account.fiscal.position"].create(
            [
                {
                    "name": "FP First",
                    "country_group_id": country_group.id,
                },
                {
                    "name": "FP Second",
                    "country_id": my_country.id,
                },
                {
                    "name": "FP 3",
                    "country_group_id": country_group.id,
                },
            ]
        )
        self.assertEqual(
            self.env.company.account_config_id.domestic_fiscal_position_id, fp_2
        )

        (fp_1 + fp_2 + fp_3).write({"sequence": 10})
        fp_1.write(
            {
                "country_id": my_country.id,
                "country_group_id": False,
            }
        )
        fp_2.write({"country_id": False})
        self.assertEqual(
            self.env.company.account_config_id.domestic_fiscal_position_id, fp_1
        )

        (fp_1 + fp_2).write({"country_group_id": country_group.id})
        fp_1.write({"country_id": False})
        fp_2.write({"country_id": my_country.id})
        fp_3.write({"country_group_id": a_country_group.id})
        self.assertEqual(
            self.env.company.account_config_id.domestic_fiscal_position_id, fp_2
        )

        fp_2.write({"sequence": 20})
        fp_3.write({"sequence": 15})
        self.assertEqual(
            self.env.company.account_config_id.domestic_fiscal_position_id, fp_1
        )

        fp_1.write({"sequence": 30})
        fp_2.write({"country_id": False})
        fp_3.write({"country_group_id": False})
        self.assertEqual(
            self.env.company.account_config_id.domestic_fiscal_position_id, fp_2
        )

    def test_fiscal_position_constraint(self):
        fiscal_position = self.fp.create(
            {
                "name": "Test fiscal",
                "auto_apply": True,
                "country_id": self.be.id,
                "vat_required": True,
                "sequence": 10,
            }
        )
        with self.assertRaises(ValidationError):
            fiscal_position.write(
                {
                    "zip_from": "123",
                }
            )
        with self.assertRaises(ValidationError):
            fiscal_position.write(
                {
                    "zip_to": "456",
                }
            )
        fiscal_position.write(
            {
                "zip_from": "123",
                "zip_to": "456",
            }
        )

        self.assertRecordValues(
            fiscal_position,
            [
                {
                    "name": "Test fiscal",
                    "auto_apply": True,
                    "country_id": self.be.id,
                    "zip_from": "123",
                    "zip_to": "456",
                }
            ],
        )

    def test_zip_range_multi_record_write(self):
        fp_short, fp_long = self.fp.create(
            [
                {"name": "ZIP short", "zip_from": "1", "zip_to": "999"},
                {"name": "ZIP long", "zip_from": "1", "zip_to": "999999"},
            ]
        )
        self.assertRecordValues(
            fp_short | fp_long,
            [
                {"zip_from": "001", "zip_to": "999"},
                {"zip_from": "000001", "zip_to": "999999"},
            ],
        )

        (fp_short | fp_long).write({"zip_from": "5"})

        self.assertRecordValues(
            fp_short | fp_long,
            [
                {"zip_from": "005", "zip_to": "999"},
                {"zip_from": "000005", "zip_to": "999999"},
            ],
        )

    def test_fiscal_position_different_vat_country(self):
        fiscal_position = self.fp.create(
            {
                "name": "Special Delivery Case",
                "country_id": self.env.ref("base.fr").id,
                "foreign_vat": "BE0477472701",
            }
        )
        self.assertEqual(fiscal_position.foreign_vat, "BE0477472701")

    def test_get_first_fiscal_position(self):
        fiscal_positions = self.fp.create(
            [
                {
                    "name": f"fiscal_position_{sequence}",
                    "auto_apply": True,
                    "country_id": self.jc.country_id.id,
                    "sequence": sequence,
                }
                for sequence in range(1, 3)
            ]
        )
        self.assertEqual(self.fp._get_fiscal_position(self.jc), fiscal_positions[0])
