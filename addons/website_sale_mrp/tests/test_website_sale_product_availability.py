# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.sale.tests.test_sale_product_attribute_value_config import TestSaleProductAttributeValueCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleMrpAvailability(HttpCase, TestSaleProductAttributeValueCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Run the tests in another company, so the tests do not rely on the
        # database state (eg the default company's warehouse)
        cls.company = cls.env['res.company'].create({'name': 'Kit Company'})
        cls.env = cls.env['base'].with_company(cls.company).env
        cls.env.user.company_id = cls.company
        cls.website = cls.env.ref('website.default_website')
        cls.website.company_id = cls.env.company
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)

        # Create two storable products
        cls.super_kit_product, cls.kit_product, cls.component_A, cls.component_B = cls.env['product.product'].create([
            {
                'name': product_name,
                'allow_out_of_stock_order': False,
                'type': 'consu',
                'is_storable': True,
                'website_published': True,
                'show_availability': True,
                'available_threshold': 100,
            } for product_name in ("Super Kit Product", "Kit Product", "Component A", "Component B")
        ])

        cls.consumable_component = cls.env['product.product'].create({
                'name': "Consumable Component",
                'allow_out_of_stock_order': False,
                'type': 'consu',
                'is_storable': False,
                'website_published': True,
                'show_availability': True,
                'available_threshold': 100,
        })

        cls.super_kit_bom, cls.kit_bom = cls.env['mrp.bom'].create([
            {
                'product_tmpl_id': cls.super_kit_product.product_tmpl_id.id,
                'type': 'phantom',
                'product_qty': 2,
                'bom_line_ids': [
                    Command.create({'product_id': cls.component_A.id, 'product_qty': 8}),
                    Command.create({'product_id': cls.kit_product.id, 'product_qty': 2}),
                    Command.create({'product_id': cls.consumable_component.id, 'product_qty': 1}),
                ],
            },
            {
                'product_tmpl_id': cls.kit_product.product_tmpl_id.id,
                'type': 'phantom',
                'product_qty': 1,
                'bom_line_ids': [
                    Command.create({'product_id': cls.component_A.id, 'product_qty': 1}),
                    Command.create({'product_id': cls.component_B.id, 'product_qty': 5}),
                    Command.create({'product_id': cls.consumable_component.id, 'product_qty': 1}),
                ],
            },
        ])

        # Add 100 Component A and Component B in stock
        cls.env['stock.quant']._update_available_quantity(cls.component_A, cls.warehouse.lot_stock_id, 100)
        cls.env['stock.quant']._update_available_quantity(cls.component_B, cls.warehouse.lot_stock_id, 100)

    def test_website_sale_availability_kit(self):
        """
        Check that the website availability of products is influenced by kits present in the cart.
        """
        self.start_tour("/shop", 'test_website_sale_availability_kit', login="")
