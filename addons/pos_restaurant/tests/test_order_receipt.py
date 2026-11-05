# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_order_receipt import TestPosOrderReceipt


@tagged('post_install', '-at_install')
class TestPosOrderReceiptRestaurant(TestPosOrderReceipt):

    def test_service_fee_is_the_last_receipt_line_with_courses(self):
        """
        The PoS keeps the service fee in the last course, at the bottom of the order. The
        receipt must list it last too, whatever the order the lines were created in.
        """
        preset = self.env['pos.preset'].create({
            'name': 'Service fee preset',
            'service_fee': True,
            'service_fee_type': 'percent',
            'service_fee_amount': 0.1,
            'service_fee_based_on': 'pre_discount',
        })
        fee_product = preset.service_fee_product_id
        starter_product = self.env['product.product'].create({
            'name': 'Soup', 'available_in_pos': True, 'list_price': 8.0,
        })
        main_product = self.env['product.product'].create({
            'name': 'Steak', 'available_in_pos': True, 'list_price': 25.0,
        })
        dessert_product = self.env['product.product'].create({
            'name': 'Cake', 'available_in_pos': True, 'list_price': 6.0,
        })
        self.main_pos_config.write({'module_pos_restaurant': True})
        self.main_pos_config.with_user(self.pos_user).open_ui()

        def line_values(product, qty=1, price=None, **values):
            price = product.lst_price if price is None else price
            return {
                'product_id': product.id,
                'qty': qty,
                'price_unit': price,
                'price_subtotal': price * qty,
                'price_subtotal_incl': price * qty,
                **values,
            }

        order = self.env['pos.order'].create({
            'session_id': self.main_pos_config.current_session_id.id,
            'company_id': self.env.company.id,
            'preset_id': preset.id,
            'amount_total': 0,
            'amount_paid': 0,
            'amount_tax': 0,
            'amount_return': 0,
            'lines': [Command.create(line_values(starter_product))],
        })
        starter, main = self.env['restaurant.order.course'].create([
            {'name': 'Course 1', 'index': 1, 'order_id': order.id},
            {'name': 'Course 2', 'index': 2, 'order_id': order.id},
        ])
        order.lines.course_id = starter
        # The fee was created when the first course was alone, then moved to the last
        # course as the second one came: its line predates the lines of that course.
        self.env['pos.order.line'].create([
            line_values(fee_product, price=3.3, order_id=order.id, course_id=main.id),
            line_values(main_product, order_id=order.id, course_id=main.id),
            line_values(dessert_product, order_id=order.id, course_id=main.id),
        ])

        receipt_lines = order._order_receipt_generate_line_data()

        self.assertEqual(
            [line['product_data']['display_name'] for line in receipt_lines],
            ['Soup', 'Steak', 'Cake', fee_product.name],
        )
        self.assertTrue(receipt_lines[-1]['is_service_fee_line'])

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
