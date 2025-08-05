# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest import skip

from odoo import Command, fields
from odoo.tests import Form, tagged
from odoo.tools.float_utils import float_round, float_compare

from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon
from odoo.addons.mrp_account.tests.test_bom_price import TestBomPriceCommon


@tagged('post_install', '-at_install')
@skip('Temporary to fast merge new valuation')
class TestAccountSubcontractingFlows(TestMrpSubcontractingCommon):
    def test_subcontracting_account_flow_1(self):
        # pylint: disable=bad-whitespace
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.uom_unit = self.env.ref('uom.product_uom_unit')

        product_category_all = self.product_category
        product_category_all.property_cost_method = 'fifo'
        product_category_all.property_valuation = 'real_time'
        valu_account = self.env['account.account'].create({
            'name': 'VALU Account',
            'code': '000003',
            'account_type': 'asset_current',
        })
        production_cost_account = self.env['account.account'].create({
            'name': 'PROD COST Account',
            'code': '000004',
            'account_type': 'asset_current',
        })
        product_category_all.property_stock_account_production_cost_id = production_cost_account
        product_category_all.property_stock_valuation_account_id = valu_account
        stock_valu_acc_id = product_category_all.property_stock_valuation_account_id.id
        stock_cop_acc_id = product_category_all.property_stock_account_production_cost_id.id
        expense_acc_id = product_category_all.property_account_expense_categ_id.id

        # IN 10@10 comp1 10@20 comp2
        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.env.company.subcontracting_location_id.id,
            'product_id': self.comp1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 10.0
        move1.picked = True
        move1._action_done()
        move2 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.env.company.subcontracting_location_id.id,
            'product_id': self.comp2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 20.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 10.0
        move2.picked = True
        move2._action_done()

        all_amls_ids = self.env['account.move.line'].search([]).ids

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        picking_receipt.move_ids.price_unit = 15.0

        picking_receipt.action_confirm()
        # Suppose the additional cost changes:
        picking_receipt.move_ids.price_unit = 30.0
        picking_receipt.move_ids.quantity = 1.0
        picking_receipt.move_ids.picked = True
        picking_receipt._action_done()

        mo1 = picking_receipt._get_subcontract_production()
        # Finished is made of 1 comp1 and 1 comp2.
        # Cost of comp1 = 10
        # Cost of comp2 = 20
        # --> Cost of finished = 10 + 20 = 30
        # Additionnal cost = 30 (from the purchase order line or directly set on the stock move here)
        # Total cost of subcontracting 1 unit of finished = 30 + 30 = 60
        self.assertEqual(mo1.move_finished_ids.stock_valuation_layer_ids.value, 60)
        self.assertEqual(picking_receipt.move_ids.stock_valuation_layer_ids.value, 0)
        self.assertEqual(picking_receipt.move_ids.product_id.value_svl, 60)

        amls = self.env['account.move.line'].search([('id', 'not in', all_amls_ids)])
        all_amls_ids += amls.ids
        self.assertRecordValues(amls, [
            # Receipt from subcontractor
            {'account_id': stock_valu_acc_id,   'product_id': self.finished.id,    'debit': 60.0, 'credit': 0.0},
            {'account_id': stock_cop_acc_id,    'product_id': self.finished.id,    'debit': 0.0,   'credit': 30.0},
            # Delivery com2 to subcontractor
            {'account_id': stock_valu_acc_id,   'product_id': self.comp2.id,       'debit': 0.0,   'credit': 20.0},
            {'account_id': stock_cop_acc_id,    'product_id': self.comp2.id,       'debit': 20.0,  'credit': 0.0},
            # Delivery com2 to subcontractor
            {'account_id': stock_valu_acc_id,   'product_id': self.comp1.id,       'debit': 0.0,   'credit': 10.0},
            {'account_id': stock_cop_acc_id,    'product_id': self.comp1.id,       'debit': 10.0,  'credit': 0.0},
        ])

        # Do the same without any additionnal cost
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        picking_receipt.move_ids.price_unit = 0

        picking_receipt.action_confirm()
        picking_receipt.move_ids.quantity = 1.0
        picking_receipt.move_ids.picked = True
        picking_receipt._action_done()

        mo2 = picking_receipt._get_subcontract_production()
        # In this case, since there isn't any additionnal cost, the total cost of the subcontracting
        # is the sum of the components' costs: 10 + 20 = 30
        self.assertEqual(mo2.move_finished_ids.stock_valuation_layer_ids.value, 30)
        self.assertEqual(picking_receipt.move_ids.product_id.value_svl, 90)

        amls = self.env['account.move.line'].search([('id', 'not in', all_amls_ids)])
        all_amls_ids += amls.ids
        self.assertRecordValues(amls, [
            # Receipt from subcontractor
            {'account_id': stock_cop_acc_id,     'product_id': self.finished.id,    'debit': 0.0,   'credit': 30.0},
            {'account_id': stock_valu_acc_id,   'product_id': self.finished.id,    'debit': 30.0,  'credit': 0.0},
            # Delivery com2 to subcontractor
            {'account_id': stock_valu_acc_id,   'product_id': self.comp2.id,       'debit': 0.0,   'credit': 20.0},
            {'account_id': stock_cop_acc_id,    'product_id': self.comp2.id,       'debit': 20.0,  'credit': 0.0},
            # Delivery com2 to subcontractor
            {'account_id': stock_valu_acc_id,   'product_id': self.comp1.id,       'debit': 0.0,   'credit': 10.0},
            {'account_id': stock_cop_acc_id,    'product_id': self.comp1.id,       'debit': 10.0,  'credit': 0.0},
        ])

        # Scrap first subcontract MO and ensure that the additional cost is not added.
        scrap = self.env['stock.scrap'].create({
            'product_id': self.finished.id,
            'product_uom_id': self.uom_unit.id,
            'scrap_qty': 1,
            'production_id': mo1.id,
            'location_id': self.stock_location.id,
        })
        scrap.do_scrap()

        amls = self.env['account.move.line'].search([('id', 'not in', all_amls_ids)])
        all_amls_ids += amls.ids
        self.assertRecordValues(amls, [
            {'account_id': stock_valu_acc_id, 'product_id': self.finished.id, 'debit': 0.0, 'credit': 60.0},
            {'account_id': expense_acc_id, 'product_id': self.finished.id, 'debit': 60.0, 'credit': 0.0},
        ])

    def test_subcontracting_account_flow_2(self):
        """Test when set Cost of Production account on production location, subcontracting
        should use it.
        """
        # pylint: disable=bad-whitespace
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.uom_unit = self.env.ref('uom.product_uom_unit')
        product_category_all = self.product_category
        product_category_all.property_cost_method = 'fifo'
        product_category_all.property_valuation = 'real_time'
        in_account = self.env['account.account'].create({
            'name': 'IN Account',
            'code': '000001',
            'account_type': 'asset_current',
        })
        out_account = self.env['account.account'].create({
            'name': 'OUT Account',
            'code': '000002',
            'account_type': 'asset_current',
        })
        valu_account = self.env['account.account'].create({
            'name': 'VALU Account',
            'code': '000003',
            'account_type': 'asset_current',
        })
        production_cost_account = self.env['account.account'].create({
            'name': 'PROD COST Account',
            'code': '000004',
            'account_type': 'asset_current',
        })
        product_category_all.property_stock_account_input_categ_id = in_account
        product_category_all.property_stock_account_output_categ_id = out_account
        product_category_all.property_stock_account_production_cost_id = production_cost_account
        product_category_all.property_stock_valuation_account_id = valu_account
        stock_in_acc_id = product_category_all.property_stock_account_input_categ_id.id
        stock_valu_acc_id = product_category_all.property_stock_valuation_account_id.id
        stock_cop_acc_id = product_category_all.property_stock_account_production_cost_id.id

        # set Cost of Production account on production location
        cop_account = self.env['account.account'].create({
            'name': 'Cost of Production',
            'code': 'CoP',
            "account_type": 'expense',
            'reconcile': False,
        })
        self.comp1.property_stock_production.write({
            'valuation_out_account_id': cop_account.id,
            'valuation_in_account_id': cop_account.id,
        })

        # IN 10@10 comp1 10@20 comp2
        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.env.company.subcontracting_location_id.id,
            'product_id': self.comp1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 10.0
        move1.picked = True
        move1._action_done()
        move2 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.env.company.subcontracting_location_id.id,
            'product_id': self.comp2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 20.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 10.0
        move2.picked = True
        move2._action_done()

        all_amls_ids = self.env['account.move.line'].search([]).ids

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        picking_receipt.move_ids.price_unit = 30.0
        picking_receipt.action_confirm()
        picking_receipt.move_ids.quantity = 1.0
        picking_receipt.move_ids.picked = True
        picking_receipt._action_done()

        amls = self.env['account.move.line'].search([('id', 'not in', all_amls_ids)])
        all_amls_ids += amls.ids
        # get the account/input account of production location
        production_location = self.env['stock.location'].search([('usage', '=', 'production'), ('company_id', '=', self.env.company.id)])
        production_in_acc_id = production_location.valuation_in_account_id.id
        production_out_acc_id = production_location.valuation_out_account_id.id
        self.assertRecordValues(amls, [
            # Receipt from subcontractor     | should use output account of production location
            {'account_id': stock_valu_acc_id,      'product_id': self.finished.id,    'debit': 60.0,  'credit': 0.0},
            {'account_id': stock_in_acc_id,        'product_id': self.finished.id,    'debit': 0.0,   'credit': 30.0},
            {'account_id': production_out_acc_id,  'product_id': self.finished.id,    'debit': 0.0,   'credit': 30.0},
            # Delivery com2 to subcontractor | should use input account of production location
            {'account_id': stock_valu_acc_id,      'product_id': self.comp2.id,       'debit': 0.0,   'credit': 20.0},
            {'account_id': production_in_acc_id,   'product_id': self.comp2.id,       'debit': 20.0,  'credit': 0.0},
            # Delivery com2 to subcontractor | should use input account of production location
            {'account_id': stock_valu_acc_id,      'product_id': self.comp1.id,       'debit': 0.0,   'credit': 10.0},
            {'account_id': production_in_acc_id,   'product_id': self.comp1.id,       'debit': 10.0,  'credit': 0.0},
        ])

    def test_subcontracting_account_backorder(self):
        """ This test uses tracked (serial and lot) component and tracked (serial) finished product
        The original subcontracting production order will be split into 4 backorders. This test
        ensure the extra cost asked from the subcontractor is added correctly on all the finished
        product valuation layer. Not only the first one. """
        todo_nb = 4
        self.comp2.tracking = 'lot'
        self.comp1.tracking = 'serial'
        self.comp2.standard_price = 100
        self.finished.tracking = 'serial'
        self.product_category.property_cost_method = 'fifo'

        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = todo_nb
            move.quantity = todo_nb
        picking_receipt = picking_form.save()
        # Mimic the extra cost on the po line
        picking_receipt.move_ids.price_unit = 50
        picking_receipt.action_confirm()
        picking_receipt.do_unreserve()

        # We should be able to call the 'record_components' button
        self.assertTrue(picking_receipt.display_action_record_components)

        lot_comp2 = self.env['stock.lot'].create({
            'name': 'lot_comp2',
            'product_id': self.comp2.id,
        })
        serials_finished = []
        serials_comp1 = []
        for i in range(todo_nb):
            serials_finished.append(self.env['stock.lot'].create({
                'name': 'serial_fin_%s' % i,
                'product_id': self.finished.id,
            }))
            serials_comp1.append(self.env['stock.lot'].create({
                'name': 'serials_comp1_%s' % i,
                'product_id': self.comp1.id,
            }))

        for i in range(todo_nb):
            action = picking_receipt.action_record_components()
            mo = self.env['mrp.production'].browse(action['res_id'])
            mo_form = Form(mo.with_context(**action['context']), view=action['view_id'])
            mo_form.lot_producing_id = serials_finished[i]
            with mo_form.move_line_raw_ids.edit(0) as ml:
                self.assertEqual(ml.product_id, self.comp1)
                ml.lot_id = serials_comp1[i]
            with mo_form.move_line_raw_ids.edit(1) as ml:
                self.assertEqual(ml.product_id, self.comp2)
                ml.lot_id = lot_comp2
            mo = mo_form.save()
            mo.subcontracting_record_component()

        # We should not be able to call the 'record_components' button
        picking_receipt.move_ids.picked = True
        picking_receipt.button_validate()

        f_layers = self.finished.stock_valuation_layer_ids
        self.assertEqual(len(f_layers), 4)
        for layer in f_layers:
            self.assertEqual(layer.value, 100 + 50)

    def test_tracked_compo_and_backorder(self):
        """
        Suppose a subcontracted product P with two tracked components, P is FIFO
        Create a receipt for 10 x P, receive 5, then 3 and then 2
        """
        self.product_category.property_cost_method = 'fifo'
        self.comp1.tracking = 'lot'
        self.comp1.standard_price = 10
        self.comp2.tracking = 'lot'
        self.comp2.standard_price = 20

        lot01, lot02 = self.env['stock.lot'].create([{
            'name': "Lot of %s" % product.name,
            'product_id': product.id,
        } for product in (self.comp1, self.comp2)])

        receipt_form = Form(self.env['stock.picking'])
        receipt_form.picking_type_id = self.env.ref('stock.picking_type_in')
        receipt_form.partner_id = self.subcontractor_partner1
        with receipt_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 10
        receipt = receipt_form.save()
        # add an extra cost
        receipt.move_ids.price_unit = 50
        receipt.action_confirm()

        for qty_producing in (5, 3, 2):
            action = receipt.action_record_components()
            mo = self.env['mrp.production'].browse(action['res_id'])
            mo_form = Form(mo.with_context(**action['context']), view=action['view_id'])
            mo_form.qty_producing = qty_producing
            with mo_form.move_line_raw_ids.edit(0) as ml:
                ml.lot_id = lot01
            with mo_form.move_line_raw_ids.edit(1) as ml:
                ml.lot_id = lot02
            mo = mo_form.save()
            mo.subcontracting_record_component()

            action = receipt.button_validate()
            if isinstance(action, dict):
                Form.from_action(self.env, action).save().process()
                receipt = receipt.backorder_ids

        self.assertRecordValues(self.finished.stock_valuation_layer_ids, [
            {'quantity': 5, 'value': 5 * (10 + 20 + 50)},
            {'quantity': 3, 'value': 3 * (10 + 20 + 50)},
            {'quantity': 2, 'value': 2 * (10 + 20 + 50)},
        ])

    def test_subcontract_cost_different_when_standard_price(self):
        """Test when subcontracting with standard price when
            Final product cost != Components cost + Subcontracting cost
        When posting the account entries for receiving final product, the
        subcontracting cost will be adjusted based on the difference of the cost.
        """
        # pylint: disable=bad-whitespace
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.uom_unit = self.env.ref('uom.product_uom_unit')
        product_category_all = self.product_category
        product_category_all.property_cost_method = 'standard'
        product_category_all.property_valuation = 'real_time'

        in_account = self.env['account.account'].create({
            'name': 'IN Account',
            'code': '000001',
            'account_type': 'asset_current',
        })
        out_account = self.env['account.account'].create({
            'name': 'OUT Account',
            'code': '000002',
            'account_type': 'asset_current',
        })
        valu_account = self.env['account.account'].create({
            'name': 'VALU Account',
            'code': '000003',
            'account_type': 'asset_current',
        })
        production_cost_account = self.env['account.account'].create({
            'name': 'PROD COST Account',
            'code': '000004',
            'account_type': 'asset_current',
        })
        product_category_all.property_stock_account_input_categ_id = in_account
        product_category_all.property_stock_account_output_categ_id = out_account
        product_category_all.property_stock_account_production_cost_id = production_cost_account
        product_category_all.property_stock_valuation_account_id = valu_account
        stock_in_acc_id = product_category_all.property_stock_account_input_categ_id.id
        stock_valu_acc_id = product_category_all.property_stock_valuation_account_id.id
        stock_cop_acc_id = product_category_all.property_stock_account_production_cost_id.id
        self.comp1.standard_price = 10
        self.comp2.standard_price = 20
        self.finished.standard_price = 40

        all_amls_ids = self.env['account.move.line'].search([]).ids

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        # subcontracting cost is 15
        picking_receipt.move_ids.price_unit = 15.0
        picking_receipt.action_confirm()

        picking_receipt.move_ids.quantity = 1.0
        picking_receipt.move_ids.picked = True
        picking_receipt._action_done()

        amls = self.env['account.move.line'].search([('id', 'not in', all_amls_ids)])
        self.assertRecordValues(amls, [
            # Receipt from subcontractor
            {'account_id': stock_valu_acc_id,   'product_id': self.finished.id,    'debit': 40.0,  'credit': 0.0},
            {'account_id': stock_in_acc_id,     'product_id': self.finished.id,    'debit': 0.0,   'credit': 10.0},   # adjust according to the difference
            {'account_id': stock_cop_acc_id,    'product_id': self.finished.id,    'debit': 0.0,   'credit': 30.0},
            # Delivery com2 to subcontractor
            {'account_id': stock_valu_acc_id,   'product_id': self.comp2.id,       'debit': 0.0,   'credit': 20.0},
            {'account_id': stock_cop_acc_id,    'product_id': self.comp2.id,       'debit': 20.0,  'credit': 0.0},
            # Delivery com2 to subcontractor
            {'account_id': stock_valu_acc_id,   'product_id': self.comp1.id,       'debit': 0.0,   'credit': 10.0},
            {'account_id': stock_cop_acc_id,    'product_id': self.comp1.id,       'debit': 10.0,  'credit': 0.0},
        ])

    def test_input_output_accout_with_subcontract(self):
        """
        Test that the production stock account is optional, and we will fallback on input/output accounts.
        """
        product_category_all = self.product_category
        product_category_all.property_cost_method = 'fifo'
        product_category_all.property_valuation = 'real_time'
        self._setup_category_stock_journals()
        # set the production account to False
        product_category_all.property_stock_account_production_cost_id = False
        product_category_all.invalidate_recordset()
        self.assertFalse(product_category_all.property_stock_account_production_cost_id)
        self.assertEqual(self.bom.type, 'subcontract')
        self.comp1.standard_price = 1.0
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()
        picking_receipt.move_ids.quantity = 1.0
        picking_receipt.move_ids.picked = True
        picking_receipt._action_done()
        self.assertEqual(picking_receipt.state, 'done')

        mo = picking_receipt._get_subcontract_production()
        stock_valu_acc_id = product_category_all.property_stock_valuation_account_id.id
        out_account = product_category_all.property_stock_account_output_categ_id.id
        in_account = product_category_all.property_stock_account_input_categ_id.id
        # Check that the input account is used for the finished move, as the production account is set to False.
        self.assertRecordValues(mo.move_finished_ids.stock_valuation_layer_ids.account_move_id.line_ids, [
            {'account_id': in_account, 'product_id': self.finished.id, 'debit': 0.0, 'credit': 1.0},
            {'account_id': stock_valu_acc_id, 'product_id': self.finished.id, 'debit': 1.0, 'credit': 0.0},
        ])
        # Check that the output account is used for the move raw, as the production account is set to False.
        self.assertRecordValues(mo.move_raw_ids.stock_valuation_layer_ids.account_move_id.line_ids, [
            {'account_id': stock_valu_acc_id, 'product_id': self.comp1.id, 'debit': 0.0, 'credit': 1.0},
            {'account_id': out_account, 'product_id': self.comp1.id, 'debit': 1.0, 'credit': 0.0},
        ])


