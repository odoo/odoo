# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase  # pylint: disable=W0403


class TestSO2PO(TransactionCase):

    def setUp(self):
        super(TestSO2PO, self).setUp()

        self.route_mto = self.env.ref('stock.route_warehouse0_mto', False)
        self.route_buy = self.env.ref('purchase.route_warehouse0_buy', False)

        if not self.route_buy:
            self.skipTest("Purchase addon not installed. Test skipped...")

        # Find demo user and set it only salesman group for this test
        self.tuser = self.env.ref('base.user_demo')
        self.tuser.write({
            'groups_id': [
                (5, 0),
                (6, 0,  [self.ref('sales_team.group_sale_salesman')]),
            ],
        })

    def test_so_2_po(self):
        self.uenv = self.env(user=self.tuser)

        self.product_uom_unit = self.uenv.ref(
            "product.product_uom_unit")

        # Set product routes to MTO + Buy
        product = self.uenv.ref('product.product_product_20')
        product.sudo().write({
            'route_ids': [(4, self.route_mto.id)],
        })
        self.assertIn(self.route_mto, product.route_ids)
        self.assertIn(self.route_buy, product.route_ids)

        # Create SO for product that have route MTO+Buy
        so = self.uenv['sale.order'].create({
            "partner_id": self.uenv.ref("base.res_partner_2").id,
            "partner_invoice_id": self.uenv.ref("base.res_partner_2").id,
            "partner_shipping_id": self.uenv.ref("base.res_partner_2").id,
            "user_id": self.tuser.id,
            "pricelist_id": self.uenv.ref("product.list0").id,
            "order_line": [
                (0, 0, {
                    "name": product.name,
                    "product_id": product.id,
                    "product_uom_qty": 2.0,
                    "product_uom": self.product_uom_unit.id,
                    "price_unit": 75.00,
                }),
            ]
        })
        self.assertEqual(so.state, 'draft')

        # Confirm sale order and ensure it is in 'Sale' state
        so.action_confirm()
        self.assertEqual(so.state, 'sale')

        # Test that SO confirmation generated have generated two procurements:
        # one for move and one for buy
        self.assertIn(
            'move',
            so.procurement_group_id.procurement_ids.mapped('rule_id.action'))
        self.assertIn(
            'buy',
            so.procurement_group_id.procurement_ids.mapped('rule_id.action'))

        # Ensure procurement order (buy) have related purchase order
        po_procurement = so.procurement_group_id.procurement_ids.filtered(
            lambda p: p.rule_id.action == 'buy')

        self.assertTrue(po_procurement.purchase_id)
        self.assertTrue(po_procurement.purchase_line_id)
