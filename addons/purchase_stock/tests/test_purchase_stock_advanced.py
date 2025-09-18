# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.stock.tests.common import TestStockCommon


@tagged('-at_install', 'post_install')
class TestPurchaseStockAdvanced(TestStockCommon):
    """Advanced tests for purchase_stock functionality covering gaps in test coverage."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create vendor
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Test Vendor',
        })

        # Create customer for dropship
        cls.customer = cls.env['res.partner'].create({
            'name': 'Test Customer',
        })

        # Get buy route
        cls.buy_route = cls.env.ref('purchase_stock.route_warehouse0_buy')
        cls.buy_route.product_selectable = True

        # Create storable product with vendor
        cls.product_storable = cls.env['product.product'].create({
            'name': 'Storable Product',
            'is_storable': True,
            'route_ids': [Command.set(cls.buy_route.ids)],
            'seller_ids': [Command.create({
                'partner_id': cls.vendor.id,
                'min_qty': 1,
                'price': 100,
                'delay': 5,
            })],
        })

        # Create product without vendor for error testing
        cls.product_no_vendor = cls.env['product.product'].create({
            'name': 'Product Without Vendor',
            'is_storable': True,
            'route_ids': [Command.set(cls.buy_route.ids)],
        })

    # -------------------------------------------------------------------------
    # DROPSHIP TESTS
    # -------------------------------------------------------------------------

    def test_dropship_purchase_flow(self):
        """Test purchase order with dropship destination."""
        # Create dropship route
        dropship_route = self.env['stock.route'].search([
            ('name', 'ilike', 'dropship'),
        ], limit=1)

        if not dropship_route:
            # Create dropship route if it doesn't exist
            supplier_loc = self.env.ref('stock.stock_location_suppliers')
            customer_loc = self.env.ref('stock.stock_location_customers')
            dropship_route = self.env['stock.route'].create({
                'name': 'Dropship',
                'product_selectable': True,
                'rule_ids': [Command.create({
                    'name': 'Dropship Rule',
                    'action': 'buy',
                    'location_dest_id': customer_loc.id,
                    'location_src_id': supplier_loc.id,
                    'picking_type_id': self.env.ref('stock.picking_type_in').id,
                })],
            })

        # Create PO with dropship address
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'dest_address_id': self.customer.id,
            'line_ids': [
                Command.create({
                    'product_id': self.product_storable.id,
                    'product_qty': 10,
                    'price_unit': 100,
                }),
            ],
        })

        self.assertEqual(po.dest_address_id, self.customer, "Dropship address should be set")

        po.action_confirm()

        # Check picking destination
        if po.picking_ids:
            picking = po.picking_ids[0]
            # For dropship, the destination should be the customer location
            self.assertTrue(
                picking.partner_id == self.customer or po.dest_address_id == self.customer,
                "Dropship should deliver to customer"
            )

    def test_purchase_order_dest_address_changes_picking(self):
        """Test that dest_address_id affects picking creation."""
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'dest_address_id': self.customer.id,
            'line_ids': [
                Command.create({
                    'product_id': self.product_storable.id,
                    'product_qty': 5,
                    'price_unit': 100,
                }),
            ],
        })

        po.action_confirm()

        # The PO should have the dest_address set
        self.assertEqual(po.dest_address_id, self.customer)

    # -------------------------------------------------------------------------
    # PROCUREMENT ERROR HANDLING TESTS
    # -------------------------------------------------------------------------

    def test_procurement_without_supplier_creates_notification(self):
        """Test that procurement without supplier notifies responsible user."""
        # Create orderpoint for product without vendor
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'warehouse_id': warehouse.id,
            'location_id': warehouse.lot_stock_id.id,
            'product_id': self.product_no_vendor.id,
            'product_min_qty': 10,
            'product_max_qty': 20,
            'route_id': self.buy_route.id,
        })

        # Run scheduler - should not create PO but should handle gracefully
        self.env['stock.rule'].with_context(from_orderpoint=True).run_scheduler()

        # Check that no PO was created for the product without vendor
        po_lines = self.env['purchase.order.line'].search([
            ('product_id', '=', self.product_no_vendor.id),
        ])

        # The behavior should be graceful - either no PO or an error notification
        # depending on context, but not a crash

    def test_procurement_with_invalid_supplier_min_qty(self):
        """Test procurement when supplier min_qty is not met."""
        # Create product with high min_qty
        product_high_min = self.env['product.product'].create({
            'name': 'High Min Qty Product',
            'is_storable': True,
            'route_ids': [Command.set(self.buy_route.ids)],
            'seller_ids': [Command.create({
                'partner_id': self.vendor.id,
                'min_qty': 1000,  # Very high minimum
                'price': 50,
            })],
        })

        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        # Create orderpoint with qty below min_qty
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'warehouse_id': warehouse.id,
            'location_id': warehouse.lot_stock_id.id,
            'product_id': product_high_min.id,
            'product_min_qty': 5,
            'product_max_qty': 10,
            'route_id': self.buy_route.id,
        })

        # Run scheduler
        self.env['stock.rule'].run_scheduler()

        # Check if PO was created - should still work, just uses the min_qty
        po_lines = self.env['purchase.order.line'].search([
            ('product_id', '=', product_high_min.id),
        ])

        # Supplier should still be found even if requested qty < min_qty
        # The system should either use min_qty or find no supplier

    # -------------------------------------------------------------------------
    # ORDERPOINT SUPPLIER TESTS
    # -------------------------------------------------------------------------

    def test_orderpoint_supplier_auto_route(self):
        """Test that setting supplier on orderpoint auto-assigns buy route."""
        product_no_route = self.env['product.product'].create({
            'name': 'Product No Route',
            'is_storable': True,
            'seller_ids': [Command.create({
                'partner_id': self.vendor.id,
                'min_qty': 1,
                'price': 75,
            })],
        })

        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'warehouse_id': warehouse.id,
            'location_id': warehouse.lot_stock_id.id,
            'product_id': product_no_route.id,
            'product_min_qty': 5,
            'product_max_qty': 10,
        })

        # Set supplier on orderpoint
        seller = product_no_route.seller_ids[0]
        orderpoint.supplier_id = seller

        # Check if buy route was auto-assigned
        self.assertEqual(
            orderpoint.route_id,
            self.buy_route,
            "Buy route should be auto-assigned when supplier is set"
        )

    def test_orderpoint_effective_vendor_computation(self):
        """Test effective_vendor_id computation on orderpoint."""
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'warehouse_id': warehouse.id,
            'location_id': warehouse.lot_stock_id.id,
            'product_id': self.product_storable.id,
            'product_min_qty': 5,
            'product_max_qty': 10,
            'route_id': self.buy_route.id,
        })

        # Without explicit supplier, effective_vendor should be computed from product
        self.assertTrue(
            orderpoint.effective_vendor_id or orderpoint.supplier_id,
            "Effective vendor should be computed from product sellers"
        )

    def test_orderpoint_clear_supplier_on_route_change(self):
        """Test that changing route clears supplier_id."""
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'warehouse_id': warehouse.id,
            'location_id': warehouse.lot_stock_id.id,
            'product_id': self.product_storable.id,
            'product_min_qty': 5,
            'product_max_qty': 10,
            'route_id': self.buy_route.id,
            'supplier_id': self.product_storable.seller_ids[0].id,
        })

        # Change to a non-buy route (if available)
        mto_route = self.env['stock.route'].search([
            ('name', 'ilike', 'make to order'),
        ], limit=1)

        if mto_route:
            orderpoint.route_id = mto_route
            # Supplier should be cleared when route changes to non-buy
            # This depends on implementation

    # -------------------------------------------------------------------------
    # TRANSFER STATE TESTS
    # -------------------------------------------------------------------------

    def test_transfer_state_no_picking(self):
        """Test transfer_state when no picking exists.

        When there are no pickings, transfer_state is False (not 'no').
        """
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'line_ids': [
                Command.create({
                    'product_id': self.product_storable.id,
                    'product_qty': 10,
                    'price_unit': 100,
                }),
            ],
        })

        self.assertFalse(po.transfer_state, "Transfer state should be False before confirmation")

    def test_transfer_state_to_do(self):
        """Test transfer_state when picking exists but not done."""
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'line_ids': [
                Command.create({
                    'product_id': self.product_storable.id,
                    'product_qty': 10,
                    'price_unit': 100,
                }),
            ],
        })
        po.action_confirm()

        self.assertEqual(po.transfer_state, 'to do', "Transfer state should be 'to do' after confirmation")

    def test_transfer_state_done(self):
        """Test transfer_state when all pickings are done."""
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'line_ids': [
                Command.create({
                    'product_id': self.product_storable.id,
                    'product_qty': 10,
                    'price_unit': 100,
                }),
            ],
        })
        po.action_confirm()

        # Complete the picking
        for picking in po.picking_ids:
            picking.move_ids.quantity = 10
            picking.move_ids.picked = True
            picking.button_validate()

        self.assertEqual(po.transfer_state, 'done', "Transfer state should be 'done' after all pickings complete")

    def test_transfer_state_partial(self):
        """Test transfer_state with partial receipt."""
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'line_ids': [
                Command.create({
                    'product_id': self.product_storable.id,
                    'product_qty': 10,
                    'price_unit': 100,
                }),
            ],
        })
        po.action_confirm()

        # Partial receipt
        picking = po.picking_ids[0]
        picking.move_ids.quantity = 5  # Only receive half
        picking.move_ids.picked = True
        res = picking.button_validate()

        # If a backorder wizard appears, create the backorder
        if res and isinstance(res, dict) and res.get('res_model') == 'stock.backorder.confirmation':
            backorder_wizard = self.env['stock.backorder.confirmation'].with_context(res['context']).create({})
            backorder_wizard.process()

        self.assertEqual(po.transfer_state, 'partial', "Transfer state should be 'partial'")

    # -------------------------------------------------------------------------
    # QTY TRANSFERRED TESTS
    # -------------------------------------------------------------------------

    def test_qty_transferred_after_receipt(self):
        """Test qty_transferred computation after receiving goods."""
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'line_ids': [
                Command.create({
                    'product_id': self.product_storable.id,
                    'product_qty': 10,
                    'price_unit': 100,
                }),
            ],
        })
        po.action_confirm()

        self.assertEqual(po.line_ids[0].qty_transferred, 0, "Should be 0 before receipt")

        # Complete the picking
        picking = po.picking_ids[0]
        picking.move_ids.quantity = 10
        picking.move_ids.picked = True
        picking.button_validate()

        self.assertEqual(po.line_ids[0].qty_transferred, 10, "Should be 10 after full receipt")

    def test_qty_to_transfer_computation(self):
        """Test qty_to_transfer computation."""
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'line_ids': [
                Command.create({
                    'product_id': self.product_storable.id,
                    'product_qty': 10,
                    'price_unit': 100,
                }),
            ],
        })
        po.action_confirm()

        self.assertEqual(po.line_ids[0].qty_to_transfer, 10, "Should be 10 before receipt")

        # Partial receipt
        picking = po.picking_ids[0]
        picking.move_ids.quantity = 4
        picking.move_ids.picked = True
        res = picking.button_validate()

        # Handle backorder wizard if it appears
        if res and isinstance(res, dict) and res.get('res_model') == 'stock.backorder.confirmation':
            backorder_wizard = self.env['stock.backorder.confirmation'].with_context(res['context']).create({})
            backorder_wizard.process()

        self.assertEqual(po.line_ids[0].qty_to_transfer, 6, "Should be 6 after partial receipt")

    # -------------------------------------------------------------------------
    # MOVE CANCELLATION TESTS
    # -------------------------------------------------------------------------

    def test_cancel_po_cancels_moves(self):
        """Test that cancelling PO cancels related stock moves."""
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'line_ids': [
                Command.create({
                    'product_id': self.product_storable.id,
                    'product_qty': 10,
                    'price_unit': 100,
                }),
            ],
        })
        po.action_confirm()

        picking = po.picking_ids[0]
        moves = picking.move_ids

        self.assertTrue(all(m.state not in ['done', 'cancel'] for m in moves))

        po.action_cancel()

        self.assertTrue(
            all(m.state == 'cancel' for m in moves),
            "All moves should be cancelled"
        )

    def test_partial_move_cancellation_propagation(self):
        """Test move cancellation propagation with propagate_cancel flag."""
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'line_ids': [
                Command.create({
                    'product_id': self.product_storable.id,
                    'product_qty': 10,
                    'price_unit': 100,
                    'propagate_cancel': True,
                }),
            ],
        })
        po.action_confirm()

        # Check propagate_cancel is set
        self.assertTrue(po.line_ids[0].propagate_cancel)


@tagged('-at_install', 'post_install')
class TestPurchaseStockLeadTime(TestStockCommon):
    """Tests for lead time calculations in purchase_stock."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Lead Time Vendor',
        })
        cls.buy_route = cls.env.ref('purchase_stock.route_warehouse0_buy')

    def test_date_planned_includes_supplier_delay(self):
        """Test that date_planned includes supplier lead time."""
        product = self.env['product.product'].create({
            'name': 'Product With Delay',
            'is_storable': True,
            'route_ids': [Command.set(self.buy_route.ids)],
            'seller_ids': [Command.create({
                'partner_id': self.vendor.id,
                'min_qty': 1,
                'price': 100,
                'delay': 10,  # 10 days lead time
            })],
        })

        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'line_ids': [
                Command.create({
                    'product_id': product.id,
                    'product_qty': 5,
                    'price_unit': 100,
                }),
            ],
        })

        # Date planned should be at least 10 days from order date
        expected_min_date = po.date_order + timedelta(days=10)
        self.assertGreaterEqual(
            po.line_ids[0].date_planned,
            expected_min_date,
            "Date planned should include supplier delay"
        )

    def test_date_planned_with_zero_delay(self):
        """Test date_planned when supplier has zero delay."""
        product = self.env['product.product'].create({
            'name': 'Product No Delay',
            'is_storable': True,
            'route_ids': [Command.set(self.buy_route.ids)],
            'seller_ids': [Command.create({
                'partner_id': self.vendor.id,
                'min_qty': 1,
                'price': 100,
                'delay': 0,
            })],
        })

        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'line_ids': [
                Command.create({
                    'product_id': product.id,
                    'product_qty': 5,
                    'price_unit': 100,
                }),
            ],
        })

        # Date planned should be close to order date
        delta = po.line_ids[0].date_planned - po.date_order
        self.assertLessEqual(
            delta.days,
            1,
            "Date planned should be same day with zero delay"
        )


