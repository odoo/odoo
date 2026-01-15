# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, Form
from odoo.addons.stock_account.tests.common import TestStockValuationCommon


@tagged('-at_install', 'post_install')
class TestBomPriceCommon(TestStockValuationCommon):

    @classmethod
    def _create_product(cls, name, price, quantity=100, category=None):
        vals = {
            'name': name,
            'is_storable': True,
            'standard_price': price,
            'qty_available': quantity,
        }
        if category:
            vals['categ_id'] = category.id
        return cls.Product.create(vals)

    @classmethod
    def _create_mo(cls, bom, quantity, confirm=True):
        mo = cls.env['mrp.production'].create({
            'product_id': bom.product_id.id,
            'bom_id': bom.id,
            'product_qty': quantity,
        })
        if confirm:
            mo.action_confirm()
        return mo

    @classmethod
    def _produce(cls, mo, quantity=0):
        mo_form = Form(mo)
        if not quantity:
            quantity = mo.product_qty - mo.qty_produced
        mo_form.qty_producing += quantity
        return mo_form.save()

    @classmethod
    def _use_production_accounting(cls):
        cls.account_production = cls.env['account.account'].create({
            'name': 'Production Account',
            'code': '100102',
            'account_type': 'asset_current',
        })
        production_locations = cls.env['stock.location'].search([('usage', '=', 'production'), ('company_id', '=', cls.company.id)])
        production_locations.valuation_account_id = cls.account_production.id
        return cls.account_production

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Required for `product_uom_id ` to be visible in the view
        cls.env.user.group_ids += cls.env.ref('uom.group_uom')
        # Required for `product_id ` to be visible in the view
        cls.env.user.group_ids += cls.env.ref('product.group_product_variant')
        cls.Product = cls.env['product.product']
        cls.Bom = cls.env['mrp.bom']
        cls.prod_location = cls.warehouse._get_production_location()

        # Products.
        cls.dining_table = cls._create_product('Dining Table', 1000, quantity=0, category=cls.category_fifo_auto)
        cls.table_head = cls._create_product('Table Head', 300)
        cls.screw = cls._create_product('Screw', 10)
        cls.leg = cls._create_product('Leg', 25)
        cls.glass = cls._create_product('Glass', 100, quantity=0, category=cls.category_avco_auto)

        # Unit of Measure.
        cls.dozen = cls.env.ref("uom.product_uom_dozen")

        # Bills Of Materials.
        # -------------------------------------------------------------------------------
        # Cost of BoM (Dining Table 1 Unit)
        # Component Cost =  Table Head   1 Unit * 300 = 300 (468.75 from it's components)
        #                   Screw        5 Unit *  10 =  50
        #                   Leg          4 Unit *  25 = 100
        #                   Glass        1 Unit * 100 = 100
        # Total = 550 [718.75 if components of Table Head considered] (for 1 Unit)
        # -------------------------------------------------------------------------------

        bom_form = Form(cls.Bom)
        bom_form.product_id = cls.dining_table
        bom_form.product_tmpl_id = cls.dining_table.product_tmpl_id
        bom_form.product_qty = 1.0
        bom_form.product_uom_id = cls.uom
        bom_form.type = 'normal'
        with bom_form.bom_line_ids.new() as line:
            line.product_id = cls.table_head
            line.product_qty = 1
        with bom_form.bom_line_ids.new() as line:
            line.product_id = cls.screw
            line.product_qty = 5
        with bom_form.bom_line_ids.new() as line:
            line.product_id = cls.leg
            line.product_qty = 4
        with bom_form.bom_line_ids.new() as line:
            line.product_id = cls.glass
            line.product_qty = 1
        cls.bom_1 = bom_form.save()

        # Table Head's components.
        cls.plywood_sheet = cls._create_product('Plywood Sheet', 200)
        cls.bolt = cls._create_product('Bolt', 10)
        cls.colour = cls._create_product('Colour', 100)
        cls.corner_slide = cls._create_product('Corner Slide', 25)

        # -----------------------------------------------------------------
        # Cost of BoM (Table Head 1 Dozen)
        # Component Cost =  Plywood Sheet   12 Unit * 200 = 2400
        #                   Bolt            60 Unit *  10 =  600
        #                   Colour          12 Unit * 100 = 1200
        #                   Corner Slide    57 Unit * 25  = 1425
        #                                           Total = 5625
        #                          1 Unit price (5625/12) =  468.75
        # -----------------------------------------------------------------

        bom_form2 = Form(cls.Bom)
        bom_form2.product_id = cls.table_head
        bom_form2.product_tmpl_id = cls.table_head.product_tmpl_id
        bom_form2.product_qty = 1.0
        bom_form2.product_uom_id = cls.dozen
        bom_form2.type = 'phantom'
        with bom_form2.bom_line_ids.new() as line:
            line.product_id = cls.plywood_sheet
            line.product_qty = 12
        with bom_form2.bom_line_ids.new() as line:
            line.product_id = cls.bolt
            line.product_qty = 60
        with bom_form2.bom_line_ids.new() as line:
            line.product_id = cls.colour
            line.product_qty = 12
        with bom_form2.bom_line_ids.new() as line:
            line.product_id = cls.corner_slide
            line.product_qty = 57
        cls.bom_2 = bom_form2.save()
        cls._use_production_accounting()


