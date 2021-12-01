# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestPointOfSale(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ignore pre-existing pricelists for the purpose of this test
        cls.env["product.pricelist"].search([]).write({"active": False})

        cls.currency = cls.env.ref("base.USD")
        cls.company1 = cls.env["res.company"].create({
            "name": "company 1",
            "currency_id": cls.currency.id
        })
        cls.company2 = cls.env["res.company"].create({
            "name": "company 2",
            "currency_id": cls.currency.id
        })
        cls.company2_pricelist = cls.env["product.pricelist"].create({
            "name": "company 2 pricelist",
            "currency_id": cls.currency.id,
            "company_id": cls.company2.id,
            "sequence": 1,  # force this pricelist to be first
        })

        cls.env.user.company_id = cls.company1

    def test_default_pricelist_with_company(self):
        """ Verify that the default pricelist belongs to the same company as the config """
        company1_pricelist = self.env["product.pricelist"].create({
            "name": "company 1 pricelist",
            "currency_id": self.currency.id,
            "company_id": self.company1.id,
            "sequence": 2,
        })

        # make sure this doesn't pick the company2 pricelist
        new_config = self.env["pos.config"].create({
            "name": "usd config"
        })

        self.assertEqual(new_config.pricelist_id, company1_pricelist,
                         "POS config incorrectly has pricelist %s" % new_config.pricelist_id.display_name)

    def test_default_pricelist_without_company(self):
        """ Verify that a default pricelist without a company works """
        universal_pricelist = self.env["product.pricelist"].create({
            "name": "universal pricelist",
            "currency_id": self.currency.id,
            "sequence": 2,
        })

        # make sure this doesn't pick the company2 pricelist
        new_config = self.env["pos.config"].create({
            "name": "usd config"
        })

        self.assertEqual(new_config.pricelist_id, universal_pricelist,
                         "POS config incorrectly has pricelist %s" % new_config.pricelist_id.display_name)
