# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestPOSLoyaltyProductLoading(TestPointOfSaleHttpCommon):
    def test_loyalty_product_loading(self):
        """ Test that loyalty products are loaded correctly in the PoS session. """
        new_product = self.env['product.product'].create({
            'name': 'New Product',
            'is_storable': True,
            'list_price': 1,
            'available_in_pos': True,
            'taxes_id': False,
        })

        program = self.env['loyalty.program'].create({
            'name': 'Program',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': new_product.id,
                'reward_product_qty': 1,
                'required_points': 2,
            })],
        })
        self.env['loyalty.program'].search([]).write({
            'active': False,
        })

        self.env['ir.config_parameter'].sudo().set_param('point_of_sale.limited_product_count', 1)

        self.main_pos_config.open_ui()
        current_session = self.main_pos_config.current_session_id

        data = current_session.with_context(
            pos_limited_loading=True,
        ).load_data(['pos.config', 'product.template'])

        self.assertNotIn(new_product.product_tmpl_id.id, [product['id'] for product in data['product.template']],
                        "Loyalty product should not be loaded in the PoS session when limited loading is enabled and program is inactive.")

        self.assertNotIn(new_product.id, data['pos.session'][0]['_pos_special_products_ids'],
                        "Loyalty product should not be in _pos_special_products_ids when program is inactive.")

        # Activate the program to ensure the product is loaded
        program.write({'active': True})

        data = current_session.with_context(
            pos_limited_loading=True,
        ).load_data(['pos.config', 'product.template'])

        self.assertIn(new_product.product_tmpl_id.id, [product['id'] for product in data['product.template']],
                        "Loyalty product should be loaded in the PoS session when program is active.")

        self.assertNotIn(new_product.id, data['pos.session'][0]['_pos_special_products_ids'],
                        "Loyalty product should not be in _pos_special_products_ids since it is loaded.")

        # Make the product not available in the PoS
        new_product.write({'available_in_pos': False})

        data = current_session.with_context(
            pos_limited_loading=True,
        ).load_data(['pos.config', 'product.template'])

        self.assertIn(new_product.product_tmpl_id.id, [product['id'] for product in data['product.template']],
                        "Loyalty product should be loaded in the PoS session when it is used in a program, even if not available in the PoS.")

        self.assertIn(new_product.id, data['pos.session'][0]['_pos_special_products_ids'],
                        "Loyalty product should be in _pos_special_products_ids since it is loaded but not available in the PoS.")
