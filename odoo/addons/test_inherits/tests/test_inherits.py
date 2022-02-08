# -*- coding: utf-8 -*-
from odoo.tests import common
from odoo.exceptions import ValidationError
from odoo import Command


class test_inherits(common.TransactionCase):

    def test_create_3_levels_inherits(self):
        """ Check that we can create an inherits on 3 levels """
        pallet = self.env['test.pallet'].create({
            'name': 'B',
            'field_in_box': 'box',
            'field_in_pallet': 'pallet',
        })
        self.assertTrue(pallet)
        self.assertEqual(pallet.name, 'B')
        self.assertEqual(pallet.field_in_box, 'box')
        self.assertEqual(pallet.field_in_pallet, 'pallet')

    def test_create_3_levels_inherits_with_defaults(self):
        unit = self.env['test.unit'].create({
            'name': 'U',
            'state': 'a',
            'size': 1,
        })
        ctx = {
            'default_state': 'b',       # 'state' is inherited from 'test.unit'
            'default_size': 2,          # 'size' is inherited from 'test.box'
        }
        pallet = self.env['test.pallet'].with_context(ctx).create({
            'name': 'P',
            'unit_id': unit.id,         # grand-parent field is set
        })
        # default 'state' should be ignored, but default 'size' should not
        self.assertEqual(pallet.state, 'a')
        self.assertEqual(pallet.size, 2)

    def test_read_3_levels_inherits(self):
        """ Check that we can read an inherited field on 3 levels """
        pallet = self.env.ref('test_inherits.pallet_a')
        self.assertEqual(pallet.read(['name']), [{'id': pallet.id, 'name': 'Unit A'}])

    def test_write_3_levels_inherits(self):
        """ Check that we can create an inherits on 3 levels """
        pallet = self.env.ref('test_inherits.pallet_a')
        pallet.write({'name': 'C'})
        self.assertEqual(pallet.name, 'C')

    def test_write_4_one2many(self):
        """ Check that we can write on an inherited one2many field. """
        box = self.env.ref('test_inherits.box_a')
        box.write({'line_ids': [Command.create({'name': 'Line 1'})]})
        self.assertTrue(all(box.line_ids._ids))
        self.assertEqual(box.line_ids.mapped('name'), ['Line 1'])
        self.assertEqual(box.line_ids, box.unit_id.line_ids)
        box.flush()
        box.invalidate_cache(['line_ids'])
        box.write({'line_ids': [Command.create({'name': 'Line 2'})]})
        self.assertTrue(all(box.line_ids._ids))
        self.assertEqual(box.line_ids.mapped('name'), ['Line 1', 'Line 2'])
        self.assertEqual(box.line_ids, box.unit_id.line_ids)
        box.flush()
        box.invalidate_cache(['line_ids'])
        box.write({'line_ids': [Command.update(box.line_ids[0].id, {'name': 'First line'})]})
        self.assertTrue(all(box.line_ids._ids))
        self.assertEqual(box.line_ids.mapped('name'), ['First line', 'Line 2'])
        self.assertEqual(box.line_ids, box.unit_id.line_ids)

    def test_write_5_field_readonly(self):
        """ Check that we can write on an inherited readonly field. """
        self.assertTrue(self.env['test.box']._fields['readonly_name'])
        box = self.env.ref('test_inherits.box_a')
        box.write({'readonly_name': "Superuser's box"})
        self.assertEqual(box.readonly_name, "Superuser's box")
        self.assertEqual(box.unit_id.readonly_name, "Superuser's box")

    def test_ir_model_data_inherits(self):
        """ Check the existence of the correct ir.model.data """
        IrModelData = self.env['ir.model.data']
        field = IrModelData.search([('name', '=', 'field_test_unit__name')])
        self.assertEqual(len(field), 1)
        self.assertEqual(field.module, 'test_inherits')

        field = IrModelData.search([('name', '=', 'field_test_box__name')])
        self.assertEqual(len(field), 1)
        self.assertEqual(field.module, 'test_inherits')

    def test_constraint_inherits(self):
        """Validate constraints on inherits when the parent is not updated"""
        Model = self.env['test.another_box']

        with self.assertRaises(ValidationError):
            another_box = Model.create({'val1': 1, 'val2': 2})
        another_box = Model.create({'val1': 1, 'val2': 1})

        with self.assertRaises(ValidationError):
            another_box.write({'val2': 2})
        another_box.write({'val1': 2, 'val2': 2})

    def test_constraint_inherits_parent_change(self):
        """Validate constraints on inherits when parent is updated too"""
        UnitModel = self.env['test.another_unit']
        BoxModel = self.env['test.another_box']

        unit1 = UnitModel.create({'val1': 1})
        box = BoxModel.create({'another_unit_id': unit1.id, 'val2': 1})

        unit2 = UnitModel.create({'val1': 2})
        box.write({'another_unit_id': unit2.id, 'val2': 2})

        unit3 = UnitModel.create({'val1': 3})
        box.write({'another_unit_id': unit3.id, 'val1': 4, 'val2': 4})

        unit4 = UnitModel.create({'val1': 5})
        with self.assertRaises(ValidationError):
            box.write({'another_unit_id': unit4.id, 'val2': 6})

        unit5 = UnitModel.create({'val1': 7})
        with self.assertRaises(ValidationError):
            box.write({'another_unit_id': unit5.id, 'val1': 8, 'val2': 7})

    def test_display_name(self):
        """ Check the 'display_name' of an inherited translated 'name'. """
        self.env['res.lang']._activate_lang('fr_FR')

        # concrete check
        pallet_en = self.env['test.pallet'].create({'name': 'Bread'})
        pallet_fr = pallet_en.with_context(lang='fr_FR')
        pallet_fr.box_id.unit_id.name = 'Pain'
        self.assertEqual(pallet_en.display_name, 'Bread')
        self.assertEqual(pallet_fr.display_name, 'Pain')

        # check model
        Unit = type(self.env['test.unit'])
        Box = type(self.env['test.box'])
        Pallet = type(self.env['test.pallet'])
        self.assertTrue(Unit.name.translate)
        self.assertIn('lang', self.registry.field_depends_context[Unit.display_name])
        self.assertIn('lang', self.registry.field_depends_context[Box.display_name])
        self.assertIn('lang', self.registry.field_depends_context[Pallet.display_name])

    def test_multi_write_m2o_inherits(self):
        """Verify that an inherits m2o field can be written to in batch"""
        unit_foo = self.env['test.unit'].create({'name': 'foo'})
        boxes = self.env['test.box'].create([{'unit_id': unit_foo.id}] * 5)

        unit_bar = self.env['test.unit'].create({'name': 'bar'})
        boxes.unit_id = unit_bar

        self.assertEqual(boxes.mapped('unit_id.name'), ['bar'])
