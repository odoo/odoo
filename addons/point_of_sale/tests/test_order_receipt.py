# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tests import tagged
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
            'pos.order': ['last_order_preparation_change', 'lines', 'payment_ids', 'message_ids', 'write_date'],
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

    def compare_data(self, frontend, backend):
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
        self.main_pos_config.write({
            'receipt_header': 'This is a test header for receipt',
            'receipt_footer': 'This is a test footer for receipt',
            'ship_later': True,
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

        # Add function to model
        order_model = self.env.registry.models['pos.order']
        order_model.get_order_frontend_receipt_data = get_order_frontend_receipt_data
        self.start_pos_tour("test_receipt_data")
        self.compare_data(data['frontend_data'], data['backend_data'])
