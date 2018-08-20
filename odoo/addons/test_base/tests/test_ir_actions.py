# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

import odoo
from odoo.exceptions import UserError, ValidationError
from odoo.tools import mute_logger
from odoo.tests import common


class TestServerActionsBase(common.TransactionCase):

    def setUp(self):
        super(TestServerActionsBase, self).setUp()

        # Data on which we will run the server action
        self.test_m2o_id = self.env['test_m2o_relational.model'].create({
            'name': 'Testing Relational Record',
            'code': 'TY',
        })
        self.test_record = self.env['test_base.model'].create({
            'name': 'Testing Base Record',
            'email': 'test@test.com',
            'many2one_id': self.test_m2o_id.id,
        })
        self.context = {
            'active_model': 'test_base.model',
            'active_id': self.test_record.id,
        }

        # Model data
        Model = self.env['ir.model']
        Fields = self.env['ir.model.fields']
        self.base_test_model = Model.search([('model', '=', 'test_base.model')])
        self.base_test_name_field = Fields.search([('model', '=', 'test_base.model'), ('name', '=', 'name')])
        self.base_test_email_field = Fields.search([('model', '=', 'test_base.model'), ('name', '=', 'email')])
        self.base_test_parent_id_field = Fields.search([('model', '=', 'test_base.model'), ('name', '=', 'parent_id')])
        self.relational_model = Model.search([('model', '=', 'test_m2o_relational.model')])
        self.relational_name_field = Fields.search([('model', '=', 'test_m2o_relational.model'), ('name', '=', 'name')])
        self.relational_code_field = Fields.search([('model', '=', 'test_m2o_relational.model'), ('name', '=', 'code')])

        # create server action to
        self.action = self.env['ir.actions.server'].create({
            'name': 'TestAction',
            'model_id': self.base_test_model.id,
            'state': 'code',
            'code': 'record.write({"name": "MyName"})',
        })

