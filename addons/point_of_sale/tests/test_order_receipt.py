# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestPosOrderReceipt(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        tax = self.env['account.tax'].create({
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
            'taxes_id': [(6, 0, [tax.id])],
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
<<<<<<< 5b0f47b69c635e85015cb5fc9ee63517456e9691

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
||||||| 11e0a09060707970989d112590088e1ca8799f5a
=======

    def _create_receipt_test_order(self, date_order, preset_time=False):
        preset = self.env['pos.preset'].create({
            'name': 'Online Order',
            'use_timing': True,
        })
        return self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'date_order': date_order,
            'preset_id': preset.id,
            'preset_time': preset_time,
            'amount_total': 0,
            'amount_paid': 0,
            'amount_tax': 0,
            'amount_return': 0,
            'lines': [Command.create({
                'product_id': self.example_simple_product.product_variant_id.id,
                'qty': 1,
                'price_unit': 5.80,
                'price_subtotal': 5.80,
                'price_subtotal_incl': 5.80,
            })],
        })

    def test_change_receipt_times_use_shop_timezone(self):
        """
        Preparation ticket times must use the shop timezone, not the acting user's,
        since backend users (public user, OdooBot, self ordering user) may have no tz.
        """
        self.env.company.tz = 'Europe/Brussels'  # UTC+2
        public_user = self.env.ref('base.public_user')
        self.assertFalse(public_user.tz, "the public user carries no timezone")

        self.main_pos_config.with_user(self.pos_user).open_ui()
        order = self._create_receipt_test_order('2026-08-27 11:16:53', '2026-08-27 16:15:00')

        data = order.with_user(public_user).sudo()._order_change_receipt_generate_data(set(self.category.ids))
        self.assertTrue(data, "the order has one new line, it must produce a ticket")
        extra_data = data[0]['extra_data']

        self.assertEqual(extra_data['time'], '13:16', "13:16 in Brussels, not 11:16 in UTC")
        self.assertEqual(extra_data['preset_time'], '06:15 PM', "18:15 in Brussels, not 16:15 in UTC")
>>>>>>> 0be1c9f80a62b61f6f83f3f9bfea0c9193151e9b
