# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestORM(TransactionCase):
    """Test that when an included tax is mapped by a fiscal position, the included tax must be
    subtracted to the price of the product.
    """

    def test_orm_compute_on_create(self):

        # temp_order = self.env['sale.order'].new({
        #     'partner_id': self.env.user.partner_id.id,
        #     'order_line': [(0, 0, dict(product_id=self.env['product.product'].search([('sale_ok', '=', True)], limit=1)))]
        # })

        # Verify Sales Order and Sales Order Line can be created with minimal information.
        order = self.env['sale.order'].create({
            'partner_id': self.env.user.partner_id.id,
            'order_line': [(0, 0, dict(product_id=self.env['product.product'].search([('sale_ok', '=', True)], limit=1).id))]
        })

        # Check everything one2many is correctly created

        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(order.order_line.price_unit, order.amount_total) # No tax
