# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo.tests import common
from odoo import fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.fields import Datetime


class TestRentalCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rental_start_date = Datetime.today() + timedelta(days=1)
        cls.rental_return_date = Datetime.today() + timedelta(days=7)
        cls.warehouse_id = cls.env.user._get_default_warehouse_id()

        cls.env.company.extra_product = cls.env['product.product'].create({'name': 'Late fee', 'type': 'service'})

        cls.product_id = cls.env['product.product'].create({
            'name': 'Test1',
            'categ_id': cls.env.ref('product.product_category_all').id,  # remove category if possible?
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
            'rent_ok': True,
            'is_storable': True,
            'extra_daily': 10.0
        })
        cls.tracked_product_id = cls.env['product.product'].create({
            'name': 'Test2',
            'categ_id': cls.env.ref('product.product_category_all').id,  # remove category if possible?
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
            'rent_ok': True,
            'is_storable': True,
            'tracking': 'serial',
        })

        # Set Stock quantities

        cls.lot_id1 = cls.env['stock.lot'].create({
            'product_id': cls.tracked_product_id.id,
            'name': "RentalLot1",
        })

        cls.lot_id2 = cls.env['stock.lot'].create({
            'product_id': cls.tracked_product_id.id,
            'name': "RentalLot2",
        })

        cls.lot_id3 = cls.env['stock.lot'].create({
            'product_id': cls.tracked_product_id.id,
            'name': "RentalLot3",
        })

        quants = cls.env['stock.quant'].create({
            'product_id': cls.product_id.id,
            'inventory_quantity': 4.0,
            'location_id': cls.env.user._get_default_warehouse_id().lot_stock_id.id
        })
        quants |= cls.env['stock.quant'].create({
            'product_id': cls.tracked_product_id.id,
            'inventory_quantity': 1.0,
            'lot_id': cls.lot_id1.id,
            'location_id': cls.env.user._get_default_warehouse_id().lot_stock_id.id
        })
        quants |= cls.env['stock.quant'].create({
            'product_id': cls.tracked_product_id.id,
            'inventory_quantity': 1.0,
            'lot_id': cls.lot_id2.id,
            'location_id': cls.env.user._get_default_warehouse_id().lot_stock_id.id
        })
        quants |= cls.env['stock.quant'].create({
            'product_id': cls.tracked_product_id.id,
            'inventory_quantity': 1.0,
            'lot_id': cls.lot_id3.id,
            'location_id': cls.env.user._get_default_warehouse_id().lot_stock_id.id
        })
        quants.action_apply_inventory()

        # Define rental order and lines

        cls.cust1 = cls.env['res.partner'].create({'name': 'test_rental_1'})
        # cls.cust2 = cls.env['res.partner'].create({'name': 'test_rental_2'})

        cls.user_id = mail_new_test_user(
            cls.env,
            name='Rental',
            login='renter',
            email='sale.rental@example.com',
            notification_type='inbox',
        )

        cls.sale_order_id = cls.env['sale.order'].create({
            'partner_id': cls.cust1.id,
            'partner_invoice_id': cls.cust1.id,
            'partner_shipping_id': cls.cust1.id,
            'user_id': cls.user_id.id,
            'rental_start_date': fields.Datetime.today(),
            'rental_return_date': fields.Datetime.today() + timedelta(days=3),
        })

        cls.order_line_id1 = cls.env['sale.order.line'].create({
            'order_id': cls.sale_order_id.id,
            'product_id': cls.product_id.id,
            'product_uom_qty': 0.0,
            'price_unit': 150,
        })
        cls.order_line_id1.update({'is_rental': True})

        cls.sale_order_id.action_confirm()

        cls.lots_rental_order = cls.env['sale.order'].create({
            'partner_id': cls.cust1.id,
            'partner_invoice_id': cls.cust1.id,
            'partner_shipping_id': cls.cust1.id,
            'user_id': cls.user_id.id,
        })

        cls.order_line_id2 = cls.env['sale.order.line'].create({
            'order_id': cls.lots_rental_order.id,
            'product_id': cls.tracked_product_id.id,
            'product_uom_qty': 0.0,
            'price_unit': 250,
        })
        cls.order_line_id2.update({'is_rental': True})

        cls.order_line_id3 = cls.env['sale.order.line'].create({
            'order_id': cls.lots_rental_order.id,
            'product_id': cls.tracked_product_id.id,
            'product_uom_qty': 0.0,
            'price_unit': 250,
        })
        cls.order_line_id3.update({'is_rental': True})
