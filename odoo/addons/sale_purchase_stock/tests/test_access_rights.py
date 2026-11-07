# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.sale_purchase.tests.common import TestCommonSalePurchaseNoChart


@tagged('post_install', '-at_install')
class TestAccessRights(TestCommonSalePurchaseNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestAccessRights, cls).setUpClass()

        group_sale_user = cls.env.ref('sales_team.group_sale_salesman')

        cls.user_salesperson = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Le Grand Jojo User',
            'login': 'grand.jojo',
            'email': 'grand.jojo@chansonbelge.com',
            'groups_id': [(6, 0, [group_sale_user.id])]
        })

    def test_access_saleperson_decreases_qty(self):
        """
        Suppose a user who has no right on PO
        Suppose a PO linked to a SO
        The user decreases the qty on the SO
        This test ensures that an activity (warning) is added to the PO
        """
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        buy_route = self.env.ref('purchase_stock.route_warehouse0_buy')
        mto_route.active = True

        vendor = self.env['res.partner'].create({'name': 'vendor'})
        seller = self.env['product.supplierinfo'].create({
            'partner_id': vendor.id,
            'price': 8,
        })

        product = self.env['product.product'].create({
            'name': 'SuperProduct',
            'type': 'product',
            'seller_ids': [(6, 0, seller.ids)],
            'route_ids': [(6, 0, (mto_route + buy_route).ids)]
        })

        so = self.env['sale.order'].with_user(self.user_salesperson).create({
            'partner_id': self.partner_a.id,
            'user_id': self.user_salesperson.id,
        })
        so_line, _ = self.env['sale.order.line'].create([{
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'product_uom': product.uom_id.id,
            'price_unit': product.list_price,
            'tax_id': False,
            'order_id': so.id,
        }, {
            'name': 'Super Section',
            'display_type': 'line_section',
            'order_id': so.id,
        }])

        so.action_confirm()

        po = self.env['purchase.order'].search([('partner_id', '=', vendor.id)])
        po.button_confirm()

        # salesperson writes on the SO
        so.write({
            'order_line': [(1, so_line.id, {'product_uom_qty': 0.9})]
        })

        self.assertIn(so.name, po.activity_ids.note)

    def test_access_saleperson_with_orderpoint(self):
        """
        Suppose a user with no rights on SO creates a product with an orderpoint,
        then creates an SO, SO the PO will be generated. After creating a second SO,
        the PO should be updated since it has not been confirmed yet.
        """
        seller = self.env['product.supplierinfo'].create({
            'partner_id': self.partner_a.id,
            'price': 8,
        })
        product = self.env['product.product'].create({
            'name': 'SuperProduct',
            'type': 'product',
            'seller_ids': [(6, 0, seller.ids)],
        })
        self.env['stock.warehouse.orderpoint'].create({
            'name': 'orderpoint test',
            'product_id': product.id,
            'product_min_qty': 0,
            'product_max_qty': 1,
            'route_id': self.env.ref('purchase_stock.route_warehouse0_buy').id,
        })
        # Create a SO that will automatically generate a SO since we have an orderpoint"
        so = self.env['sale.order'].with_user(self.user_salesperson).create({
            'partner_id': self.partner_b.id,
            'user_id': self.user_salesperson.id,
            'order_line': [
                (0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': 10,
                    'product_uom': product.uom_id.id,
                    'price_unit': product.list_price,
                })]
        })
        so.action_confirm()
        # Create a second SO, and since a PO has already been created but not yet validated, it will be updated.
        so_2 = so.copy()
        # Find the PO that will be updated in order to invalidate its cache,
        # so the fields will be reloaded with the sales user.
        po = self.env['purchase.order'].search([('partner_id', '=', self.partner_a.id)])
        self.assertEqual(po.order_line[0].product_qty, 11)
        po.order_line[0].invalidate_recordset()
        # Confirm the second SO and verify if PO has been updated.
        so_2.action_confirm()
        self.assertEqual(po.order_line[0].product_qty, 21)
        po.button_confirm()
        self.assertEqual(po.state, 'purchase')
