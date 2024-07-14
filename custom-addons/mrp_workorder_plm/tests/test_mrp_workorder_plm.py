# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.mrp_plm.tests.test_common import TestPlmCommon
from odoo.tests import Form

class TestMrpWorkorderPlm(TestPlmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMrpWorkorderPlm, cls).setUpClass()
        cls.picking_type_manufacturing = cls.env.ref('stock.warehouse0').manu_type_id
        cls.quality_point_test1 = cls.env['quality.point'].create({
            'name': 'QP1',
            'product_ids': [(4, cls.table.id)],
            'picking_type_ids': [(4, cls.picking_type_manufacturing.id)],
            'operation_id': cls.bom_table.operation_ids[0].id,
            'test_type_id': cls.env.ref('quality.test_type_instructions').id,
        })
        cls.quality_point_test2 = cls.env['quality.point'].create({
            'name': 'QP2',
            'product_ids': [(4, cls.table.id)],
            'picking_type_ids': [(4, cls.picking_type_manufacturing.id)],
            'operation_id': cls.bom_table.operation_ids[0].id,
            'test_type_id': cls.env.ref('quality.test_type_instructions').id,
        })

    def test_create_eco_from_production_with_wo(self):
        """ Creates an ECO from a Manufacturing Order and checks the
        modifications done in the MO are in the revised BoM."""
        # Creates a new MO, modifies some fields and confirms it.
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_table
        mo_form.product_qty = 3
        with mo_form.move_raw_ids.edit(1) as table_leg_raw_move:
            table_leg_raw_move.product_uom_qty = 12
        mo = mo_form.save()
        mo_form = Form(mo)
        with mo_form.workorder_ids.edit(0) as op1_wo:
            op1_wo.duration_expected = 45
        mo = mo_form.save()
        mo.action_confirm()
        # Generates an ECO from the MO and starts the revision.
        action = mo.action_create_eco()
        new_eco_form = Form(self.env['mrp.eco'].with_context(action['context']))
        new_eco = new_eco_form.save()
        new_eco.action_new_revision()
        # Checks the ECO's revision BoM has the expected changes.
        new_bom = new_eco.new_bom_id
        self.assertEqual(new_bom.bom_line_ids[1].product_qty, 4)
        self.assertEqual(new_bom.operation_ids[0].time_cycle_manual, 15)
        self.assertRecordValues(new_bom.operation_ids.quality_point_ids, [
            {'title': self.bom_table.operation_ids.quality_point_ids[0].title},
            {'title': self.bom_table.operation_ids.quality_point_ids[1].title},
        ])

    def test_create_eco_from_production_with_wo_using_uom(self):
        """ Creates an ECO from a Manufacturing Order and checks the modifications done in the MO
        are correct even if the UoM used in the MO is different than the BoM's one."""
        self.env.user.groups_id += self.env.ref('uom.group_uom')
        uom_dozen = self.env.ref('uom.product_uom_dozen')
        # Creates a new MO and modifies some fields. Don't confirm it since we want to keep the dozen as the used UoM.
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_table
        mo_form.product_uom_id = uom_dozen
        mo_form.product_qty = 2
        with mo_form.move_raw_ids.edit(1) as table_leg_raw_move:
            table_leg_raw_move.product_uom = uom_dozen
            table_leg_raw_move.product_uom_qty = 8
        mo = mo_form.save()
        mo_form = Form(mo)
        with mo_form.workorder_ids.edit(0) as op1_wo:
            op1_wo.duration_expected = 360
        mo = mo_form.save()
        # Generates an ECO from the MO and starts the revision.
        action = mo.action_create_eco()
        new_eco_form = Form(self.env['mrp.eco'].with_context(action['context']))
        new_eco = new_eco_form.save()
        new_eco.action_new_revision()
        # Checks the ECO's revision BoM has the expected changes.
        new_bom = new_eco.new_bom_id
        self.assertEqual(new_bom.bom_line_ids[0].product_qty, self.bom_table.bom_line_ids[0].product_qty)
        self.assertEqual(new_bom.bom_line_ids[1].product_qty, 4)
        self.assertEqual(new_bom.operation_ids[0].time_cycle_manual, 15)

    def test_operation_change(self):
        "Test eco with bom operation changes."
        # --------------------------------
        # Create ecos for bill of material.
        # ---------------------------------

        eco1 = self._create_eco('ECO1', self.bom_table, self.eco_type.id, self.eco_stage.id)

        # Start new revision of eco1
        eco1.action_new_revision()

        # -----------------------------------------
        # Check eco status after start new revision.
        # ------------------------------------------

        self.assertEqual(eco1.state, 'progress', "Wrong state on eco1.")

        # change quality_point_test1 type
        eco1.new_bom_id.operation_ids[0].quality_point_ids[0].test_type_id = self.env.ref('quality.test_type_picture')

        # remove quality_point_test2
        eco1.new_bom_id.operation_ids[0].quality_point_ids[1].unlink()

        # add quality_point_test3
        self.env['quality.point'].create({
            'name': 'QP3',
            'product_ids': [(4, self.table.id)],
            'picking_type_ids': [(4, self.picking_type_manufacturing.id)],
            'operation_id': eco1.new_bom_id.operation_ids[1].id,
            'test_type_id': self.env.ref('quality.test_type_instructions').id,
        })

        # Check correctness
        self.assertEqual(eco1.routing_change_ids[0].change_type, 'update', "Wrong type on opration change line.")
        self.assertEqual(eco1.routing_change_ids[1].change_type, 'remove', "Wrong type on opration change line.")
        self.assertEqual(eco1.routing_change_ids[2].change_type, 'add', "Wrong type on opration change line.")
