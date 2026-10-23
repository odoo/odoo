# Copyright 2015 Yannick Vaucher, Camptocamp SA
# Copyright 2018-2021 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import psycopg2

from odoo.exceptions import ValidationError
from odoo.tests import Form, common
from odoo.tools.misc import mute_logger


class TestBaseLocation(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        state_obj = cls.env["res.country.state"]
        city_obj = cls.env["res.city"]
        zip_obj = cls.env["res.city.zip"]
        cls.partner_obj = cls.env["res.partner"]
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.state_vd = cls.env.ref("base.state_ch_vd")
        cls.env.ref("base.es").write({"enforce_cities": True})
        cls.company = cls.env.ref("base.main_company")
        cls.country_es = cls.env.ref("base.es")
        cls.state_bcn = state_obj.create(
            {"name": "Barcelona", "code": "08", "country_id": cls.country_es.id}
        )
        cls.state_madrid = state_obj.create(
            {"name": "Madrid", "code": "28", "country_id": cls.env.ref("base.es").id}
        )
        cls.city_bcn = city_obj.create(
            {
                "name": "Barcelona",
                "state_id": cls.state_bcn.id,
                "country_id": cls.env.ref("base.es").id,
            }
        )
        cls.city_madrid = city_obj.create(
            {
                "name": "Madrid",
                "state_id": cls.state_madrid.id,
                "country_id": cls.env.ref("base.es").id,
            }
        )
        cls.city_lausanne = city_obj.create(
            {
                "name": "Lausanne",
                "state_id": cls.state_vd.id,
                "country_id": cls.env.ref("base.ch").id,
            }
        )
        cls.lausanne = zip_obj.create({"name": "666", "city_id": cls.city_lausanne.id})
        cls.barcelona = zip_obj.create({"name": "444", "city_id": cls.city_bcn.id})

    def test_onchange_partner_city_completion(self):
        """Test that partner data is filled accodingly"""
        partner1 = Form(self.env["res.partner"])
        partner1.zip_id = self.barcelona
        self.assertEqual(partner1.zip, self.barcelona.name)
        self.assertEqual(partner1.city, self.barcelona.city_id.name)
        self.assertEqual(partner1.state_id, self.barcelona.city_id.state_id)
        self.assertEqual(partner1.country_id, self.barcelona.city_id.country_id)

    def test_onchange_company_city_completion(self):
        """Test that company data is filled accodingly"""
        company = self.env["res.company"].new({"name": "Test"})
        company.zip_id = self.lausanne
        company._onchange_zip_id()
        self.assertEqual(company.zip, self.lausanne.name)
        self.assertEqual(company.city, self.lausanne.city_id.name)
        self.assertEqual(company.state_id, self.lausanne.city_id.state_id)
        self.assertEqual(company.country_id, self.lausanne.city_id.country_id)

    def test_company_address_fields(self):
        """Test if the partner address fields changes when
        changing the ones from the company"""
        company = self.env["res.company"].create({"name": "Test"})
        self.assertTrue(company.partner_id)
        company.partner_id.write(
            {
                "zip_id": self.lausanne.id,
                "state_id": self.lausanne.city_id.state_id.id,
                "country_id": self.lausanne.city_id.country_id.id,
                "city_id": self.lausanne.city_id.id,
                "city": self.lausanne.city_id.name,
                "zip": self.lausanne.name,
            }
        )
        company._compute_address()
        self.assertEqual(company.zip_id, company.partner_id.zip_id)
        self.assertEqual(company.city_id, company.partner_id.city_id)

    def test_company_address_fields_inverse(self):
        """Test inverse fields from res.company"""
        company = self.env["res.company"].create({"name": "Test"})
        company.zip_id = self.barcelona.id
        company._inverse_city_id()
        company._inverse_zip_id()
        self.assertEqual(company.zip_id, company.partner_id.zip_id)
        self.assertEqual(company.city_id, company.partner_id.city_id)

    def test_onchange_company_city_id_completion(self):
        """Test city auto-completion when changing zip in a company"""
        company = self.env["res.company"].new({"name": "Test"})
        company.zip_id = self.barcelona
        company._onchange_zip_id()
        self.assertEqual(company.city_id, self.barcelona.city_id)

    def test_constrains_partner_01(self):
        """Test zip_id constraints"""
        with self.assertRaises(ValidationError):
            self.partner_obj.create(
                {"name": "P1", "zip_id": self.barcelona.id, "state_id": False}
            )
        with self.assertRaises(ValidationError):
            self.partner_obj.create(
                {"name": "P1", "zip_id": self.barcelona.id, "country_id": False}
            )
        with self.assertRaises(ValidationError):
            self.partner_obj.create(
                {"name": "P1", "zip_id": self.barcelona.id, "city_id": False}
            )
        with self.assertRaises(ValidationError):
            self.partner_obj.create(
                {"name": "P1", "zip_id": self.barcelona.id, "zip": False}
            )

    def test_writing_company(self):
        self.company.zip_id = self.barcelona

    def test_constrains_partner_country(self):
        """Test partner country constraints"""
        partner = self.partner_obj.create(
            {
                "name": "P1",
                "zip_id": self.barcelona.id,
                "country_id": self.barcelona.city_id.country_id.id,
                "state_id": self.barcelona.city_id.state_id.id,
                "city_id": self.barcelona.city_id.id,
            }
        )

        with self.assertRaises(ValidationError):
            partner.country_id = self.ref("base.ch")

    def test_constrains_partner_state(self):
        """Test partner state constraints"""
        partner = self.partner_obj.create(
            {
                "name": "P1",
                "zip_id": self.barcelona.id,
                "country_id": self.barcelona.city_id.country_id.id,
                "state_id": self.barcelona.city_id.state_id.id,
                "city_id": self.barcelona.city_id.id,
            }
        )

        with self.assertRaises(ValidationError):
            partner.state_id = self.state_vd.id

    def test_constrains_partner_city(self):
        """Test partner city constraints"""
        partner = self.partner_obj.create(
            {
                "name": "P1",
                "zip_id": self.barcelona.id,
                "country_id": self.barcelona.city_id.country_id.id,
                "state_id": self.barcelona.city_id.state_id.id,
                "city_id": self.barcelona.city_id.id,
            }
        )

        with self.assertRaises(ValidationError):
            partner.city_id = self.city_lausanne

    def test_partner_onchange_country(self):
        """Test partner onchange country_id"""
        partner = self.partner_obj.new({"name": "TEST", "zip_id": self.lausanne.id})
        partner.country_id = self.env.ref("base.es")
        partner._onchange_country_id()
        self.assertFalse(partner.zip_id)

    def test_partner_onchange_state(self):
        """Test partner onchange state_id"""
        partner = Form(self.env["res.partner"])
        partner.zip_id = self.lausanne
        partner.state_id = self.state_bcn
        self.assertFalse(partner.zip_id)
        self.assertEqual(partner.country_id, self.country_es)

    def test_company_onchange_state(self):
        """Test company onchange state_id"""
        self.company.state_id = self.state_bcn
        self.company._onchange_state_id()
        self.assertEqual(self.company.country_id, self.company.state_id.country_id)

    def test_partner_address_field_sync(self):
        """Test that zip_id is correctly synced with parent of contact addresses"""
        parent = self.env["res.partner"].create(
            {
                "name": "ACME Inc.",
                "is_company": True,
                "street": "123 Fake St.",
                "city": "Springfield",
                "state_id": self.barcelona.state_id.id,
                "country_id": self.barcelona.country_id.id,
                "zip_id": self.barcelona.id,
            }
        )
        contact = self.env["res.partner"].create(
            {
                "name": "John Doe",
                "type": "contact",
                "parent_id": parent.id,
            }
        )
        parent.zip_id = self.lausanne
        self.assertEqual(contact.zip_id, self.lausanne, "Contact should be synced")

    def test_display_name(self):
        """Test if the display_name is stored and computed properly"""
        self.assertEqual(
            self.lausanne.display_name,
            "666, Lausanne, Waadt, " + self.browse_ref("base.ch").name,
        )

    def test_name_search(self):
        """Test that zips can be searched through both the name of the
        city or the zip code"""
        madrid_data = {"city_id": self.city_madrid.id, "name": "555"}

        madrid = self.env["res.city.zip"].create(madrid_data)

        found_recs = self.env["res.city.zip"].name_search(name="444")
        self.assertEqual(len(found_recs), 1)
        self.assertEqual(found_recs[0][0], self.barcelona.id)
        found_recs = self.env["res.city.zip"].name_search(name="Barcelona")
        self.assertEqual(len(found_recs), 1)
        self.assertEqual(found_recs[0][0], self.barcelona.id)

        found_recs = self.env["res.city.zip"].name_search(name="555")
        self.assertEqual(len(found_recs), 1)
        self.assertEqual(found_recs[0][0], madrid.id)
        found_recs = self.env["res.city.zip"].name_search(name="Madrid")
        self.assertEqual(len(found_recs), 1)
        self.assertEqual(found_recs[0][0], madrid.id)

        found_recs = self.env["res.city.zip"].name_search(name="666")
        self.assertEqual(len(found_recs), 1)
        self.assertEqual(found_recs[0][0], self.lausanne.id)
        found_recs = self.env["res.city.zip"].name_search(name="Lausanne")
        self.assertEqual(len(found_recs), 1)
        self.assertEqual(found_recs[0][0], self.lausanne.id)

    def test_zip_ql_constraints(self):
        """Test UNIQUE name within it's area for zips"""
        with self.assertRaises(psycopg2.IntegrityError), mute_logger("odoo.sql_db"):
            self.env["res.city.zip"].create(
                {"name": "666", "city_id": self.city_lausanne.id}
            )

    def test_city_sql_contraint(self):
        """Test UNIQUE name within it's area for cities"""
        with self.assertRaises(psycopg2.IntegrityError), mute_logger("odoo.sql_db"):
            self.env["res.city"].create(
                {
                    "name": "Barcelona",
                    "state_id": self.state_bcn.id,
                    "country_id": self.ref("base.es"),
                }
            )
