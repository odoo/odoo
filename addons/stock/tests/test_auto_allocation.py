from datetime import timedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests import Form
from odoo.addons.stock.tests.common import TestStockCommon


class TestAutoAllocation(TestStockCommon):
    _test_user_groups = ('stock.group_stock_manager',)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.picking_type_in.write({
            'auto_show_allocation_report': True,
            'allocation_mode': 'automatic',
        })
        cls.picking_type_out.reservation_method = 'at_confirm'
        cls.product = cls.env['product.product'].create({
            'name': 'Auto Allocated Product',
            'is_storable': True,
        })

    def _create_picking(self, picking_type, qty, confirm=True, **kwargs):
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'move_ids': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': qty,
                **kwargs,
            })],
        })
        if confirm:
            picking.action_confirm()
        return picking

    def test_auto_allocation_at_confirm(self):
        """ Needs reserved at confirmation are allocated as soon as the receipt is confirmed,
        by priority, and only up to the incoming quantity."""
        delivery_1 = self._create_picking(self.picking_type_out, 4)
        delivery_2 = self._create_picking(self.picking_type_out, 4)
        delivery_2.priority = '1'
        self.assertEqual(delivery_1.move_ids.state, 'confirmed')

        receipt = self._create_picking(self.picking_type_in, 6)

        # Starred delivery is fully allocated first, then the remaining 2 units go to the other one (split).
        self.assertEqual(delivery_2.move_ids.move_orig_ids, receipt.move_ids)
        allocated_move_1 = delivery_1.move_ids.filtered('move_orig_ids')
        self.assertRecordValues(allocated_move_1, [{'product_uom_qty': 2, 'move_orig_ids': receipt.move_ids.ids}])
        self.assertRecordValues(delivery_1.move_ids - allocated_move_1, [{'product_uom_qty': 2, 'state': 'confirmed'}])

        # Once received, allocated moves are reserved.
        receipt.button_validate()
        self.assertEqual(delivery_2.move_ids.state, 'assigned')
        self.assertEqual(allocated_move_1.state, 'assigned')

    def test_auto_allocation_manual_reservation(self):
        """ Needs reserved manually are never automatically allocated."""
        self.picking_type_out.reservation_method = 'manual'
        delivery = self._create_picking(self.picking_type_out, 4)
        receipt = self._create_picking(self.picking_type_in, 6)
        self.assertFalse(delivery.move_ids.move_orig_ids)
        self.env['stock.rule'].run_scheduler()
        self.assertFalse(delivery.move_ids.move_orig_ids)
        self.assertFalse(receipt.move_ids.move_dest_ids)

    def test_auto_allocation_by_date(self):
        """ Needs reserved before scheduled date are allocated only when their reservation date is
        reached, by the scheduler."""
        self.picking_type_out.write({
            'reservation_method': 'by_date',
            'reservation_days_before': 2,
        })
        delivery_soon = self._create_picking(self.picking_type_out, 2, confirm=False)
        delivery_soon.scheduled_date = fields.Datetime.now() + timedelta(days=1)
        delivery_late = self._create_picking(self.picking_type_out, 2, confirm=False)
        delivery_late.scheduled_date = fields.Datetime.now() + timedelta(days=10)
        (delivery_soon | delivery_late).action_confirm()

        receipt = self._create_picking(self.picking_type_in, 10)
        self.assertEqual(delivery_soon.move_ids.move_orig_ids, receipt.move_ids)
        self.assertFalse(delivery_late.move_ids.move_orig_ids)

        # Scheduler allocates nothing as long as the reservation date isn't reached.
        self.env['stock.rule'].run_scheduler()
        self.assertFalse(delivery_late.move_ids.move_orig_ids)

        delivery_late.move_ids.reservation_date = fields.Date.today()
        self.env['stock.rule'].run_scheduler()
        self.assertEqual(delivery_late.move_ids.move_orig_ids, receipt.move_ids)

    def test_auto_allocation_by_date_starred(self):
        """ Starring a need uses the "days before when starred" rule: the scheduler allocates it as
        soon as this earlier reservation date is reached."""
        self.picking_type_out.write({
            'reservation_method': 'by_date',
            'reservation_days_before': 2,
            'reservation_days_before_priority': 10,
        })
        delivery = self._create_picking(self.picking_type_out, 2, confirm=False)
        delivery.scheduled_date = fields.Datetime.now() + timedelta(days=5)
        delivery.action_confirm()
        receipt = self._create_picking(self.picking_type_in, 10)

        self.env['stock.rule'].run_scheduler()
        self.assertFalse(delivery.move_ids.move_orig_ids)

        delivery.priority = '1'
        self.assertEqual(delivery.move_ids.reservation_date, fields.Date.today() - timedelta(days=5))
        self.env['stock.rule'].run_scheduler()
        self.assertEqual(delivery.move_ids.move_orig_ids, receipt.move_ids)

    def test_auto_allocation_disabled(self):
        """ No automatic allocation in manual mode or when the allocation isn't shown."""
        delivery = self._create_picking(self.picking_type_out, 4)
        self.picking_type_in.allocation_mode = 'manual'
        self._create_picking(self.picking_type_in, 6)
        self.picking_type_in.write({'allocation_mode': 'automatic', 'auto_show_allocation_report': False})
        self._create_picking(self.picking_type_in, 6)
        self.env['stock.rule'].run_scheduler()
        self.assertFalse(delivery.move_ids.move_orig_ids)

    def test_auto_allocation_partially_reserved(self):
        """ Only the part of the need which isn't already reserved from stock is allocated."""
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 2)
        delivery = self._create_picking(self.picking_type_out, 4)
        self.assertRecordValues(delivery.move_ids, [{'state': 'partially_available', 'quantity': 2}])

        receipt = self._create_picking(self.picking_type_in, 10)

        allocated_move = delivery.move_ids.filtered('move_orig_ids')
        self.assertRecordValues(allocated_move, [{'product_uom_qty': 2, 'move_orig_ids': receipt.move_ids.ids}])
        self.assertRecordValues(delivery.move_ids - allocated_move, [{'product_uom_qty': 2, 'quantity': 2}])
        product_line = self.env['stock.allocation.report']._get_product_lines(receipt)[self.product.id]
        self.assertEqual(product_line['assigned_qty'], 2)
        self.assertEqual(product_line['free_qty'], 8)

    def test_auto_allocation_backorder(self):
        """ Creating a backorder at validation mustn't trigger an allocation which would change
        the received quantity."""
        receipt = self._create_picking(self.picking_type_in, 10)
        # The need appears after the receipt confirmation: nothing is allocated yet.
        self._create_picking(self.picking_type_out, 4)
        self.assertFalse(receipt.move_ids.move_dest_ids)

        receipt.move_ids.write({'quantity': 6, 'picked': True})
        Form.from_action(self.env, receipt.button_validate()).save().process()

        self.assertRecordValues(receipt.move_ids, [{'state': 'done', 'quantity': 6}])
        self.assertRecordValues(receipt.backorder_ids.move_ids, [{'product_uom_qty': 4}])
        self.assertEqual(self.product.qty_available, 6)

    def test_auto_allocation_allocated_location(self):
        """ When a location for allocation is set, the allocated quantity is split from the
        receipt move and sent to that location."""
        allocation_location = self.env['stock.location'].create({
            'name': 'Allocation',
            'location_id': self.stock_location.id,
        })
        self.picking_type_in.allocated_location_id = allocation_location
        delivery = self._create_picking(self.picking_type_out, 4)
        receipt = self._create_picking(self.picking_type_in, 10)

        allocated_move = receipt.move_ids.filtered('move_dest_ids')
        self.assertRecordValues(allocated_move, [{
            'product_uom_qty': 4,
            'location_dest_id': allocation_location.id,
            'move_dest_ids': delivery.move_ids.ids,
        }])
        self.assertRecordValues(receipt.move_ids - allocated_move, [{
            'product_uom_qty': 6,
            'location_dest_id': self.stock_location.id,
            'move_dest_ids': [],
        }])

    def test_auto_allocation_allocated_location_several_needs(self):
        """ A receipt which already goes to the location for allocation (e.g. duplicated from an
        allocated receipt) can be allocated to several needs: only the allocated quantity goes there."""
        allocation_location = self.env['stock.location'].create({
            'name': 'Allocation',
            'location_id': self.stock_location.id,
        })
        self.picking_type_in.allocated_location_id = allocation_location
        deliveries = self._create_picking(self.picking_type_out, 4) | self._create_picking(self.picking_type_out, 4)
        receipt = self._create_picking(self.picking_type_in, 10, confirm=False)
        receipt.move_ids.location_dest_id = allocation_location
        receipt.action_confirm()

        allocated_move = receipt.move_ids.filtered('move_dest_ids')
        self.assertRecordValues(allocated_move, [{
            'product_uom_qty': 8,
            'location_dest_id': allocation_location.id,
            'move_dest_ids': deliveries.move_ids.ids,
        }])
        self.assertRecordValues(receipt.move_ids - allocated_move, [{
            'product_uom_qty': 2,
            'location_dest_id': self.stock_location.id,
        }])

    def test_auto_allocation_cancel_receipt(self):
        """ Cancelling a receipt doesn't cancel the moves allocated to it: they're only unallocated
        and can be allocated to another receipt."""
        delivery = self._create_picking(self.picking_type_out, 4)
        receipt = self._create_picking(self.picking_type_in, 10)
        self.assertEqual(delivery.move_ids.move_orig_ids, receipt.move_ids)

        receipt.action_cancel()
        self.assertRecordValues(delivery.move_ids, [{
            'state': 'confirmed',
            'move_orig_ids': [],
            'procure_method': 'make_to_stock',
            'is_allocated': False,
        }])

        other_receipt = self._create_picking(self.picking_type_in, 10)
        self.assertEqual(delivery.move_ids.move_orig_ids, other_receipt.move_ids)

    def test_auto_allocation_partial_reception(self):
        """ When less is received than allocated, the allocated moves only keep what was received
        (by priority): the rest is unallocated, then allocated again to the backorder."""
        # The starred delivery is created last: the received quantity is still given to it first.
        delivery_2 = self._create_picking(self.picking_type_out, 6)
        delivery_1 = self._create_picking(self.picking_type_out, 4)
        delivery_1.priority = '1'
        receipt = self._create_picking(self.picking_type_in, 10)
        self.assertEqual((delivery_1 | delivery_2).move_ids.move_orig_ids, receipt.move_ids)

        receipt.move_ids.quantity = 6
        # Before validation, the report shows what the received quantity will cover.
        product_line = self.env['stock.allocation.report']._get_product_lines(receipt)[self.product.id]
        covered_qty_by_move = {need['id']: need['covered_quantity'] for need in product_line['needs']}
        self.assertEqual(covered_qty_by_move, {delivery_1.move_ids.id: 4, delivery_2.move_ids.id: 2})

        Form.from_action(self.env, receipt.button_validate()).save().process()

        backorder = receipt.backorder_ids
        self.assertRecordValues(delivery_1.move_ids, [
            {'product_uom_qty': 4, 'quantity': 4, 'state': 'assigned', 'move_orig_ids': receipt.move_ids.ids},
        ])
        self.assertRecordValues(delivery_2.move_ids, [
            {'product_uom_qty': 2, 'quantity': 2, 'state': 'assigned', 'move_orig_ids': receipt.move_ids.ids, 'is_allocated': True},
            {'product_uom_qty': 4, 'quantity': 0, 'state': 'waiting', 'move_orig_ids': backorder.move_ids.ids, 'is_allocated': True},
        ])

    def test_auto_allocation_partial_reception_manual(self):
        """ In manual mode, the part of the allocated moves which wasn't received isn't allocated to
        the backorder: it doesn't wait for anything and can be reserved from stock."""
        self.picking_type_in.allocation_mode = 'manual'
        delivery = self._create_picking(self.picking_type_out, 6)
        receipt = self._create_picking(self.picking_type_in, 10)
        self.env['stock.allocation.report'].action_assign(receipt.move_ids.ids, delivery.move_ids.ids, 6)
        self.assertEqual(delivery.move_ids.move_orig_ids, receipt.move_ids)

        receipt.move_ids.quantity = 2
        Form.from_action(self.env, receipt.button_validate()).save().process()

        self.assertFalse(receipt.backorder_ids.move_ids.move_dest_ids)
        self.assertRecordValues(delivery.move_ids, [
            {'product_uom_qty': 2, 'quantity': 2, 'procure_method': 'make_to_order', 'move_orig_ids': receipt.move_ids.ids, 'is_allocated': True},
            {'product_uom_qty': 4, 'quantity': 0, 'procure_method': 'make_to_stock', 'move_orig_ids': [], 'is_allocated': False},
        ])
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 4)
        delivery.action_assign()
        self.assertEqual(delivery.state, 'assigned')
