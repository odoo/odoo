# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from psycopg2 import IntegrityError, ProgrammingError

import odoo
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.tools import mute_logger
from odoo.tests import common
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo import Command


class TestServerActionsBase(TransactionCaseWithUserDemo):

    def setUp(self):
        super(TestServerActionsBase, self).setUp()

        # Data on which we will run the server action
        self.test_country = self.env['res.country'].create({
            'name': 'TestingCountry',
            'code': 'TY',
            'address_format': 'SuperFormat',
        })
        self.test_partner = self.env['res.partner'].create({
            'name': 'TestingPartner',
            'city': 'OrigCity',
            'country_id': self.test_country.id,
        })
        self.context = {
            'active_model': 'res.partner',
            'active_id': self.test_partner.id,
        }

        # Model data
        Model = self.env['ir.model']
        Fields = self.env['ir.model.fields']
        self.comment_html = '<p>MyComment</p>'
        self.res_partner_model = Model.search([('model', '=', 'res.partner')])
        self.res_partner_name_field = Fields.search([('model', '=', 'res.partner'), ('name', '=', 'name')])
        self.res_partner_city_field = Fields.search([('model', '=', 'res.partner'), ('name', '=', 'city')])
        self.res_partner_country_field = Fields.search([('model', '=', 'res.partner'), ('name', '=', 'country_id')])
        self.res_partner_parent_field = Fields.search([('model', '=', 'res.partner'), ('name', '=', 'parent_id')])
        self.res_partner_children_field = Fields.search([('model', '=', 'res.partner'), ('name', '=', 'child_ids')])
        self.res_partner_category_field = Fields.search([('model', '=', 'res.partner'), ('name', '=', 'category_id')])
        self.res_country_model = Model.search([('model', '=', 'res.country')])
        self.res_country_name_field = Fields.search([('model', '=', 'res.country'), ('name', '=', 'name')])
        self.res_country_code_field = Fields.search([('model', '=', 'res.country'), ('name', '=', 'code')])
        self.res_partner_category_model = Model.search([('model', '=', 'res.partner.category')])
        self.res_partner_category_name_field = Fields.search([('model', '=', 'res.partner.category'), ('name', '=', 'name')])

        # create server action to
        self.action = self.env['ir.actions.server'].create({
            'name': 'TestAction',
            'model_id': self.res_partner_model.id,
            'model_name': 'res.partner',
            'state': 'code',
            'code': 'record.write({"comment": "%s"})' % self.comment_html,
        })


