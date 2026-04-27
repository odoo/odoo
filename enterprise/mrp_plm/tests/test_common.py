# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import common


class TestPlmCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestPlmCommon, cls).setUpClass()
        cls.Bom = cls.env['mrp.bom']
        grp_workorder = cls.env.ref('mrp.group_mrp_routings')
        cls.env.user.write({'groups_id': [(4, grp_workorder.id)]})
        cls.table = cls.env['product.product'].create({
            'name': 'Table (MTO)',
            'is_storable': True,
            'tracking': 'serial',
        })
        cls.table_sheet = cls.env['product.product'].create({
            'name': 'Table Top',
            'is_storable': True,
            'tracking': 'serial',
        })
        cls.table_leg = cls.env['product.product'].create({
            'name': 'Table Leg',
            'is_storable': True,
            'tracking': 'lot',
        })
        cls.table_bolt = cls.env['product.product'].create({
            'name': 'Bolt',
            'is_storable': True,
        })

        cls.workcenter_1 = cls.env['mrp.workcenter'].create({
            'name': 'Workcenter',
            'default_capacity': 2,
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 80,
        })

        cls.workcenter_2 = cls.env['mrp.workcenter'].create({
            'name': 'Nuclear Workcenter',
            'default_capacity': 2,
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 80,
        })

        cls.workcenter_3 = cls.env['mrp.workcenter'].create({
            'name': 'Nuclear Weapon Workcenter',
            'default_capacity': 2,
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 80,
        })

        # ------------------------------------------------------
        # Create bill of material for table
        # Computer Table
        #       Table Sheet 1 Unit
        #       Table Lag 3 Unit
        # -------------------------------------------------------

        cls.bom_table = cls.Bom.create({
            'product_id': cls.table.id,
            'product_tmpl_id': cls.table.product_tmpl_id.id,
            'product_uom_id': cls.table.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.table_sheet.id, 'product_qty': 1}),
                (0, 0, {'product_id': cls.table_leg.id, 'product_qty': 3})
            ],
            'operation_ids': [
                (0, 0, {'name': 'op1', 'workcenter_id': cls.workcenter_1.id, 'time_cycle_manual': 10, 'sequence': 1}),
                (0, 0, {'name': 'op2', 'workcenter_id': cls.workcenter_2.id, 'time_cycle_manual': 10, 'sequence': 2}),
            ]
            })
        cls.eco_type = cls.env['mrp.eco.type'].search([], limit=1)
        cls.eco_stage = cls.eco_type.stage_ids.filtered('allow_apply_change')[0]
        cls.eco_stage_folded = cls.eco_type.stage_ids.filtered('folded')[0]

    @classmethod
    def _create_eco(cls, name, bom, type_id, stage_id):
        return cls.env['mrp.eco'].create({
            'name': name,
            'bom_id': bom.id,
            'product_tmpl_id': bom.product_tmpl_id.id,
            'type_id': type_id,
            'stage_id': stage_id,
            'type': 'bom'})
