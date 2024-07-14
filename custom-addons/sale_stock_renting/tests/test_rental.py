# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo.fields import Datetime
from odoo.tests import Form
from odoo.addons.sale_stock_renting.tests.test_rental_common import TestRentalCommon


class TestRentalWizard(TestRentalCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_rental_product_flow(self):

        self.assertEqual(
            self.product_id.qty_available,
            4
        )

        self.order_line_id1.write({
            'product_uom_qty': 3
        })

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin,
                self.order_line_id1.return_date,
                # self.order_line_id1.id,
            ), 3
        )

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin - timedelta(days=1),
                self.order_line_id1.return_date,
            ), 3
        )

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin,
                self.order_line_id1.return_date - timedelta(days=1),
            ), 3
        )

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin - timedelta(days=1),
                self.order_line_id1.return_date - timedelta(days=1),
            ), 3
        )

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin + timedelta(days=1),
                self.order_line_id1.return_date + timedelta(days=1),
            ), 3
        )

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin,
                self.order_line_id1.return_date + timedelta(days=1),
            ), 3
        )

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin + timedelta(days=1),
                self.order_line_id1.return_date,
            ), 3
        )

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin - timedelta(days=1),
                self.order_line_id1.return_date + timedelta(days=1),
            ), 3
        )

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin + timedelta(days=1),
                self.order_line_id1.return_date - timedelta(days=1),
            ), 3
        )

        """
            Total Pickup
        """

        self.order_line_id1.write({
            'qty_delivered': 3
        })

        """ In sale order warehouse """
        self.assertEqual(
            self.product_id.with_context(
                warehouse=self.order_line_id1.order_id.warehouse_id.id,
                from_date=self.order_line_id1.reservation_begin,
                to_date=self.order_line_id1.return_date,
            ).qty_available,
            1
        )

        self.env.invalidate_all()
        """ In company internal rental location (in stock valuation but not in available qty) """
        self.assertEqual(
            self.product_id.with_context(
                location=self.env.company.rental_loc_id.id,
                from_date=self.order_line_id1.start_date,
                to_date=self.order_line_id1.return_date,
            ).qty_available,
            3
        )

        """ In company warehouses """
        self.assertEqual(
            self.product_id.qty_available,
            1
        )

        """ In company stock valuation """
        self.assertEqual(
            self.product_id.quantity_svl,
            4
        )

        ####################################
        # Cancel deliver then re-apply
        ####################################

        self.order_line_id1.write({'qty_delivered': 0})
        self.assertEqual(self.product_id.qty_available, 4)
        self.order_line_id1.write({'qty_delivered': 3})

        """
            Partial Return
        """

        self.order_line_id1.write({
            'qty_returned': 2
        })

        """ In sale order warehouse """
        self.assertEqual(
            self.product_id.with_context(
                warehouse=self.order_line_id1.order_id.warehouse_id.id
            ).qty_available,
            3
        )

        """ In company internal rental location (in stock valuation but not in available qty) """
        self.assertEqual(
            self.product_id.with_context(
                location=self.env.company.rental_loc_id.id,
                from_date=self.order_line_id1.start_date,
                to_date=self.order_line_id1.return_date,
            ).qty_available,
            1
        )

        """ In company warehouses """
        self.assertEqual(
            self.product_id.qty_available,
            3
        )

        """ In company stock valuation """
        self.assertEqual(
            self.product_id.quantity_svl,
            4
        )

        """
            Total Return
        """

        self.order_line_id1.write({
            'qty_returned': 3
        })

        self.assertEqual(
            self.product_id.qty_available,
            4.0
        )

    def test_rental_lot_flow(self):
        self.lots_rental_order.action_confirm()

        lots = self.env['stock.lot'].search([('product_id', '=', self.tracked_product_id.id)])
        rentable_lots = self.env['stock.lot']._get_available_lots(self.tracked_product_id)
        self.assertEqual(set(lots.ids), set(rentable_lots.ids))  # set is here to ensure that order wont break test

        self.order_line_id2.reserved_lot_ids += self.lot_id1
        self.order_line_id2.product_uom_qty = 1.0

        self.order_line_id2.pickedup_lot_ids += self.lot_id2

        # Ensure lots are unreserved if other lots are picked up in their place
        # and qty pickedup = product_uom_qty (qty reserved)
        self.assertEqual(self.order_line_id2.reserved_lot_ids, self.order_line_id2.pickedup_lot_ids)

        return

    def test_rental_lot_concurrent(self):
        """The purpose of this test is to mimmic a concurrent picking of a rental product.
        As the same lot is applied to the sol twice, its qty_delivered should be 1.
        """
        so = self.lots_rental_order
        sol = self.order_line_id2
        lot = self.lot_id2

        sol.product_uom_qty = 1.0
        so.action_confirm()

        wizard_vals = so.action_open_pickup()
        for _i in range(2):
            wizard = self.env[wizard_vals['res_model']].with_context(wizard_vals['context']).create({
                'rental_wizard_line_ids': [
                    (0, 0, {
                        'order_line_id': sol.id,
                        'product_id': sol.product_id.id,
                        'qty_delivered': 1.0,
                        'pickedup_lot_ids':[[6, False, [lot.id]]],
                    })
                ]
            })
            wizard.apply()

        self.assertEqual(sol.qty_delivered, len(sol.pickedup_lot_ids), "The quantity delivered should not exceed the number of picked up lots")

        for _i in range(2):
            wizard = self.env[wizard_vals['res_model']].with_context(wizard_vals['context']).create({
                'rental_wizard_line_ids': [
                    (0, 0, {
                        'order_line_id': sol.id,
                        'product_id': sol.product_id.id,
                        'qty_returned': 1.0,
                        'returned_lot_ids':[[6, False, [lot.id]]],
                    })
                ]
            })
            wizard.apply()

        self.assertEqual(sol.qty_returned, len(sol.returned_lot_ids), "The quantity returned should not exceed the number of returned lots")

    def test_schedule_report(self):
        """Verify sql scheduling view consistency.

        One sale.order.line with 3 different lots (reserved/pickedup/returned)
        is represented by 3 sale.rental.schedule to allow grouping reservation information
        by stock.lot .

        Note that a lot can be pickedup (sol.pickedup_lot_ids) even if not reserved (sol.reserved_lot_ids).
        """
        self.order_line_id2.reserved_lot_ids = self.lot_id1
        # Avoid magic setting pickedup lots as reserved when full quantity has been pickedup
        self.order_line_id2.product_uom_qty = 2.0

        # Lot pickedup but not reserved.
        self.order_line_id2.pickedup_lot_ids = self.lot_id2

        self.assertEqual(
            self.env["sale.rental.schedule"].search_count([('lot_id', '=', self.lot_id2.id)]),
            1,
        )
        scheduling_recs = self.env["sale.rental.schedule"].search([
            ('order_line_id', '=', self.order_line_id2.id),
        ])
        self.assertEqual(
            len(scheduling_recs),
            2, # 1 reserved, 1 pickedup
        )
        self.assertEqual(
            scheduling_recs.mapped('report_line_status'),
            ["reserved", "pickedup"],
        )

        # More generic behavior:
        # 2 reserved, 2 pickedup, 1 returned
        self.order_line_id2.returned_lot_ids = self.lot_id2
        self.order_line_id2.pickedup_lot_ids += self.lot_id1
        self.env.invalidate_all()
        scheduling_recs = self.env["sale.rental.schedule"].search([
            ('order_line_id', '=', self.order_line_id2.id)
        ])
        self.assertEqual(
            len(scheduling_recs),
            2,
        )
        self.assertEqual(
            scheduling_recs.lot_id,
            self.lot_id1 + self.lot_id2,
        )
        self.assertEqual(
            scheduling_recs.mapped('report_line_status'),
            ["pickedup", "returned"],
        )

    def test_lot_accuracy_in_schedule(self):
        """ Schedule should only display lots that are associated with
        rental order lines
        """
        rental_schedule = self.env['sale.rental.schedule']
        rental_transfers_group = self.env.ref('sale_stock_renting.group_rental_stock_picking')
        self.env.user.groups_id = [(4, rental_transfers_group.id)]
        so = self.lots_rental_order
        self.order_line_id2.product_uom_qty = 1.0
        so.order_line = [(6, 0, [self.order_line_id2.id])]
        so.action_confirm()

        # Rental schedule should have 1 out of the 3 total lots for `self.tracked_product_id`
        self.assertEqual(
            rental_schedule.search_count([('product_id', '=', self.tracked_product_id.id)]),
            1
        )

