# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo import Command
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.point_of_sale.tests.common import archive_products


@odoo.tests.tagged("post_install", "-at_install")
class SelfOrderCommonTest(odoo.tests.HttpCase):
    browser_size = "375x667"
    touch_enabled = True
    allow_inherited_tests_method = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        archive_products(cls.env)
        cls.pos_user = mail_new_test_user(
            cls.env,
            groups="base.group_user,point_of_sale.group_pos_user",
            login="pos_user",
            name="POS User",
            tz="Europe/Brussels",
        )
        cls.pos_admin = mail_new_test_user(
            cls.env,
            groups="base.group_user,point_of_sale.group_pos_manager",
            login="pos_admin",
            name="POS Admin",
            tz="Europe/Brussels",
        )

        pos_categ_misc = cls.env['pos.category'].create({
            'name': 'Miscellaneous',
        })

        cls.cola = cls.env['product.product'].create({
            'name': 'Coca-Cola',
            'is_storable': True,
            'list_price': 2.2,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
            'default_code': '12345',
        })
        cls.free = cls.env['product.product'].create({
            'name': 'Free',
            'is_storable': True,
            'list_price': 0,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
            'default_code': '12345',
        })
        cls.fanta = cls.env['product.product'].create({
            'name': 'Fanta',
            'is_storable': True,
            'list_price': 2.2,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
        })
        cls.ketchup = cls.env['product.product'].create({
            'name': 'Ketchup',
            'is_storable': True,
            'list_price': 0,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
        })

        #desk organizer
        cls.desk_organizer = cls.env['product.product'].create({
            'name': 'Desk Organizer',
            'available_in_pos': True,
            'list_price': 5.10,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
        })
        desk_size_attribute = cls.env['product.attribute'].create({
            'name': 'Size',
            'display_type': 'radio',
            'create_variant': 'no_variant',
        })
        desk_size_s = cls.env['product.attribute.value'].create({
            'name': 'S',
            'attribute_id': desk_size_attribute.id,
        })
        desk_size_m = cls.env['product.attribute.value'].create({
            'name': 'M',
            'attribute_id': desk_size_attribute.id,
        })
        desk_size_l = cls.env['product.attribute.value'].create({
            'name': 'L',
            'attribute_id': desk_size_attribute.id,
        })
        cls.env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.desk_organizer.product_tmpl_id.id,
            'attribute_id': desk_size_attribute.id,
            'value_ids': [(6, 0, [desk_size_s.id, desk_size_m.id, desk_size_l.id])]
        })
        desk_fabrics_attribute = cls.env['product.attribute'].create({
            'name': 'Fabric',
            'display_type': 'select',
            'create_variant': 'no_variant',
        })
        desk_fabrics_leather = cls.env['product.attribute.value'].create({
            'name': 'Leather',
            'attribute_id': desk_fabrics_attribute.id,
        })
        desk_fabrics_other = cls.env['product.attribute.value'].create({
            'name': 'Custom',
            'attribute_id': desk_fabrics_attribute.id,
            'is_custom': True,
        })
        cls.env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.desk_organizer.product_tmpl_id.id,
            'attribute_id': desk_fabrics_attribute.id,
            'value_ids': [(6, 0, [desk_fabrics_leather.id, desk_fabrics_other.id])]
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
        journal_obj = self.env['account.journal']
        main_company = self.env.company
        self.bank_journal = journal_obj.create({
            'name': 'Bank Test',
            'type': 'bank',
            'company_id': main_company.id,
            'code': 'BNK',
            'sequence': 10,
        })

        self.bank_payment_method = self.env['pos.payment.method'].create({
            'name': 'Bank',
            'journal_id': self.bank_journal.id,
        })

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

        self.pos_config = self.env["pos.config"].create(
            {
                "name": "BarTest",
                "self_ordering_default_user_id": self.pos_user.id,
                "module_pos_restaurant": True,
                "self_ordering_mode": "consultation",
                "floor_ids": self.env["restaurant.floor"].search([]),
                "payment_method_ids": [(4, self.bank_payment_method.id)],
                "use_presets": True,
                "available_preset_ids": [(4, self.out_preset.id), (4, self.in_preset.id), (4, self.delivery_preset.id)],
                "default_preset_id": self.in_preset.id,
            }
        )

        self.default_tax15 = self.env["account.tax"].create(
            {
                "name": "Default Tax for Self Order",
                "amount": 15,
                "amount_type": "percent",
            }
        )

        # We need a table and a floor to be able to do some tours when we do not have demo data.
        # and thus no floors.
        self.pos_main_floor = self.env['restaurant.floor'].create({
            'name': 'Main Floor Test',
            'pos_config_ids': [(4, self.pos_config.id)],
        })

        self.pos_table_1 = self.env['restaurant.table'].create({
            'table_number': 1,
            'floor_id': self.pos_main_floor.id,
            'seats': 4,
            'shape': 'square',
            'position_h': 150,
            'position_v': 100,
        })

        # we need a default tax fixed at 15% to all product because in the test prices are based on this tax.
        # some time with the localization this may not be the case. So we force it.
        self.env["product.product"].search([]).taxes_id = self.default_tax15

        # A new tax is added to each product and this tax is from a different company.
        # This is important in the test because the added tax should not be used in the tour.
        self._add_tax_to_product_from_different_company()
