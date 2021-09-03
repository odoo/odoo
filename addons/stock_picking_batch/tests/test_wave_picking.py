# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestBatchPicking(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """ Create 3 standard pickings and reserve them to have some move lines.
        The setup data looks like this:
        Picking1                Picking2                Picking3
            ProductA                ProductA                ProductB
                Lot1: 5 units           Lot4: 5 units           SN6 : 1 unit
                Lot2: 5 units                                   SN7 : 1 unit
                Lot3: 5 units                                   SN8 : 1 unit
            ProductB                                            SN9 : 1 unit
                SN1 : 1 unit                                    SN10: 1 unit
                SN2 : 1 unit
                SN3 : 1 unit
                SN4 : 1 unit
                SN5 : 1 unit
        """
        super().setUpClass()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.picking_type_out = cls.env['ir.model.data']._xmlid_to_res_id('stock.picking_type_out')
        cls.user_demo = cls.env['res.users'].search([('login', '=', 'demo')])

        cls.productA = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'tracking': 'lot',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.lots_p_a = cls.env['stock.production.lot'].create([{
            'name': 'lot_product_a_' + str(i + 1),
            'product_id': cls.productA.id,
            'company_id': cls.env.company.id,
        } for i in range(4)])
        cls.productB = cls.env['product.product'].create({
            'name': 'Product B',
            'type': 'product',
            'tracking': 'serial',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.lots_p_b = cls.env['stock.production.lot'].create([{
            'name': 'lot_product_a_' + str(i + 1),
            'product_id': cls.productB.id,
            'company_id': cls.env.company.id,
        } for i in range(10)])

        Quant = cls.env['stock.quant']
        for lot in cls.lots_p_a:
            Quant._update_available_quantity(cls.productA, cls.stock_location, 5.0, lot_id=lot)
        for lot in cls.lots_p_b:
            Quant._update_available_quantity(cls.productB, cls.stock_location, 1.0, lot_id=lot)

        cls.picking_client_1 = cls.env['stock.picking'].create({
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
            'picking_type_id': cls.picking_type_out,
            'company_id': cls.env.company.id,
        })

        cls.env['stock.move'].create({
            'name': cls.productA.name,
            'product_id': cls.productA.id,
            'product_uom_qty': 15,
            'product_uom': cls.productA.uom_id.id,
            'picking_id': cls.picking_client_1.id,
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
        })

        cls.env['stock.move'].create({
            'name': cls.productB.name,
            'product_id': cls.productB.id,
            'product_uom_qty': 5,
            'product_uom': cls.productB.uom_id.id,
            'picking_id': cls.picking_client_1.id,
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
        })

        cls.picking_client_2 = cls.env['stock.picking'].create({
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
            'picking_type_id': cls.picking_type_out,
            'company_id': cls.env.company.id,
        })

        cls.env['stock.move'].create({
            'name': cls.productA.name,
            'product_id': cls.productA.id,
            'product_uom_qty': 5,
            'product_uom': cls.productA.uom_id.id,
            'picking_id': cls.picking_client_2.id,
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
        })

        cls.picking_client_3 = cls.env['stock.picking'].create({
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
            'picking_type_id': cls.picking_type_out,
            'company_id': cls.env.company.id,
        })

        cls.env['stock.move'].create({
            'name': cls.productB.name,
            'product_id': cls.productB.id,
            'product_uom_qty': 5,
            'product_uom': cls.productB.uom_id.id,
            'picking_id': cls.picking_client_3.id,
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
        })
        cls.all_pickings = cls.picking_client_1 | cls.picking_client_2 | cls.picking_client_3
        cls.all_pickings.action_confirm()

    def test_creation_from_lines(self):
        """ Select all the move_lines and create a wave from them """
        all_lines = self.all_pickings.move_line_ids
        res_dict = all_lines.action_open_add_to_wave()
        res_dict['context'] = {'active_model': 'stock.move.line', 'active_ids': all_lines.ids}
        self.assertEqual(res_dict.get('res_model'), 'stock.add.to.wave')
        wizard_form = Form(self.env[res_dict['res_model']].with_context(res_dict['context']))
        wizard_form.mode = 'new'
        wizard_form.user_id = self.user_demo
        wizard_form.save().attach_pickings()

        wave = self.env['stock.picking.batch'].search([
            ('is_wave', '=', True)
        ])
        self.assertTrue(wave)
        self.assertEqual(wave.picking_ids, self.all_pickings)
        self.assertEqual(wave.move_line_ids, all_lines)
        self.assertEqual(wave.user_id, self.user_demo)

    def test_creation_from_pickings(self):
        """ Select all the picking_ids and create a wave from them """
        action = self.env['ir.actions.actions']._for_xml_id('stock_picking_batch.stock_add_to_wave_action_stock_picking')
        action['context'] = {'active_model': 'stock.picking', 'active_ids': self.all_pickings.ids}
        self.assertEqual(action.get('res_model'), 'stock.add.to.wave')
        wizard_form = Form(self.env[action['res_model']].with_context(action['context']))
        wizard_form.mode = 'new'
        wizard = wizard_form.save()
        res = wizard.attach_pickings()
        self.assertEqual(set(res['context']['picking_to_wave']), set(self.all_pickings.ids))

    def test_add_to_existing_wave_from_lines(self):
        res_dict = self.picking_client_1.move_line_ids.action_open_add_to_wave()
        res_dict['context'] = {'active_model': 'stock.move.line', 'active_ids': self.picking_client_1.move_line_ids.ids}
        wizard_form = Form(self.env[res_dict['res_model']].with_context(res_dict['context']))
        wizard_form.mode = 'new'
        wizard_form.user_id = self.user_demo
        wizard_form.save().attach_pickings()
        wave = self.env['stock.picking.batch'].search([
            ('is_wave', '=', True)
        ])

        res_dict = self.picking_client_2.move_line_ids.action_open_add_to_wave()
        res_dict['context'] = {'active_model': 'stock.move.line', 'active_ids': self.picking_client_2.move_line_ids.ids}
        wizard_form = Form(self.env[res_dict['res_model']].with_context(res_dict['context']))
        wizard_form.mode = 'existing'
        wizard_form.wave_id = wave
        wizard_form.save().attach_pickings()

        wave = self.env['stock.picking.batch'].search([
            ('is_wave', '=', True)
        ])
        self.assertEqual(len(wave), 1)
        self.assertEqual(wave.picking_ids, self.picking_client_1 | self.picking_client_2)

    def test_add_to_existing_wave_from_pickings(self):
        res_dict = self.picking_client_1.move_line_ids.action_open_add_to_wave()
        res_dict['context'] = {'active_model': 'stock.move.line', 'active_ids': self.picking_client_1.move_line_ids.ids}
        wizard_form = Form(self.env[res_dict['res_model']].with_context(res_dict['context']))
        wizard_form.mode = 'new'
        wizard_form.user_id = self.user_demo
        action = wizard_form.save().attach_pickings()
        wave = self.env['stock.picking.batch'].search([
            ('is_wave', '=', True)
        ])

        action = self.env['ir.actions.actions']._for_xml_id('stock_picking_batch.stock_add_to_wave_action_stock_picking')
        action['context'] = {'active_model': 'stock.picking', 'active_ids': self.all_pickings.ids}
        self.assertEqual(action.get('res_model'), 'stock.add.to.wave')
        wizard_form = Form(self.env[action['res_model']].with_context(action['context']))
        wizard_form.mode = 'existing'
        wizard_form.wave_id = wave
        wizard = wizard_form.save()
        res = wizard.attach_pickings()
        self.assertEqual(set(res['context']['picking_to_wave']), set(self.all_pickings.ids))
        self.assertEqual(res['context']['active_wave_id'], wave.id)
