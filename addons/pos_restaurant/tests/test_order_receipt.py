# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_order_receipt import TestPosOrderReceipt


@tagged('post_install', '-at_install')
class TestPosOrderReceiptRestaurant(TestPosOrderReceipt):

    def test_split_per_product_preserves_course_grouping(self):
        """Test that split_per_product preserves course names on each split ticket."""
        category = self.env['pos.category'].create({'name': 'Food'})
        product_a = self.env['product.product'].create({
            'name': 'Soup',
            'available_in_pos': True,
            'list_price': 8.0,
            'pos_categ_ids': [(4, category.id)],
        })
        product_b = self.env['product.product'].create({
            'name': 'Steak',
            'available_in_pos': True,
            'list_price': 25.0,
            'pos_categ_ids': [(4, category.id)],
        })

        printer = self.env['pos.printer'].create({
            'name': 'Split Printer',
            'printer_type': 'epson_epos',
            'printer_ip': '0.0.0.0',
            'use_type': 'preparation',
            'product_categories_ids': [Command.set(self.env['pos.category'].search([]).ids)],
            'is_split_per_product': True,
        })
        self.main_pos_config.write({
            'preparation_printer_ids': [(4, printer.id)],
            'module_pos_restaurant': True,
        })

        order, _ = self.create_backend_pos_order({
            'pos_config': self.main_pos_config,
            'line_data': [
                {'product_id': product_a.id, 'qty': 1},
                {'product_id': product_b.id, 'qty': 1},
            ],
        })

        course1 = self.env['restaurant.order.course'].create({
            'name': 'Starter',
            'index': 1,
            'order_id': order.id,
        })
        course2 = self.env['restaurant.order.course'].create({
            'name': 'Main',
            'index': 2,
            'order_id': order.id,
        })
        order.lines[0].course_id = course1
        order.lines[1].course_id = course2

        prep_set = set(self.env['pos.category'].search([]).ids)
        prep_data = order._generate_preparation_change_for_categories(prep_set)
        receipts = order._generate_preparation_receipt_data(prep_data, is_split_per_product=True)

        self.assertEqual(len(receipts), 2, "Should have 2 split tickets")

        soup_ticket = next(
            r for r in receipts
            if any(d.get('product_id') == product_a.id for d in r['changes'].get('data', []))
        )
        steak_ticket = next(
            r for r in receipts
            if any(d.get('product_id') == product_b.id for d in r['changes'].get('data', []))
        )

        self.assertIn('grouped_data', soup_ticket['changes'], "Soup ticket should have grouped_data")
        self.assertEqual(len(soup_ticket['changes']['grouped_data']), 1)
        self.assertEqual(soup_ticket['changes']['grouped_data'][0]['name'], 'Starter')

        self.assertIn('grouped_data', steak_ticket['changes'], "Steak ticket should have grouped_data")
        self.assertEqual(len(steak_ticket['changes']['grouped_data']), 1)
        self.assertEqual(steak_ticket['changes']['grouped_data'][0]['name'], 'Main')
