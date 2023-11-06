# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo import Command
from odoo.addons.point_of_sale.tests.common import archive_products


@odoo.tests.tagged("post_install", "-at_install")
class SelfOrderCommonTest(odoo.tests.HttpCase):
    browser_size = "375x667"
    touch_enabled = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        archive_products(cls.env)
        cls.pos_user = cls.env['res.users'].create({
            'name': 'POS User',
            'login': 'pos_user',
            'password': 'pos_user',
            'groups_id': [
                (4, cls.env.ref('base.group_user').id),
                (4, cls.env.ref('point_of_sale.group_pos_user').id),
            ],
        })

        pos_categ_misc = cls.env['pos.category'].create({
            'name': 'Chairs',
        })

        cls.office_chair = cls.env['product.product'].create({
            'name': 'Office Chair',
            'available_in_pos': True,
            'list_price': 70.0,
            'taxes_id': False,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
        })
        cls.office_chair_black = cls.env['product.product'].create({
            'name': 'Office Chair Black',
            'available_in_pos': True,
            'list_price': 120.50,
            'taxes_id': False,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
        })
        cls.conference_chair = cls.env['product.product'].create({
            'name': 'Conference Chair (Aluminium)',
            'available_in_pos': True,
            'list_price': 39.40,
            'taxes_id': False,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
        })
        cls.large_cabinet = cls.env['product.product'].create({
            'name': 'Large Cabinet',
            'available_in_pos': True,
            'list_price': 320.0,
            'taxes_id': False,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
        })
        cls.cabinet_with_doors = cls.env['product.product'].create({
            'name': 'Cabinet with Doors',
            'available_in_pos': True,
            'list_price': 140.0,
            'taxes_id': False,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
        })
        cls.letter_tray = cls.env['product.product'].create({
            'name': 'Letter Tray',
            'available_in_pos': True,
            'list_price': 4.8,
            'taxes_id': False,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
        })
        cls.desk_pad = cls.env['product.product'].create({
            'name': 'Desk Pad',
            'available_in_pos': True,
            'list_price': 1.98,
            'taxes_id': False,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
        })
        cls.funghi = cls.env['product.product'].create({
            'name': 'Funghi',
            'available_in_pos': True,
            'list_price': 7.0,
            'taxes_id': False,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
        })
        cls.virtual_home_staging = cls.env['product.product'].create({
            # demo data product.product_product_2
            'name': 'Virtual Home Staging',
            'available_in_pos': True,
            'list_price': 38.25,
            'type': 'service',
            'taxes_id': False,
            'pos_categ_ids': [(4, pos_categ_misc.id)],
        })
        cls.desk_organizer = cls.env['product.product'].create({
            'name': 'Desk Organizer',
            'available_in_pos': True,
            'list_price': 5.10,
            'taxes_id': False,
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

        new_tax = self.env['account.tax'].with_company(new_company).create({
            'name': 'Tax that should not be used',
            'amount': 50,
            'amount_type': 'percent',
            'tax_group_id': self.env['account.tax.group'].with_company(new_company).create({
                'name': 'Tax Group that should not be used',
            }).id,
            'company_id': new_company.id,
        })

        self.env['product.product'].search([]).with_company(new_company).write({
            'taxes_id': [Command.link(id) for id in new_tax.ids],
        })

    def setUp(self):
        super().setUp()
        self.pos_config = self.env["pos.config"].create(
            {
                "name": "BarTest",
                "module_pos_restaurant": True,
                "self_order_view_mode": True,
                "floor_ids": self.env["restaurant.floor"].search([]),
                "self_order_table_mode": False,
            }
        )

        # We need a table and a floor to be able to do some tours when we do not have demo data.
        # and thus no floors.
        self.pos_main_floor = self.env['restaurant.floor'].create({
            'name': 'Main Floor Test',
            'pos_config_ids': [(4, self.pos_config.id)],
        })

        self.pos_table_1 = self.env['restaurant.table'].create({
            'name': '1',
            'floor_id': self.pos_main_floor.id,
            'seats': 4,
            'shape': 'square',
            'position_h': 150,
            'position_v': 100,
        })

        # we need a default tax fixed at 15% to all product because in the test prices are based on this tax.
        # some time with the localization this may not be the case. So we force it.
        self.env['product.product'].search([]).taxes_id = self.env['account.tax'].create({
            'name': 'Default Tax for Self Order',
            'amount': 15,
            'amount_type': 'percent',
        })

        # A new tax is added to each product and this tax is from a different company.
        # This is important in the test because the added tax should not be used in the tour.
        self._add_tax_to_product_from_different_company()
