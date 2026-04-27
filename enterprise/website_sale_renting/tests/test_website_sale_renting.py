# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta, FR, SA, SU

from freezegun import freeze_time

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
            'rental_return_date': now + relativedelta(weeks=1, weekday=SA),
            'website_id': self.website.id,
        })
        sol = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': self.computer.id,
        })
        sol.update({'is_rental': True})

        # Created a sale order with same dates for different website
        so_2 = so.copy({'website_id': self.website_2.id})
        sol_2 = self.env['sale.order.line'].create({
            'order_id': so_2.id,
            'product_id': self.computer.id,
        })
        sol_2.update({'is_rental': True})

        self.assertFalse(
            so._is_valid_renting_dates(),
            "Pickup and Return dates cannot be set on renting unavailabilities days"
        )
        self.assertTrue(
            so_2._is_valid_renting_dates(),
            "Pickup and Return dates can be set on renting availabilities days"
        )

        so.write({
            'rental_start_date': now + relativedelta(weekday=FR),
            'rental_return_date': now + relativedelta(weeks=1, weekday=SA),
        })
        self.assertFalse(
            so._is_valid_renting_dates(),
            "Return date cannot be set on a renting unavailabilities day"
        )
        so_2.write({
            'rental_start_date': now + relativedelta(weekday=FR),
            'rental_return_date': now + relativedelta(weeks=1, weekday=SA),
        })
        self.assertTrue(
            so_2._is_valid_renting_dates(),
            "Return date can be set on a renting availabilities day"
        )

        so.write({
            'rental_start_date': now + relativedelta(weekday=SA),
            'rental_return_date': now + relativedelta(weeks=1, weekday=FR),
        })
        self.assertFalse(
            so._is_valid_renting_dates(), "Start date cannot be set on a renting unavailabilities day"
        )
        so_2.write({
            'rental_start_date': now + relativedelta(weekday=SA),
            'rental_return_date': now + relativedelta(weeks=1, weekday=FR),
        })
        self.assertTrue(
            so_2._is_valid_renting_dates(), "Start date can be set on a renting availabilities day"
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

    def test_daylight_saving_time_change(self):
        self.website.tz = 'Europe/Brussels'

        # pytz.exceptions.AmbiguousTimeError:
        with freeze_time('2024-10-27 02:01:00 UTC'):
            self.assertTrue(self.website._is_customer_in_the_same_timezone())

        # pytz.exceptions.NonExistentTimeError
        with freeze_time('2025-03-30 02:01:00 UTC'):
            self.assertTrue(self.website._is_customer_in_the_same_timezone())
