# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields
from odoo.fields import Command
from odoo.tests import Form, tagged

from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale_renting.tests.common import TestWebsiteSaleRentingCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockRenting(TestWebsiteSaleRentingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.computer.is_storable = True
        cls.computer.allow_out_of_stock_order = False
        cls.computer.website_published = True

        cls.company.update({
            'renting_forbidden_sat': False,
            'renting_forbidden_sun': False,
        })
        cls.current_website = cls.env['website'].create({
            'name': "Website Sale Stock Renting",
            'company_id': cls.company.id,
        })

        cls.wh = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        quants = cls.env['stock.quant'].create({
            'product_id': cls.computer.id,
            'inventory_quantity': 5.0,
            'location_id': cls.wh.lot_stock_id.id
        })
        quants.action_apply_inventory()
        cls.now = fields.Datetime.now()
        cls.so = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'company_id': cls.company.id,
            'warehouse_id': cls.wh.id,
            'website_id': cls.current_website.id,
            'rental_start_date': cls.now + relativedelta(days=1),
            'rental_return_date': cls.now + relativedelta(days=3),
        })
        cls.sol = cls.env['sale.order.line'].create({
            'order_id': cls.so.id,
            'product_id': cls.computer.id,
            'product_uom_qty': 3,
        })
        cls.sol.write({'is_rental': True})
        cls.user = cls.env['res.users'].with_company(cls.company.id).create({
            'name': 'Test User',
            'login': 'test_user',
            'company_id': cls.company.id,
        })

    def test_available_and_rented_quantities_for_draft_so(self):
        from_date = self.now
        to_date = self.now + relativedelta(days=4)

        self._assert_rented_quantities(
            from_date,
            to_date,
            expected_rented_quantities={},
            expected_key_dates=[from_date, to_date],
        )
        self._assert_availabilities(
            from_date,
            to_date,
            expected_availabilities=[
                {'start': from_date, 'end': to_date, 'quantity_available': 5},
            ],
        )
        self.so.update({'rental_start_date': from_date, 'rental_return_date': to_date})
        self._assert_cart_and_free_qty(self.so, expected_cart_qty=3, expected_free_qty=5)

    def test_available_and_rented_quantities_for_sent_so(self):
        self.so.action_quotation_sent()
        from_date = self.now
        to_date = self.now + relativedelta(days=4)
        start_date = self.sol.start_date
        return_date = self.sol.return_date

        self._assert_rented_quantities(
            from_date,
            to_date,
            expected_rented_quantities={start_date: 3, return_date: -3},
            expected_key_dates=[from_date, start_date, return_date, to_date],
        )
        self._assert_availabilities(
            from_date,
            to_date,
            expected_availabilities=[
                {'start': from_date, 'end': start_date, 'quantity_available': 5},
                {'start': start_date, 'end': return_date, 'quantity_available': 2},
                {'start': return_date, 'end': to_date, 'quantity_available': 5},
            ],
        )
        self.so.update({'rental_start_date': from_date, 'rental_return_date': to_date})
        self._assert_cart_and_free_qty(self.so, expected_cart_qty=3, expected_free_qty=5)

    def test_available_and_rented_quantities_for_confirmed_so(self):
        self.so.action_confirm()
        from_date = self.now
        to_date = self.now + relativedelta(days=4)
        start_date = self.sol.start_date
        return_date = self.sol.return_date

        self._assert_rented_quantities(
            from_date,
            to_date,
            expected_rented_quantities={start_date: 3, return_date: -3},
            expected_key_dates=[from_date, start_date, return_date, to_date],
        )
        self._assert_availabilities(
            from_date,
            to_date,
            expected_availabilities=[
                {'start': from_date, 'end': start_date, 'quantity_available': 5},
                {'start': start_date, 'end': return_date, 'quantity_available': 2},
                {'start': return_date, 'end': to_date, 'quantity_available': 5},
            ],
        )
        self.so.update({'rental_start_date': from_date, 'rental_return_date': to_date})
        self._assert_cart_and_free_qty(self.so, expected_cart_qty=3, expected_free_qty=5)

    def test_available_and_rented_quantities_for_picked_up_so(self):
        self.so.action_confirm()
        self._pickup_so(self.so)
        from_date = self.now
        to_date = self.now + relativedelta(days=4)
        start_date = self.sol.start_date
        return_date = self.sol.return_date

        self._assert_rented_quantities(
            from_date,
            to_date,
            expected_rented_quantities={from_date: 3, start_date: 0, return_date: -3},
            expected_key_dates=[from_date, start_date, return_date, to_date],
        )
        self._assert_availabilities(
            from_date,
            to_date,
            expected_availabilities=[
                {'start': from_date, 'end': start_date, 'quantity_available': 2},
                {'start': start_date, 'end': return_date, 'quantity_available': 2},
                {'start': return_date, 'end': to_date, 'quantity_available': 5},
            ],
        )
        self.so.update({'rental_start_date': from_date, 'rental_return_date': to_date})
        self._assert_cart_and_free_qty(self.so, expected_cart_qty=3, expected_free_qty=5)

    def test_available_and_rented_quantities_for_returned_so(self):
        self.so.action_confirm()
        self._pickup_so(self.so)
        self._return_so(self.so)
        from_date = self.now
        to_date = self.now + relativedelta(days=4)
        start_date = self.sol.start_date
        return_date = self.sol.return_date

        self._assert_rented_quantities(
            from_date,
            to_date,
            expected_rented_quantities={from_date: 0, start_date: 0, return_date: 0},
            expected_key_dates=[from_date, start_date, return_date, to_date],
        )
        self._assert_availabilities(
            from_date,
            to_date,
            expected_availabilities=[
                {'start': from_date, 'end': start_date, 'quantity_available': 5},
                {'start': start_date, 'end': return_date, 'quantity_available': 5},
                {'start': return_date, 'end': to_date, 'quantity_available': 5},
            ],
        )
        self.so.update({'rental_start_date': from_date, 'rental_return_date': to_date})
        self._assert_cart_and_free_qty(self.so, expected_cart_qty=0, expected_free_qty=5)

    def test_available_and_rented_quantities_for_multiple_sos(self):
        self.so.action_confirm()
        so2 = self._create_so_with_sol(
            rental_start_date=self.now + relativedelta(days=1),
            rental_return_date=self.now + relativedelta(days=2),
            product_uom_qty=2,
        )
        so2.action_confirm()
        from_date = self.now
        to_date = self.now + relativedelta(days=4)
        start_date = self.sol.start_date
        return_date = self.sol.return_date
        return_date2 = so2.rental_return_date

        self._assert_rented_quantities(
            from_date,
            to_date,
            expected_rented_quantities={start_date: 5, return_date2: -2, return_date: -3},
            expected_key_dates=[from_date, start_date, return_date2, return_date, to_date],
        )
        self._assert_availabilities(
            from_date,
            to_date,
            expected_availabilities=[
                {'start': from_date, 'end': start_date, 'quantity_available': 5},
                {'start': start_date, 'end': return_date2, 'quantity_available': 0},
                {'start': return_date2, 'end': return_date, 'quantity_available': 2},
                {'start': return_date, 'end': to_date, 'quantity_available': 5},
            ],
        )
        self.so.update({'rental_start_date': from_date, 'rental_return_date': to_date})
        self._assert_cart_and_free_qty(so2, expected_cart_qty=2, expected_free_qty=2)

    def test_available_and_rented_quantities_for_multiple_sos_with_one_picked_up(self):
        self.so.action_confirm()
        self._pickup_so(self.so)
        so2 = self._create_so_with_sol(
            rental_start_date=self.now + relativedelta(days=1),
            rental_return_date=self.now + relativedelta(days=2),
            product_uom_qty=2,
        )
        so2.action_confirm()
        from_date = self.now
        to_date = self.now + relativedelta(days=4)
        return_date = self.sol.return_date
        start_date2 = so2.rental_start_date
        return_date2 = so2.rental_return_date

        self._assert_rented_quantities(
            from_date,
            to_date,
            expected_rented_quantities={
                from_date: 3, start_date2: 2, return_date2: -2, return_date: -3,
            },
            expected_key_dates=[from_date, start_date2, return_date2, return_date, to_date],
        )
        self._assert_availabilities(
            from_date,
            to_date,
            expected_availabilities=[
                {'start': from_date, 'end': start_date2, 'quantity_available': 2},
                {'start': start_date2, 'end': return_date2, 'quantity_available': 0},
                {'start': return_date2, 'end': return_date, 'quantity_available': 2},
                {'start': return_date, 'end': to_date, 'quantity_available': 5},
            ],
        )
        self.so.update({'rental_start_date': from_date, 'rental_return_date': to_date})
        self._assert_cart_and_free_qty(so2, expected_cart_qty=2, expected_free_qty=2)

    def test_add_max_quantity_to_cart(self):
        with MockRequest(self.env, website=self.current_website, sale_order_id=self.so.id):
            website_so = self.current_website.with_user(self.user).sale_get_order()
            values = website_so._cart_update(
                product_id=self.computer.id, line_id=self.sol.id, add_qty=3,
            )
            self.assertEqual(values['quantity'], 5)
            self.assertTrue(values['warning'])

    def test_add_picked_up_products_not_yet_returned_to_cart_before_return_date(self):
        self.so.action_confirm()
        self._pickup_so(self.so)
        so2 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'warehouse_id': self.wh.id,
        })

        with MockRequest(self.env, website=self.current_website, sale_order_id=so2.id):
            website_so = self.current_website.with_user(self.user).sale_get_order()
            from_date = self.sol.return_date + relativedelta(days=-1)
            to_date = self.sol.return_date + relativedelta(days=2)

            website_so.update({'rental_start_date': from_date, 'rental_return_date': to_date})
            self._assert_cart_and_free_qty(website_so, expected_cart_qty=0, expected_free_qty=2)
            values = website_so._cart_update(
                product_id=self.computer.id, add_qty=5, start_date=from_date, end_date=to_date,
            )
            self.assertEqual(values['quantity'], 2)
            self.assertTrue(values['warning'])

    def test_add_picked_up_products_not_yet_returned_to_cart_after_return_date(self):
        self.so.action_confirm()
        self._pickup_so(self.so)
        so2 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'warehouse_id': self.wh.id,
        })

        with MockRequest(self.env, website=self.current_website, sale_order_id=so2.id):
            website_so = self.current_website.with_user(self.user).sale_get_order()
            from_date = self.sol.return_date + relativedelta(days=1)
            to_date = self.sol.return_date + relativedelta(days=2)

            website_so.update({'rental_start_date': from_date, 'rental_return_date': to_date})
            self._assert_cart_and_free_qty(website_so, expected_cart_qty=0, expected_free_qty=5)
            values = website_so._cart_update(
                product_id=self.computer.id, add_qty=5, start_date=from_date, end_date=to_date,
            )
            self.assertEqual(values['quantity'], 5)
            self.assertFalse(values['warning'])

    def test_show_rental_product_that_will_be_available_in_future(self):
        """
        When you filter rental products on the /shop with the datepicker,
        you should be able to see rental products that would be available in the future,
        even if today the quantity on hand is 0 because it is being rented
        """
        self.sol.product_uom_qty = 5
        self.so.action_confirm()
        self._pickup_so(self.so)
        from_date = self.sol.return_date + relativedelta(days=1)
        to_date = self.sol.return_date + relativedelta(days=2)

        product_template = self.sol.product_template_id.with_company(self.company).sudo()
        filtered_products_during_rental = (
            product_template._filter_on_available_rental_products(
                self.sol.start_date, self.sol.return_date, self.wh.id,
            )
        )
        self.assertFalse(filtered_products_during_rental)
        filtered_products_after_rental = (
            product_template._filter_on_available_rental_products(from_date, to_date, self.wh.id)
        )
        self.assertTrue(filtered_products_after_rental)

    def test_cart_and_free_qty_with_line(self):
        with freeze_time(self.now):
            cart_qty, free_qty = self.so._get_cart_and_free_qty(
                product=self.env['product.product'], line=self.sol
            )

        self.assertEqual(cart_qty, 3)
        self.assertEqual(free_qty, 5)

    def _assert_rented_quantities(
        self, from_date, to_date, expected_rented_quantities, expected_key_dates
    ):
        with freeze_time(self.now):
            rented_quantities, key_dates = self.computer._get_rented_quantities(from_date, to_date)
        self.assertDictEqual(rented_quantities, expected_rented_quantities)
        self.assertListEqual(key_dates, expected_key_dates)

    def _assert_availabilities(self, from_date, to_date, expected_availabilities):
        with freeze_time(self.now):
            availabilities = self.computer._get_availabilities(from_date, to_date, self.wh.id)
        self.assertListEqual(availabilities, expected_availabilities)

    def _assert_cart_and_free_qty(self, so, expected_cart_qty, expected_free_qty):
        with freeze_time(self.now):
            cart_qty, free_qty = so._get_cart_and_free_qty(product=self.computer)
        self.assertEqual(cart_qty, expected_cart_qty)
        self.assertEqual(free_qty, expected_free_qty)

    def _create_so_with_sol(self, rental_start_date, rental_return_date, **sol_values):
        return self.env['sale.order'].with_context(in_rental_app=True).create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'warehouse_id': self.wh.id,
            'rental_start_date': rental_start_date,
            'rental_return_date': rental_return_date,
            'order_line': [
                Command.create({
                    'product_id': self.computer.id,
                    **sol_values,
                })
            ]
        })

    def _pickup_so(self, so):
        pickup_action = so.action_open_pickup()
        Form(self.env['rental.order.wizard'].with_context(pickup_action['context'])).save().apply()

    def _return_so(self, so):
        return_action = so.action_open_return()
        Form(self.env['rental.order.wizard'].with_context(return_action['context'])).save().apply()
