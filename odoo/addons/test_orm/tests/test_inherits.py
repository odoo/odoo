from odoo.tests import tagged, common
from odoo.exceptions import ValidationError
from odoo import Command
from unittest.mock import patch
from odoo.tools import mute_logger


@tagged('at_install', '-post_install')  # LEGACY at_install
class test_inherits(common.TransactionCase):

    def test_ir_model_inherit(self):
        imi = self.env['ir.model.inherit'].search(
            [('model_id.model', '=', 'test.box')]
        )
        self.assertEqual(len(imi), 1)
        self.assertEqual(imi.parent_id.model, 'test.unit')
        self.assertEqual(imi.parent_field_id.name, 'unit_id')

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
        pallet = self.env.ref('test_orm.pallet_a')
        self.assertEqual(pallet.read(['name']), [{'id': pallet.id, 'name': 'Unit A'}])

    def test_write_3_levels_inherits(self):
        """ Check that we can create an inherits on 3 levels """
        pallet = self.env.ref('test_orm.pallet_a')
        pallet.write({'name': 'C'})
        self.assertEqual(pallet.name, 'C')

    def test_write_4_one2many(self):
        """ Check that we can write on an inherited one2many field. """
        box = self.env.ref('test_orm.box_a')
        box.write({'line_ids': [Command.create({'name': 'Line 1'})]})
        self.assertTrue(all(box.line_ids._ids))
        self.assertEqual(box.line_ids.mapped('name'), ['Line 1'])
        self.assertEqual(box.line_ids, box.unit_id.line_ids)
        self.env.flush_all()
        box.invalidate_model(['line_ids'])
        box.write({'line_ids': [Command.create({'name': 'Line 2'})]})
        self.assertTrue(all(box.line_ids._ids))
        self.assertEqual(box.line_ids.mapped('name'), ['Line 1', 'Line 2'])
        self.assertEqual(box.line_ids, box.unit_id.line_ids)
        self.env.flush_all()
        box.invalidate_model(['line_ids'])
        box.write({'line_ids': [Command.update(box.line_ids[0].id, {'name': 'First line'})]})
        self.assertTrue(all(box.line_ids._ids))
        self.assertEqual(box.line_ids.mapped('name'), ['First line', 'Line 2'])
        self.assertEqual(box.line_ids, box.unit_id.line_ids)

    def test_write_5_field_readonly(self):
        """ Check that we can write on an inherited readonly field. """
        self.assertTrue(self.env['test.box']._fields['readonly_name'])
        box = self.env.ref('test_orm.box_a')
        box.write({'readonly_name': "Superuser's box"})
        self.assertEqual(box.readonly_name, "Superuser's box")
        self.assertEqual(box.unit_id.readonly_name, "Superuser's box")

    def test_ir_model_data_inherits(self):
        """ Check the existence of the correct ir.model.data """
        IrModelData = self.env['ir.model.data']
        field = IrModelData.search([('name', '=', 'field_test_unit__name')])
        self.assertEqual(len(field), 1)
        self.assertEqual(field.module, 'test_orm')

        field = IrModelData.search([('name', '=', 'field_test_box__name')])
        self.assertEqual(len(field), 1)
        self.assertEqual(field.module, 'test_orm')

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

    def test_access_rights_on_parent(self):
        # introduce an ir.rule on the parent model of 'test.box'
        self.env['ir.rule'].create({
            'name': "Only access to state a",
            'model_id': self.env['ir.model']._get('test.unit').id,
            'domain_force': [('state', '=', 'a')],
        })
        user = self.env['res.users'].create({
            'name': 'test',
            'login': 'test_access_rights_on_parent',
            'group_ids': [(6, 0, [self.env.ref("base.group_system").id])],
        })
        model = self.env['test.box'].with_user(user)
        box_ids = model.sudo().create([
            {'name': 'a', 'state': 'a'},
            {'name': 'b', 'state': 'b'},
        ]).ids

        # search with an order on the parent model: the ir.rule above should
        # appear in the WHERE clause, but not in the JOIN clause used to reach
        # the inherited field(s)
        model.search([('id', 'in', box_ids)], order='readonly_name')  # warmup
        with self.assertQueries(["""
            SELECT "test_box"."id"
            FROM "test_box"
            JOIN "test_unit" AS "test_box__unit_id" ON ("test_box"."unit_id" = "test_box__unit_id"."id")
            WHERE "test_box"."id" IN %s
            AND "test_box__unit_id"."state" IN %s
            ORDER BY "test_box__unit_id"."readonly_name"
        """]):
            model.search([('id', 'in', box_ids)], order='readonly_name')

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

    def test_write_cache_x2m_unstored_inherits(self):
        # test_unstored_inherits_shared_line_ids field is inherited through inheritS
        # writing on that field invokes its inverse method, and should not write the value twice on the field
        parent = self.env['test.unstored.inherits.parent'].create({'name': 'foo'})

        field = parent._fields['test_unstored_inherits_shared_line_ids']
        with patch.object(field, '_cache_missing_ids', side_effect=lambda recs: iter(recs.ids)):
            parent.write({'test_unstored_inherits_shared_line_ids': [(0, 0, {'name': 'Coucou'})]})
            self.assertTrue(parent.child_id)
            self.assertEqual(len(parent.child_id.test_unstored_inherits_shared_line_ids), 1)


