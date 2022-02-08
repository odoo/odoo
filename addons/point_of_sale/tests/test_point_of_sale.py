# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestPointOfSale(TransactionCase):
    def setUp(self):
        super(TestPointOfSale, self).setUp()

        # ignore pre-existing pricelists for the purpose of this test
        self.env["product.pricelist"].search([]).write({"active": False})

        self.currency = self.env.ref("base.USD")
        self.company1 = self.env["res.company"].create({
            "name": "company 1",
            "currency_id": self.currency.id
        })
        self.company2 = self.env["res.company"].create({
            "name": "company 2",
            "currency_id": self.currency.id
        })
        self.company2_pricelist = self.env["product.pricelist"].create({
            "name": "company 2 pricelist",
            "currency_id": self.currency.id,
            "company_id": self.company2.id,
            "sequence": 1,  # force this pricelist to be first
        })

        self.env.user.company_id = self.company1

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
