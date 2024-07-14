# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo.fields import Datetime
from odoo.tests import Form
from odoo.addons.sale_stock_renting.tests.test_rental_common import TestRentalCommon


class TestRentalKits(TestRentalCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['res.config.settings'].create({'group_rental_stock_picking': True}).execute()

        cls.component_1 = cls.env['product.product'].create({'name': 'compo 1', 'type': 'product'})
        cls.component_2 = cls.env['product.product'].create({'name': 'compo 2', 'type': 'product'})
        cls.bom = cls.env['mrp.bom'].create({
            'product_id': cls.product_id.id,
            'product_tmpl_id': cls.product_id.product_tmpl_id.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.component_1.id, 'product_qty': 1}),
                (0, 0, {'product_id': cls.component_2.id, 'product_qty': 2})
            ]
        })

        quants = cls.env['stock.quant'].create({
            'product_id': cls.component_1.id,
            'inventory_quantity': 5.0,
            'location_id': cls.warehouse_id.lot_stock_id.id
        })
        quants |= cls.env['stock.quant'].create({
            'product_id': cls.component_2.id,
            'inventory_quantity': 10.0,
            'location_id': cls.warehouse_id.lot_stock_id.id
        })
        quants.action_apply_inventory()

    def test_flow_1(self):
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 3, 'is_rental': True})
        rental_order_1.rental_start_date = self.rental_start_date
        rental_order_1.rental_return_date = self.rental_return_date
        rental_order_1.action_confirm()
        self.assertEqual([d.date() for d in rental_order_1.picking_ids.mapped('scheduled_date')],
                         [rental_order_1.rental_start_date.date(), rental_order_1.rental_return_date.date()])
        self.assertEqual(len(rental_order_1.picking_ids), 2)
        self.assertEqual(len(rental_order_1.picking_ids.move_ids), 4)

        outgoing_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'waiting')
        self.assertEqual(outgoing_picking.move_ids.mapped('product_uom_qty'), [3.0, 6.0])
        self.assertEqual(incoming_picking.move_ids.mapped('product_uom_qty'), [3.0, 6.0])

        rental_order_1.order_line.write({'product_uom_qty': 4})
        self.assertEqual(outgoing_picking.move_ids.mapped('product_uom_qty'), [4.0, 8.0])
        self.assertEqual(incoming_picking.move_ids.mapped('product_uom_qty'), [4.0, 8.0])

        rental_order_1.order_line.write({'product_uom_qty': 2})
        self.assertEqual(outgoing_picking.move_ids.mapped('product_uom_qty'), [2.0, 4.0])
        self.assertEqual(incoming_picking.move_ids.mapped('product_uom_qty'), [2.0, 4.0])

        outgoing_picking.move_ids[0].quantity = 1
        outgoing_picking.move_ids[1].quantity = 2
        backorder_wizard_dict = outgoing_picking.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 1)

        outgoing_picking_2 = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned' and p.picking_type_code == 'outgoing')
        self.assertEqual(outgoing_picking_2.move_ids.mapped('product_uom_qty'), [1.0, 2.0])
        rental_order_1.order_line.write({'product_uom_qty': 3})
        self.assertEqual(outgoing_picking_2.move_ids.mapped('product_uom_qty'), [2.0, 4.0])
        self.assertEqual(incoming_picking.move_ids.mapped('product_uom_qty'), [3.0, 6.0])
        self.assertEqual(incoming_picking.move_ids.mapped('quantity'), [1.0, 2.0])

        outgoing_picking_2.move_ids[0].quantity = 1
        outgoing_picking_2.move_ids[1].quantity = 2
        backorder_wizard_dict = outgoing_picking_2.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 2)

        incoming_picking.move_ids[0].quantity = 1
        incoming_picking.move_ids[1].quantity = 2
        backorder_wizard_dict = incoming_picking.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()
        self.assertEqual(rental_order_1.order_line.qty_returned, 1)

        outgoing_picking_3 = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned' and p.picking_type_code == 'outgoing')
        incoming_picking_2 = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned' and p.picking_type_code == 'incoming')
        self.assertEqual(incoming_picking_2.move_ids.mapped('product_uom_qty'), [2.0, 4.0])

        outgoing_picking_3.button_validate()
        incoming_picking_2.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_returned, 3)

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
        incoming_picking.move_ids[0].picked = True
        backorder_wizard_dict = incoming_picking.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()
        self.assertEqual(rental_order_1.order_line.qty_returned, 0)
        self.assertEqual(len(rental_order_1.order_line), 1)

        incoming_picking_2 = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(incoming_picking_2.scheduled_date.date(), rental_order_1.rental_return_date.date())
        incoming_picking_2.move_ids[0].quantity = 2
        incoming_picking_2.button_validate()

        self.assertEqual(len(rental_order_1.order_line), 2)
        late_fee_order_line = rental_order_1.order_line.filtered(lambda l: l.product_id.type == 'service')
        self.assertEqual(late_fee_order_line.price_unit, 30)

    def test_subkits_and_same_component(self):
        """
        - Kit
            - 1 x C1
                - 1 x C2
                - 1 x C3
            - 2X C2

        Rental with delivery
        Ensure that qties of both delivery and return are correct
        """
        stock_location = self.warehouse_id.lot_stock_id
        rental_location = self.env.company.rental_loc_id

        component_3 = self.env['product.product'].create({
            'name': 'compo 3',
            'type': 'consu',
        })

        sub_bom = self.env['mrp.bom'].create({
            'product_id': self.component_1.id,
            'product_tmpl_id': self.component_1.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': self.component_2.id, 'product_qty': 1}),
                (0, 0, {'product_id': component_3.id, 'product_qty': 1})
            ]
        })
        _bom_line_01, bom_line_02 = self.bom.bom_line_ids
        bom_line_03, bom_line_04 = sub_bom.bom_line_ids

        rental = self.sale_order_id.copy()
        rental.order_line.write({'product_uom_qty': 1, 'is_rental': True})
        rental.rental_start_date = Datetime.now() - timedelta(days=7)
        rental.rental_return_date = Datetime.now() - timedelta(days=3)
        rental.action_confirm()

        self.assertRecordValues(rental.picking_ids.move_ids, [
            {'product_id': self.component_2.id, 'product_qty': 2, 'bom_line_id': bom_line_02.id, 'location_id': stock_location.id},
            {'product_id': self.component_2.id, 'product_qty': 1, 'bom_line_id': bom_line_03.id, 'location_id': stock_location.id},
            {'product_id': component_3.id, 'product_qty': 1, 'bom_line_id': bom_line_04.id, 'location_id': stock_location.id},
            {'product_id': self.component_2.id, 'product_qty': 2, 'bom_line_id': bom_line_02.id, 'location_id': rental_location.id},
            {'product_id': self.component_2.id, 'product_qty': 1, 'bom_line_id': bom_line_03.id, 'location_id': rental_location.id},
            {'product_id': component_3.id, 'product_qty': 1, 'bom_line_id': bom_line_04.id, 'location_id': rental_location.id},
        ])