class TestBomPriceSubcontracting(TestBomPriceCommon):

    def test_01_compute_price_subcontracting_cost(self):
        """Test calculation of bom cost with subcontracting."""
        partner = self.env['res.partner'].create({
            'name': 'A name can be a Many2one...'
        })
        (self.bom_1 | self.bom_2).write({
            'type': 'subcontract',
            'subcontractor_ids': [Command.link(partner.id)]
        })
        suppliers = self.env['product.supplierinfo'].create([
            {
                'partner_id': partner.id,
                'product_tmpl_id': self.dining_table.product_tmpl_id.id,
                'price': 150.0,
            }, {
                'partner_id': partner.id,
                'product_tmpl_id': self.table_head.product_tmpl_id.id,
                'price': 120.0,
                'product_uom_id': self.dozen.id,
            }
        ])
        self.assertEqual(suppliers.mapped('is_subcontractor'), [True, True])

        # -----------------------------------------------------------------
        # Cost of BoM (Dining Table 1 Unit)
        # -----------------------------------------------------------------
        # Component Cost =  Table Head     1 Unit * 300 = 300 (478.75 from it's components)
        #                   Screw          5 Unit *  10 =  50
        #                   Leg            4 Unit *  25 = 100
        #                   Glass          1 Unit * 100 = 100
        #                   Subcontracting 1 Unit * 150 = 150
        # Total = 700 [878.75 if components of Table Head considered] (for 1 Unit)
        # -----------------------------------------------------------------
        self.assertEqual(self.dining_table.standard_price, 1000, "Initial price of the Product should be 1000")
        self.dining_table.button_bom_cost()
        self.assertEqual(float_round(self.dining_table.standard_price, precision_digits=2), 700.0, "After computing price from BoM price should be 700")

        # Cost of BoM (Table Head 1 Dozen)
        # -----------------------------------------------------------------
        # Component Cost =  Plywood Sheet   12 Unit * 200 = 2400
        #                   Bolt            60 Unit *  10 =  600
        #                   Colour          12 Unit * 100 = 1200
        #                   Corner Slide    57 Unit * 25  = 1425
        #                   Subcontracting  1 Dozen * 120 =  120
        #                                           Total = 5745
        #                          1 Unit price (5745/12) =  478.75
        # -----------------------------------------------------------------

        self.assertEqual(self.table_head.standard_price, 300, "Initial price of the Product should be 300")
        self.Product.browse([self.dining_table.id, self.table_head.id]).action_bom_cost()
        self.assertEqual(float_compare(self.table_head.standard_price, 478.75, precision_digits=2), 0, "After computing price from BoM price should be 878.75")
        self.assertEqual(float_compare(self.dining_table.standard_price, 878.75, precision_digits=2), 0, "After computing price from BoM price should be 878.75")

    def test_02_compute_price_subcontracting_cost(self):
        """Test calculation of bom cost with subcontracting and supplier in different currency."""
        currency_a = self.env['res.currency'].create({
            'name': 'ZEN',
            'symbol': 'Z',
            'rounding': 0.01,
            'currency_unit_label': 'Zenny',
            'rate_ids': [(0, 0, {
                'name': fields.Date.today(),
                'company_rate': 0.5,
            })],
        })

        partner = self.env['res.partner'].create({
            'name': 'supplier',
        })
        product = self.env['product.product'].create({
            'name': 'product',
            'is_storable': True,
            'standard_price': 100,
            'company_id': self.env.company.id,
        })
        supplier = self.env['product.supplierinfo'].create([{
                'partner_id': partner.id,
                'product_tmpl_id': product.product_tmpl_id.id,
                'price': 120.0,
                'currency_id': currency_a.id,
        }])
        self.env['mrp.bom'].create({
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'subcontract',
            'subcontractor_ids': [Command.link(partner.id)],
            'bom_line_ids': [
                (0, 0, {'product_id': self.table_head.id, 'product_qty': 1}),
            ],
        })
        self.table_head.standard_price = 100
        self.assertEqual(supplier.is_subcontractor, True)
        self.assertEqual(product.standard_price, 100, "Initial price of the Product should be 100")
        product.button_bom_cost()
        # 120 Zen = 240 USD (120 * 2)
        # price = 240 + 100 (1 unit of component "table_head") = 340
        self.assertEqual(product.standard_price, 340, "After computing price from BoM price should be 340")
