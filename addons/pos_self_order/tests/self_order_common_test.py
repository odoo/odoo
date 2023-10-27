# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo import Command


@odoo.tests.tagged("post_install", "-at_install")
class SelfOrderCommonTest(odoo.tests.HttpCase):
    browser_size = "375x667"
    touch_enabled = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pos_user = cls.env['res.users'].create({
            'name': 'POS User',
            'login': 'pos_user',
            'password': 'pos_user',
            'groups_id': [
                (4, cls.env.ref('base.group_user').id),
                (4, cls.env.ref('point_of_sale.group_pos_user').id),
            ],
        })
        cls.pos_admin = cls.env['res.users'].create({
            'name': 'POS Admin',
            'login': 'pos_admin',
            'password': 'pos_admin',
            'groups_id': [
                (4, cls.env.ref('base.group_user').id),
                (4, cls.env.ref('point_of_sale.group_pos_manager').id),
            ],
        })

    def _add_tax_to_product_from_different_company(self):
        new_company = self.env['res.company'].create({
            'name': 'Test Company',
            'currency_id': self.env.ref('base.USD').id,
            'country_id': self.env.ref('base.us').id,
        })

        self.other_company_tax = (
            self.env["account.tax"]
            .with_company(new_company)
            .create(
                {
                    "name": "Tax that should not be used",
                    "amount": 50,
                    "amount_type": "percent",
                    "tax_group_id": self.env["account.tax.group"]
                    .with_company(new_company)
                    .create(
                        {
                            "name": "Tax Group that should not be used",
                        }
                    )
                    .id,
                    "company_id": new_company.id,
                }
            )
        )

        self.env['product.product'].search([]).with_company(new_company).write({
            'taxes_id': [Command.link(id) for id in self.other_company_tax.ids],
        })

    def setUp(self):
        super().setUp()
        self.pos_config = self.env["pos.config"].create(
            {
                "name": "BarTest",
                "self_ordering_default_user_id": self.pos_user.id,
                "module_pos_restaurant": True,
                "self_ordering_mode": "consultation",
                "floor_ids": self.env["restaurant.floor"].search([]),
            }
        )

        self.default_tax15 = self.env["account.tax"].create(
            {
                "name": "Default Tax for Self Order",
                "amount": 15,
                "amount_type": "percent",
            }
        )

        # we need a default tax fixed at 15% to all product because in the test prices are based on this tax.
        # some time with the localization this may not be the case. So we force it.
        self.env["product.product"].search([]).taxes_id = self.default_tax15

        # A new tax is added to each product and this tax is from a different company.
        # This is important in the test because the added tax should not be used in the tour.
        self._add_tax_to_product_from_different_company()