class TestServerActions(TestServerActionsBase):

    def test_00_action(self):
        self.action.with_context(self.context).run()
        self.assertEqual(self.test_record.name, 'MyName', 'ir_actions_server: invalid condition check')
        self.test_record.write({'name': False})

        # Do: create contextual action
        self.action.create_action()
        self.assertEqual(self.action.binding_model_id.model, 'test_base.model')

        # Do: remove contextual action
        self.action.unlink_action()
        self.assertFalse(self.action.binding_model_id)

    def test_10_code(self):
        self.action.write({
            'state': 'code',
            'code': ("record_name = record.name + '_code'\n"
                     "record.env['test_base.model'].create({'name': record_name})"),
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: code server action correctly finished should return False')
        record = self.test_record.search([('name', 'ilike', 'Testing Base Record_code')])
        self.assertEqual(len(record), 1, 'ir_actions_server: 1 new record should have been created')

    def test_20_crud_create(self):
        _email = 'Test@new.com'
        _name = 'TestNew'

        # Do: create a new record in the same model and link it
        self.action.write({
            'state': 'object_create',
            'crud_model_id': self.action.model_id.id,
            'link_field_id': self.base_test_parent_id_field.id,
            'fields_lines': [(0, 0, {'col1': self.base_test_name_field.id, 'value': _name}),
                             (0, 0, {'col1': self.base_test_email_field.id, 'value': _email})],
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new record created
        record = self.test_record.search([('name', 'ilike', _name)])
        self.assertEqual(len(record), 1, 'ir_actions_server: TODO')
        self.assertEqual(record.email, _email, 'ir_actions_server: TODO')
        # Test: new record linked
        self.assertEqual(self.test_record.parent_id, record, 'ir_actions_server: TODO')

        # Do: create a new record in another model
        self.action.write({
            'state': 'object_create',
            'crud_model_id': self.relational_model.id,
            'link_field_id': False,
            'fields_lines': [(5,),
                             (0, 0, {'col1': self.relational_name_field.id, 'value': 'record.name', 'evaluation_type': 'equation'}),
                             (0, 0, {'col1': self.relational_code_field.id, 'value': 'record.name[0:2]', 'evaluation_type': 'equation'})],
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new relational record created
        record = self.test_m2o_id.search([('name', 'ilike', 'Testing Base Record')])
        self.assertEqual(len(record), 1, 'ir_actions_server: TODO')
        self.assertEqual(record.code, 'Te', 'ir_actions_server: TODO')

    def test_30_crud_write(self):
        _name = 'TestNew'

        # Do: update record name
        self.action.write({
            'state': 'object_write',
            'fields_lines': [(0, 0, {'col1': self.base_test_name_field.id, 'value': _name})],
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: record updated
        record = self.test_record.search([('name', 'ilike', _name)])
        self.assertEqual(len(record), 1, 'ir_actions_server: TODO')
        self.assertEqual(record.email, 'test@test.com', 'ir_actions_server: TODO')

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_40_multi(self):
        # Data: 2 server actions that will be nested
        action1 = self.action.create({
            'name': 'Subaction1',
            'sequence': 1,
            'model_id': self.base_test_model.id,
            'state': 'code',
            'code': 'action = {"type": "ir.actions.act_window"}',
        })
        action2 = self.action.create({
            'name': 'Subaction2',
            'sequence': 2,
            'model_id': self.base_test_model.id,
            'crud_model_id': self.base_test_model.id,
            'state': 'object_create',
            'fields_lines': [(0, 0, {'col1': self.base_test_name_field.id, 'value': 'RaoulettePoiluchette'}),
                             (0, 0, {'col1': self.base_test_email_field.id, 'value': 'TestingEmail'})],
        })
        action3 = self.action.create({
            'name': 'Subaction3',
            'sequence': 3,
            'model_id': self.base_test_model.id,
            'state': 'code',
            'code': 'action = {"type": "ir.actions.act_url"}',
        })
        self.action.write({
            'state': 'multi',
            'child_ids': [(6, 0, [action1.id, action2.id, action3.id])],
        })

        # Do: run the action
        res = self.action.with_context(self.context).run()

        # Test: new record created
        # currently base test overrides default['name'] whatever its value
        record = self.test_record.search([('name', 'ilike', 'RaoulettePoiluchette')])
        self.assertEqual(len(record), 1)
        # Test: action returned
        self.assertEqual(res.get('type'), 'ir.actions.act_url')

        # Test loops
        with self.assertRaises(ValidationError):
            self.action.write({
                'child_ids': [(6, 0, [self.action.id])]
            })


class TestActionBindings(common.TransactionCase):

    def test_bindings(self):
        """ check the action bindings on models """
        Actions = self.env['ir.actions.actions']

        # first make sure there is no bound action
        self.env.ref('test_base.action_base_test').unlink()
        bindings = Actions.get_bindings('test_base.model')
        self.assertFalse(bindings['action'])
        self.assertFalse(bindings['report'])
        # create action bindings, and check the returned bindings
        action1 = self.env.ref('test_base.action_base_test_model')
        action2 = self.env.ref('test_base.ir_default_test_action')
        action3 = self.env['ir.actions.report'].search([('groups_id', '=', False)], limit=1)
        action1.binding_model_id = action2.binding_model_id \
                                 = action3.binding_model_id \
                                 = self.env['ir.model']._get('test_base.model')

        bindings = Actions.get_bindings('test_base.model')
        self.assertItemsEqual(
            bindings['action'],
            (action1 + action2).read(),
            "Wrong action bindings",
        )
        self.assertItemsEqual(
            bindings['report'],
            action3.read(),
            "Wrong action bindings",
        )

        # add a group on an action, and check that it is not returned
        group = self.env.ref('base.group_user')
        action2.groups_id += group
        self.env.user.groups_id -= group

        bindings = Actions.get_bindings('test_base.model')
        self.assertItemsEqual(
            bindings['action'],
            action1.read(),
            "Wrong action bindings",
        )
        self.assertItemsEqual(
            bindings['report'],
            action3.read(),
            "Wrong action bindings",
        )


class TestCustomFields(common.TransactionCase):
    MODEL = 'test_base.model'
    COMODEL = 'test_m2o_relational.model'

    def setUp(self):
        # check that the registry is properly reset
        registry = odoo.registry()
        fnames = set(registry[self.MODEL]._fields)
        @self.addCleanup
        def check_registry():
            assert set(registry[self.MODEL]._fields) == fnames

        super(TestCustomFields, self).setUp()

        # use a test cursor instead of a real cursor
        self.registry.enter_test_mode(self.cr)
        self.addCleanup(self.registry.leave_test_mode)

    def create_field(self, name, *, field_type='char'):
        """ create a custom field and return it """
        model = self.env['ir.model'].search([('model', '=', self.MODEL)])
        field = self.env['ir.model.fields'].create({
            'model_id': model.id,
            'name': name,
            'field_description': name,
            'ttype': field_type,
        })
        self.assertIn(name, self.env[self.MODEL]._fields)
        return field

    def create_view(self, name):
        """ create a view with the given field name """
        return self.env['ir.ui.view'].create({
            'name': 'yet another view',
            'model': self.MODEL,
            'arch': '<tree string="X"><field name="%s"/></tree>' % name,
        })

    def test_create_custom(self):
        """ custom field names must be start with 'x_' """
        with self.assertRaises(ValidationError):
            self.create_field('foo')

    def test_rename_custom(self):
        """ custom field names must be start with 'x_' """
        field = self.create_field('x_foo')
        with self.assertRaises(ValidationError):
            field.name = 'foo'

    def test_create_valid(self):
        """ field names must be valid pg identifiers """
        with self.assertRaises(ValidationError):
            self.create_field('x_foo bar')

    def test_rename_valid(self):
        """ field names must be valid pg identifiers """
        field = self.create_field('x_foo')
        with self.assertRaises(ValidationError):
            field.name = 'x_foo bar'

    def test_create_unique(self):
        """ one cannot create two fields with the same name on a given model """
        self.create_field('x_foo')
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.create_field('x_foo')

    def test_rename_unique(self):
        """ one cannot create two fields with the same name on a given model """
        field1 = self.create_field('x_foo')
        field2 = self.create_field('x_bar')
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            field2.name = field1.name

    def test_remove_without_view(self):
        """ try removing a custom field that does not occur in views """
        field = self.create_field('x_foo')
        field.unlink()

    def test_rename_without_view(self):
        """ try renaming a custom field that does not occur in views """
        field = self.create_field('x_foo')
        field.name = 'x_bar'

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_remove_with_view(self):
        """ try removing a custom field that occurs in a view """
        field = self.create_field('x_foo')
        self.create_view('x_foo')

        # try to delete the field, this should fail but not modify the registry
        with self.assertRaises(UserError):
            field.unlink()
        self.assertIn('x_foo', self.env[self.MODEL]._fields)

    @mute_logger('odoo.addons.base.models.ir_ui_view')
    def test_rename_with_view(self):
        """ try renaming a custom field that occurs in a view """
        field = self.create_field('x_foo')
        self.create_view('x_foo')

        # try to delete the field, this should fail but not modify the registry
        with self.assertRaises(UserError):
            field.name = 'x_bar'
        self.assertIn('x_foo', self.env[self.MODEL]._fields)

    def test_unlink_with_inverse(self):
        """ create a custom o2m and then delete its m2o inverse """
        model = self.env['ir.model']._get(self.MODEL)
        comodel = self.env['ir.model']._get(self.COMODEL)

        m2o_field = self.env['ir.model.fields'].create({
            'model_id': comodel.id,
            'name': 'x_my_m2o',
            'field_description': 'my_m2o',
            'ttype': 'many2one',
            'relation': self.MODEL,
        })

        o2m_field = self.env['ir.model.fields'].create({
            'model_id': model.id,
            'name': 'x_my_o2m',
            'field_description': 'my_o2m',
            'ttype': 'one2many',
            'relation': self.COMODEL,
            'relation_field': m2o_field.name,
        })

        # normal mode: you cannot break dependencies
        with self.assertRaises(UserError):
            m2o_field.unlink()

        # uninstall mode: unlink dependant fields
        m2o_field.with_context(_force_unlink=True).unlink()
        self.assertFalse(o2m_field.exists())

    def test_unlink_with_dependant(self):
        """ create a computed field, then delete its dependency """
        # Also applies to compute fields
        comodel = self.env['ir.model'].search([('model', '=', self.COMODEL)])

        field = self.create_field('x_my_char')
        dependant = self.env['ir.model.fields'].create({
            'model_id': comodel.id,
            'name': 'x_oh_boy',
            'field_description': 'x_oh_boy',
            'ttype': 'char',
            'related': 'base_model_id.x_my_char',
        })
        # normal mode: you cannot break dependencies
        with self.assertRaises(UserError):
            field.unlink()

        # uninstall mode: unlink dependant fields
        field.with_context(_force_unlink=True).unlink()
        self.assertFalse(dependant.exists())

    def test_create_binary(self):
        """ binary custom fields should be created as attachment=True to avoid
        bloating the DB when creating e.g. image fields via studio
        """
        self.create_field('x_image', field_type='binary')
        custom_binary = self.env[self.MODEL]._fields['x_image']

        self.assertTrue(custom_binary.attachment)
