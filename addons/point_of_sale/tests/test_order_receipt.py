# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
from datetime import datetime
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged
from odoo.tools import (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    BinaryBytes,
)
from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.addons.point_of_sale.tests.common_setup_methods import setup_product_combo_items
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestPosOrderReceipt(TestPointOfSaleHttpCommon, CommonPosTest):
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.tax = self.env['account.tax'].create({
            'name': 'Tax 15%',
            'amount': 25,
            'price_include_override': 'tax_included',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })

        self.category = self.env['pos.category'].create({
            'name': 'Misc test',
        })

        self.example_simple_product = self.env['product.template'].create({
            'name': 'Example Simple Product',
            'available_in_pos': True,
            'list_price': 5.80,
            'taxes_id': [(6, 0, [self.tax.id])],
            'weight': 0.01,
            'to_weight': True,
            'pos_categ_ids': [(4, self.category.id)],
            'company_id': self.env.company.id,
        })

        self.example_partner = self.env['res.partner'].create({
            'name': 'Example Partner',
            'street': '123 Example St',
            'city': 'Example City',
            'zip': '12345',
            'country_id': self.env.ref('base.us').id,
            'email': 'example.partner@example.com',
        })

        self.main_pos_config.write({
            'iface_available_categ_ids': [(6, 0, [self.category.id])],
            'limit_categories': True,
        })

        self.key_to_skip = {
            'pos.order': ['lines', 'payment_ids', 'message_ids', 'write_date'],
            'pos.order.line': ['write_date'],
            'pos.payment': ['write_date'],
            'res.partner': ['write_date'],
            'pos.preset': ['write_date'],
            'res.company': ['write_date'],
            'extra_data': ['formated_date_order'],
            'image': [],
            'prices': [],
        }

    def compare_string(self, str1, str2):
        if not str1 and not str2:
            return True
        if (not str1 and str2) or (str1 and not str2):
            return False
        return str1.replace("\xa0", " ") == str2.replace("\xa0", " ")

    def compare_numbers(self, num1, num2):
        try:
            return float(num1) == float(num2)
        except (ValueError, TypeError):
            return False

    def compare_date(self, date_str1, backend_dt, field_type):
        type = DEFAULT_SERVER_DATETIME_FORMAT if field_type == 'datetime' else DEFAULT_SERVER_DATE_FORMAT
        date_str2 = backend_dt.strftime(type)
        if not date_str1 and not date_str2:
            return True
        if (not date_str1 and date_str2) or (date_str1 and not date_str2):
            return False

        date_obj1 = datetime.strptime(date_str1, type)
        date_obj2 = datetime.strptime(date_str2, type)

        if field_type == 'datetime':
            return abs((date_obj1 - date_obj2).total_seconds()) < 10  # 10 seconds tolerance for datetime fields
        return date_obj1 == date_obj2

    def get_field_type(self, model_name, field_name):
        try:
            return self.env[model_name]._fields[field_name].type
        except KeyError:
            return None
        except AttributeError:
            return None

    def compare_list(self, list1, list2):
        for i1, i2 in zip(list1, list2):
            if isinstance(i1, dict) and isinstance(i2, dict):
                self.comparator(i1, i2)
                continue
            if isinstance(i1, str) and isinstance(i2, str):
                return self.compare_string(i1, i2)
            if isinstance(i1, (int, float)) and isinstance(i2, (int, float)):
                return self.compare_numbers(i1, i2)
        return True

    def comparator(self, obj1, obj2, model_name=False):
        if not obj1 and not obj2:
            return  # Not setting anything, both are empty

        if (not obj1 and obj2) or (obj1 and not obj2):
            log = f"Mismatch on object '{model_name}': frontend='{obj1}' vs backend='{obj2}'"
            _logger.warning(log)
            return  # One is empty, the other is not

        for key in obj1:
            f_val = obj2.get(key)
            b_val = obj1.get(key)
            field_type = self.get_field_type(model_name, key)

            if key in self.key_to_skip.get(model_name, []):
                continue

            if len(str(b_val)) > 500 and len(str(f_val)) > 500:
                continue  # Probably an encoded image, skip comparison

            if not bool(b_val) and not bool(f_val):
                continue  # Both are falsy, consider equal

            if field_type in ['date', 'datetime'] and self.compare_date(f_val, b_val, field_type):
                continue

            if isinstance(b_val, dict) and isinstance(f_val, dict):
                self.comparator(b_val, f_val)
                continue

            if isinstance(b_val, list) and isinstance(f_val, list) and self.compare_list(b_val, f_val):
                continue

            if isinstance(b_val, str) and isinstance(f_val, str) and self.compare_string(b_val, f_val):
                continue

            if isinstance(b_val, (int, float)) and isinstance(f_val, (int, float)) and self.compare_numbers(b_val, f_val):
                continue

            log = f"Mismatch on field '{key}': frontend='{f_val}' vs backend='{b_val}'"
            _logger.warning(log)

    def compare_receipt_data(self, frontend, backend):
        backend_prices = backend['extra_data'].pop('prices', {})
        frontend_prices = frontend['extra_data'].pop('prices', {})
        backend_taxes = backend_prices.pop('taxes', {})
        frontend_taxes = frontend_prices.pop('taxes', {})

        self.comparator(backend_prices, frontend_prices, 'prices')
        self.comparator(backend['extra_data'], frontend['extra_data'], 'extra_data')
        self.comparator(backend['order'], frontend['order'], 'pos.order')
        self.comparator(backend['partner'], frontend['partner'], 'res.partner')
        self.comparator(backend['company'], frontend['company'], 'res.company')
        self.comparator(backend['preset'], frontend['preset'], 'pos.preset')
        self.comparator(backend['conditions'], frontend['conditions'], 'conditions')
        self.comparator(backend['image'], frontend['image'], 'image')
        self.assertEqual(backend['extra_data']['total_item_count'], frontend['extra_data']['total_item_count'])

        for taxes in zip(backend_taxes, frontend_taxes):
            self.comparator(taxes[0], taxes[1])

        for lines in zip(backend['lines'], frontend['lines']):
            product_data_1 = lines[0].pop('product_data')
            product_data_2 = lines[1].pop('product_data')
            self.comparator(product_data_1, product_data_2)
            self.comparator(lines[0], lines[1], 'pos.order.line')

        for payments in zip(backend['payments'], frontend['payments']):
            pm_data1 = payments[0].pop('payment_method_data')
            pm_data2 = payments[1].pop('payment_method_data')
            self.comparator(pm_data1, pm_data2)
            self.comparator(payments[0], payments[1], 'pos.payment')

    def test_receipt_data(self):
        image = """<?xml version='1.0' encoding='UTF-8' ?>
        <svg height='180' width='180' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'>
            <rect width="180" height="180" style="fill: #FF5F1F;" />
            <text fill='#EEE' font-size='96' text-anchor='middle' x='90' y='125'>P</text>
        </svg>"""
        self.main_pos_config.write({
            'receipt_header': 'This is a test header for receipt',
            'receipt_footer': 'This is a test footer for receipt',
            'logo': BinaryBytes(image.encode()),
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        data = {
            'frontend_data': None,
            'backend_data': None,
        }

        def get_order_frontend_receipt_data(self, frontend_data):
            backend_data = self.order_receipt_generate_data()
            data['frontend_data'] = frontend_data
            data['backend_data'] = backend_data

        with patch.object(self.env.registry['pos.order'], 'get_order_frontend_receipt_data', get_order_frontend_receipt_data, create=True):
            self.start_pos_tour("test_receipt_data")
            self.compare_receipt_data(data['frontend_data'], data['backend_data'])

            logo_image = data['backend_data']['image']['logo']
            self.assertTrue(logo_image.startswith('data:image/svg+xml;base64,'))

    def compare_change_receipt_data(self, frontend, backend):
        for key, value in frontend.items():
            self.assertIn(key, backend, f"Key '{key}' not found in backend data")
            if isinstance(value, dict):
                self.compare_change_receipt_data(value, backend[key])
            else:
                self.assertEqual(value, backend[key], f"Mismatch on field '{key}': frontend='{value}' vs backend='{backend[key]}'")

    def test_change_receipt_data(self):
        printer = self.env['pos.printer'].create({
            'name': 'Printer',
            'printer_type': 'epson_epos',
            'printer_ip': '0.0.0.0',
            'use_type': 'preparation',
            'product_categories_ids': [Command.set(self.env['pos.category'].search([]).ids)],
        })
        self.main_pos_config.write({
            'preparation_printer_ids': [(4, printer.id)],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        data = {
            'frontend_data': None,
            'backend_data': None,
        }

        def get_order_frontend_receipt_data(self, frontend_data):
            prep_set = set(self.env['pos.category'].search([]).ids)
            prep_data = self._generate_preparation_change_for_categories(prep_set)
            backend_data = self._generate_preparation_receipt_data(prep_data)
            data['frontend_data'] = frontend_data[0]['changes']['data'][0]
            data['backend_data'] = backend_data[0]['changes']['data'][0]
            self.env['ir.qweb']._render(
                'point_of_sale.pos_order_change_receipt',
                backend_data[0],
            )

        with patch.object(self.env.registry['pos.order'], 'get_order_frontend_receipt_data', get_order_frontend_receipt_data, create=True):
            self.start_pos_tour("test_change_receipt_data")
            self.compare_change_receipt_data(data['frontend_data'], data['backend_data'])

    def _get_service_fee_receipt_info(self, service_fee_type):
        preset = self.env['pos.preset'].create({
            'name': 'Service fee preset',
            'service_fee': True,
            'service_fee_type': service_fee_type,
            'service_fee_amount': 0.1 if service_fee_type == 'percent' else 2,
            'service_fee_based_on': 'pre_discount',
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        product = self.example_simple_product.product_variant_id
        fee_product = preset.service_fee_product_id
        fee_amount = 0.58 if service_fee_type == 'percent' else 2
        order = self.env['pos.order'].create({
            'session_id': self.main_pos_config.current_session_id.id,
            'company_id': self.env.company.id,
            'preset_id': preset.id,
            'amount_total': product.lst_price + fee_amount,
            'amount_paid': 0,
            'amount_tax': 0,
            'amount_return': 0,
            'lines': [
                Command.create({
                    'product_id': product.id,
                    'qty': 1,
                    'price_unit': product.lst_price,
                    'price_subtotal': product.lst_price,
                    'price_subtotal_incl': product.lst_price,
                }),
                Command.create({
                    'product_id': fee_product.id,
                    'qty': 1,
                    'price_unit': fee_amount,
                    'price_subtotal': fee_amount,
                    'price_subtotal_incl': fee_amount,
                }),
            ],
        })
        fee_line = next(
            line for line in order._order_receipt_generate_line_data()
            if line['is_service_fee_line']
        )
        return fee_line['service_fee_display_info']

    def test_service_fee_receipt_description_percent(self):
        """
        A percentage fee is taken from an order total, so the receipt says which.
        """
        self.assertEqual(
            self._get_service_fee_receipt_info('percent')['description'],
            " (before discount)",
        )

    def test_service_fee_receipt_description_fixed(self):
        """
        `based on` has nothing to qualify on a flat amount.
        """
        self.assertEqual(self._get_service_fee_receipt_info('fixed')['description'], "")

    def test_split_per_product_preserves_combo_children(self):
        """Test that split_per_product keeps combo parent + children on the same ticket."""
        category_a = self.env['pos.category'].create({'name': 'Category A'})
        category_b = self.env['pos.category'].create({'name': 'Category B'})

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'list_price': 10.0,
            'pos_categ_ids': [(4, category_a.id)],
        })
        product_b = self.env['product.product'].create({
            'name': 'Product B',
            'available_in_pos': True,
            'list_price': 5.0,
            'pos_categ_ids': [(4, category_b.id)],
        })
        product_c = self.env['product.product'].create({
            'name': 'Product C',
            'available_in_pos': True,
            'list_price': 3.0,
            'pos_categ_ids': [(4, category_b.id)],
        })

        combo = self.env['product.combo'].create({'name': 'Test Combo'})
        self.env['product.combo.item'].create({
            'product_id': product_b.id,
            'combo_id': combo.id,
        })
        self.env['product.combo.item'].create({
            'product_id': product_c.id,
            'combo_id': combo.id,
        })

        combo_template = self.env['product.template'].create({
            'name': 'Combo Product',
            'type': 'combo',
            'combo_ids': [(4, combo.id)],
            'list_price': 15.0,
        })
        combo_product = combo_template.product_variant_id

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
        })

        order, _ = self.create_backend_pos_order({
            'pos_config': self.main_pos_config,
            'line_data': [
                {'product_id': combo_product.id, 'qty': 2},
                {'product_id': product_b.id, 'qty': 2},
                {'product_id': product_c.id, 'qty': 2},
                {'product_id': product_a.id, 'qty': 2},
            ],
        })

        parent_line = order.lines.filtered(lambda l: l.product_id == combo_product)[:1]
        order.lines.filtered(lambda l: l.product_id == product_b).write({'combo_parent_id': parent_line.id})
        order.lines.filtered(lambda l: l.product_id == product_c).write({'combo_parent_id': parent_line.id})

        prep_set = set(self.env['pos.category'].search([]).ids)
        prep_data = order._generate_preparation_change_for_categories(prep_set)
        receipts = order._generate_preparation_receipt_data(prep_data, is_split_per_product=True)

        self.assertTrue(len(receipts) > 0, "Should have at least one receipt")

        combo_tickets = [
            r for r in receipts
            if r['changes'].get('data') and any(
                d.get('product_id') == combo_product.id
                for d in r['changes']['data']
            )
        ]
        self.assertEqual(len(combo_tickets), 2, "Combo product (qty=2) should produce 2 tickets")

        for ticket in combo_tickets:
            product_ids = [d['product_id'] for d in ticket['changes']['data']]
            self.assertIn(combo_product.id, product_ids, "Combo parent should be on ticket")
            self.assertIn(product_b.id, product_ids, "Combo child B should be on same ticket as parent")
            self.assertIn(product_c.id, product_ids, "Combo child C should be on same ticket as parent")
            self.assertEqual(len(ticket['changes']['data']), 3, "Combo ticket should have parent + 2 children")

        standalone_tickets = [
            r for r in receipts
            if r['changes'].get('data') and any(
                d.get('product_id') == product_a.id
                for d in r['changes']['data']
            )
        ]
        self.assertEqual(len(standalone_tickets), 2, "Standalone product A (qty=2) should produce 2 tickets")
        for ticket in standalone_tickets:
            product_ids = [d['product_id'] for d in ticket['changes']['data']]
            self.assertEqual(product_ids, [product_a.id], "Standalone ticket should only have product A")

    def test_total_item_count(self):
        setup_product_combo_items(self)
        self.weighted_product = self.env['product.template'].create({
            'name': 'Weighted Product',
            'available_in_pos': True,
            'list_price': 4.20,
            'taxes_id': [(6, 0, [self.tax.id])],
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
            'pos_categ_ids': [(4, self.category.id)],
            'company_id': self.env.company.id,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        order, _ = self.create_backend_pos_order({
            'pos_config': self.main_pos_config,
            'line_data': [
                {'product_id': self.example_simple_product.product_variant_id.id, 'qty': 2, 'price_subtotal': 0.0, 'price_subtotal_incl': 0.0},
                {'product_id': self.weighted_product.product_variant_id.id, 'qty': 2.5, 'price_subtotal': 0.0, 'price_subtotal_incl': 0.0},
                {'product_id': self.office_combo.id, 'qty': 1, 'price_subtotal': 0.0, 'price_subtotal_incl': 0.0},
            ],
        })
        order.lines.filtered(lambda line: line.product_id == self.office_combo).write({
            "combo_line_ids": [
                Command.create({
                    "order_id": order.id,
                    "product_id": item.product_id.id,
                    "qty": 1,
                    "price_subtotal": 0.0,
                    "price_subtotal_incl": 0.0,
                })
                for item in self.desks_combo.combo_item_ids
            ],
        })
        self.assertEqual(order.order_receipt_generate_data()['extra_data']['total_item_count'], 5)

    def _create_order(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        product = self.example_simple_product.product_variant_id
        return self.env['pos.order'].create({
            'session_id': self.main_pos_config.current_session_id.id,
            'company_id': self.env.company.id,
            'state': 'paid',
            'amount_total': product.lst_price,
            'amount_paid': product.lst_price,
            'amount_tax': 0,
            'amount_return': 0,
            'lines': [
                Command.create({
                    'product_id': product.id,
                    'qty': 1,
                    'price_unit': product.lst_price,
                    'price_subtotal': product.lst_price,
                    'price_subtotal_incl': product.lst_price,
                }),
            ],
        })

    def _create_receipt_printer(self, **vals):
        return self.env['pos.printer'].create({
            'name': 'Receipt Printer',
            'printer_type': 'epson_epos',
            'printer_ip': '0.0.0.0',
            'use_type': 'receipt',
            **vals,
        })

    def test_receipt_print_data_without_printer(self):
        """
        Without a receipt printer, the backend can only use the browser printing flow.
        """
        data = self._create_order().get_receipt_print_data()
        self.assertFalse(data['printers'])
        self.assertIn('pos-receipt', data['receipt_html'])

    def test_receipt_print_data_with_printers(self):
        """
        Each usable printer gets a receipt, ready to be sent to it by the client.
        """
        printer = self._create_receipt_printer(paper_size='58')
        label_printer = self._create_receipt_printer(name='Label Printer', paper_size='label')
        self.main_pos_config.write({
            'receipt_printer_ids': [Command.set((printer + label_printer).ids)],
        })

        data = self._create_order().get_receipt_print_data()

        self.assertEqual(
            [p['id'] for p in data['printers']], printer.ids,
            "Label printers expect ZPL, they can't print the receipt template",
        )
        self.assertEqual(data['printers'][0]['printer_ip'], '0.0.0.0')
        self.assertIn('<epos-print', data['printers'][0]['receipt'])
        self.assertIn('pos-receipt', data['receipt_html'])

    def test_receipt_print_format(self):
        """
        Printers behind an IoT box are given an image, the ePOS ones a document.
        """
        order = self._create_order()
        self.assertIn('<epos-print', order._order_receipt_generate_for_format('epos', '80'))
        self.assertTrue(
            base64.b64decode(order._order_receipt_generate_for_format('image', '80')),
            "An IoT box expects the receipt as a base64 image",
        )

    def test_receipt_paper_style(self):
        """
        The receipt is rendered for the paper size of the printer it is sent to.
        """
        order = self._create_order()
        self.assertIn('width: 360px', order._order_receipt_paper_style_css('58'))
        self.assertIn('width: 512px', order._order_receipt_paper_style_css('80'))
        self.assertIn('width: 240px', order._order_receipt_paper_style_css('tm_l100_40'))
        self.assertIn(
            'width: 512px', order._order_receipt_paper_style_css(False),
            "An unknown paper size falls back on the size the receipt is designed for",
        )
