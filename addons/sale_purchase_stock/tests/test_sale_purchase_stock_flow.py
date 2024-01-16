# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, Form
from freezegun import freeze_time
from datetime import datetime, timedelta

class TestSalePurchaseStockFlow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestSalePurchaseStockFlow, cls).setUpClass()
        cls.mto_route = cls.env.ref('stock.route_warehouse0_mto')
        cls.buy_route = cls.env.ref('purchase_stock.route_warehouse0_buy')
        cls.mto_route.active = True

        cls.customer_location = cls.env.ref('stock.stock_location_customers')

        cls.vendor = cls.env['res.partner'].create({'name': 'Super Vendor'})
        cls.customer = cls.env['res.partner'].create({'name': 'Super Customer'})

        cls.mto_product = cls.env['product.product'].create({
            'name': 'SuperProduct',
            'type': 'product',
            'route_ids': [(6, 0, (cls.mto_route + cls.buy_route).ids)],
            'seller_ids': [(0, 0, {
                'partner_id': cls.vendor.id,
            })],
        })

    def test_cancel_so_with_draft_po(self):
        """
        Sell a MTO+Buy product -> a PO is generated
        Cancel the SO -> an activity should be added to the PO
        """
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.env.user.partner_id
        with so_form.order_line.new() as line:
            line.product_id = self.mto_product
        so = so_form.save()
        so.action_confirm()

        po = self.env['purchase.order'].search([('partner_id', '=', self.vendor.id)])

        so._action_cancel()

        self.assertTrue(po.activity_ids)
        self.assertIn(so.name, po.activity_ids.note)

    def test_qty_delivered_with_mto_and_done_quantity_change(self):
        """
        MTO product P
        Sell 10 x P. On the delivery, set the done quantity to 12, validate and
        then set the done quantity to 10: the delivered qty of the SOL should
        be 10
        """
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'name': self.mto_product.name,
                'product_id': self.mto_product.id,
                'product_uom_qty': 10,
                'product_uom': self.mto_product.uom_id.id,
                'price_unit': 1,
            })],
        })
        so.action_confirm()

        delivery = so.picking_ids.filtered(lambda p: p.location_dest_id == self.customer_location)
        sm = delivery.move_ids
        sm.move_line_ids = [(5, 0, 0), (0, 0, {
            'location_id': sm.location_id.id,
            'location_dest_id': sm.location_dest_id.id,
            'product_id': sm.product_id.id,
            'quantity': 12,
            'company_id': sm.company_id.id,
            'product_uom_id': sm.product_uom.id,
            'picking_id': delivery.id,
        })]
        delivery.button_validate()

        self.assertEqual(delivery.state, 'done')
        self.assertEqual(delivery.move_ids.move_line_ids.quantity, 12)
        self.assertEqual(so.order_line.qty_delivered, 12)

        sm.move_line_ids.quantity = 10
        self.assertEqual(so.order_line.qty_delivered, 10)

    @freeze_time('2024-01-01')
    def test_reordering_with_visibility_days(self):
        """
        If reordering rules' visibility is set bigger than
        DAYS_FROM_TODAY_TO_ORDER (plus lead time). Then the
        order should be included in the calculation of quantity to order.

            ┌─ Today                     ┌── Scheduled Delivery
            │ (2024-01-01)               │    (2024-02-01)
            │                            │    aka commitment_date
            │                            │
            ▼                            ▼
          ──────────────────────────────────────────►
                                                    time
            ◄────────────────────────────►
                DAYS_FROM_TODAY_TO_ORDER

                                    ◄────►
                                    lead_time
        """
        N_ORDERED_QTY = 666
        DAYS_FROM_TODAY_TO_ORDER = 30
        MONTH_FROM_TODAY = (datetime.today() + timedelta(days=DAYS_FROM_TODAY_TO_ORDER)).strftime('%Y-%m-%d')

        # Setup: Create a product with vendor
        partner = self.env['res.partner'].create({'name': 'Azure Interior'})
        seller = self.env['product.supplierinfo'].create({
                'partner_id': partner.id,
                'price': 1.0,
        })
        product = self.env['product.product'].create({
            'name': 'Dummy Product',
            'type': 'product',
            'seller_ids': [seller.id],
        })

        # Setup: Create sale order scheduled in the future
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'commitment_date': MONTH_FROM_TODAY,
            'order_line': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'price_unit': 1,
                'product_uom_qty': N_ORDERED_QTY,
            })],
        })
        so.action_confirm() # so.state: 'draft' -> 'sale'

        # Create Reordering rule and trigger  recalculation
        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'])
        orderpoint_form.product_id = product
        orderpoint_form.visibility_days = DAYS_FROM_TODAY_TO_ORDER
        orderpoint = orderpoint_form.save()

        self.assertEqual(orderpoint.qty_to_order, N_ORDERED_QTY, f"Order from {DAYS_FROM_TODAY_TO_ORDER} days from today NOT included into the qty_to_order calculation, despite having visibility days set {DAYS_FROM_TODAY_TO_ORDER}!")
