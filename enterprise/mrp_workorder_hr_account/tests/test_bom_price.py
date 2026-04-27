# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tools.float_utils import float_round, float_compare
from odoo.addons.mrp_account.tests.test_bom_price import TestBomPriceCommon


class TestBomPrice(TestBomPriceCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # -----------------------------------------------------------------
        # Dinning Table Operation Cost(1 Unit)
        # -----------------------------------------------------------------
        # Operation cost calculate for 1 units
        # Cutting        (15 + 15 + (20 * 100/80) / 60) * (100 + 200) =  275.01
        # Drilling       (15 + 15 + (25 * 100/80) / 60) * (100 + 200) =  306.24
        # Fitting        (15 + 15 + (30 * 100/80) / 60) * (100 + 200) =  337.50
        # ----------------------------------------
        # Operation Cost  1 unit = 918,75
        # -----------------------------------------------------------------


        # --------------------------------------------------------------------------
        # Table Head Operation Cost (1 Dozen)
        # --------------------------------------------------------------------------
        # Operation cost calculate for 1 dozens
        # Cutting        (15 + 15 + (20 * 1 * 100/80) / 60) * (100 + 200) =  275.01
        # Drilling       (15 + 15 + (25 * 1 * 100/80) / 60) * (100 + 200) =  306.24
        # Fitting        (15 + 15 + (30 * 1 * 100/80) / 60) * (100 + 200) =  337.50
        # ----------------------------------------
        # Operation Cost 1 dozen (918,75 per dozen) and 76.56 for 1 Unit
        # --------------------------------------------------------------------------
        workcenter_from1 = Form(cls.env['mrp.workcenter'])
        workcenter_from1.name = 'Workcenter'
        workcenter_from1.time_efficiency = 80
        workcenter_from1.default_capacity = 2
        workcenter_from1.oee_target = 100
        workcenter_from1.time_start = 15
        workcenter_from1.time_stop = 15
        workcenter_from1.costs_hour = 100
        workcenter_from1.employee_costs_hour = 200
        workcenter_1 = workcenter_from1.save()
        cls.bom_1.write({
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
        cls.bom_2.write({
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

    def test_compute_price_operation_cost_hr_01(self):
        self.assertEqual(self.dining_table.standard_price, 1000, "Initial price of the Product should be 1000")
        self.dining_table.button_bom_cost()
        # Total cost of Dining Table = (550) + Total cost of operations (918,75) = 1468,75
        self.assertEqual(float_round(self.dining_table.standard_price, precision_digits=2), 1468.75, "After computing price from BoM price should be 1468.75")
        self.Product.browse([self.dining_table.id, self.table_head.id]).action_bom_cost()
        # Total cost of Dining Table = (718.75) + Total cost of all operations (918,75 + 76.56) = 1714.06
        self.assertEqual(float_compare(self.dining_table.standard_price, 1714.06, precision_digits=2), 0, "After computing price from BoM price should be 1714.06")
