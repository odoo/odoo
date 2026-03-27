# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields
from odoo.tests import Form, tagged
from odoo.tools.float_utils import float_round, float_compare

from odoo.addons.mrp_account.tests.common import TestBomPriceCommon
from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon
from odoo.addons.stock_account.tests.common import TestStockValuationCommon


@tagged('post_install', '-at_install')
class TestAccountSubcontractingFlows(TestMrpSubcontractingCommon, TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_production = cls.env['account.account'].create({
            'name': 'Production Account',
            'code': '100102',
            'account_type': 'asset_current',
        })
        cls.prod_location = cls.env['stock.location'].search([('usage', '=', 'production'), ('company_id', '=', cls.company.id)])
        cls.prod_location.valuation_account_id = cls.account_production.id
        cls.comp1.standard_price = 10.0
        cls.comp2.standard_price = 20.0

    def test_subcontracting_account_flow_1(self):
        (self.comp1 | self.comp2 | self.finished).categ_id = self.category_fifo_auto
        self._make_in_move(self.comp1, 10, unit_cost=10, location_dest_id=self.env.company.subcontracting_location_id.id)
        self._make_in_move(self.comp2, 10, unit_cost=20, location_dest_id=self.env.company.subcontracting_location_id.id)
        all_amls_ids = self.env['account.move.line'].search([]).ids

        move = self._make_in_move(
            self.finished,
            1,
            unit_cost=30,
            create_picking=True,
            partner_id=self.subcontractor_partner1.id,
        )

        picking_receipt = move.picking_id
        mo1 = move.picking_id._get_subcontract_production()
        # Finished is made of 1 comp1 and 1 comp2.
        # Cost of comp1 = 10
        # Cost of comp2 = 20
        # --> Cost of finished = 10 + 20 = 30
        # Additionnal cost = 30 (from the purchase order line or directly set on the stock move here)
        # Total cost of subcontracting 1 unit of finished = 30 + 30 = 60
        # Account move lines of the mo should only take components into account. The bill will take care of the extra cost.
        self.assertEqual(mo1.move_finished_ids.value, 60)
        self.assertEqual(picking_receipt.move_ids.value, 0)
        self.assertEqual(picking_receipt.move_ids.product_id.total_value, 60)

        amls = self.env['account.move.line'].search([('id', 'not in', all_amls_ids)])
        all_amls_ids += amls.ids
        # stock valo only 30 because the extra can only be added with a bill
        self.assertRecordValues(amls.sorted('product_id'), [
            # Delivery com1 to subcontractor
            {'account_id': self.account_stock_valuation.id,   'product_id': self.comp1.id,       'debit': 0.0,   'credit': 10.0},
            {'account_id': self.account_production.id,    'product_id': self.comp1.id,       'debit': 10.0,  'credit': 0.0},
            # Delivery com2 to subcontractor
            {'account_id': self.account_stock_valuation.id,   'product_id': self.comp2.id,       'debit': 0.0,   'credit': 20.0},
            {'account_id': self.account_production.id,    'product_id': self.comp2.id,       'debit': 20.0,  'credit': 0.0},
            # Receipt from subcontractor
            {'account_id': self.account_production.id,    'product_id': self.finished.id,    'debit': 0.0,   'credit': 30.0},
            {'account_id': self.account_stock_valuation.id,   'product_id': self.finished.id,    'debit': 30.0, 'credit': 0.0},
        ])

        # Validate the bill from the subcontractor
        scrap = self.env['stock.scrap'].create({
            'product_id': self.finished.id,
            'product_uom_id': self.finished.uom_id.id,
            'scrap_qty': 1,
            'production_id': mo1.id,
            'location_id': self.stock_location.id,
        })
        scrap.do_scrap()

        self.assertEqual(self.finished.total_value, 0)

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
        self.finished.categ_id = self.category_fifo

        picking_receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_in.id,
            'partner_id': self.subcontractor_partner1.id,
            'move_ids': [Command.create({
                'product_id': self.finished.id,
                'product_uom_qty': todo_nb,
                'price_unit': 50,
            })],
        })
        picking_receipt.action_confirm()
        picking_receipt.do_unreserve()

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

        action = picking_receipt.move_ids.action_show_details()
        with Form(picking_receipt.move_ids.with_context(action['context']), view=action['view_id']) as move_form:
            for serial in serials_finished:
                with move_form.move_line_ids.new() as move_line:
                    move_line.lot_id = serial
                    move_line.picked = True
                    move_line.quantity = 1
            move_form.save()

        for mo, compo_1_serial in zip(picking_receipt._get_subcontract_production(), serials_comp1):
            action = mo.move_raw_ids[0].action_show_details()
            with Form(mo.move_raw_ids[0].with_context(action['context']), view=action['view_id']) as move_form:
                with move_form.move_line_ids.new() as move_line:
                    self.assertEqual(move_line.product_id, self.comp1)
                    move_line.lot_id = compo_1_serial
                    move_line.picked = True
                    move_line.quantity = 1
                move_form.save()
            action = mo.move_raw_ids[1].action_show_details()
            with Form(mo.move_raw_ids[1].with_context(action['context']), view=action['view_id']) as move_form:
                with move_form.move_line_ids.new() as move_line:
                    self.assertEqual(move_line.product_id, self.comp2)
                    move_line.lot_id = lot_comp2
                    move_line.picked = True
                    move_line.quantity = 1
                move_form.save()

        # We should not be able to call the 'record_components' button
        picking_receipt.move_ids.picked = True
        picking_receipt.button_validate()
        self.assertEqual(picking_receipt.state, 'done')

        f_move = self.env['stock.move'].search([(
            'product_id', '=', self.finished.id,
        )])
        self.assertEqual(len(f_move), 5)
        self.assertRecordValues(f_move, [
            {'is_in': False, 'value': 0, 'quantity': 4},
            {'is_in': True, 'value': 160, 'quantity': 1},
            {'is_in': True, 'value': 160, 'quantity': 1},
            {'is_in': True, 'value': 160, 'quantity': 1},
            {'is_in': True, 'value': 160, 'quantity': 1},
        ])

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

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_in.id,
            'partner_id': self.subcontractor_partner1.id,
            'move_ids': [Command.create({
                'product_id': self.finished.id,
                'product_uom_qty': 10,
                'price_unit': 50,
            })],
        })
        receipt.action_confirm()

        for qty_producing in (5, 3, 2):
            receipt.move_ids.quantity = qty_producing
            mo = receipt._get_subcontract_production()
            action = mo.move_raw_ids[0].action_show_details()
            with Form(mo.move_raw_ids[0].with_context(action['context']), view=action['view_id']) as move_form:
                with move_form.move_line_ids.new() as move_line:
                    move_line.lot_id = lot01
                    move_line.quantity = qty_producing
                move_form.save()
            action = mo.move_raw_ids[1].action_show_details()
            with Form(mo.move_raw_ids[1].with_context(action['context']), view=action['view_id']) as move_form:
                with move_form.move_line_ids.new() as move_line:
                    move_line.lot_id = lot02
                    move_line.quantity = qty_producing
                move_form.save()
            action = receipt.button_validate()
            if isinstance(action, dict):
                Form.from_action(self.env, action).save().process()
                receipt = receipt.backorder_ids

        f_move = self.env['stock.move'].search([(
            'product_id', '=', self.finished.id,
        )])
        self.assertRecordValues(f_move, [
            {'quantity': 5, 'value': 0, 'state': 'done'},
            {'quantity': 5, 'value': 5 * (10 + 20 + 50), 'state': 'done'},
            {'quantity': 3, 'value': 0, 'state': 'done'},
            {'quantity': 3, 'value': 3 * (10 + 20 + 50), 'state': 'done'},
            {'quantity': 2, 'value': 0, 'state': 'done'},
            {'quantity': 2, 'value': 2 * (10 + 20 + 50), 'state': 'done'},
        ])

    def test_subcontract_cost_different_when_standard_price(self):
        """Test when subcontracting with standard price when
            Final product cost != Components cost + Subcontracting cost
        When posting the account entries for receiving final product, the
        subcontracting cost will be adjusted based on the difference of the cost.
        """
        (self.comp1 | self.comp2 | self.finished).categ_id = self.category_standard_auto
        self.comp1.standard_price = 10
        self.comp2.standard_price = 20
        self.finished.standard_price = 40

        all_amls_ids = self.env['account.move.line'].search([]).ids

        self._make_in_move(self.finished, 1, unit_cost=15,
                           create_picking=True,
                           partner_id=self.subcontractor_partner1.id)

        amls = self.env['account.move.line'].search([('id', 'not in', all_amls_ids)])
        self.assertRecordValues(amls.sorted("account_id, product_id"), [
            # Receipt from subcontractor
            {'account_id': self.account_production.id,    'product_id': self.comp1.id,       'debit': 10.0,  'credit': 0.0},
            {'account_id': self.account_production.id,    'product_id': self.comp2.id,       'debit': 20.0,  'credit': 0.0},
            {'account_id': self.account_production.id,    'product_id': self.finished.id,    'debit': 0.0,   'credit': 40.0},
            {'account_id': self.account_stock_valuation.id,   'product_id': self.comp1.id,       'debit': 0.0,   'credit': 10.0},
            {'account_id': self.account_stock_valuation.id,   'product_id': self.comp2.id,       'debit': 0.0,   'credit': 20.0},
            {'account_id': self.account_stock_valuation.id,   'product_id': self.finished.id,    'debit': 40.0,  'credit': 0.0},
        ])

    def test_subcontract_without_prod_account(self):
        """
        Test that the production stock account is optional, and we will fallback on input/output accounts.
        """
        (self.comp1 | self.comp2 | self.finished).categ_id = self.category_fifo_auto
        self.comp1.standard_price = 1.0
        self.prod_location.valuation_account_id = False
        all_amls_ids = self.env['account.move.line'].search([]).ids
        self._make_in_move(self.finished, 1, create_picking=True,
                                             partner_id=self.subcontractor_partner1.id).picking_id

        amls = self.env['account.move.line'].search([('id', 'not in', all_amls_ids)])
        # Check that no account move line are created if there is no production account
        self.assertFalse(amls)


