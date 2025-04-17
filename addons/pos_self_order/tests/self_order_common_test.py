# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo import Command
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@odoo.tests.tagged("post_install", "-at_install")
class SelfOrderCommonTest(TestPointOfSaleHttpCommon):
    browser_size = "375x667"
    touch_enabled = True
    allow_inherited_tests_method = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.default_tax15 = cls.env["account.tax"].create({
            "name": "Default Tax for Self Order",
            "amount": 15,
            "amount_type": "percent",
        })
        cls.pos_admin.group_ids += cls.env.ref('account.group_account_invoice')
        cls.pos_config.write({
            'module_pos_restaurant': True,
            'self_ordering_default_user_id': cls.pos_admin.id,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
            'use_presets': False,
            'payment_method_ids': [(6, 0, [cls.bank_payment_method.id])],
        })

    def start_pos_self_tour(self, tour_name, **kwargs):
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, tour_name, **kwargs)

    def setup_test_self_presets(self):
        self.delivery_preset = self.env['pos.preset'].create({
            'name': 'Test-Delivery',
            'service_at': 'delivery',
            'identification': 'address',
            'available_in_self': True,
        })
        self.out_preset = self.env['pos.preset'].create({
            'name': 'Test-Takeout',
            'service_at': 'counter',
            'identification': 'name',
            'available_in_self': True,
        })
        self.in_preset = self.env['pos.preset'].create({
            'name': 'Test-In',
            'service_at': 'table',
            'identification': 'none',
            'available_in_self': True,
        })

        self.main_pos_config.write({
            "use_presets": True,
            'default_preset_id': self.in_preset.id,
            "available_preset_ids": [(4, self.out_preset.id), (4, self.in_preset.id), (4, self.delivery_preset.id)],
        })

    def setup_self_floor_and_table(self):
        self.env['restaurant.table'].search([]).action_archive()
        self.env['restaurant.floor'].search([]).action_archive()
        floor = self.env["restaurant.floor"].create({
            "name": 'Main Floor',
            "background_color": 'rgb(249,250,251)',
            "table_ids": [(0, 0, {
                "table_number": 1,
            }), (0, 0, {
                "table_number": 2,
            }), (0, 0, {
                "table_number": 3,
            })],
        })

        # Only set one floor to the pos_config, otherwise it can have two table with the same name
        # which will cause the test to fail
        self.pos_config.write({
            "floor_ids": [(6, 0, [floor.id])],
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
        # we need a default tax fixed at 15% to all product because in the test prices are based on this tax.
        # some time with the localization this may not be the case. So we force it.
        self.env["product.product"].search([]).taxes_id = self.default_tax15

        # A new tax is added to each product and this tax is from a different company.
        # This is important in the test because the added tax should not be used in the tour.
        self._add_tax_to_product_from_different_company()
