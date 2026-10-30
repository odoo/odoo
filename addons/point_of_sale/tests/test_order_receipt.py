# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
from datetime import datetime
from unittest.mock import patch

from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from odoo.tools import (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    BinaryBytes,
)

from odoo.addons.point_of_sale.tests.common import CommonPosTest, PosHttpCommon

_logger = logging.getLogger(__name__)


class PosReceiptCommon(CommonPosTest):
    """Shared receipt fixtures and comparison helpers."""

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tax = cls.env['account.tax'].create({
            'name': 'Tax 15%',
            'amount': 25,
            'price_include_override': 'tax_included',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })

        cls.category = cls.env['pos.category'].create({
            'name': 'Misc test',
        })

        cls.example_simple_product = cls.create_product_template(
            'Example Simple Product', 5.80,
            pos_categ_ids=cls.category.ids,
            tax_ids=cls.tax.ids,
            is_storable=False,
            weight=0.01,
            to_weight=True,
            company_id=cls.env.company.id,
        )

        cls.example_partner = cls.env['res.partner'].create({
            'name': 'Example Partner',
            'street': '123 Example St',
            'city': 'Example City',
            'zip': '12345',
            'country_id': cls.env.ref('base.us').id,
            'email': 'example.partner@example.com',
        })

        cls.main_pos_config.write({
            'iface_available_categ_ids': [Command.set(cls.category.ids)],
            'limit_categories': True,
        })

        cls.key_to_skip = {
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

    def compare_change_receipt_data(self, frontend, backend):
        for key, value in frontend.items():
            self.assertIn(key, backend, f"Key '{key}' not found in backend data")
            if isinstance(value, dict):
                self.compare_change_receipt_data(value, backend[key])
            else:
                self.assertEqual(value, backend[key], f"Mismatch on field '{key}': frontend='{value}' vs backend='{backend[key]}'")

    def _create_receipt_test_order(self, date_order, preset_time=False):
        preset = self.env['pos.preset'].create({
            'name': 'Online Order',
            'use_timing': True,
        })
        return self.create_pos_order(
            [[self.example_simple_product.product_variant_id]],
            state='draft',
            date_order=date_order,
            preset_id=preset.id,
            preset_time=preset_time,
        )

    def _get_preparation_extra_data(self, order):
        changes = order._generate_preparation_change_for_categories(set(self.category.ids))
        data = order._generate_preparation_receipt_data(changes)
        self.assertTrue(data, "the order has one new line, it must produce a ticket")
        return data[0]['extra_data']

    def _create_receipt_printer(self, **vals):
        return self.env['pos.printer'].create({
            'name': 'Receipt Printer',
            'printer_type': 'epson_epos',
            'printer_ip': '0.0.0.0',
            'use_type': 'receipt',
            **vals,
        })


@tagged('post_install', '-at_install')
class TestPosReceiptHttp(PosReceiptCommon, PosHttpCommon):
    """Compare receipt data produced by the frontend and backend."""

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
            'iface_tax_included': "total",
        })
        data = {
            'frontend_data': None,
            'backend_data': None,
        }

        def get_order_frontend_receipt_data(self, frontend_data):
            backend_data = self.order_receipt_generate_data()
            data['frontend_data'] = frontend_data
            data['backend_data'] = backend_data

        def run_tour_and_compare():
            with patch.object(self.env.registry['pos.order'], 'get_order_frontend_receipt_data', get_order_frontend_receipt_data, create=True):
                self.start_pos_tour("test_receipt_data")
                self.compare_receipt_data(data['frontend_data'], data['backend_data'])

        self.main_pos_config.with_user(self.pos_user).open_ui()
        run_tour_and_compare()
        self.close_pos_session()

        self.main_pos_config.iface_tax_included = "subtotal"
        self.main_pos_config.with_user(self.pos_user).open_ui()
        run_tour_and_compare()

        logo_image = data['backend_data']['image']['logo']
        self.assertTrue(logo_image.startswith('data:image/svg+xml;base64,'))

    def test_change_receipt_data(self):
        printer = self._create_receipt_printer(
            name='Printer',
            use_type='preparation',
            product_categories_ids=[Command.set(self.env['pos.category'].search([]).ids)],
        )
        self.main_pos_config.write({
            'preparation_printer_ids': [Command.link(printer.id)],
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


@tagged('post_install', '-at_install')
class TestPosReceipt(PosReceiptCommon):
    """Receipt generation and preparation ticket tests without a browser."""

    def _get_service_fee_receipt_info(self, service_fee_type):
        preset = self.env['pos.preset'].create({
            'name': 'Service fee preset',
            'service_fee': True,
            'service_fee_type': service_fee_type,
            'service_fee_amount': 0.1 if service_fee_type == 'percent' else 2,
            'service_fee_based_on': 'pre_discount',
        })
        product = self.example_simple_product.product_variant_id
        fee_product = preset.service_fee_product_id
        fee_amount = 0.58 if service_fee_type == 'percent' else 2
        order = self.create_pos_order(
            [[product], [fee_product, 1, 0, {'price_unit': fee_amount}]],
            state='draft',
            preset_id=preset.id,
        )
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

        product_a = self.create_product(
            'Product A', 10.0, is_storable=False,
            pos_categ_ids=[Command.set(category_a.ids)],
        )
        product_b = self.create_product(
            'Product B', 5.0, is_storable=False,
            pos_categ_ids=[Command.set(category_b.ids)],
        )
        product_c = self.create_product(
            'Product C', 3.0, is_storable=False,
            pos_categ_ids=[Command.set(category_b.ids)],
        )
        combo = self.env['product.combo'].create({
            'name': 'Test Combo',
            'company_id': self.env.company.id,
            'combo_item_ids': [
                Command.create({'product_id': product.id})
                for product in (product_b, product_c)
            ],
        })
        combo_product = self.create_product(
            'Combo Product', 15.0, type='combo', is_storable=False,
            combo_ids=[Command.set(combo.ids)],
        )

        printer = self._create_receipt_printer(
            name='Split Printer',
            use_type='preparation',
            product_categories_ids=[Command.set(self.env['pos.category'].search([]).ids)],
            is_split_per_product=True,
        )
        self.main_pos_config.write({
            'preparation_printer_ids': [Command.link(printer.id)],
        })

        order = self.create_pos_order(
            [[product, 2] for product in (combo_product, product_b, product_c, product_a)],
            state='draft',
        )

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

    def test_group_by_categ_receipts(self):
        """Customer receipt lines and preparation ticket groups follow the PoS category sequence."""
        food, drinks = self.env['pos.category'].create([
            {'name': 'Food', 'sequence': 2},
            {'name': 'Drinks', 'sequence': 1},
        ])
        lemonade, napkins, cheeseburger, cola, fries = self.env['product.product'].create([
            {'name': name, 'available_in_pos': True, 'pos_categ_ids': categ.ids}
            for name, categ in [
                ('Lemonade', drinks),
                ('Napkins', self.env['pos.category']),
                ('Cheeseburger', food),
                ('Cola', drinks),
                ('Fries', food),
            ]
        ])
        burger_menu = self.env['product.product'].create({
            'name': 'Burger Menu',
            'type': 'combo',
            'available_in_pos': True,
            'combo_ids': [Command.create({
                'name': 'Menu Combo',
                'combo_item_ids': [Command.create({'product_id': p.id}) for p in cheeseburger | cola],
            })],
            'pos_categ_ids': food.ids,
        })
        self.main_pos_config.iface_group_by_categ = True

        order, _ = self.create_backend_pos_order({
            'pos_config': self.main_pos_config,
            'line_data': [
                {'product_id': product.id, 'qty': 1}
                for product in [lemonade, napkins, burger_menu, cheeseburger, cola, fries]
            ],
        })
        menu_line = order.lines.filtered(lambda l: l.product_id == burger_menu)
        order.lines.filtered(lambda l: l.product_id in cheeseburger | cola).combo_parent_id = menu_line

        receipt_lines = order.order_receipt_generate_data()['lines']
        self.assertEqual(
            [line['product_data']['display_name'] for line in receipt_lines],
            ['Lemonade', 'Burger Menu', 'Cheeseburger', 'Cola', 'Fries', 'Napkins'],
        )

        changes = order._generate_preparation_change_for_categories(set((food | drinks).ids))
        groups = order._generate_preparation_receipt_data(changes)[0]['changes']['groupedData']
        self.assertEqual(
            [(group['name'], [line['basic_name'] for line in group['data']]) for group in groups],
            [('Drinks', ['Lemonade', 'Burger Menu', 'Cola']), ('Food', ['Burger Menu', 'Cheeseburger', 'Fries'])],
        )

    def test_total_item_count(self):
        self._setup_combo_product()
        self.weighted_product = self.create_product_template(
            'Weighted Product', 4.20,
            pos_categ_ids=self.category.ids,
            tax_ids=self.tax.ids,
            is_storable=False,
            uom_id=self.env.ref('uom.product_uom_kgm').id,
            company_id=self.env.company.id,
        )
        order = self.create_pos_order(
            [
                [self.example_simple_product.product_variant_id, 2],
                [self.weighted_product.product_variant_id, 2.5],
                [self.office_combo],
            ],
            state='draft',
        )
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

    def test_change_receipt_times_use_shop_timezone(self):
        """
        Preparation ticket times must use the shop timezone, not the acting user's,
        since backend users (public user, OdooBot, self ordering user) may have no tz.
        """
        self.env.company.tz = 'Europe/Brussels'  # UTC+2
        public_user = self.env.ref('base.public_user')
        self.assertFalse(public_user.tz, "the public user carries no timezone")

        self.open_new_session()
        with freeze_time('2026-08-27 11:16:53'):
            order = self._create_receipt_test_order('2026-08-27 11:16:53', '2026-08-27 16:15:00')
            extra_data = self._get_preparation_extra_data(order.with_user(public_user).sudo())

        self.assertEqual(extra_data['time'], '13:16', "13:16 in Brussels, not 11:16 in UTC")
        self.assertEqual(extra_data['preset_time'], '06:15 PM', "18:15 in Brussels, not 16:15 in UTC")

    def test_change_receipt_preset_time_dates_the_pickup_only_when_needed(self):
        """
        Mirror of the JS presetDateTime getter: a pickup on the order's own day prints its
        hour alone, one on another day prints its date too. Both days are the shop's, which
        is what makes the first order below same-day despite spanning two UTC days.
        """
        self.env.company.tz = 'Europe/Brussels'  # UTC+2
        self.open_new_session()

        # 08-27 23:30 UTC is already 08-28 01:30 in Brussels, the pickup's own day
        same_day = self._create_receipt_test_order('2026-08-27 23:30:00', '2026-08-28 09:00:00')
        other_day = self._create_receipt_test_order('2026-08-27 11:16:53', '2026-08-28 16:15:00')

        self.assertEqual(
            self._get_preparation_extra_data(same_day)['preset_time'],
            '11:00 AM',
            "same day in Brussels, even though the order was placed on the previous UTC day",
        )
        self.assertEqual(
            self._get_preparation_extra_data(other_day)['preset_time'],
            '08/28/2026 06:15:00 PM',
            "a pickup on another day needs its date spelled out",
        )

    def test_receipt_print_data_without_printer(self):
        """
        Without a receipt printer, the backend can only use the browser printing flow.
        """
        order = self.create_pos_order(
            [[self.example_simple_product.product_variant_id]], state='draft',
        )

        data = order.get_receipt_print_data()
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

        order = self.create_pos_order(
            [[self.example_simple_product.product_variant_id]], state='draft',
        )
        data = order.get_receipt_print_data()

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
        order = self.create_pos_order(
            [[self.example_simple_product.product_variant_id]], state='draft',
        )
        self.assertIn('<epos-print', order._order_receipt_generate_for_format('epos', '80'))
        self.assertTrue(
            base64.b64decode(order._order_receipt_generate_for_format('image', '80')),
            "An IoT box expects the receipt as a base64 image",
        )

    def test_receipt_paper_style(self):
        """
        The receipt is rendered for the paper size of the printer it is sent to.
        """
        order = self.create_pos_order(
            [[self.example_simple_product.product_variant_id]], state='draft',
        )
        self.assertIn('width: 360px', order._order_receipt_paper_style_css('58'))
        self.assertIn('width: 512px', order._order_receipt_paper_style_css('80'))
        self.assertIn('width: 240px', order._order_receipt_paper_style_css('tm_l100_40'))
        self.assertIn(
            'width: 512px', order._order_receipt_paper_style_css(False),
            "An unknown paper size falls back on the size the receipt is designed for",
        )


# TODO-PARP: Migrate subclasses to the appropriate PosReceiptCommon or TestPosReceiptHttp receipt test class.
# Remove TestPosOrderReceipt once all modules have migrated.
TestPosOrderReceipt = TestPosReceiptHttp