class TestBomPriceOperationCommon(TestBomPriceCommon):
    """ Common bom setup with workorder operations"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.write({'group_ids': [(4, cls.env.ref('mrp.group_mrp_routings').id)]})
        cls.account_expense_wo = cls.env['account.account'].create({
            'code': 'X2120',
            'name': 'WO - Expenses',
            'account_type': 'expense',
        })
        cls.workcenter = cls.env['mrp.workcenter'].create({
            'name': 'Workcenter',
            'time_efficiency': 80,
            'oee_target': 100,
            'time_start': 15,
            'time_stop': 15,
            'costs_hour': 100,
            'expense_account_id': cls.account_expense.id,
        })
        cls.env['mrp.workcenter.capacity'].create({
            'product_id': cls.dining_table.id,
            'workcenter_id': cls.workcenter.id,
            'time_start': 17,
            'time_stop': 16,
        })

        # -----------------------------------------------------------------
        # Dinning Table Operation Cost(1 Unit)
        # -----------------------------------------------------------------
        # Operation cost calculate for 1 units
        # Cutting        (15 + 15 + (20 * 100/80) / 60) * 100 =   91.67
        # Drilling       (15 + 15 + (25 * 100/80) / 60) * 100 =  102.08
        # Fitting        (15 + 15 + (30 * 100/80) / 60) * 100 =  112.50
        # Table Capacity (3 operations * (2 + 1)  / 60) * 100 =   15.00
        # ----------------------------------------
        # Operation Cost  1 unit = 321.25
        # -----------------------------------------------------------------

        # --------------------------------------------------------------------------
        # Table Head Operation Cost (1 Dozen)
        # --------------------------------------------------------------------------
        # Operation cost calculate for 1 dozens
        # Cutting        (15 + 15 + (20 * 1 * 100/80) / 60) * 100 =   91.67
        # Drilling       (15 + 15 + (25 * 1 * 100/80) / 60) * 100 =  102.08
        # Fitting        (15 + 15 + (30 * 1 * 100/80) / 60) * 100 =  112.50
        # Table Capacity (3 operations * (2 + 1)      / 60) * 100 =   15.00
        # ----------------------------------------
        # Operation Cost 1 dozen (306.25 + 15 = 321.25 per dozen) and 25.52 for 1 Unit
        # --------------------------------------------------------------------------
        cls.bom_1.write({
            'operation_ids': [
                (0, 0, {
                    'name': 'Cutting',
                    'workcenter_id': cls.workcenter.id,
                    'time_mode': 'manual',
                    'time_cycle_manual': 20,
                    'sequence': 1,
                }),
                (0, 0, {
                    'name': 'Drilling',
                    'workcenter_id': cls.workcenter.id,
                    'time_mode': 'manual',
                    'time_cycle_manual': 25,
                    'sequence': 2,
                }),
                (0, 0, {
                    'name': 'Fitting',
                    'workcenter_id': cls.workcenter.id,
                    'time_mode': 'manual',
                    'time_cycle_manual': 30,
                    'sequence': 3,
                }),
            ],
        })
        cls.bom_2.write({
            'operation_ids': [
                (0, 0, {
                    'name': 'Cutting',
                    'workcenter_id': cls.workcenter.id,
                    'time_mode': 'manual',
                    'time_cycle_manual': 20,
                    'sequence': 1,
                }),
                (0, 0, {
                    'name': 'Drilling',
                    'workcenter_id': cls.workcenter.id,
                    'time_mode': 'manual',
                    'time_cycle_manual': 25,
                    'sequence': 2,
                }),
                (0, 0, {
                    'name': 'Fitting',
                    'workcenter_id': cls.workcenter.id,
                    'time_mode': 'manual',
                    'time_cycle_manual': 30,
                    'sequence': 3,
                }),
            ],
        })

        # byproduct

        # Cost Breakdown.
        # -------------------------------------------------------------------------------
        # Total Cost of BoM = 550 [718.75 if components of Table Head considered] (for 1 Unit)
        # Dining Table 1 Unit = 1 - (25 + 50) / 100 * 550 = 0.25 * 550 = 137.5
        # Scrap Wood 1 Unit = (25 + 50) / 100 * 550 / (8 units + 12 units) = 20.625
        # -------------------------------------------------------------------------------

        cls.scrap_wood = cls._create_product('Scrap Wood', 30, quantity=0)

        # different byproduct line uoms => 20 total units with a total of 75% of cost share
        cls.bom_1.write({
            'byproduct_ids': [
                (0, 0, {
                    'product_id': cls.scrap_wood.id,
                    'product_uom_id': cls.uom.id,
                    'product_qty': 8,
                    'bom_id': cls.bom_1.id,
                    'cost_share': 1,
                }),
                (0, 0, {
                    'product_id': cls.scrap_wood.id,
                    'product_uom_id': cls.dozen.id,
                    'product_qty': 1,
                    'bom_id': cls.bom_1.id,
                    'cost_share': 12,
                }),
            ],
        })
