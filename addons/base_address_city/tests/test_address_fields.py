# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestAddressFields(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.country_us = cls.env.ref("base.us")
        cls.country_us.write({"enforce_cities": True})
        cls.city_a = cls.env["res.city"].create({"name": "City A", "country_id": cls.country_us.id})
        cls.city_b = cls.env["res.city"].create({"name": "City B", "country_id": cls.country_us.id})

    def test_partner_operations(self):
        company = self.Partner.create({
            "is_company": True,
            "name": "Test Company",
            "country_id": self.country_us.id,
            "city_id": self.city_a.id
        })
        child = self.Partner.create({
            "name": "Test child",
            "parent_id": company.id
        })
        self.assertEqual(child.city_id, self.city_a)
        company.city_id = self.city_b
        self.assertEqual(child.city_id, self.city_b)
