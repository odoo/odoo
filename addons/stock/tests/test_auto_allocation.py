from datetime import timedelta

from odoo import fields
from odoo.fields import Command
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

    def test_auto_allocation_disabled(self):
        """ No automatic allocation in manual mode or when the allocation isn't shown."""
        delivery = self._create_picking(self.picking_type_out, 4)
        self.picking_type_in.allocation_mode = 'manual'
        self._create_picking(self.picking_type_in, 6)
        self.picking_type_in.write({'allocation_mode': 'automatic', 'auto_show_allocation_report': False})
        self._create_picking(self.picking_type_in, 6)
        self.env['stock.rule'].run_scheduler()
        self.assertFalse(delivery.move_ids.move_orig_ids)

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
