# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.sale_purchase.tests.common import TestCommonSalePurchaseNoChart
from odoo.exceptions import AccessError
from odoo.tests import tagged


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
            'group_ids': [(6, 0, [group_sale_user.id])]
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
        mto_route.rule_ids.procure_method = "make_to_order"
        mto_route.active = True

        vendor = self.env['res.partner'].create({'name': 'vendor'})

        product = self.env['product.product'].create({
            'name': 'SuperProduct',
            'is_storable': True,
            'seller_ids': [Command.create({
                'partner_id': vendor.id,
                'price': 8,
            })],
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
            'price_unit': product.list_price,
            'tax_ids': False,
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
        then creates a sale order, so the PO will be generated. After creating a second SO,
        the PO should be updated since it has not been confirmed yet.
        """
        product = self.env['product.product'].create({
            'name': 'SuperProduct',
            'is_storable': True,
            'seller_ids': [Command.create({
                'partner_id': self.partner_a.id,
                'price': 8,
            })],
        })
        self.env['stock.warehouse.orderpoint'].create({
            'name': 'orderpoint test',
            'product_id': product.id,
            'product_min_qty': 0,
            'product_max_qty': 0,
            'route_id': self.env.ref('purchase_stock.route_warehouse0_buy').id,
        })
        # Create a SO that will automatically generate a PO since we have an orderpoint"
        so = self.env['sale.order'].with_user(self.user_salesperson).create({
            'partner_id': self.partner_b.id,
            'user_id': self.user_salesperson.id,
            'order_line': [
                (0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': 10,
                    'price_unit': product.list_price,
                })]
        })
        so.action_confirm()
        po = self.env['purchase.order'].search([('partner_id', '=', self.partner_a.id)])
        self.assertEqual(po.order_line[0].product_qty, 10)
        so.order_line = [Command.create({
            'product_id': product.id,
            'product_uom_qty': 11,
            'price_unit': product.list_price,
        })]

        self.assertEqual(po.order_line[0].product_qty, 21)
        po.button_confirm()
        self.assertEqual(po.state, 'purchase')

    def test_sales_user_can_access_forecast_report(self):
        # `get_report_values` calls `_get_source_document`, which can be a PO, SO, MO, repair etc.
        # A sales user might not have access to that model by default.
        # This PO provides a source document to test if it can be accessed in the forecast report.
        po = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': 'test',
                'product_id': self.product.id,
                'product_qty': 1,
                'product_uom_id': self.product.uom_id.id,
            })]
        })
        # This PO belongs to a different company, it should not be shown
        different_company_po = self.env['purchase.order'].create({
            'company_id': self.env['res.company'].create({'name': 'Different Company'}).id,
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': 'test',
                'product_id': self.product.id,
                'product_qty': 2,
                'product_uom_id': self.product.uom_id.id,
            })]
        })
        # (POs are not confirmed, to keep the lines in the 'draft' state)
        # Reset the cache to correctly test the permissions
        po.env.invalidate_all()
        different_company_po.env.invalidate_all()
        # A sales user can access the report without any errors
        report_values = self.env['stock.forecasted_product_product'].with_user(
            self.user_salesperson
        ).get_report_values(docids=self.product.ids)
        # No exception was raised, but user is not allowed to edit pickings
        self.assertEqual(report_values['docs']['user_can_edit_pickings'], False)
        # The data in the report includes only the first PO
        self.assertEqual(report_values['docs']['product'][self.product.id]['draft_purchase_qty']['in'], 1)
        self.assertEqual(report_values['docs']['product'][self.product.id]['draft_purchase_orders'], [{'id': po.id, 'name': po.name}])
        # A sales user cannot access the PO directly, despite viewing it's info in the report
        with self.assertRaises(AccessError, msg='Sales user is not allowed to access a PO'):
            po.with_user(self.user_salesperson).button_confirm()
