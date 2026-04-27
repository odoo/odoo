# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import Form
from odoo.tests.common import new_test_user

from .test_common import TestPlmCommon


class TestMrpPlm(TestPlmCommon):

    def test_create_eco_from_production_using_uom(self):
        """ Creates an ECO from a Manufacturing Order (using different UoM than its BoM) and checks
        the modifications done in the MO are in the revised BoM."""
        self.env.user.groups_id += self.env.ref('uom.group_uom')
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_dozen = self.env.ref('uom.product_uom_dozen')
        # Creates a BoM.
        common_vals = {'is_storable': True}
        finished_product = self.env['product.product'].create(dict(common_vals, name="Clover"))
        component_1 = self.env['product.product'].create(dict(common_vals, name="Clover's stem"))
        component_2 = self.env['product.product'].create(dict(common_vals, name="Clover's leaf"))
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                Command.create({'product_id': component_1.id, 'product_qty': 1}),
                Command.create({'product_id': component_2.id, 'product_qty': 3}),
            ]
        })
        # Creates a new MO, modifies some fields and confirms it.
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom
        mo_form.product_qty = 3
        mo_form.product_uom_id = uom_dozen
        with mo_form.move_raw_ids.edit(1) as clover_leaves_raw_move:
            clover_leaves_raw_move.product_uom_qty = 144
        mo = mo_form.save()
        mo_form = Form(mo)
        mo = mo_form.save()
        mo.action_confirm()
        # Generates an ECO from the MO and starts the revision.
        action = mo.action_create_eco()
        new_eco_form = Form(self.env['mrp.eco'].with_context(action['context']))
        new_eco = new_eco_form.save()
        new_eco.will_update_version = False
        new_eco.action_new_revision()
        # Checks the ECO's revision BoM has the expected changes.
        new_bom = new_eco.new_bom_id
        self.assertEqual(new_bom.version, bom.version, "Update version was unchecked in eco, so new bom version should equal original bom's")
        self.assertRecordValues(new_bom.bom_line_ids, [
            {'product_id': component_1.id, 'product_qty': 1, 'product_uom_id': uom_unit.id},
            {'product_id': component_2.id, 'product_qty': 4, 'product_uom_id': uom_unit.id},
        ])

        # Does the same test but switches the BoM and MO's UoM, and use an UoM
        # from another UoM's category for one of the component.
        uom_cm = self.env.ref('uom.product_uom_cm')
        comp_cm_vals = {'name': "Clover's stem", 'uom_id': uom_cm.id, 'uom_po_id': uom_cm.id}
        component_1_in_cm = self.env['product.product'].create(dict(common_vals, **comp_cm_vals))
        bom_dozen = self.env['mrp.bom'].create({
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'product_uom_id': uom_dozen.id,
            'bom_line_ids': [
                Command.create({
                    'product_id': component_1_in_cm.id,
                    'product_qty': 84,
                    'product_uom_id': uom_cm.id
                }),
                Command.create({
                    'product_id': component_2.id,
                    'product_qty': 3,
                    'product_uom_id': uom_dozen.id
                }),
            ]
        })
        # Creates a new MO, modifies some fields and confirms it.
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom_dozen
        mo_form.product_qty = 3
        mo_form.product_uom_id = uom_unit
        mo = mo_form.save()
        with mo_form.move_raw_ids.edit(0) as clover_stem_raw_move:
            clover_stem_raw_move.product_uom_qty = 15
        with mo_form.move_raw_ids.edit(1) as clover_leaves_raw_move:
            clover_leaves_raw_move.product_uom_qty = 12
            clover_leaves_raw_move.product_uom = uom_unit
        mo = mo_form.save()
        mo_form = Form(mo)
        mo = mo_form.save()
        mo.action_confirm()
        # Generates an ECO from the MO and starts the revision.
        action = mo.action_create_eco()
        new_eco_form = Form(self.env['mrp.eco'].with_context(action['context']))
        new_eco = new_eco_form.save()
        new_eco.action_new_revision()
        # Checks the ECO's revision BoM has the expected changes.
        new_bom = new_eco.new_bom_id
        self.assertEqual(new_bom.version, bom.version + 1, "By default, new bom version should be original bom's + 1")
        self.assertRecordValues(new_bom.bom_line_ids, [
            {'product_id': component_1_in_cm.id, 'product_qty': 60, 'product_uom_id': uom_cm.id},
            {'product_id': component_2.id, 'product_qty': 4, 'product_uom_id': uom_dozen.id},
        ])

    def test_rebase_with_old_bom_change(self):
        "Test eco rebase with old bom changes."

        # Create eco for bill of material.
        version_num = self.bom_table.version
        self.eco1 = self._create_eco('ECO1', self.bom_table, self.eco_type.id, self.eco_stage.id)
        # Start new revision of eco1.
        self.eco1.action_new_revision()

        # Eco should be in progress and new revision of BoM should be created.
        self.assertTrue(self.eco1.new_bom_id, "New revision of bill of material should be created.")
        self.assertEqual(self.eco1.state, 'progress', "Wrong state on eco")

        # Change old bom lines
        old_bom_leg = self.bom_table.bom_line_ids.filtered(lambda x: x.product_id == self.table_leg)
        new_bom_leg = self.eco1.new_bom_id.bom_line_ids.filtered(lambda x: x.product_id == self.table_leg)

        # Update quantity current bill of materials.
        old_bom_leg.product_qty = 8

        # Check status of eco
        self.assertEqual(self.eco1.state, 'rebase', "Wrong state on eco.")
        self.assertEqual(new_bom_leg.product_qty, 3, "Wrong table leg quantity on new revision of BoM.")

        # Rebase eco1 with current BoM changes ( 3 + 5 ( New added product )).
        self.eco1.apply_rebase()
        self.assertEqual(self.eco1.new_bom_revision, version_num + 1, "By default, new bom version should match original bom's + 1")

        # Check quantity of table lag on new revision of BoM.
        self.assertEqual(new_bom_leg.product_qty, 8, "Wrong table leg quantity on new revision of bom.")

        # Add new bom line with product bolt in old BoM.
        self.env['mrp.bom.line'].create({'product_id': self.table_bolt.id, 'bom_id': self.bom_table.id, 'product_qty': 3})

        # Check status of eco and rebase line after adding new product on current BoM.
        self.assertEqual(self.eco1.state, 'rebase', "Wrong state on eco.")
        self.assertEqual(len(self.eco1.bom_rebase_ids), 1, "Wrong rebase line on eco.")
        self.assertEqual(self.eco1.bom_rebase_ids.change_type, 'add', "Wrong type on rebase line.")
        self.eco1.will_update_version = False
        self.assertEqual(self.eco1.new_bom_revision, version_num, "Update version was unchecked in eco, so new bom version should equal original bom's")

        # Rebase eco1 with BoM changes.
        self.eco1.apply_rebase()
        self.assertEqual(self.eco1.new_bom_revision, version_num, "Update version was unchecked in eco, rebasing should leave new bom version as equal to original bom's")

        new_bom_bolt = self.eco1.new_bom_id.bom_line_ids.filtered(lambda x: x.product_id == self.table_bolt)

        # Check eco status and bom line should be added on new bom revision.
        self.assertTrue(new_bom_bolt, "BoM line should be added for bolt on new revision of BoM.")
        self.assertEqual(self.eco1.state, 'progress', "Wrong state on eco.")

        # Remove line form current BoM
        self.eco1.bom_id.bom_line_ids.filtered(lambda x: x.product_id == self.table_bolt).unlink()

        # Check status of eco with rebase lines.
        self.assertEqual(self.eco1.state, 'rebase', "Wrong state on eco.")
        self.assertEqual(len(self.eco1.bom_rebase_ids), 1, "Wrong BoM rebase line on eco.")
        self.assertEqual(self.eco1.bom_rebase_ids.change_type, 'update', "Wrong type on rebase line.")
        self.assertEqual(self.eco1.bom_rebase_ids.upd_product_qty, -3, "Wrong quantity on rebase line.")

        # Rebase eco
        self.eco1.apply_rebase()
        self.assertFalse(self.eco1.new_bom_id.bom_line_ids.filtered(lambda x: x.product_id == self.table_bolt), "BoM line should be unlink from new revision of BoM.")

        # Change old BoM leg and new revision BoM leg quantity.
        old_bom_leg.product_qty = 10
        new_bom_leg.product_qty = 12
        self.assertEqual(self.eco1.bom_rebase_ids.change_type, 'update', "Wrong type on rebase line.")
        self.assertEqual(self.eco1.bom_rebase_ids.upd_product_qty, 2, "Wrong quantity on rebase line.")

        # Rebase ecos with changes of old bill of material.
        self.eco1.apply_rebase()
        self.assertEqual(self.eco1.state, 'conflict', "Wrong state on eco.")

        # Manually resolve conflict.
        self.eco1.conflict_resolve()
        self.assertEqual(self.eco1.state, 'progress', "Wrong state on eco.")

    def test_rebase_with_previous_eco_change(self):
        "Test eco rebase with previous eco changes."

        # --------------------------------
        # Create ecos for bill of material.
        # ---------------------------------

        eco1 = self._create_eco('ECO1', self.bom_table, self.eco_type.id, self.eco_stage.id)
        eco2 = self._create_eco('ECO2', self.bom_table, self.eco_type.id, self.eco_stage.id)
        eco3 = self._create_eco('ECO3', self.bom_table, self.eco_type.id, self.eco_stage.id)
        version_num = self.bom_table.version

        # Start new revision of eco1, eco2, eco3
        eco1.action_new_revision()
        eco2.action_new_revision()
        eco3.action_new_revision()

        # -----------------------------------------
        # Check eco status after start new revision.
        # ------------------------------------------

        self.assertEqual(eco1.state, 'progress', "Wrong state on eco1.")
        self.assertEqual(eco2.state, 'progress', "Wrong state on eco2.")
        self.assertEqual(eco3.state, 'progress', "Wrong state on eco2.")

        # ---------------------------------------------------------------
        # ECO 1 : Update Table Leg quantity in new BoM revision.
        # ---------------------------------------------------------------

        eco1_new_table_leg = eco1.new_bom_id.bom_line_ids.filtered(lambda x: x.product_id == self.table_leg)
        eco1_new_table_leg.product_qty = 6

        # -------------------------------------------------------------------------------
        # ECO 1 : Check status of ecos after apply changes and activate new bom revision.
        # -------------------------------------------------------------------------------

        eco1.action_apply()
        self.assertEqual(eco1.new_bom_revision, version_num + 1, "By default, new bom version should match original bom's + 1")
        self.assertFalse(eco1.bom_id.active, "Old BoM of eco1 should be deactivated.")
        self.assertTrue(eco1.new_bom_id.active, "New BoM revision of ECO 1 should be activated.")
        # Check eco status after activate new bom revision of eco.
        self.assertEqual(eco1.state, 'done', "Wrong state on eco1.")
        self.assertEqual(eco2.state, 'rebase', "Wrong state on eco2.")
        self.assertEqual(eco3.state, 'rebase', "Wrong state on eco3.")

        # ------------------------------
        # ECO 2 : Rebase with ECO 1 changes.
        # ------------------------------

        eco2.will_update_version = False
        eco2.apply_rebase()
        self.assertEqual(eco2.state, 'progress', "Wrong state on eco2.")
        self.assertEqual(eco1.new_bom_id.id, eco2.bom_id.id, "Eco2 BoM should replace with new activated BoM revision of Eco1.")
        self.assertEqual(eco2.new_bom_revision, eco1.new_bom_id.version, "Update version was unchecked in eco, rebasing should leave new bom version as BoM revision of Eco1")

        # ----------------------------------------------------------------------
        # ECO 2 : Add new product 'Table Bolt'
        # ----------------------------------------------------------------------

        eco2.new_bom_id.bom_line_ids.create({'product_id': self.table_bolt.id, 'bom_id': eco2.new_bom_id.id, 'product_qty': 3})
        self.assertTrue(eco2.bom_change_ids, "Eco 2 should have BoM change lines.")

        # -------------------------------------------------------------------------------
        # ECO 2 : Check status of after apply changes and activate new bom revision.
        # -------------------------------------------------------------------------------

        eco2.action_apply()

        self.assertFalse(eco1.bom_id.active, "BoM of ECO 1 should be deactivated")
        self.assertFalse(eco1.new_bom_id.active, "BoM revision of ECO 1 should be deactivated")
        self.assertTrue(eco2.new_bom_id.active, "BoM revision of ECO 2 should be activated")
        self.assertEqual(eco2.new_bom_revision, eco1.new_bom_id.version, "Update version was unchecked in eco, new bom version should still match BoM revision of Eco1")

        # -----------------------------------------------------
        # ECO3 : Change same line in eco3 as changes in eco1.
        # ----------------------------------------------------

        eco3_new_table_leg = eco3.new_bom_id.bom_line_ids.filtered(lambda x: x.product_id == self.table_leg)
        eco3_new_table_leg.product_qty = 4

        # -----------------------------------
        # Rebase eco3 with eco1 BoM changes.
        # -----------------------------------

        eco3.apply_rebase()

        # Check status of eco3 after rebase.
        self.assertEqual(eco3.state, 'conflict', "Wrong state on eco.")

        # Resolve conflict manually.
        self.assertTrue(eco3.previous_change_ids.ids, "Wrong previous bom change on bom lines.")
        eco3.conflict_resolve()
        self.assertEqual(eco3.state, 'progress', "Wrong state on eco.")
        eco3.action_apply()
        self.assertFalse(eco2.new_bom_id.active, "BoM revision of ECO 2 should be deactivated")
        self.assertTrue(eco3.new_bom_id.active, "BoM revision of ECO 3 should be activated")
        self.assertEqual(eco3.new_bom_revision, eco2.new_bom_id.version + 1, "By default, new bom version should match eco2 bom's + 1")
        self.assertFalse(eco3.previous_change_ids.ids)
        self.assertFalse(eco3.bom_rebase_ids.ids)

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

        # ---------------------------------------------------------------
        # ECO 1 : Update duration on operation1
        # ---------------------------------------------------------------

        op1 = eco1.new_bom_id.operation_ids.filtered(lambda x: x.workcenter_id == self.workcenter_1)
        op1.time_cycle_manual = 20

        # Check correctness
        op1_change = eco1.routing_change_ids.filtered(lambda x: x.workcenter_id == self.workcenter_1)
        self.assertEqual(op1_change[0].change_type, 'update', "Wrong type on operation change line.")
        self.assertEqual(op1_change[0].upd_time_cycle_manual, 10.0, "Wrong duration change.")

        # ---------------------------------------------------------------
        # ECO 1 : Remove operation2
        # ---------------------------------------------------------------

        op2 = eco1.new_bom_id.operation_ids.filtered(lambda x: x.workcenter_id == self.workcenter_2)
        op2.unlink()

        op2_change = eco1.routing_change_ids.filtered(lambda x: x.workcenter_id == self.workcenter_2)
        self.assertEqual(op2_change.change_type, 'remove', "Wrong type on operation change line.")

        # ---------------------------------------------------------------
        # ECO 1 : Add operation3
        # ---------------------------------------------------------------

        eco1.new_bom_id.operation_ids.create({
            'name': 'op3',
            'bom_id': eco1.new_bom_id.id,
            'workcenter_id': self.workcenter_3.id,
            'time_cycle_manual': 10,
            'sequence': 2,
        })

        op3_change = eco1.routing_change_ids.filtered(lambda x: x.workcenter_id == self.workcenter_3)
        self.assertEqual(op3_change.change_type, 'add', "Wrong type on operation change line.")
        self.assertEqual(op3_change.upd_time_cycle_manual, 10.0, "Wrong duration change.")

    def test_operation_eco_counting(self):
        """ Test when count ECOs for a bom, all ECOs, including the ones for previous
        version boms, are counted.
        """
        eco1 = self._create_eco('ECO1', self.bom_table, self.eco_type.id, self.eco_stage.id)
        eco1.action_new_revision()
        eco1.action_apply()
        self.assertEqual(eco1.stage_id, self.eco_stage_folded, "Wrong stage.")

        eco2 = self._create_eco('ECO2', eco1.new_bom_id, self.eco_type.id, self.eco_stage.id)
        eco2.action_new_revision()
        self.assertEqual(eco2.stage_id, self.eco_stage, "Wrong stage.")

        self.assertEqual(eco1.new_bom_id.eco_count, 2)

    def test_do_not_merge_bom_lines(self):
        """
        Test that when applying a mrp.eco on a BoM for which the same product is present twice in the bom lines
        (same product, multiple operations), the BoM changes are correctly computed
        """
        workcenter = self.env['mrp.workcenter'].create({'name': 'A center'})
        product_a = self.env['product.product'].create({'name': 'a_product'})
        product_b = self.env['product.product'].create({'name': 'b_product'})
        bom = self.env['mrp.bom'].create({
            'product_id': product_a.id,
            'product_tmpl_id': product_a.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_b.id, 'product_qty': 2}),
                (0, 0, {'product_id': product_b.id, 'product_qty': 3}),
            ]
        })
        operation_a = self.env['mrp.routing.workcenter'].create({
            'name': 'Some operation',
            'workcenter_id': workcenter.id,
            'bom_id': bom.id
        })
        operation_b = self.env['mrp.routing.workcenter'].create({
            'name': 'Other operation',
            'workcenter_id': workcenter.id,
            'bom_id': bom.id
        })
        bom.bom_line_ids[0].operation_id = operation_a.id
        bom.bom_line_ids[1].operation_id = operation_b.id
        type_id = self.env['mrp.eco.type'].search([], limit=1).id
        mrp_eco = self.env['mrp.eco'].create({
            'name': 'a plm',
            'bom_id': bom.id,
            'product_tmpl_id': bom.product_tmpl_id.id,
            'type_id': type_id,
            'type': 'bom'
        })
        mrp_eco.action_new_revision()
        self.assertEqual(len(mrp_eco.bom_change_ids), 0)
        mrp_eco.new_bom_id.bom_line_ids[0].product_qty = 13  # Change from 2 to 13
        self.assertRecordValues(mrp_eco.bom_change_ids, [
            {'change_type': 'update', 'upd_product_qty': 11},
        ])

    def test_bom_changes(self):
        """
            Test that when creating a `mrp.eco` for a BOM with operations and components consumed in the operations,
            the difference lines between the old and the new BOM is done correctly
        """
        workcenter = self.env['mrp.workcenter'].create({'name': 'wc 1'})
        operation_1 = self.env['mrp.routing.workcenter'].create({
            'name': 'op1',
            'workcenter_id': workcenter.id,
            'bom_id': self.bom_table.id
        })
        operation_2 = self.env['mrp.routing.workcenter'].create({
            'name': 'op2',
            'workcenter_id': workcenter.id,
            'bom_id': self.bom_table.id
        })
        self.bom_table.operation_ids = [(6, 0, (operation_1 + operation_2).ids)]
        # Consume the first component in the first operation
        self.bom_table.bom_line_ids[0].operation_id = self.bom_table.operation_ids[0]
        # Create eco for bill of material.
        eco1 = self._create_eco('ECO1', self.bom_table, self.eco_type.id, self.eco_stage.id)
        # Start new revision of eco1.
        eco1.action_new_revision()
        self.assertEqual(eco1.state, 'progress', "Wrong state on eco1.")
        # Make sure there is no change between the two BOMs
        self.assertEqual(len(eco1.bom_change_ids), 0)
        # Modify the new BOM to consume the first component in the second operation
        eco1.new_bom_id.bom_line_ids[0].operation_id = eco1.new_bom_id.operation_ids[1]
        # A bom changes must be created
        self.assertRecordValues(eco1.bom_change_ids, [
            {'change_type': 'add', 'operation_change': 'op2'},
            {'change_type': 'remove', 'operation_change': 'op1'},
        ])

    def test_product_version(self):
        """Test product version number increases or doesn't increase after a product ECO is done
        depending on setting.
        """
        version_num = self.table.product_tmpl_id.version
        mrp_eco = self.env['mrp.eco'].create({
            'name': 'a plm',
            'product_tmpl_id': self.table.product_tmpl_id.id,
            'stage_id': self.eco_stage.id,
            'type_id': self.eco_type.id,
            'type': 'product',
        })
        mrp_eco.action_new_revision()
        mrp_eco.action_apply()
        self.assertEqual(mrp_eco.state, 'done')
        self.assertEqual(self.table.product_tmpl_id.version, version_num + 1, "By default, product's version should increment when eco applied")

        version_num = self.table.product_tmpl_id.version
        mrp_eco_no_change = self.env['mrp.eco'].create({
            'name': 'plm no version change',
            'product_tmpl_id': self.table.product_tmpl_id.id,
            'stage_id': self.eco_stage.id,
            'type_id': self.eco_type.id,
            'type': 'product',
            'will_update_version': False
        })
        mrp_eco_no_change.action_new_revision()
        mrp_eco_no_change.action_apply()
        self.assertEqual(mrp_eco_no_change.state, 'done')
        self.assertEqual(self.table.product_tmpl_id.version, version_num, "Update version was unchecked in eco, so product's version shouldn't increment when eco applied")

    def test_new_bom_version(self):
        """Test new bom version number increases or doesn't increase depending on state + setting
        We force the state values because it's assumed there are other tests checking that the state matches
        """
        # updates version = True by default
        version_num = self.bom_table.version
        bom_eco = self._create_eco('bom_eco', self.bom_table, self.eco_type.id, self.eco_stage.id)
        bom_eco.action_new_revision()
        self.assertEqual(bom_eco.new_bom_revision, version_num + 1)
        # unchecking updates version => the new bom version auto-increments down even when not done
        bom_eco.will_update_version = False
        self.assertEqual(bom_eco.new_bom_revision, version_num)
        # rechecking updates version => the new bom version auto-increments up when not done
        bom_eco.will_update_version = True
        self.assertEqual(bom_eco.new_bom_revision, version_num + 1)

        # check that version updates occur as long as eco != Done
        # note that test for rebasing increments version as expected is done
        # in another test due to conditions needed for rebasing to work
        bom_eco.state = 'rebase'
        self.assertEqual(bom_eco.new_bom_revision, version_num + 1)
        bom_eco.will_update_version = False
        self.assertEqual(bom_eco.new_bom_revision, version_num)
        bom_eco.will_update_version = True
        self.assertEqual(bom_eco.new_bom_revision, version_num + 1)

        bom_eco.state = 'conflict'
        self.assertEqual(bom_eco.new_bom_revision, version_num + 1)
        bom_eco.will_update_version = False
        self.assertEqual(bom_eco.new_bom_revision, version_num)
        bom_eco.will_update_version = True
        self.assertEqual(bom_eco.new_bom_revision, version_num + 1)
        bom_eco.conflict_resolve()
        self.assertEqual(bom_eco.new_bom_revision, version_num + 1)
        bom_eco.state = 'conflict'
        bom_eco.will_update_version = False
        bom_eco.conflict_resolve()
        self.assertEqual(bom_eco.new_bom_revision, version_num)
        bom_eco.will_update_version = True

        bom_eco.state = 'progress'
        self.assertEqual(bom_eco.new_bom_revision, version_num + 1)
        bom_eco.action_apply()
        self.assertEqual(bom_eco.state, 'done')
        self.assertEqual(bom_eco.new_bom_revision, version_num + 1)

        # in theory the field shouldn't be update-able when eco is done, but let's check anyways
        bom_eco.will_update_version = False
        self.assertEqual(bom_eco.new_bom_revision, version_num + 1)

    def test_mrp_user_without_plm_permission_can_create_bom(self):
        mrp_manager = new_test_user(
            self.env, 'temp_stock_manager', 'mrp.group_mrp_manager',
        )
        bom = self.env['mrp.bom'].with_user(mrp_manager).create({
            'product_id': self.table.id,
            'product_tmpl_id': self.table.product_tmpl_id.id,
            'bom_line_ids': [
                (0, 0, {'product_id': self.table_sheet.id, 'product_qty': 1}),
            ],
        })

        # Admin creates an ECO
        self.env['mrp.eco'].sudo().create({
            'name': 'a plm',
            'bom_id': bom.id,
            'product_tmpl_id': bom.product_tmpl_id.id,
            'type_id': self.env['mrp.eco.type'].search([], limit=1).id,
            'type': 'bom',
            # Status 'progress' or 'rebase' is required to trigger rebase lines
            'state': 'progress',
        })

        # MRP manager should still be able to edit the original object
        bom.bom_line_ids[0].product_qty = 2

    def create_eco(self, eco_type):
        eco_form = Form(self.env['mrp.eco'])
        eco_form.type = eco_type
        eco_form.type_id = self.eco_type
        eco_form.name = 'test_plm_bom_document'
        eco_form.product_tmpl_id = self.table_bolt.product_tmpl_id
        eco = eco_form.save()
        eco.action_new_revision()
        return eco

    def test_plm_bom_document(self):

        doc_product = self.env['product.document'].create({
            'name': 'doc_product_mo',
            'attached_on_mrp': 'hidden',
            'res_id': self.table_bolt.id,
            'res_model': 'product.product',
        })
        doc_template = self.env['product.document'].create({
            'name': 'doc_product_mo',
            'attached_on_mrp': 'hidden',
            'res_id': self.table_bolt.product_tmpl_id.id,
            'res_model': 'product.template',
        })
        self.env['mrp.bom'].create({
            'product_tmpl_id': self.table_bolt.product_tmpl_id.id,
            'product_uom_id': self.table_bolt.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            })

        eco = self.create_eco('bom')
        self.assertEqual(eco.document_count, 0, 'Document count should be 0, no docs are visible on bom')

        doc_template.attached_on_mrp = 'bom'
        doc_product.attached_on_mrp = 'bom'
        eco = self.create_eco('bom')
        self.assertEqual(eco.document_count, 2, 'Document count should be 2, docs related to the template and the product have to be copied.')
        docs = self.env['product.document'].search([('id', 'in', [doc_product.id, doc_template.id])])
        self.assertNotEqual(eco.document_ids, docs, 'The documents have to be differents')

    def test_plm_product_document(self):

        self.env['product.document'].create({
            'name': 'doc_product_mo',
            'attached_on_mrp': 'hidden',
            'res_id': self.table_bolt.id,
            'res_model': 'product.product',
        })
        self.env['product.document'].create({
            'name': 'doc_product_mo',
            'attached_on_mrp': 'hidden',
            'res_id': self.table_bolt.product_tmpl_id.id,
            'res_model': 'product.template',
        })
        eco = self.create_eco('product')
        self.assertEqual(eco.document_count, 2, 'Document count should be 2, all docs have to be copied.')

    def test_duplicate_eco_template_with_same_user_and_stage(self):
        """Test that two ECO approval templates cannot be created
        with the same user for the same stage."""
        self.env['mrp.eco.approval.template'].create({
            'name': 'eco approval template',
            'approval_type': 'mandatory',
            'user_ids': [Command.set(self.env.ref('base.user_admin').ids)],
            'stage_id': self.eco_stage.id,
        })
        with self.assertRaises(ValidationError):
            self.env['mrp.eco.approval.template'].create({
                'name': 'eco approval template',
                'approval_type': 'mandatory',
                'user_ids': [Command.set(self.env.ref('base.user_admin').ids)],
                'stage_id': self.eco_stage.id,
            })

    def test_eco_count(self):
        """Test that the ECO count is correctly updated for both
        the product and the BOM when creating a new revision.
        """
        self.assertEqual(self.table.eco_count, 0)
        self.assertEqual(self.bom_table.eco_count, 0)
        # Create an ECO for the BOM and verify the count for both the BOM and the product
        eco = self.env['mrp.eco'].create({
            'name': 'eco',
            'product_tmpl_id': self.table.product_tmpl_id.id,
            'type_id': self.eco_type.id,
            'type': 'bom',
            'bom_id': self.bom_table.id,
        })
        self.table.invalidate_recordset(['eco_count'])
        self.table.product_tmpl_id.invalidate_recordset(['eco_count'])
        self.bom_table.invalidate_recordset(['eco_count'])
        self.assertEqual(self.table.eco_count, 0)
        self.assertEqual(self.bom_table.eco_count, 1)
        # Update the ECO type to "Product" and verify that
        # the bom_id field is cleared and the count is updated
        eco.type = 'product'
        self.assertFalse(eco.bom_id)
        self.table.invalidate_recordset(['eco_count'])
        self.table.product_tmpl_id.invalidate_recordset(['eco_count'])
        self.bom_table.invalidate_recordset(['eco_count'])
        self.assertEqual(self.table.eco_count, 1)
        self.assertEqual(self.bom_table.eco_count, 0)

    def _create_eco_approval_workflow(self):
        """Create an ECO type with an approval workflow for testing purposes."""
        self.random_approver = new_test_user(
            self.env, "random_approver", "mrp_plm.group_plm_manager"
        )
        self.admin = self.env.ref("base.user_admin")
        self.approval_eco_type = self.env["mrp.eco.type"].create(
            {
                "name": "ECO Type with approval",
            }
        )
        self.approval_new_stage = self.env["mrp.eco.stage"].create(
            {
                "name": "New",
                "sequence": 0,
                "type_ids": [Command.link(self.approval_eco_type.id)],
            }
        )
        self.approval_first_stage = self.env["mrp.eco.stage"].create(
            {
                "name": "First approval",
                "type_ids": [Command.link(self.approval_eco_type.id)],
                "sequence": 10,
                "approval_template_ids": [
                    Command.create(
                        {
                            "name": "First Approval",
                            "user_ids": [Command.set(self.admin.ids)],
                            "approval_type": "optional",
                        }
                    ),
                    Command.create(
                        {
                            "name": "Second Approval",
                            "user_ids": [Command.set(self.random_approver.ids)],
                            "approval_type": "mandatory",
                        }
                    ),
                ],
            }
        )
        self.approval_done_stage = self.env["mrp.eco.stage"].create(
            {
                "name": "Done",
                "type_ids": [Command.link(self.approval_eco_type.id)],
                "final_stage": True,
                "sequence": 30,
            }
        )

    def test_dashboard_waiting_for_me(self):
        """Test that the dashboard computes the ECOs waiting for my approval properly."""
        self._create_eco_approval_workflow()
        eco = self._create_eco(
            "ECO1",
            self.bom_table,
            self.approval_eco_type.id,
            self.approval_new_stage.id,
        )
        eco.action_new_revision()
        eco.stage_id = self.approval_first_stage
        # Just landed on first stage, both users need to approve
        self.approval_eco_type.invalidate_recordset(["nb_approvals_my"])
        self.assertEqual(
            self.approval_eco_type.with_user(self.random_approver).nb_approvals_my,
            1,
            "Random approver should have 1 approval waiting",
        )
        self.approval_eco_type.invalidate_recordset(["nb_approvals_my"])
        self.assertEqual(
            self.approval_eco_type.with_user(self.admin).nb_approvals_my,
            1,
            "Admin should have 1 approval waiting",
        )
        # Admin approves
        eco.with_user(self.admin).approve()
        # Check that counter is correct
        self.approval_eco_type.invalidate_recordset(["nb_approvals_my"])
        self.assertEqual(
            self.approval_eco_type.with_user(self.random_approver).nb_approvals_my,
            1,
            "Random approver should have 1 approval waiting",
        )
        self.approval_eco_type.invalidate_recordset(["nb_approvals_my"])
        self.assertEqual(
            self.approval_eco_type.with_user(self.admin).nb_approvals_my,
            0,
            "Admin should have 0 approval waiting",
        )

    def test_compute_component_upd_product_qty(self):
        """Test the correct computation of BoM component quantity changes when
        using high-precision units of measure. We ensure that the updated
        quantity respects the UoM decimal digits instead of the default precision.
        """
        self.env['decimal.precision'].search([('name', '=', 'Product Unit of Measure')]).digits = 4
        self.bom_table.product_uom_id.rounding = 0.0001
        bom_eco = self._create_eco('bom_eco', self.bom_table, self.eco_type.id, self.eco_stage.id)
        bom_eco.action_new_revision()
        self.assertFalse(bom_eco.bom_change_ids)
        self.assertEqual(bom_eco.bom_id.bom_line_ids[0].product_qty, 1.0)
        bom_eco.new_bom_id.bom_line_ids[0].product_qty = 1.0003
        self.assertEqual(bom_eco.new_bom_id.bom_line_ids[0].product_qty, 1.0003)
        self.assertEqual(bom_eco.bom_change_ids.upd_product_qty, 0.0003)

    def test_eco_attachments(self):
        """Test that applying an ECO updates the origin_attachment_id for product.document"""
        tmpl = self.env["product.template"].create({"name": "Test"})
        eco_form = Form(self.env["mrp.eco"])
        eco_form.name = "ELCT ECO"
        eco_form.type_id = self.eco_type
        eco_form.type = "product"
        eco_form.product_tmpl_id = tmpl
        eco = eco_form.save()
        eco.stage_id = self.eco_stage
        eco.action_new_revision()
        eco.document_ids = [
            (
                0,
                0,
                {
                    "name": "test.pdf",
                    "type": "binary",
                    "raw": b"Original content",
                    "res_id": eco.id,
                    "res_model": "mrp.eco",
                },
            )
        ]
        doc = eco.document_ids[0]
        old_origin_id = doc.origin_attachment_id
        eco.action_apply()
        self.assertNotEqual(doc.origin_attachment_id, old_origin_id)