class TestServerActions(TestServerActionsBase):

    def test_00_action(self):
        self.action.with_context(self.context).run()
        self.assertEqual(self.test_partner.comment, self.comment_html, 'ir_actions_server: invalid condition check')
        self.test_partner.write({'comment': False})

        # Do: create contextual action
        self.action.create_action()
        self.assertEqual(self.action.binding_model_id.model, 'res.partner')

        # Do: remove contextual action
        self.action.unlink_action()
        self.assertFalse(self.action.binding_model_id)

    def test_10_code(self):
        self.action.write({
            'state': 'code',
            'code': ("partner_name = record.name + '_code'\n"
                     "record.env['res.partner'].create({'name': partner_name})"),
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: code server action correctly finished should return False')

        partners = self.test_partner.search([('name', 'ilike', 'TestingPartner_code')])
        self.assertEqual(len(partners), 1, 'ir_actions_server: 1 new partner should have been created')

    def test_20_crud_create(self):
        # Do: create a new record in another model
        self.action.write({
            'state': 'object_create',
            'crud_model_id': self.res_country_model.id,
            'link_field_id': False,
            'fields_lines': [Command.clear(),
                             Command.create({'col1': self.res_country_name_field.id, 'value': 'record.name', 'evaluation_type': 'equation'}),
                             Command.create({'col1': self.res_country_code_field.id, 'value': 'record.name[0:2]', 'evaluation_type': 'equation'})],
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new country created
        country = self.test_country.search([('name', 'ilike', 'TestingPartner')])
        self.assertEqual(len(country), 1, 'ir_actions_server: TODO')
        self.assertEqual(country.code, 'TE', 'ir_actions_server: TODO')

    def test_20_crud_create_link_many2one(self):
        _city = 'TestCity'
        _name = 'TestNew'

        # Do: create a new record in the same model and link it with a many2one
        self.action.write({
            'state': 'object_create',
            'crud_model_id': self.action.model_id.id,
            'link_field_id': self.res_partner_parent_field.id,
            'fields_lines': [Command.create({'col1': self.res_partner_name_field.id, 'value': _name}),
                             Command.create({'col1': self.res_partner_city_field.id, 'value': _city})],
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new partner created
        partner = self.test_partner.search([('name', 'ilike', _name)])
        self.assertEqual(len(partner), 1, 'ir_actions_server: TODO')
        self.assertEqual(partner.city, _city, 'ir_actions_server: TODO')
        # Test: new partner linked
        self.assertEqual(self.test_partner.parent_id, partner, 'ir_actions_server: TODO')

    def test_20_crud_create_link_one2many(self):
        _name = 'TestNew'

        # Do: create a new record in the same model and link it with a one2many
        self.action.write({
            'state': 'object_create',
            'crud_model_id': self.action.model_id.id,
            'link_field_id': self.res_partner_children_field.id,
            'fields_lines': [Command.create({'col1': self.res_partner_name_field.id, 'value': _name})],
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new partner created
        partner = self.test_partner.search([('name', 'ilike', _name)])
        self.assertEqual(len(partner), 1, 'ir_actions_server: TODO')
        self.assertEqual(partner.name, _name, 'ir_actions_server: TODO')
        # Test: new partner linked
        self.assertIn(partner, self.test_partner.child_ids, 'ir_actions_server: TODO')

    def test_20_crud_create_link_many2many(self):
        # Do: create a new record in another model
        self.action.write({
            'state': 'object_create',
            'crud_model_id': self.res_partner_category_model.id,
            'link_field_id': self.res_partner_category_field.id,
            'fields_lines': [Command.create({'col1': self.res_partner_category_name_field.id, 'value': 'record.name', 'evaluation_type': 'equation'})],
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new category created
        category = self.env['res.partner.category'].search([('name', 'ilike', 'TestingPartner')])
        self.assertEqual(len(category), 1, 'ir_actions_server: TODO')
        self.assertIn(category, self.test_partner.category_id)

    def test_30_crud_write(self):
        _name = 'TestNew'

        # Do: update partner name
        self.action.write({
            'state': 'object_write',
            'fields_lines': [Command.create({'col1': self.res_partner_name_field.id, 'value': _name})],
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: partner updated
        partner = self.test_partner.search([('name', 'ilike', _name)])
        self.assertEqual(len(partner), 1, 'ir_actions_server: TODO')
        self.assertEqual(partner.city, 'OrigCity', 'ir_actions_server: TODO')

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_40_multi(self):
        # Data: 2 server actions that will be nested
        action1 = self.action.create({
            'name': 'Subaction1',
            'sequence': 1,
            'model_id': self.res_partner_model.id,
            'state': 'code',
            'code': 'action = {"type": "ir.actions.act_window"}',
        })
        action2 = self.action.create({
            'name': 'Subaction2',
            'sequence': 2,
            'model_id': self.res_partner_model.id,
            'crud_model_id': self.res_partner_model.id,
            'state': 'object_create',
            'fields_lines': [Command.create({'col1': self.res_partner_name_field.id, 'value': 'RaoulettePoiluchette'}),
                             Command.create({'col1': self.res_partner_city_field.id, 'value': 'TestingCity'})],
        })
        action3 = self.action.create({
            'name': 'Subaction3',
            'sequence': 3,
            'model_id': self.res_partner_model.id,
            'state': 'code',
            'code': 'action = {"type": "ir.actions.act_url"}',
        })
        self.action.write({
            'state': 'multi',
            'child_ids': [Command.set([action1.id, action2.id, action3.id])],
        })

        # Do: run the action
        res = self.action.with_context(self.context).run()

        # Test: new partner created
        # currently res_partner overrides default['name'] whatever its value
        partner = self.test_partner.search([('name', 'ilike', 'RaoulettePoiluchette')])
        self.assertEqual(len(partner), 1)
        # Test: action returned
        self.assertEqual(res.get('type'), 'ir.actions.act_url')

        # Test loops
        with self.assertRaises(ValidationError):
            self.action.write({
                'child_ids': [Command.set([self.action.id])]
            })

    def test_50_groups(self):
        """ check the action is returned only for groups dedicated to user """
        Actions = self.env['ir.actions.actions']

        group0 = self.env['res.groups'].create({'name': 'country group'})

        self.context = {
            'active_model': 'res.country',
            'active_id': self.test_country.id,
        }

        # Do: update model and group
        self.action.write({
            'model_id': self.res_country_model.id,
            'binding_model_id': self.res_country_model.id,
            'groups_id': [Command.link(group0.id)],
            'code': 'record.write({"vat_label": "VatFromTest"})',
        })

        # Test: action is not returned
        bindings = Actions.get_bindings('res.country')
        self.assertFalse(bindings)

        with self.assertRaises(AccessError):
            self.action.with_context(self.context).run()
        self.assertFalse(self.test_country.vat_label)

        # add group to the user, and test again
        self.env.user.write({'groups_id': [Command.link(group0.id)]})

        bindings = Actions.get_bindings('res.country')
        self.assertItemsEqual(bindings.get('action'), self.action.read(['name', 'sequence', 'binding_view_types']))

        self.action.with_context(self.context).run()
        self.assertEqual(self.test_country.vat_label, 'VatFromTest', 'vat label should be changed to VatFromTest')

    def test_60_sort(self):
        """ check the actions sorted by sequence """
        Actions = self.env['ir.actions.actions']

        # Do: update model
        self.action.write({
            'model_id': self.res_country_model.id,
            'binding_model_id': self.res_country_model.id,
        })
        self.action2 = self.action.copy({'name': 'TestAction2', 'sequence': 1})

        # Test: action returned by sequence
        bindings = Actions.get_bindings('res.country')
        self.assertEqual([vals.get('name') for vals in bindings['action']], ['TestAction2', 'TestAction'])
        self.assertEqual([vals.get('sequence') for vals in bindings['action']], [1, 5])

    def test_70_copy_action(self):
        # first check that the base case (reset state) works normally
        r = self.env['ir.actions.todo'].create({
            'action_id': self.action.id,
            'state': 'done',
        })
        self.assertEqual(r.state, 'done')
        self.assertEqual(
            r.copy().state, 'open',
            "by default state should be reset by copy"
        )

        # then check that on server action we've changed that
        self.assertEqual(
            self.action.copy().state, 'code',
            "copying a server action should not reset the state"
        )

    def test_80_permission(self):
        self.action.write({
            'state': 'code',
            'code': """record.write({'date': datetime.date.today()})""",
        })

        user_demo = self.user_demo
        self_demo = self.action.with_user(user_demo.id)

        # can write on contact partner
        self.test_partner.type = "contact"
        self.test_partner.with_user(user_demo.id).check_access_rule("write")

        self_demo.with_context(self.context).run()
        self.assertEqual(self.test_partner.date, date.today())

        # but can not write on private address
        self.test_partner.type = "private"
        with self.assertRaises(AccessError):
            self.test_partner.with_user(user_demo.id).check_access_rule("write")
        # nor execute a server action on it
        with self.assertRaises(AccessError), mute_logger('odoo.addons.base.models.ir_actions'):
            self_demo.with_context(self.context).run()


class TestCustomFields(common.TransactionCase):
    MODEL = 'res.partner'
    COMODEL = 'res.users'

    def setUp(self):
        # check that the registry is properly reset
        fnames = set(self.registry[self.MODEL]._fields)

        @self.addCleanup
        def check_registry():
            assert set(self.registry[self.MODEL]._fields) == fnames

        self.addCleanup(self.registry.reset_changes)
        self.addCleanup(self.registry.clear_caches)

        super().setUp()

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

    def test_unlink_base(self):
        """ one cannot delete a non-custom field """
        field = self.env['ir.model.fields']._get(self.MODEL, 'ref')
        self.assertTrue(field)

        with self.assertRaisesRegex(UserError, 'This column contains module data'):
            field.unlink()

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
            'related': 'partner_id.x_my_char',
        })

        # normal mode: you cannot break dependencies
        with self.assertRaises(UserError):
            field.unlink()

        # uninstall mode: unlink dependant fields
        field.with_context(_force_unlink=True).unlink()
        self.assertFalse(dependant.exists())

    def test_unlink_inherited_custom(self):
        """ Creating a field on a model automatically creates an inherited field
            in the comodel, and the latter can only be removed by deleting the
            "parent" field.
        """
        field = self.create_field('x_foo')
        self.assertEqual(field.state, 'manual')

        inherited_field = self.env['ir.model.fields']._get(self.COMODEL, 'x_foo')
        self.assertTrue(inherited_field)
        self.assertEqual(inherited_field.state, 'base')

        # one cannot delete the inherited field itself
        with self.assertRaises(UserError):
            inherited_field.unlink()

        # but the inherited field is deleted when its parent field is
        field.unlink()
        self.assertFalse(field.exists())
        self.assertFalse(inherited_field.exists())
        self.assertFalse(self.env['ir.model.fields'].search_count([
            ('model', 'in', [self.MODEL, self.COMODEL]),
            ('name', '=', 'x_foo'),
        ]))

    def test_create_binary(self):
        """ binary custom fields should be created as attachment=True to avoid
        bloating the DB when creating e.g. image fields via studio
        """
        self.create_field('x_image', field_type='binary')
        custom_binary = self.env[self.MODEL]._fields['x_image']

        self.assertTrue(custom_binary.attachment)

    def test_related_field(self):
        """ create a custom related field, and check filled values """
        #
        # Add a custom field equivalent to the following definition:
        #
        # class Partner(models.Model)
        #     _inherit = 'res.partner'
        #     x_oh_boy = fields.Char(related="country_id.code", store=True)
        #

        # pick N=100 records in comodel
        countries = self.env['res.country'].search([('code', '!=', False)], limit=100)
        self.assertEqual(len(countries), 100, "Not enough records in comodel 'res.country'")

        # create records in model, with N distinct values for the related field
        partners = self.env['res.partner'].create([
            {'name': country.code, 'country_id': country.id} for country in countries
        ])
        partners.flush()

        # determine how many queries it takes to create a non-computed field
        query_count = self.cr.sql_log_count
        self.env['ir.model.fields'].create({
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'name': 'x_oh_box',
            'field_description': 'x_oh_box',
            'ttype': 'char',
        })
        query_count = self.cr.sql_log_count - query_count

        # create the related field, and assert it only takes 1 extra query
        with self.assertQueryCount(query_count + 1):
            self.env['ir.model.fields'].create({
                'model_id': self.env['ir.model']._get_id('res.partner'),
                'name': 'x_oh_boy',
                'field_description': 'x_oh_boy',
                'ttype': 'char',
                'related': 'country_id.code',
                'store': True,
            })

        # check the computed values
        for partner in partners:
            self.assertEqual(partner.x_oh_boy, partner.country_id.code)

    def test_selection(self):
        """ custom selection field """
        Model = self.env[self.MODEL]
        model = self.env['ir.model'].search([('model', '=', self.MODEL)])
        field = self.env['ir.model.fields'].create({
            'model_id': model.id,
            'name': 'x_sel',
            'field_description': "Custom Selection",
            'ttype': 'selection',
            'selection_ids': [
                Command.create({'value': 'foo', 'name': 'Foo', 'sequence': 0}),
                Command.create({'value': 'bar', 'name': 'Bar', 'sequence': 1}),
            ],
        })

        x_sel = Model._fields['x_sel']
        self.assertEqual(x_sel.type, 'selection')
        self.assertEqual(x_sel.selection, [('foo', 'Foo'), ('bar', 'Bar')])

        # add selection value 'baz'
        field.selection_ids.create({
            'field_id': field.id, 'value': 'baz', 'name': 'Baz', 'sequence': 2,
        })
        x_sel = Model._fields['x_sel']
        self.assertEqual(x_sel.type, 'selection')
        self.assertEqual(x_sel.selection, [('foo', 'Foo'), ('bar', 'Bar'), ('baz', 'Baz')])

        # assign values to records
        rec1 = Model.create({'name': 'Rec1', 'x_sel': 'foo'})
        rec2 = Model.create({'name': 'Rec2', 'x_sel': 'bar'})
        rec3 = Model.create({'name': 'Rec3', 'x_sel': 'baz'})
        self.assertEqual(rec1.x_sel, 'foo')
        self.assertEqual(rec2.x_sel, 'bar')
        self.assertEqual(rec3.x_sel, 'baz')

        # remove selection value 'foo'
        field.selection_ids[0].unlink()
        x_sel = Model._fields['x_sel']
        self.assertEqual(x_sel.type, 'selection')
        self.assertEqual(x_sel.selection, [('bar', 'Bar'), ('baz', 'Baz')])

        self.assertEqual(rec1.x_sel, False)
        self.assertEqual(rec2.x_sel, 'bar')
        self.assertEqual(rec3.x_sel, 'baz')

        # update selection value 'bar'
        field.selection_ids[0].value = 'quux'
        x_sel = Model._fields['x_sel']
        self.assertEqual(x_sel.type, 'selection')
        self.assertEqual(x_sel.selection, [('quux', 'Bar'), ('baz', 'Baz')])

        self.assertEqual(rec1.x_sel, False)
        self.assertEqual(rec2.x_sel, 'quux')
        self.assertEqual(rec3.x_sel, 'baz')
