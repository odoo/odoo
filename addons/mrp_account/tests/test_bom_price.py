# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import common, Form

from odoo.tools.float_utils import float_round, float_compare


class TestBomPrice(common.TransactionCase):

    def _create_product(self, name, price):
        return self.Product.create({
            'name': name,
            'type': 'product',
            'standard_price': price,
        })

    def setUp(self):
        super(TestBomPrice, self).setUp()
        self.Product = self.env['product.product']
        self.Bom = self.env['mrp.bom']

        # Products.
        self.dining_table = self._create_product('Dining Table', 1000)
        self.table_head = self._create_product('Table Head', 300)
        self.screw = self._create_product('Screw', 10)
        self.leg = self._create_product('Leg', 25)
        self.glass = self._create_product('Glass', 100)

        # Unit of Measure.
        self.unit = self.env.ref("uom.product_uom_unit")
        self.dozen = self.env.ref("uom.product_uom_dozen")

        # Bills Of Materials.
        # -------------------------------------------------------------------------------
        # Cost of BoM (Dining Table 1 Unit)
        # Component Cost =  Table Head   1 Unit * 300 = 300 (468.75 from it's components)
        #                   Screw        5 Unit *  10 =  50
        #                   Leg          4 Unit *  25 = 100
        #                   Glass        1 Unit * 100 = 100
        # Total = 550 [718.75 if components of Table Head considered] (for 1 Unit)
        # -------------------------------------------------------------------------------

        bom_form = Form(self.Bom)
        bom_form.product_id = self.dining_table
        bom_form.product_tmpl_id = self.dining_table.product_tmpl_id
        bom_form.product_qty = 1.0
        bom_form.product_uom_id = self.unit
        bom_form.type = 'normal'
        with bom_form.bom_line_ids.new() as line:
            line.product_id = self.table_head
            line.product_qty = 1
        with bom_form.bom_line_ids.new() as line:
            line.product_id = self.screw
            line.product_qty = 5
        with bom_form.bom_line_ids.new() as line:
            line.product_id = self.leg
            line.product_qty = 4
        with bom_form.bom_line_ids.new() as line:
            line.product_id = self.glass
            line.product_qty = 1
        self.bom_1 = bom_form.save()

        # Table Head's components.
        self.plywood_sheet = self._create_product('Plywood Sheet', 200)
        self.bolt = self._create_product('Bolt', 10)
        self.colour = self._create_product('Colour', 100)
        self.corner_slide = self._create_product('Corner Slide', 25)

        # -----------------------------------------------------------------
        # Cost of BoM (Table Head 1 Dozen)
        # Component Cost =  Plywood Sheet   12 Unit * 200 = 2400
        #                   Bolt            60 Unit *  10 =  600
        #                   Colour          12 Unit * 100 = 1200
        #                   Corner Slide    57 Unit * 25  = 1425
        #                                           Total = 5625
        #                          1 Unit price (5625/12) =  468.75
        # -----------------------------------------------------------------

        bom_form2 = Form(self.Bom)
        bom_form2.product_id = self.table_head
        bom_form2.product_tmpl_id = self.table_head.product_tmpl_id
        bom_form2.product_qty = 1.0
        bom_form2.product_uom_id = self.dozen
        bom_form2.type = 'phantom'
        with bom_form2.bom_line_ids.new() as line:
            line.product_id = self.plywood_sheet
            line.product_qty = 12
        with bom_form2.bom_line_ids.new() as line:
            line.product_id = self.bolt
            line.product_qty = 60
        with bom_form2.bom_line_ids.new() as line:
            line.product_id = self.colour
            line.product_qty = 12
        with bom_form2.bom_line_ids.new() as line:
            line.product_id = self.corner_slide
            line.product_qty = 57
        self.bom_2 = bom_form2.save()

    def test_00_compute_price(self):
        """Test multi-level BoM cost"""
        self.assertEqual(self.dining_table.standard_price, 1000, "Initial price of the Product should be 1000")
        self.dining_table.button_bom_cost()
        self.assertEqual(self.dining_table.standard_price, 550, "After computing price from BoM price should be 550")

    def test_01_compute_price_operation_cost(self):
        """Test calcuation of bom cost with operations."""
        workcenter_from1 = Form(self.env['mrp.workcenter'])
        workcenter_from1.name = 'Workcenter'
        workcenter_from1.time_efficiency = 80
        workcenter_from1.capacity = 2
        workcenter_from1.oee_target = 100
        workcenter_from1.time_start = 15
        workcenter_from1.time_stop = 15
        workcenter_from1.costs_hour = 100
        workcenter_1 = workcenter_from1.save()

        self.bom_1.write({
            'operation_ids': [
                (0, 0, {
                    'name': 'Cutting',
                    'workcenter_id': workcenter_1.id,
                    'time_mode': 'manual',
                    'time_cycle_manual': 20,
                    'sequence': 1,
                }),
                (0, 0, {
                    'name': 'Drilling',
                    'workcenter_id': workcenter_1.id,
                    'time_mode': 'manual',
                    'time_cycle_manual': 25,
                    'sequence': 2,
                }),
                (0, 0, {
                    'name': 'Fitting',
                    'workcenter_id': workcenter_1.id,
                    'time_mode': 'manual',
                    'time_cycle_manual': 30,
                    'sequence': 3,
                }),
            ],
        }),
        self.bom_2.write({
            'operation_ids': [
                (0, 0, {
                    'name': 'Cutting',
                    'workcenter_id': workcenter_1.id,
                    'time_mode': 'manual',
                    'time_cycle_manual': 20,
                    'sequence': 1,
                }),
                (0, 0, {
                    'name': 'Drilling',
                    'workcenter_id': workcenter_1.id,
                    'time_mode': 'manual',
                    'time_cycle_manual': 25,
                    'sequence': 2,
                }),
                (0, 0, {
                    'name': 'Fitting',
                    'workcenter_id': workcenter_1.id,
                    'time_mode': 'manual',
                    'time_cycle_manual': 30,
                    'sequence': 3,
                }),
            ],
        }),


        # -----------------------------------------------------------------
        # Dinning Table Operation Cost(1 Unit)
        # -----------------------------------------------------------------
        # Operation cost calculate for 1 units
        # Cutting        (15 + 15 + (20 * 100/80) / 60) * 100 =   91.67
        # Drilling       (15 + 15 + (25 * 100/80) / 60) * 100 =  102.08
        # Fitting        (15 + 15 + (30 * 100/80) / 60) * 100 =  112.50
        # ----------------------------------------
        # Operation Cost  1 unit = 306.25
        # -----------------------------------------------------------------


        # --------------------------------------------------------------------------
        # Table Head Operation Cost (1 Dozen)
        # --------------------------------------------------------------------------
        # Operation cost calculate for 1 dozens
        # Cutting        (15 + 15 + (20 * 1 * 100/80) / 60) * 100 =   91.67
        # Drilling       (15 + 15 + (25 * 1 * 100/80) / 60) * 100 =  102.08
        # Fitting        (15 + 15 + (30 * 1 * 100/80) / 60) * 100 =  112.50
        # ----------------------------------------
        # Operation Cost 1 dozen (306.25 per dozen) and 25.52 for 1 Unit
        # --------------------------------------------------------------------------


        self.assertEqual(self.dining_table.standard_price, 1000, "Initial price of the Product should be 1000")
        self.dining_table.button_bom_cost()
        # Total cost of Dining Table = (550) + Total cost of operations (306.25) = 856.25
        self.assertEqual(float_round(self.dining_table.standard_price, precision_digits=2), 856.25, "After computing price from BoM price should be 856.25")
        self.Product.browse([self.dining_table.id, self.table_head.id]).action_bom_cost()
        # Total cost of Dining Table = (718.75) + Total cost of all operations (306.25 + 25.52) = 1050.52
        self.assertEqual(float_compare(self.dining_table.standard_price, 1050.52, precision_digits=2), 0, "After computing price from BoM price should be 1050.52")

    def test_02_compute_byproduct_price(self):
        """Test BoM cost when byproducts with cost share"""
        # byproduct
        scrap_wood = self._create_product('Scrap Wood', 30)

        # different byproduct line uoms => 20 total units with a total of 75% of cost share
        self.bom_1.write({
            'byproduct_ids': [
                (0, 0, {
                    'product_id': scrap_wood.id,
                    'product_uom_id': self.unit.id,
                    'product_qty': 8,
                    'bom_id': self.bom_1.id,
                    'cost_share': 25,
                }),
                (0, 0, {
                    'product_id': scrap_wood.id,
                    'product_uom_id': self.dozen.id,
                    'product_qty': 1,
                    'bom_id': self.bom_1.id,
                    'cost_share': 50,
                }),
            ],
        }),

        # Cost Breakdown.
        # -------------------------------------------------------------------------------
        # Total Cost of BoM = 550 [718.75 if components of Table Head considered] (for 1 Unit)
        # Dining Table 1 Unit = 1 - (25 + 50) / 100 * 550 = 0.25 * 550 = 137.5
        # Scrap Wood 1 Unit = (25 + 50) / 100 * 550 / (8 units + 12 units) = 20.625
        # -------------------------------------------------------------------------------

        self.assertEqual(self.dining_table.standard_price, 1000, "Initial price of the Product should be 1000")
        self.assertEqual(scrap_wood.standard_price, 30, "Initial price of the By-Product should be 30")
        self.dining_table.button_bom_cost()
        self.assertEqual(self.dining_table.standard_price, 137.5, "After computing price from BoM price should be 137.5")
        scrap_wood.button_bom_cost()
        self.assertEqual(scrap_wood.standard_price, 20.63, "After computing price from BoM price should be 20.63")