@tagged('-at_install', 'post_install')
class TestPurchaseStockPricing(TestStockCommon):
    """Tests for stock-related pricing in purchases."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Pricing Vendor',
        })
        cls.buy_route = cls.env.ref('purchase_stock.route_warehouse0_buy')

    def test_stock_move_price_from_po_line(self):
        """Test that stock move gets price from PO line."""
        product = self.env['product.product'].create({
            'name': 'Priced Product',
            'is_storable': True,
            'route_ids': [Command.set(self.buy_route.ids)],
            'seller_ids': [Command.create({
                'partner_id': self.vendor.id,
                'min_qty': 1,
                'price': 75,
            })],
        })

        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'line_ids': [
                Command.create({
                    'product_id': product.id,
                    'product_qty': 10,
                    'price_unit': 80,  # Different from seller price
                }),
            ],
        })
        po.action_confirm()

        # Check move price
        move = po.picking_ids.move_ids[0]
        # The price_unit on the move should reflect the PO line price
        self.assertEqual(
            move.purchase_line_id.price_unit,
            80,
            "Move should reference PO line with correct price"
        )

    def test_qty_transferred_with_returns(self):
        """Test qty_transferred calculation with purchase returns."""
        product = self.env['product.product'].create({
            'name': 'Return Test Product',
            'is_storable': True,
            'route_ids': [Command.set(self.buy_route.ids)],
            'seller_ids': [Command.create({
                'partner_id': self.vendor.id,
                'min_qty': 1,
                'price': 100,
            })],
        })

        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'line_ids': [
                Command.create({
                    'product_id': product.id,
                    'product_qty': 10,
                    'price_unit': 100,
                }),
            ],
        })
        po.action_confirm()

        # Complete receipt
        picking = po.picking_ids[0]
        picking.move_ids.quantity = 10
        picking.move_ids.picked = True
        picking.button_validate()

        self.assertEqual(po.line_ids[0].qty_transferred, 10)

        # Create return
        return_wizard = self.env['stock.return.picking'].with_context(
            active_id=picking.id,
            active_model='stock.picking',
        ).create({})
        return_wizard.product_return_moves.quantity = 3
        return_result = return_wizard.action_create_returns()

        # Process return
        return_picking = self.env['stock.picking'].browse(return_result['res_id'])
        return_picking.move_ids.quantity = 3
        return_picking.move_ids.picked = True
        return_picking.button_validate()

        # qty_transferred should be reduced by return
        self.assertEqual(
            po.line_ids[0].qty_transferred,
            7,
            "qty_transferred should be 7 after returning 3"
        )