class TestSubcontractingBOMCost(TestBomPriceCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'A name can be a Many2one...'
        })
        (cls.bom_1 | cls.bom_2).write({
            'type': 'subcontract',
            'subcontractor_ids': [Command.link(cls.partner.id)],
        })

    def test_01_compute_price_subcontracting_cost(self):
        """Test calculation of bom cost with subcontracting."""
        suppliers = self.env['product.supplierinfo'].create([
            {
                'partner_id': self.partner.id,
                'product_tmpl_id': self.dining_table.product_tmpl_id.id,
                'price': 150.0,
            }, {
                'partner_id': self.partner.id,
                'product_tmpl_id': self.table_head.product_tmpl_id.id,
                'price': 120.0,
                'product_uom_id': self.dozen.id,
            },
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
            'rate_ids': [Command.create({
                'name': fields.Date.today(),
                'company_rate': 0.5,
            })],
        })

        self.env['product.supplierinfo'].create([{
                'partner_id': self.partner.id,
                'product_tmpl_id': self.dining_table.product_tmpl_id.id,
                'price': 120.0,
                'currency_id': currency_a.id,
        }])
        self.assertEqual(self.dining_table.standard_price, 1000)
        self.dining_table.button_bom_cost()
        self.assertEqual(self.dining_table.standard_price, 790)