@tagged('at_install', '-post_install')
class TestInherits(common.TransactionCase):
    """ test the behavior of the orm for models that use _inherits;
        specifically: res.users, that inherits from res.partner
    """

    def test_default(self):
        """ `default_get` cannot return a dictionary or a new id """
        defaults = self.env['res.users'].default_get(['partner_id'])
        if 'partner_id' in defaults:
            self.assertIsInstance(defaults['partner_id'], (bool, int))

    def test_create(self):
        """ creating a user should automatically create a new partner """
        partners_before = self.env['res.partner'].search([])
        user_foo = self.env['res.users'].create({'name': 'Foo', 'login': 'foo'})

        self.assertNotIn(user_foo.partner_id, partners_before)

    def test_create_with_ancestor(self):
        """ creating a user with a specific 'partner_id' should not create a new partner """
        partner_foo = self.env['res.partner'].create({'name': 'Foo'})
        partners_before = self.env['res.partner'].search([])
        user_foo = self.env['res.users'].create({'partner_id': partner_foo.id, 'login': 'foo'})
        partners_after = self.env['res.partner'].search([])

        self.assertEqual(partners_before, partners_after)
        self.assertEqual(user_foo.name, 'Foo')
        self.assertEqual(user_foo.partner_id, partner_foo)

    @mute_logger('odoo.models')
    def test_read(self):
        """ inherited fields should be read without any indirection """
        user_foo = self.env['res.users'].create({'name': 'Foo', 'login': 'foo'})
        user_values, = user_foo.read()
        partner_values, = user_foo.partner_id.read()

        self.assertEqual(user_values['name'], partner_values['name'])
        self.assertEqual(user_foo.name, user_foo.partner_id.name)

    @mute_logger('odoo.models')
    def test_copy(self):
        """ copying a user should automatically copy its partner, too """
        user_foo = self.env['res.users'].create({
            'name': 'Foo',
            'login': 'foo',
            'employee': True,
        })
        foo_before, = user_foo.read()
        del foo_before['create_date']
        del foo_before['write_date']
        user_bar = user_foo.copy({'login': 'bar'})
        foo_after, = user_foo.read()
        del foo_after['create_date']
        del foo_after['write_date']
        self.assertEqual(foo_before, foo_after)

        self.assertEqual(user_bar.name, 'Foo (copy)')
        self.assertEqual(user_bar.login, 'bar')
        self.assertEqual(user_foo.employee, user_bar.employee)
        self.assertNotEqual(user_foo.id, user_bar.id)
        self.assertNotEqual(user_foo.partner_id.id, user_bar.partner_id.id)

    @mute_logger('odoo.models')
    def test_copy_with_ancestor(self):
        """ copying a user with 'parent_id' in defaults should not duplicate the partner """
        user_foo = self.env['res.users'].create({'login': 'foo', 'name': 'Foo', 'signature': 'Foo'})
        partner_bar = self.env['res.partner'].create({'name': 'Bar'})

        foo_before, = user_foo.read()
        del foo_before['create_date']
        del foo_before['write_date']
        del foo_before['login_date']
        partners_before = self.env['res.partner'].search([])
        user_bar = user_foo.copy({'partner_id': partner_bar.id, 'login': 'bar'})
        foo_after, = user_foo.read()
        del foo_after['create_date']
        del foo_after['write_date']
        del foo_after['login_date']
        partners_after = self.env['res.partner'].search([])

        self.assertEqual(foo_before, foo_after)
        self.assertEqual(partners_before, partners_after)

        self.assertNotEqual(user_foo.id, user_bar.id)
        self.assertEqual(user_bar.partner_id.id, partner_bar.id)
        self.assertEqual(user_bar.login, 'bar', "login is given from copy parameters")
        self.assertFalse(user_bar.password, "password should not be copied from original record")
        self.assertEqual(user_bar.name, 'Bar', "name is given from specific partner")
        self.assertEqual(user_bar.signature, user_foo.signature, "signature should be copied")

    @mute_logger('odoo.models')
    def test_write_date(self):
        """ modifying inherited fields must update write_date """
        user = self.env.user
        write_date_before = user.write_date

        # write base64 image
        user.write({'image_1920': 'R0lGODlhAQABAIAAAP///////yH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=='})
        write_date_after = user.write_date
        self.assertNotEqual(write_date_before, write_date_after)
