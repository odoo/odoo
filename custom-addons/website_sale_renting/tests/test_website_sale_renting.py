# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta, FR, SA, SU

from freezegun import freeze_time
from pytz import timezone

from odoo import fields
from odoo.tests import tagged
from .common import TestWebsiteSaleRentingCommon

@tagged('post_install', '-at_install')
class TestWebsiteSaleRenting(TestWebsiteSaleRentingCommon):

    def test_is_add_to_cart_possible(self):
        self.product_id = self.env['product.product'].create({
            'name': 'Projector',
            'categ_id': self.env.ref('product.product_category_all').id,
            'type': 'consu',
            'rent_ok': True,
            'extra_hourly': 7.0,
            'extra_daily': 30.0,
        })

        self.product_template_id = self.product_id.product_tmpl_id
        # Check that `is_add_to_cart_possible` returns True when
        # the product is active and can be rent or/and sold
        self.product_template_id.write({'sale_ok': False, 'rent_ok': False})
        self.assertFalse(self.product_template_id._is_add_to_cart_possible())
        self.product_template_id.write({'sale_ok': True})
        self.assertTrue(self.product_template_id._is_add_to_cart_possible())
        self.product_template_id.write({'sale_ok': False, 'rent_ok': True})
        self.assertTrue(self.product_template_id._is_add_to_cart_possible())
        self.product_template_id.write({'sale_ok': True})
        self.assertTrue(self.product_template_id._is_add_to_cart_possible())
        self.product_template_id.write({'active': False})
        self.assertFalse(self.product_template_id._is_add_to_cart_possible())

    @freeze_time('2023, 1, 1')
    def test_invalid_dates(self):
        now = fields.Datetime.now()
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'rental_start_date': now + relativedelta(weekday=SA),
            'rental_return_date': now + relativedelta(weeks=1, weekday=SU),
        })
        sol = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': self.computer.id,
        })
        sol.update({'is_rental': True})
        self.assertFalse(
            so._is_valid_renting_dates(),
            "Pickup and Return dates cannot be set on renting unavailabilities days"
        )
        so.write({
            'rental_start_date': now + relativedelta(weekday=FR),
            'rental_return_date': now + relativedelta(weeks=1, weekday=SU),
        })
        self.assertFalse(
            so._is_valid_renting_dates(),
            "Return date cannot be set on a renting unavailabilities day"
        )
        so.write({
            'rental_start_date': now + relativedelta(weekday=SU),
            'rental_return_date': now + relativedelta(weeks=1, weekday=FR),
        })
        self.assertFalse(
            so._is_valid_renting_dates(), "Start date cannot be set on a renting unavailabilities day"
        )
        so.write({
            'rental_start_date': now + relativedelta(weeks=1, weekday=SU),
            'rental_return_date': now,
        })
        self.assertFalse(
            so._is_valid_renting_dates(), "Return date cannot be prior to pickup date"
        )

    def test_add_rental_product_to_cart(self):
        """
        Make sure that we can add a rental product
        (only marked as "can be rented" and not "can be sold") to the shopping cart
        """
        self.computer.write({
            'website_published': True,
            'active': True,
            'sale_ok': False,
            'rent_ok': True,
        })
        self.assertTrue(self.computer._is_add_to_cart_allowed(), "Rental product should be addable to the cart")

    def test_now_is_valid_date(self):
        with freeze_time('2023-01-02 00:00:00'):
            now = fields.Datetime.now()
            so = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'company_id': self.company.id,
                'rental_start_date': now,
                'rental_return_date': now + relativedelta(weeks=1),
            })
        with freeze_time('2023-01-02 00:10:00'): # tolerance of 15 minutes
            self.assertTrue(
                so._is_valid_renting_dates(), "It should be possible to rent the product now"
            )

    def test_availability_in_clients_tz(self):
        """
        Frontend sends dates to the server in UTC, but the server
        should check the availability in customer's timezone.
        """
        # UTC+1
        tzinfo = timezone('Europe/Paris')
        # 2024-04-15 is a Monday
        with freeze_time(datetime(year=2024, month=4, day=15, hour=0, minute=0, second=0, tzinfo=tzinfo)):
            now = fields.Datetime.now()
            so = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'company_id': self.company.id,
                'rental_start_date': now,
                'rental_return_date': now + relativedelta(days=1),
            })
            sol = self.env['sale.order.line'].create({
                'order_id': so.id,
                'product_id': self.computer.id,
            })
            sol.update({'is_rental': True})
            self.assertTrue(
                so._is_valid_renting_dates(), "It should be possible to rent the product on Monday"
            )
