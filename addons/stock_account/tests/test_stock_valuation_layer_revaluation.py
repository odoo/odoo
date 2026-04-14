# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.addons.stock_account.tests.test_stockvaluation import _create_accounting_data
from odoo.addons.stock_account.tests.test_stockvaluationlayer import TestStockValuationCommon


class TestStockValuationLayerRevaluation(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super(TestStockValuationLayerRevaluation, cls).setUpClass()
        cls.stock_input_account, cls.stock_output_account, cls.stock_valuation_account, cls.expense_account, cls.stock_journal = _create_accounting_data(cls.env)
        cls.product1.write({
            'property_account_expense_id': cls.expense_account.id,
        })
        cls.product1.categ_id.write({
            'property_valuation': 'real_time',
            'property_stock_account_input_categ_id': cls.stock_input_account.id,
            'property_stock_account_output_categ_id': cls.stock_output_account.id,
            'property_stock_valuation_account_id': cls.stock_valuation_account.id,
            'property_stock_journal': cls.stock_journal.id,
        })

        cls.product1.categ_id.property_valuation = 'real_time'

    def test_stock_valuation_layer_revaluation_avco(self):
        self.product1.categ_id.property_cost_method = 'average'
        context = {
            'default_product_id': self.product1.id,
            'default_company_id': self.env.company.id,
            'default_added_value': 0.0
        }
        # Quantity of product1 is zero, raise
        with self.assertRaises(UserError):
            Form(self.env['stock.valuation.layer.revaluation'].with_context(context)).save()

        self._make_in_move(self.product1, 10, unit_cost=2)
        self._make_in_move(self.product1, 10, unit_cost=4)

        self.assertEqual(self.product1.standard_price, 3)
        self.assertEqual(self.product1.quantity_svl, 20)

        old_layers = self.env['stock.valuation.layer'].search([('product_id', '=', self.product1.id)], order="create_date desc, id desc")

        self.assertEqual(len(old_layers), 2)
        self.assertEqual(old_layers[0].remaining_value, 40)

        revaluation_wizard = Form(self.env['stock.valuation.layer.revaluation'].with_context(context))
        revaluation_wizard.added_value = 20
        revaluation_wizard.account_id = self.stock_valuation_account
        revaluation_wizard.save().action_validate_revaluation()

        # Check standard price change
        self.assertEqual(self.product1.standard_price, 4)
        self.assertEqual(self.product1.quantity_svl, 20)

        # Check the creation of stock.valuation.layer
        new_layer = self.env['stock.valuation.layer'].search([('product_id', '=', self.product1.id)], order="create_date desc, id desc", limit=1)
        self.assertEqual(new_layer.value, 20)

        # Check the remaing value of current layers
        self.assertEqual(old_layers[0].remaining_value, 50)
        self.assertEqual(sum(slv.remaining_value for slv in old_layers), 80)

        # Check account move
        self.assertTrue(bool(new_layer.account_move_id))
        self.assertEqual(len(new_layer.account_move_id.line_ids), 2)

        self.assertEqual(sum(new_layer.account_move_id.line_ids.mapped("debit")), 20)
        self.assertEqual(sum(new_layer.account_move_id.line_ids.mapped("credit")), 20)

        credit_lines = [l for l in new_layer.account_move_id.line_ids if l.credit > 0]
        self.assertEqual(len(credit_lines), 1)
        self.assertEqual(credit_lines[0].account_id.id, self.stock_valuation_account.id)

    def test_stock_valuation_layer_revaluation_avco_rounding(self):
        self.product1.categ_id.property_cost_method = 'average'
        context = {
            'default_product_id': self.product1.id,
            'default_company_id': self.env.company.id,
            'default_added_value': 0.0
        }
        # Quantity of product1 is zero, raise
        with self.assertRaises(UserError):
            Form(self.env['stock.valuation.layer.revaluation'].with_context(context)).save()

        self._make_in_move(self.product1, 1, unit_cost=1)
        self._make_in_move(self.product1, 1, unit_cost=1)
        self._make_in_move(self.product1, 1, unit_cost=1)

        self.assertEqual(self.product1.standard_price, 1)
        self.assertEqual(self.product1.quantity_svl, 3)

        old_layers = self.env['stock.valuation.layer'].search([('product_id', '=', self.product1.id)], order="create_date desc, id desc")

        self.assertEqual(len(old_layers), 3)
        self.assertEqual(old_layers[0].remaining_value, 1)

        revaluation_wizard = Form(self.env['stock.valuation.layer.revaluation'].with_context(context))
        revaluation_wizard.added_value = 1
        revaluation_wizard.account_id = self.stock_valuation_account
        revaluation_wizard.save().action_validate_revaluation()

        # Check standard price change
        self.assertEqual(self.product1.standard_price, 1.33)
        self.assertEqual(self.product1.quantity_svl, 3)

        # Check the creation of stock.valuation.layer
        new_layer = self.env['stock.valuation.layer'].search([('product_id', '=', self.product1.id)], order="create_date desc, id desc", limit=1)
        self.assertEqual(new_layer.value, 1)

        # Check the remaing value of current layers
        self.assertEqual(sum(slv.remaining_value for slv in old_layers), 4)
        self.assertTrue(1.34 in old_layers.mapped("remaining_value"))

        # Check account move
        self.assertTrue(bool(new_layer.account_move_id))
        self.assertEqual(len(new_layer.account_move_id.line_ids), 2)

        self.assertEqual(sum(new_layer.account_move_id.line_ids.mapped("debit")), 1)
        self.assertEqual(sum(new_layer.account_move_id.line_ids.mapped("credit")), 1)

        credit_lines = [l for l in new_layer.account_move_id.line_ids if l.credit > 0]
        self.assertEqual(len(credit_lines), 1)
        self.assertEqual(credit_lines[0].account_id.id, self.stock_valuation_account.id)

    def test_stock_valuation_layer_revaluation_avco_rounding_2_digits(self):
        """
        Check that the rounding of the new price (cost) is equivalent to the rounding of the standard price (cost)
        The check is done indirectly via the layers valuations.
        If correct => rounding method is correct too
        """
        self.product1.categ_id.property_cost_method = 'average'

        self.env['decimal.precision'].search([
            ('name', '=', 'Product Price'),
        ]).digits = 2
        self.product1.write({'standard_price': 0})

        # First Move
        self.product1.write({'standard_price': 0.022})
        self._make_in_move(self.product1, 10000)

        self.assertEqual(self.product1.standard_price, 0.02)
        self.assertEqual(self.product1.quantity_svl, 10000)

        layer = self.product1.stock_valuation_layer_ids
        self.assertEqual(layer.value, 200)

        # Second Move
        self.product1.write({'standard_price': 0.053})

        self.assertEqual(self.product1.standard_price, 0.05)
        self.assertEqual(self.product1.quantity_svl, 10000)

        layers = self.product1.stock_valuation_layer_ids
        self.assertEqual(layers[0].value, 200)
        self.assertEqual(layers[1].value, 300)

    def test_stock_valuation_layer_revaluation_avco_rounding_5_digits(self):
        """
        Check that the rounding of the new price (cost) is equivalent to the rounding of the standard price (cost)
        The check is done indirectly via the layers valuations.
        If correct => rounding method is correct too
        """
        self.product1.categ_id.property_cost_method = 'average'

        self.env['decimal.precision'].search([
            ('name', '=', 'Product Price'),
        ]).digits = 5

        # First Move
        self.product1.write({'standard_price': 0.00875})
        self._make_in_move(self.product1, 10000)

        self.assertEqual(self.product1.standard_price, 0.00875)
        self.assertEqual(self.product1.quantity_svl, 10000)

        layer = self.product1.stock_valuation_layer_ids
        self.assertEqual(layer.value, 87.5)

        # Second Move
        self.product1.write({'standard_price': 0.00975})

        self.assertEqual(self.product1.standard_price, 0.00975)
        self.assertEqual(self.product1.quantity_svl, 10000)

        layers = self.product1.stock_valuation_layer_ids
        self.assertEqual(layers[0].value, 87.5)
        self.assertEqual(layers[1].value, 10)

    def test_stock_valuation_layer_revaluation_fifo(self):
        self.product1.categ_id.property_cost_method = 'fifo'
        context = {
            'default_product_id': self.product1.id,
            'default_company_id': self.env.company.id,
            'default_added_value': 0.0
        }
        # Quantity of product1 is zero, raise
        with self.assertRaises(UserError):
            Form(self.env['stock.valuation.layer.revaluation'].with_context(context)).save()

        self._make_in_move(self.product1, 10, unit_cost=2)
        self._make_in_move(self.product1, 10, unit_cost=4)

        self.assertEqual(self.product1.standard_price, 3)
        self.assertEqual(self.product1.quantity_svl, 20)

        old_layers = self.env['stock.valuation.layer'].search([('product_id', '=', self.product1.id)], order="create_date desc, id desc")

        self.assertEqual(len(old_layers), 2)
        self.assertEqual(old_layers[0].remaining_value, 40)

        revaluation_wizard = Form(self.env['stock.valuation.layer.revaluation'].with_context(context))
        revaluation_wizard.added_value = 20
        revaluation_wizard.account_id = self.stock_valuation_account
        revaluation_wizard.save().action_validate_revaluation()

        self.assertEqual(self.product1.standard_price, 4)

        # Check the creation of stock.valuation.layer
        new_layer = self.env['stock.valuation.layer'].search([('product_id', '=', self.product1.id)], order="create_date desc, id desc", limit=1)
        self.assertEqual(new_layer.value, 20)

        # Check the remaing value of current layers
        self.assertEqual(old_layers[0].remaining_value, 50)
        self.assertEqual(sum(slv.remaining_value for slv in old_layers), 80)

        # Check account move
        self.assertTrue(bool(new_layer.account_move_id))
        self.assertTrue(len(new_layer.account_move_id.line_ids), 2)

        self.assertEqual(sum(new_layer.account_move_id.line_ids.mapped("debit")), 20)
        self.assertEqual(sum(new_layer.account_move_id.line_ids.mapped("credit")), 20)

        credit_lines = [l for l in new_layer.account_move_id.line_ids if l.credit > 0]
        self.assertEqual(len(credit_lines), 1)

    def test_stock_valuation_layer_revaluation_fifo_rounding_2_digits(self):
        """ make sure that the rounding in the wizard does not incur a negative remaining value
        """

        self.product1.categ_id.property_cost_method = 'fifo'
        context = {
            'default_product_id': self.product1.id,
            'default_company_id': self.env.company.id,
            'default_added_value': 0.0
        }

        self._make_in_move(self.product1, 67104, unit_cost=0.00952)
        self._make_in_move(self.product1, 898, unit_cost=0.00952)

        self.assertEqual(self.product1.standard_price, 0.01)
        revaluation_wizard = Form(self.env['stock.valuation.layer.revaluation'].with_context(context))
        revaluation_wizard.added_value = 636  # triggers the rounding problem
        revaluation_wizard.account_id = self.stock_valuation_account
        revaluation_wizard.save().action_validate_revaluation()

        self.assertEqual(self.product1.standard_price, 0.02)

    def test_fifo_vacuum_anglo_saxon_expense_entry_multicompany(self):
        """ The anglo-saxon expense revaluation JE created by the FIFO vacuum
        must be posted in the SVL's company, regardless of env.company.
        """
        company_a = self.env.company
        company_b = self.env['res.company'].create({'name': 'Company B'})
        self.env.user.write({'company_ids': [Command.link(company_b.id)]})
        (company_a + company_b).write({'anglo_saxon_accounting': True})
        in_b, out_b, val_b, exp_b, journal_b = _create_accounting_data(
            self.env(context={**self.env.context, 'allowed_company_ids': [company_b.id]}))

        self.product1.categ_id.with_company(company_b).write({
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
            'property_stock_account_input_categ_id': in_b.id,
            'property_stock_account_output_categ_id': out_b.id,
            'property_stock_valuation_account_id': val_b.id,
            'property_stock_journal': journal_b.id,
        })
        self.product1.product_tmpl_id.with_company(company_b).write({
            'property_account_expense_id': exp_b.id,
        })
        self.product1.with_company(company_b).standard_price = 10.0
        wh_b = self.env['stock.warehouse'].search([('company_id', '=', company_b.id)], limit=1)
        customer_loc_b = self.env['stock.location'].search(
            [('usage', '=', 'customer'), ('company_id', '=', company_b.id)], limit=1
        ) or self.customer_location

        # Out move in B -> negative SVL.
        out_move = self.env['stock.move'].with_company(company_b).create({
            'name': 'out 1', 'product_id': self.product1.id,
            'location_id': wh_b.lot_stock_id.id, 'location_dest_id': customer_loc_b.id,
            'product_uom': self.uom_unit.id, 'product_uom_qty': 1.0,
            'picking_type_id': wh_b.out_type_id.id,
        })
        out_move._action_confirm()
        self.env['stock.move.line'].create({
            'move_id': out_move.id, 'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id, 'quantity': 1.0,
            'location_id': wh_b.lot_stock_id.id, 'location_dest_id': customer_loc_b.id,
        })
        out_move.picked = True
        out_move._action_done()
        self.assertEqual(out_move.stock_valuation_layer_ids.company_id, company_b)

        # Reconcile the SVL's stock_output line with an invoice JE
        fake_invoice = self.env['account.move'].create({
            'move_type': 'entry',
            'company_id': company_b.id,
            'journal_id': journal_b.id,
            'line_ids': [
                Command.create({'account_id': exp_b.id, 'debit': 10, 'credit': 0}),
                Command.create({'account_id': out_b.id, 'debit': 0, 'credit': 10}),
            ],
        })
        fake_invoice.action_post()
        (out_move.stock_valuation_layer_ids.account_move_id.line_ids + fake_invoice.line_ids
         ).filtered(lambda l: l.account_id == out_b).reconcile()

        # In move in B while env.company = A -> triggers the vacuum.
        self.assertEqual(self.env.company, company_a)
        in_move = self.env['stock.move'].create({
            'name': 'in 1', 'product_id': self.product1.id,
            'location_id': self.supplier_location.id, 'location_dest_id': wh_b.lot_stock_id.id,
            'product_uom': self.uom_unit.id, 'product_uom_qty': 1.0,
            'price_unit': 15.0, 'picking_type_id': wh_b.in_type_id.id,
            'company_id': company_b.id,
        })
        in_move._action_confirm()
        in_move.write({'quantity': 1.0, 'picked': True})
        in_move._action_done()

        revaluation_je = self.env['account.move'].search([
            ('ref', 'like', 'Expenses Revaluation of%'),
            ('stock_move_id', '=', out_move.id),
        ])
        self.assertTrue(revaluation_je)
        self.assertEqual(revaluation_je.company_id, company_b)

    def test_multi_company_fifo_svl_negative_revaluation(self):
        """
        Check that the journal entries and stock valuation layers are created for the company related
        to the stock move even if the picking is validated using a different one.
        """
        company1 = self.env.company
        company2 = self.env['res.company'].create({
            'name': 'Lovely Company',
        })
        self.env.companies = company1 | company2

        product = self.product1
        product.categ_id.write({
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
        })
        # Modify valuation to manual_periodic for company2
        product.categ_id.with_company(company2).property_valuation = 'manual_periodic'

        # Create moves to revaluate for company1
        self._make_in_move(product, 10, unit_cost=10, create_picking=True)
        self._make_out_move(product, 15, create_picking=True)

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'move_ids': [Command.create({
                'name': 'test fifo',
                'product_id': product.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 10,
                'price_unit': 7,
            })]
        }).with_company(company2)
        receipt.action_confirm()
        receipt.button_validate()

        svls = self.env['stock.valuation.layer'].search([('product_id', '=', product.id)])
        self.assertEqual(len(svls), 4, "Expected 4 valuation layers")
        self.assertTrue(all(svl.account_move_id for svl in svls), "All SVLs should be linked to a journal entry")
