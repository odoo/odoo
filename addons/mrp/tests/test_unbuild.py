# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.exceptions import UserError


class TestUnbuild(TestMrpCommon):
    def setUp(self):
        super(TestUnbuild, self).setUp()
        self.stock_location = self.env.ref('stock.stock_location_stock')

    def test_unbuild_standart(self):
        """ This test creates a MO and then creates 3 unbuild
        orders for the final product. None of the products for this
        test are tracked. It checks the stock state after each order
        and ensure it is correct.
        """
        mo, bom, p_final, p1, p2 = self.generate_mo()
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)
        mo.action_assign()

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 5.0
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()

        mo.button_mark_done()
        self.assertEqual(mo.state, 'done', "Production order should be in done state.")

        # Check quantity in stock before unbuild.
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location), 5, 'You should have the 5 final product in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location), 80, 'You should have 80 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location), 0, 'You should have consumed all the 5 product in stock')

        # ---------------------------------------------------
        #       unbuild
        # ---------------------------------------------------

        x = Form(self.env['mrp.unbuild'])
        x.product_id = p_final
        x.bom_id = bom
        x.product_qty = 3
        x.product_uom_id = self.uom_unit
        x.save().action_unbuild()


        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location), 2, 'You should have consumed 3 final product in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location), 92, 'You should have 80 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location), 3, 'You should have consumed all the 5 product in stock')

        x = Form(self.env['mrp.unbuild'])
        x.product_id = p_final
        x.bom_id = bom
        x.product_qty = 2
        x.product_uom_id = self.uom_unit
        x.save().action_unbuild()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location), 0, 'You should have 0 finalproduct in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location), 100, 'You should have 80 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location), 5, 'You should have consumed all the 5 product in stock')

        x = Form(self.env['mrp.unbuild'])
        x.product_id = p_final
        x.bom_id = bom
        x.product_qty = 5
        x.product_uom_id = self.uom_unit
        x.save().action_unbuild()

        # Check quantity in stock after last unbuild.
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location, allow_negative=True), -5, 'You should have negative quantity for final product in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location), 120, 'You should have 80 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location), 10, 'You should have consumed all the 5 product in stock')

    def test_unbuild_with_final_lot(self):
        """ This test creates a MO and then creates 3 unbuild
        orders for the final product. Only the final product is tracked
        by lot. It checks the stock state after each order
        and ensure it is correct.
        """
        mo, bom, p_final, p1, p2 = self.generate_mo(tracking_final='lot')
        self.assertEqual(len(mo), 1, 'MO should have been created')

        lot = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': p_final.id,
            'company_id': self.env.company.id,
        })

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)
        mo.action_assign()

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 5.0
        produce_form.finished_lot_id = lot
        produce_wizard = produce_form.save()

        produce_wizard.do_produce()

        mo.button_mark_done()
        self.assertEqual(mo.state, 'done', "Production order should be in done state.")

        # Check quantity in stock before unbuild.
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location, lot_id=lot), 5, 'You should have the 5 final product in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location), 80, 'You should have 80 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location), 0, 'You should have consumed all the 5 product in stock')

        # ---------------------------------------------------
        #       unbuild
        # ---------------------------------------------------

        # This should fail since we do not choose a lot to unbuild for final product.
        with self.assertRaises(AssertionError):
            x = Form(self.env['mrp.unbuild'])
            x.product_id = p_final
            x.bom_id = bom
            x.product_qty = 3
            x.product_uom_id = self.uom_unit
            unbuild_order = x.save()

        x = Form(self.env['mrp.unbuild'])
        x.product_id = p_final
        x.bom_id = bom
        x.product_qty = 3
        x.product_uom_id = self.uom_unit
        x.lot_id = lot
        x.save().action_unbuild()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location, lot_id=lot), 2, 'You should have consumed 3 final product in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location), 92, 'You should have 80 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location), 3, 'You should have consumed all the 5 product in stock')

        x = Form(self.env['mrp.unbuild'])
        x.product_id = p_final
        x.bom_id = bom
        x.product_qty = 2
        x.lot_id = lot
        x.product_uom_id = self.uom_unit
        x.save().action_unbuild()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location, lot_id=lot), 0, 'You should have 0 finalproduct in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location), 100, 'You should have 80 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location), 5, 'You should have consumed all the 5 product in stock')

        x = Form(self.env['mrp.unbuild'])
        x.product_id = p_final
        x.bom_id = bom
        x.product_qty = 5
        x.lot_id = lot
        x.product_uom_id = self.uom_unit
        x.save().action_unbuild()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location, lot_id=lot, allow_negative=True), -5, 'You should have negative quantity for final product in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location), 120, 'You should have 80 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location), 10, 'You should have consumed all the 5 product in stock')

    def test_unbuild_with_comnsumed_lot(self):
        """ This test creates a MO and then creates 3 unbuild
        orders for the final product. Only once of the two consumed
        product is tracked by lot. It checks the stock state after each
        order and ensure it is correct.
        """
        mo, bom, p_final, p1, p2 = self.generate_mo(tracking_base_1='lot')
        self.assertEqual(len(mo), 1, 'MO should have been created')

        lot = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': p1.id,
            'company_id': self.env.company.id,
        })

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100, lot_id=lot)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)
        mo.action_assign()
        for ml in mo.move_raw_ids.mapped('move_line_ids'):
            if ml.product_id.tracking != 'none':
                self.assertEqual(ml.lot_id, lot, 'Wrong reserved lot.')

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 5.0
        produce_wizard = produce_form.save()

        produce_wizard.do_produce()

        mo.button_mark_done()
        self.assertEqual(mo.state, 'done', "Production order should be in done state.")
        # Check quantity in stock before unbuild.
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location), 5, 'You should have the 5 final product in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location, lot_id=lot), 80, 'You should have 80 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location), 0, 'You should have consumed all the 5 product in stock')

        # ---------------------------------------------------
        #       unbuild
        # ---------------------------------------------------

        x = Form(self.env['mrp.unbuild'])
        x.product_id = p_final
        x.bom_id = bom
        x.product_qty = 3
        x.product_uom_id = self.uom_unit
        unbuild_order = x.save()

        # This should fail since we do not provide the MO that we wanted to unbuild. (without MO we do not know which consumed lot we have to restore)
        with self.assertRaises(UserError):
            unbuild_order.action_unbuild()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location), 5, 'You should have consumed 3 final product in stock')

        unbuild_order.mo_id = mo.id
        unbuild_order.action_unbuild()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location), 2, 'You should have consumed 3 final product in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location, lot_id=lot), 92, 'You should have 92 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location), 3, 'You should have consumed all the 5 product in stock')

        x = Form(self.env['mrp.unbuild'])
        x.product_id = p_final
        x.bom_id = bom
        x.product_uom_id = self.uom_unit
        x.mo_id = mo
        x.product_qty = 2
        x.save().action_unbuild()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location), 0, 'You should have 0 finalproduct in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location, lot_id=lot), 100, 'You should have 80 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location), 5, 'You should have consumed all the 5 product in stock')

        x = Form(self.env['mrp.unbuild'])
        x.product_id = p_final
        x.bom_id = bom
        x.product_uom_id = self.uom_unit
        x.mo_id = mo
        x.product_qty = 5
        x.save().action_unbuild()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location, allow_negative=True), -5, 'You should have negative quantity for final product in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location, lot_id=lot), 120, 'You should have 80 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location), 10, 'You should have consumed all the 5 product in stock')

    def test_unbuild_with_everything_tracked(self):
        """ This test creates a MO and then creates 3 unbuild
        orders for the final product. All the products for this
        test are tracked. It checks the stock state after each order
        and ensure it is correct.
        """
        mo, bom, p_final, p1, p2 = self.generate_mo(tracking_final='lot', tracking_base_2='lot', tracking_base_1='lot')
        self.assertEqual(len(mo), 1, 'MO should have been created')

        lot_final = self.env['stock.production.lot'].create({
            'name': 'lot_final',
            'product_id': p_final.id,
            'company_id': self.env.company.id,
        })
        lot_1 = self.env['stock.production.lot'].create({
            'name': 'lot_consumed_1',
            'product_id': p1.id,
            'company_id': self.env.company.id,
        })
        lot_2 = self.env['stock.production.lot'].create({
            'name': 'lot_consumed_2',
            'product_id': p2.id,
            'company_id': self.env.company.id,
        })

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100, lot_id=lot_1)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5, lot_id=lot_2)
        mo.action_assign()

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 5.0
        produce_form.finished_lot_id = lot_final
        produce_wizard = produce_form.save()

        produce_wizard.do_produce()

        mo.button_mark_done()
        self.assertEqual(mo.state, 'done', "Production order should be in done state.")
        # Check quantity in stock before unbuild.
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location, lot_id=lot_final), 5, 'You should have the 5 final product in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location, lot_id=lot_1), 80, 'You should have 80 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location, lot_id=lot_2), 0, 'You should have consumed all the 5 product in stock')

        # ---------------------------------------------------
        #       unbuild
        # ---------------------------------------------------

        x = Form(self.env['mrp.unbuild'])
        with self.assertRaises(AssertionError):
            x.product_id = p_final
            x.bom_id = bom
            x.product_uom_id = self.uom_unit
            x.product_qty = 3
            x.save()

        with self.assertRaises(AssertionError):
            x.product_id = p_final
            x.bom_id = bom
            x.product_uom_id = self.uom_unit
            x.product_qty = 3
            x.save()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location, lot_id=lot_final), 5, 'You should have consumed 3 final product in stock')

        with self.assertRaises(AssertionError):
            x.product_id = p_final
            x.bom_id = bom
            x.product_uom_id = self.uom_unit
            x.mo_id = mo
            x.product_qty = 3
            x.save()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location, lot_id=lot_final), 5, 'You should have consumed 3 final product in stock')

        x = Form(self.env['mrp.unbuild'])
        x.product_id = p_final
        x.bom_id = bom
        x.product_uom_id = self.uom_unit
        x.mo_id = mo
        x.product_qty = 3
        x.lot_id = lot_final
        x.save().action_unbuild()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location, lot_id=lot_final), 2, 'You should have consumed 3 final product in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location, lot_id=lot_1), 92, 'You should have 80 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location, lot_id=lot_2), 3, 'You should have consumed all the 5 product in stock')

        x = Form(self.env['mrp.unbuild'])
        x.product_id = p_final
        x.bom_id = bom
        x.product_uom_id = self.uom_unit
        x.mo_id = mo
        x.product_qty = 2
        x.lot_id = lot_final
        x.save().action_unbuild()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location, lot_id=lot_final), 0, 'You should have 0 finalproduct in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location, lot_id=lot_1), 100, 'You should have 80 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location, lot_id=lot_2), 5, 'You should have consumed all the 5 product in stock')

        x = Form(self.env['mrp.unbuild'])
        x.product_id = p_final
        x.bom_id = bom
        x.product_uom_id = self.uom_unit
        x.mo_id = mo
        x.product_qty = 5
        x.lot_id = lot_final
        x.save().action_unbuild()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location, lot_id=lot_final, allow_negative=True), -5, 'You should have negative quantity for final product in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location, lot_id=lot_1), 120, 'You should have 80 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location, lot_id=lot_2), 10, 'You should have consumed all the 5 product in stock')

    def test_unbuild_with_duplicate_move(self):
        """ This test creates a MO from 3 different lot on a consumed product (p2).
        The unbuild order should revert the correct quantity for each specific lot.
        """
        mo, bom, p_final, p1, p2 = self.generate_mo(tracking_final='none', tracking_base_2='lot', tracking_base_1='none')
        self.assertEqual(len(mo), 1, 'MO should have been created')

        lot_1 = self.env['stock.production.lot'].create({
            'name': 'lot_1',
            'product_id': p2.id,
            'company_id': self.env.company.id,
        })
        lot_2 = self.env['stock.production.lot'].create({
            'name': 'lot_2',
            'product_id': p2.id,
            'company_id': self.env.company.id,
        })
        lot_3 = self.env['stock.production.lot'].create({
            'name': 'lot_3',
            'product_id': p2.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 1, lot_id=lot_1)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 3, lot_id=lot_2)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 2, lot_id=lot_3)
        mo.action_assign()

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 5.0
        produce_wizard = produce_form.save()

        produce_wizard.do_produce()
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done', "Production order should be in done state.")
        # Check quantity in stock before unbuild.
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location), 5, 'You should have the 5 final product in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location), 80, 'You should have 80 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location, lot_id=lot_1), 0, 'You should have consumed all the 1 product for lot 1 in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location, lot_id=lot_2), 0, 'You should have consumed all the 3 product for lot 2 in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location, lot_id=lot_3), 1, 'You should have consumed only 1 product for lot3 in stock')

        x = Form(self.env['mrp.unbuild'])
        x.product_id = p_final
        x.bom_id = bom
        x.product_uom_id = self.uom_unit
        x.mo_id = mo
        x.product_qty = 5
        x.save().action_unbuild()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(p_final, self.stock_location), 0, 'You should have no more final product in stock after unbuild')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p1, self.stock_location), 100, 'You should have 80 products in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location, lot_id=lot_1), 1, 'You should have get your product with lot 1 in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location, lot_id=lot_2), 3, 'You should have the 3 basic product for lot 2 in stock')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(p2, self.stock_location, lot_id=lot_3), 2, 'You should have get one product back for lot 3')

    def test_production_links_with_non_tracked_lots(self):
        """ This test produces an MO in two times and checks that the move lines are linked in a correct way
        """
        mo, bom, p_final, p1, p2 = self.generate_mo(tracking_final='lot', tracking_base_1='none', tracking_base_2='lot')
        lot_1 = self.env['stock.production.lot'].create({
            'name': 'lot_1',
            'product_id': p2.id,
            'company_id': self.env.company.id,
        })

        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 3, lot_id=lot_1)
        lot_finished_1 = self.env['stock.production.lot'].create({
            'name': 'lot_finished_1',
            'product_id': p_final.id,
            'company_id': self.env.company.id,
        })

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 3.0
        produce_form.finished_lot_id = lot_finished_1
        produce_wizard = produce_form.save()
        produce_wizard._workorder_line_ids()[0].lot_id = lot_1
        produce_wizard.do_produce()

        lot_2 = self.env['stock.production.lot'].create({
            'name': 'lot_2',
            'product_id': p2.id,
            'company_id': self.env.company.id,
        })

        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 4, lot_id=lot_2)
        lot_finished_2 = self.env['stock.production.lot'].create({
            'name': 'lot_finished_2',
            'product_id': p_final.id,
            'company_id': self.env.company.id,
        })

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 2.0
        produce_form.finished_lot_id = lot_finished_2

        produce_wizard = produce_form.save()
        produce_wizard._workorder_line_ids()[0].lot_id = lot_2
        produce_wizard.do_produce()
        mo.button_mark_done()
        ml = mo.finished_move_line_ids[0].consume_line_ids.filtered(lambda m: m.product_id == p1 and lot_finished_1 in m.lot_produced_ids)
        self.assertEqual(ml[0].qty_done, 12.0, 'Should have consumed 12 for the first lot')
        ml = mo.finished_move_line_ids[1].consume_line_ids.filtered(lambda m: m.product_id == p1 and lot_finished_2 in m.lot_produced_ids)
        self.assertEqual(ml[0].qty_done, 8.0, 'Should have consumed 8 for the second lot')

    def test_unbuild_with_routes(self):
        """ This test creates a MO of a stockable product (Table). A new route for rule QC/Unbuild -> Stock
        is created with Warehouse -> True.
        The unbuild order should revert the consumed components into QC/Unbuild location for quality check
        and then a picking should be generated for transferring components from QC/Unbuild location to stock.
        """
        StockQuant = self.env['stock.quant']
        ProductObj = self.env['product.product']
        # Create new QC/Unbuild location
        warehouse = self.env.ref('stock.warehouse0')
        unbuild_location = self.env['stock.location'].create({
            'name': 'QC/Unbuild',
            'usage': 'internal',
            'location_id': warehouse.view_location_id.id
        })

        # Create a product route containing a stock rule that will move product from QC/Unbuild location to stock
        product_route = self.env['stock.location.route'].create({
            'name': 'QC/Unbuild -> Stock',
            'warehouse_selectable': True,
            'warehouse_ids': [(4, warehouse.id)],
            'rule_ids': [(0, 0, {
                'name': 'Send Matrial QC/Unbuild -> Stock',
                'action': 'push',
                'picking_type_id': self.ref('stock.picking_type_internal'),
                'location_src_id': unbuild_location.id,
                'location_id': self.stock_location.id,
            })],
        })

        # Create a stockable product and its components
        finshed_product = ProductObj.create({
            'name': 'Table',
            'type': 'product',
        })
        component1 = ProductObj.create({
            'name': 'Table head',
            'type': 'product',
        })
        component2 = ProductObj.create({
            'name': 'Table stand',
            'type': 'product',
        })

        # Create bom and add components
        bom = self.env['mrp.bom'].create({
            'product_id': finshed_product.id,
            'product_tmpl_id': finshed_product.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': component1.id, 'product_qty': 1}),
                (0, 0, {'product_id': component2.id, 'product_qty': 1})
            ]})

        # Set on hand quantity
        StockQuant._update_available_quantity(component1, self.stock_location, 1)
        StockQuant._update_available_quantity(component2, self.stock_location, 1)

        # Create mo
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = finshed_product
        mo_form.bom_id = bom
        mo_form.product_uom_id = finshed_product.uom_id
        mo_form.product_qty = 1.0
        mo = mo_form.save()
        self.assertEqual(len(mo), 1, 'MO should have been created')
        mo.action_confirm()
        mo.action_assign()

        # Produce the final product
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 1.0
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()

        mo.button_mark_done()
        self.assertEqual(mo.state, 'done', "Production order should be in done state.")

        # Check quantity in stock before unbuild
        self.assertEqual(StockQuant._get_available_quantity(finshed_product, self.stock_location), 1, 'Table should be available in stock')
        self.assertEqual(StockQuant._get_available_quantity(component1, self.stock_location), 0, 'Table head should not be available in stock')
        self.assertEqual(StockQuant._get_available_quantity(component2, self.stock_location), 0, 'Table stand should not be available in stock')

        # ---------------------------------------------------
        #       Unbuild
        # ---------------------------------------------------

        # Create an unbuild order of the finished product and set the destination loacation = QC/Unbuild
        x = Form(self.env['mrp.unbuild'])
        x.product_id = finshed_product
        x.bom_id = bom
        x.product_uom_id = self.uom_unit
        x.mo_id = mo
        x.product_qty = 1
        x.location_id = self.stock_location
        x.location_dest_id = unbuild_location
        x.save().action_unbuild()

        # Check the available quantity of components and final product in stock
        self.assertEqual(StockQuant._get_available_quantity(finshed_product, self.stock_location), 0, 'Table should not be available in stock as it is unbuild')
        self.assertEqual(StockQuant._get_available_quantity(component1, self.stock_location), 0, 'Table head should not be available in stock as it is in QC/Unbuild location')
        self.assertEqual(StockQuant._get_available_quantity(component2, self.stock_location), 0, 'Table stand should not be available in stock as it is in QC/Unbuild location')

        # Find new generated picking
        picking = self.env['stock.picking'].search([('product_id', 'in', [component1.id, component2.id])])
        self.assertEqual(picking.location_id.id, unbuild_location.id, 'Wrong source location in picking')
        self.assertEqual(picking.location_dest_id.id, self.stock_location.id, 'Wrong destination location in picking')

        # Transfer it
        for ml in picking.move_ids_without_package:
            ml.quantity_done = 1
        picking.action_done()

        # Check the available quantity of components and final product in stock
        self.assertEqual(StockQuant._get_available_quantity(finshed_product, self.stock_location), 0, 'Table should not be available in stock')
        self.assertEqual(StockQuant._get_available_quantity(component1, self.stock_location), 1, 'Table head should be available in stock as the picking is transferred')
        self.assertEqual(StockQuant._get_available_quantity(component2, self.stock_location), 1, 'Table stand should be available in stock as the picking is transferred')