class TestRentalPicking(TestRentalCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['res.config.settings'].create({'group_rental_stock_picking': True}).execute()

    def test_flow_1(self):
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 3, 'is_rental': True})
        rental_order_1.rental_start_date = self.rental_start_date
        rental_order_1.rental_return_date = self.rental_return_date
        rental_order_1.action_confirm()
        self.assertEqual(len(rental_order_1.picking_ids), 2)
        self.assertEqual([d.date() for d in rental_order_1.picking_ids.mapped('scheduled_date')],
                         [rental_order_1.rental_start_date.date(), rental_order_1.rental_return_date.date()])
        self.assertEqual(rental_order_1.picking_ids.move_ids.mapped('product_uom_qty'), [3.0, 3.0])

        outgoing_picking = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming')

        outgoing_picking.move_ids.quantity = 2
        backorder_wizard_dict = outgoing_picking.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 2)
        self.assertEqual(rental_order_1.rental_status, 'pickup')
        self.assertEqual(len(rental_order_1.picking_ids), 3)
        self.assertEqual(incoming_picking.move_ids.quantity, 2)

        incoming_picking.move_ids.quantity = 1
        backorder_wizard_dict = incoming_picking.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()
        self.assertEqual(rental_order_1.order_line.qty_returned, 1)
        self.assertEqual(rental_order_1.rental_status, 'pickup')
        self.assertEqual(len(rental_order_1.picking_ids), 4)

        outgoing_picking_2 = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing' and p.state == 'assigned')
        incoming_picking_2 = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming' and p.state == 'assigned')
        self.assertEqual(outgoing_picking_2.scheduled_date.date(), rental_order_1.rental_start_date.date())
        self.assertEqual(incoming_picking_2.scheduled_date.date(), rental_order_1.rental_return_date.date())
        self.assertEqual(outgoing_picking_2.move_ids.quantity, 1)
        self.assertEqual(incoming_picking_2.move_ids.quantity, 1)

        rental_order_1.order_line.write({'product_uom_qty': 5})
        self.assertEqual(outgoing_picking_2.move_ids.product_uom_qty, 3)
        self.assertEqual(incoming_picking_2.move_ids.product_uom_qty, 4)

        outgoing_picking_2.move_ids.quantity = 1
        backorder_wizard_dict = outgoing_picking_2.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 3)
        self.assertEqual(rental_order_1.rental_status, 'pickup')
        self.assertEqual(len(rental_order_1.picking_ids), 5)
        self.assertEqual(incoming_picking_2.move_ids.quantity, 2)

        rental_order_1.order_line.write({'product_uom_qty': 4})
        outgoing_picking_3 = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing' and p.state == 'assigned')
        self.assertEqual(outgoing_picking_3.scheduled_date.date(), rental_order_1.rental_start_date.date())
        self.assertEqual(outgoing_picking_3.move_ids.product_uom_qty, 1)
        self.assertEqual(incoming_picking_2.move_ids.product_uom_qty, 3)

        outgoing_picking_3.button_validate()
        self.assertEqual(incoming_picking_2.move_ids.quantity, 3)
        self.assertEqual(rental_order_1.order_line.qty_delivered, 4)
        self.assertEqual(rental_order_1.rental_status, 'return')

        incoming_picking_2.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_returned, 4)
        self.assertEqual(rental_order_1.rental_status, 'returned')

    def test_flow_multisteps(self):
        self.warehouse_id.delivery_steps = 'pick_pack_ship'
        self.warehouse_id.reception_steps = 'three_steps'

        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 3, 'is_rental': True})
        rental_order_1.rental_start_date = self.rental_start_date
        rental_order_1.rental_return_date = self.rental_return_date
        rental_order_1.action_confirm()
        self.assertEqual(len(rental_order_1.picking_ids), 6)
        self.assertEqual([d.date() for d in rental_order_1.picking_ids.mapped('scheduled_date')],
                         [rental_order_1.rental_start_date.date(), rental_order_1.rental_start_date.date(), rental_order_1.rental_start_date.date(),
                          rental_order_1.rental_return_date.date(), rental_order_1.rental_return_date.date(), rental_order_1.rental_return_date.date()])
        self.assertEqual(rental_order_1.picking_ids.move_ids.mapped('product_uom_qty'), [3.0, 3.0, 3.0, 3.0, 3.0, 3.0])

        rental_order_1.order_line.write({'product_uom_qty': 4})
        self.assertEqual(len(rental_order_1.picking_ids), 6)
        self.assertEqual(rental_order_1.picking_ids.move_ids.mapped('product_uom_qty'), [4.0, 4.0, 4.0, 4.0, 4.0, 4.0])

        pick_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(pick_picking.location_dest_id, self.warehouse_id.wh_pack_stock_loc_id)
        pick_picking.button_validate()
        rental_order_1.order_line.write({'product_uom_qty': 1})
        self.assertEqual(len(rental_order_1.picking_ids), 7)

        return_pick_picking = rental_order_1.picking_ids.filtered(lambda p: p.location_id == self.warehouse_id.wh_pack_stock_loc_id and p.location_dest_id == self.warehouse_id.lot_stock_id)
        all_other_pickings = rental_order_1.picking_ids.filtered(lambda p: p.state != 'done' and p.id != return_pick_picking.id)
        self.assertEqual(return_pick_picking.move_ids.product_uom_qty, 3.0)
        self.assertEqual(return_pick_picking.state, 'waiting')
        self.assertEqual(all_other_pickings.move_ids.mapped('product_uom_qty'), [1.0, 1.0, 1.0, 1.0, 1.0])
        return_pick_picking.action_assign()
        return_pick_picking.button_validate()

        pack_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(pack_picking.location_dest_id, self.warehouse_id.wh_output_stock_loc_id)
        pack_picking.button_validate()

        out_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(out_picking.location_dest_id, self.env.company.rental_loc_id)
        out_picking.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 1)

        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(incoming_picking.location_dest_id, self.warehouse_id.wh_input_stock_loc_id)
        incoming_picking.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_returned, 1)

        qc_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(qc_picking.location_dest_id, self.warehouse_id.wh_qc_stock_loc_id)
        qc_picking.button_validate()

        final_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(final_picking.location_dest_id, self.warehouse_id.lot_stock_id)
        final_picking.button_validate()

    def test_flow_serial(self):
        empty_lot = self.env['stock.lot'].create({
            'product_id': self.tracked_product_id.id,
            'name': "Dofus Ocre",
            'company_id': self.env.company.id,
        })
        available_lot = self.env['stock.lot'].create({
            'product_id': self.tracked_product_id.id,
            'name': "Dofawa",
            'company_id': self.env.company.id,
        })
        available_quant = self.env['stock.quant'].create({
            'product_id': self.tracked_product_id.id,
            'inventory_quantity': 1.0,
            'lot_id': available_lot.id,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id
        })
        reserved_lot = self.env['stock.lot'].create({
            'product_id': self.tracked_product_id.id,
            'name': "Dolmanax",
            'company_id': self.env.company.id,
        })
        reserved_quant = self.env['stock.quant'].create({
            'product_id': self.tracked_product_id.id,
            'inventory_quantity': 1.0,
            'lot_id': reserved_lot.id,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id
        })
        (available_quant + reserved_quant).action_apply_inventory()

        # Reserve 1 serial
        reserved_rental = self.sale_order_id.copy()
        reserved_rental.order_line.write({'product_id': self.tracked_product_id.id, 'reserved_lot_ids': reserved_lot, 'product_uom_qty': 1})
        reserved_rental.order_line.is_rental = True
        reserved_rental.rental_start_date = self.rental_start_date
        reserved_rental.rental_return_date = self.rental_return_date
        reserved_rental.action_confirm()

        # Test with 3 serials: 1 available, 1 reserved and 1 empty
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_id': self.tracked_product_id.id, 'reserved_lot_ids': available_lot + reserved_lot + empty_lot, 'product_uom_qty': 3})
        rental_order_1.order_line.is_rental = True
        rental_order_1.rental_start_date = self.rental_start_date
        rental_order_1.rental_return_date = self.rental_return_date
        rental_order_1.action_confirm()
        self.assertEqual(len(rental_order_1.picking_ids), 2)

        outgoing_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(len(outgoing_picking.move_ids.move_line_ids), 3)
        self.assertEqual(outgoing_picking.move_ids.move_line_ids.lot_id, self.lot_id2 + self.lot_id3 + available_lot)

        outgoing_picking.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 3)
        self.assertEqual(available_lot.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.env.company.rental_loc_id)
        self.assertEqual(self.lot_id2.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.env.company.rental_loc_id)
        self.assertEqual(self.lot_id3.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.env.company.rental_loc_id)

        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(len(incoming_picking.move_ids.move_line_ids), 3)
        self.assertEqual(incoming_picking.move_ids.move_line_ids.lot_id, self.lot_id2 + self.lot_id3 + available_lot)

        incoming_picking.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_returned, 3)
        self.assertEqual(available_lot.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.warehouse_id.lot_stock_id)
        self.assertEqual(self.lot_id2.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.warehouse_id.lot_stock_id)
        self.assertEqual(self.lot_id3.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.warehouse_id.lot_stock_id)

    def test_late_fee(self):
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 1, 'is_rental': True})
        rental_order_1.rental_start_date = Datetime.now() - timedelta(days=7)
        rental_order_1.rental_return_date = Datetime.now() - timedelta(days=3)
        rental_order_1.action_confirm()

        outgoing_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(outgoing_picking.scheduled_date.date(), rental_order_1.rental_start_date.date())
        outgoing_picking.button_validate()

        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(incoming_picking.scheduled_date.date(), rental_order_1.rental_return_date.date())
        incoming_picking.button_validate()

        self.assertEqual(len(rental_order_1.order_line), 2)
        late_fee_order_line = rental_order_1.order_line.filtered(lambda l: l.product_id.type == 'service')
        self.assertEqual(late_fee_order_line.price_unit, 30)

    def test_buttons(self):
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 3, 'is_rental': True})
        rental_order_1.action_confirm()

        action_open_pickup = rental_order_1.action_open_pickup()
        action_open_return = rental_order_1.action_open_return()
        self.assertEqual(action_open_pickup.get('res_id'), rental_order_1.picking_ids[0].id)
        self.assertEqual(action_open_pickup.get('domain'), '')
        self.assertEqual(action_open_pickup.get('xml_id'), 'stock.action_picking_tree_all')
        self.assertEqual(action_open_return.get('res_id'), 0)
        self.assertEqual(action_open_return.get('domain'), [('id', 'in', rental_order_1.picking_ids.ids)])
        self.assertEqual(action_open_return.get('xml_id'), 'stock.action_picking_tree_all')

        ready_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        ready_picking.button_validate()
        self.assertEqual(rental_order_1.rental_status, 'return')

        action_open_return_2 = rental_order_1.action_open_return()
        self.assertEqual(action_open_return_2.get('res_id'), rental_order_1.picking_ids[1].id)
        self.assertEqual(action_open_return_2.get('domain'), '')
        self.assertEqual(action_open_return_2.get('xml_id'), 'stock.action_picking_tree_all')
