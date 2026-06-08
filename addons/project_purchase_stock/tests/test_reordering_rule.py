# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo import Command


@tagged('post_install', '-at_install')
class TestReorderingRuleProjectPurchase(TransactionCase):

    def test_po_creation_and_reuse_based_on_project(self):
        """
        Verify that purchase orders are reused only when their project_id matches:
        - A PO with a project is reused only for procurements with the same project.
        - A PO without a project is reused only for procurements without a project.
        """
        partner = self.env['res.partner'].create({'name': 'Test Partner'})
        buy_product = self.env['product.product'].create({
            'name': 'Buy Product',
            'is_storable': True,
            'seller_ids': [Command.create({
                'partner_id': partner.id,
            })],
        })
        # Enable MTO + Buy routes
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        mto_route.active = True
        buy_product.route_ids |= mto_route | self.env.ref('purchase_stock.route_warehouse0_buy')

        ref = self.env["stock.reference"].create({'name': 'Test mto buy procurement'})
        # 1. First procurement → creates a PO with no project
        self.env["stock.rule"].run([self.env['stock.rule'].Procurement(
            buy_product, 1, buy_product.uom_id,
            self.env.ref('stock.stock_location_customers'),
            "Test mto buy", "/", self.env.company,
            {"warehouse_id": self.env.ref('stock.warehouse0'), "reference_ids": ref},
        )])
        po = self.env["purchase.order"].search([("partner_id", "=", partner.id)])
        self.assertEqual(len(po), 1, "Expected exactly one purchase order after first procurement")
        # 2. Add a project to the first PO → next procurement should not reuse it
        po.project_id = self.env['project.project'].create({'name': 'Test Project'})
        self.env["stock.rule"].run([self.env['stock.rule'].Procurement(
            buy_product, 1, buy_product.uom_id,
            self.env.ref('stock.stock_location_customers'),
            "Test mto buy", "/", self.env.company,
            {"warehouse_id": self.env.ref('stock.warehouse0'), "reference_ids": ref},
        )])
        second_po = self.env["purchase.order"].search([
            ("partner_id", "=", partner.id),
        ]) - po
        self.assertEqual(len(second_po), 1, "A new purchase order should be created as the first one has a project set")
        self.assertFalse(second_po.project_id, "The new purchase order should have no project since the procurement has none")
        self.assertEqual(second_po.order_line.product_uom_qty, 1)

        # 3. Another procurement without project → should reuse the second PO
        self.env["stock.rule"].run([self.env['stock.rule'].Procurement(
            buy_product, 1, buy_product.uom_id,
            self.env.ref('stock.stock_location_customers'),
            "Test mto buy", "/", self.env.company,
            {"warehouse_id": self.env.ref('stock.warehouse0'), "reference_ids": ref},
        )])
        extra_po = self.env["purchase.order"].search([
            ("partner_id", "=", partner.id),
            ("id", "not in", po.ids + second_po.ids),
        ])
        self.assertFalse(extra_po, "No new purchase order should be created since the second one matches (no project)")
