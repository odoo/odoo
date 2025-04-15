# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from odoo.tests import tagged
from odoo.tests.common import new_test_user


@tagged("post_install", "-at_install")
class IrModelAccessTest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(IrModelAccessTest, cls).setUpClass()

        cls.env['ir.model.access'].create({
            'name': "read",
            'model_id': cls.env['ir.model'].search([("model", "=", "res.company")]).id,
            'group_id': cls.env.ref("base.group_public").id,
            'perm_read': False,
        })

        cls.env['ir.model.access'].create({
            'name': "read",
            'model_id': cls.env['ir.model'].search([("model", "=", "res.company")]).id,
            'group_id': cls.env.ref("base.group_portal").id,
            'perm_read': True,
        })

        cls.env['ir.model.access'].create({
            'name': "read",
            'model_id': cls.env['ir.model'].search([("model", "=", "res.company")]).id,
            'group_id': cls.env.ref("base.group_user").id,
            'perm_read': True,
        })

        cls.portal_user = new_test_user(
            cls.env, login="portalDude", groups="base.group_portal"
        )
        cls.public_user = new_test_user(
            cls.env, login="publicDude", groups="base.group_public"
        )
        cls.spreadsheet_user = new_test_user(
            cls.env, login="spreadsheetDude", groups="base.group_user"
        )

    def test_display_name_for(self):
        # Internal User with access rights can access the business name
        result = self.env['ir.model'].with_user(self.spreadsheet_user).display_name_for(["res.company"])
        self.assertEqual(result, [{"display_name": "Companies", "model": "res.company"}])
        # external user with access rights cannot access business name
        result = self.env['ir.model'].with_user(self.portal_user).display_name_for(["res.company"])
        self.assertEqual(result, [{"display_name": "res.company", "model": "res.company"}])
        # external user without access rights cannot access business name
        result = self.env['ir.model'].with_user(self.public_user).display_name_for(["res.company"])
        self.assertEqual(result, [{"display_name": "res.company", "model": "res.company"}])
        # admin has all rights
        result = self.env['ir.model'].display_name_for(["res.company"])
        self.assertEqual(result, [{"display_name": "Companies", "model": "res.company"}])
        # non existent model yields same result as a lack of access rights
        result = self.env['ir.model'].display_name_for(["unexistent"])
        self.assertEqual(result, [{"display_name": "unexistent", "model": "unexistent"}])
        # non existent model comes after existent model
        result = self.env['ir.model'].display_name_for(["res.company", "unexistent"])
        self.assertEqual(result, [{"display_name": "Companies", "model": "res.company"}, {"display_name": "unexistent", "model": "unexistent"}])
        # transient models
        result = self.env['ir.model'].display_name_for(["res.company", "base.language.export"])
        self.assertEqual(result, [{"display_name": "Companies", "model": "res.company"}, {"display_name": "base.language.export", "model": "base.language.export"}])

        # do not return results for transient models
        result = self.env['ir.model'].get_available_models()
        result = {values["model"] for values in result}
        self.assertIn("res.company", result)
        self.assertNotIn("base.language.export", result)


class TestIrModel(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # The test mode is necessary in this case.  After each test, we call
        # registry.reset_changes(), which opens a new cursor to retrieve custom
        # models and fields.  A regular cursor would correspond to the state of
        # the database before setUpClass(), which is not correct.  Instead, a
        # test cursor will correspond to the state of the database of cls.cr at
        # that point, i.e., before the call to setUp().
        cls.registry_enter_test_mode_cls()

        # model and records for banana stages
        cls.env['ir.model'].create({
            'name': 'Banana Ripeness',
            'model': 'x_banana_ripeness',
            'field_id': [
                Command.create({'name': 'x_name', 'ttype': 'char', 'field_description': 'Name'}),
            ]
        })
        # stage values are pairs (id, display_name)
        cls.ripeness_green = cls.env['x_banana_ripeness'].name_create('Green')
        cls.ripeness_okay = cls.env['x_banana_ripeness'].name_create('Okay, I guess?')
        cls.ripeness_gone = cls.env['x_banana_ripeness'].name_create('Walked away on its own')

        # model and records for bananas
        cls.bananas_model = cls.env['ir.model'].create({
            'name': 'Bananas',
            'model': 'x_bananas',
            'field_id': [
                Command.create({'name': 'x_name', 'ttype': 'char', 'field_description': 'Name'}),
                Command.create({'name': 'x_length', 'ttype': 'float', 'field_description': 'Length'}),
                Command.create({'name': 'x_color', 'ttype': 'integer', 'field_description': 'Color'}),
                Command.create({'name': 'x_ripeness_id', 'ttype': 'many2one',
                        'field_description': 'Ripeness', 'relation': 'x_banana_ripeness',
                        'group_expand': True}),
            ]
        })
        # add non-stored field that is not valid in order
        cls.env['ir.model.fields'].create({
            'name': 'x_is_yellow',
            'field_description': 'Is the banana yellow?',
            'ttype': 'boolean',
            'model_id': cls.bananas_model.id,
            'store': False,
            'depends': 'x_color',
            'compute': "for banana in self:\n    banana['x_is_yellow'] = banana.x_color == 9"
        })
        # default stage is ripeness_green
        cls.env['ir.default'].set('x_bananas', 'x_ripeness_id', cls.ripeness_green[0])
        cls.env['x_bananas'].create([{
            'x_name': 'Banana #1',
            'x_length': 3.14159,
            'x_color': 9,
        }, {
            'x_name': 'Banana #2',
            'x_length': 0,
            'x_color': 6,
        }, {
            'x_name': 'Banana #3',
            'x_length': 10,
            'x_color': 6,
        }])

    def setUp(self):
        # this cleanup is necessary after each test, and must be done last
        self.addCleanup(self.registry.reset_changes)
        super().setUp()

    def test_model_order_constraint(self):
        """Check that the order constraint is properly enforced."""
        VALID_ORDERS = ['id', 'id desc', 'id asc, x_length', 'x_color, x_length, create_uid']
        for order in VALID_ORDERS:
            self.bananas_model.order = order

        INVALID_ORDERS = ['', 'x_wat', 'id esc', 'create_uid,', 'id, x_is_yellow']
        for order in INVALID_ORDERS:
            with self.assertRaises(ValidationError):
                self.bananas_model.order = order

        # check that the constraint is checked at model creation
        fields_value = [
            Command.create({'name': 'x_name', 'ttype': 'char', 'field_description': 'Name'}),
            Command.create({'name': 'x_length', 'ttype': 'float', 'field_description': 'Length'}),
            Command.create({'name': 'x_color', 'ttype': 'integer', 'field_description': 'Color'}),
        ]
        self.env['ir.model'].create({
            'name': 'MegaBananas',
            'model': 'x_mega_bananas',
            'order': 'x_name asc, id desc',         # valid order
            'field_id': fields_value,
        })
        with self.assertRaises(ValidationError):
            self.env['ir.model'].create({
                'name': 'GigaBananas',
                'model': 'x_giga_bananas',
                'order': 'x_name asc, x_wat',       # invalid order
                'field_id': fields_value,
            })

        # ensure we can order by a stored field via inherits
        user_model = self.env['ir.model'].search([('model', '=', 'res.users')])
        user_model._check_order()  # must not raise

    def test_model_order_search(self):
        """Check that custom orders are applied when querying a model."""
        ORDERS = {
            'id asc': ['Banana #1', 'Banana #2', 'Banana #3'],
            'id desc': ['Banana #3', 'Banana #2', 'Banana #1'],
            'x_color asc, id asc': ['Banana #2', 'Banana #3', 'Banana #1'],
            'x_color asc, id desc': ['Banana #3', 'Banana #2', 'Banana #1'],
            'x_length asc, id': ['Banana #2', 'Banana #1', 'Banana #3'],
        }
        for order, names in ORDERS.items():
            self.bananas_model.order = order
            self.assertEqual(self.env['x_bananas']._order, order)

            bananas = self.env['x_bananas'].search([])
            self.assertEqual(bananas.mapped('x_name'), names, 'failed to order by %s' % order)

    def test_model_fold_search(self):
        """Check that custom orders are applied when querying a model."""
        self.assertEqual(self.bananas_model.fold_name, False)
        self.assertEqual(self.env['x_bananas']._fold_name, None)

        self.bananas_model.fold_name = 'x_name'
        self.assertEqual(self.env['x_bananas']._fold_name, 'x_name')

    def test_group_expansion(self):
        """Check that the basic custom group expansion works."""
        model = self.env['x_bananas'].with_context(read_group_expand=True)
        groups = model.formatted_read_group([], ['x_ripeness_id'], ['__count'])
        expected = [{
            'x_ripeness_id': self.ripeness_green,
            '__count': 3,
            '__extra_domain': [('x_ripeness_id', '=', self.ripeness_green[0])],
        }, {
            'x_ripeness_id': self.ripeness_okay,
            '__count': 0,
            '__extra_domain': [('x_ripeness_id', '=', self.ripeness_okay[0])],
        }, {
            'x_ripeness_id': self.ripeness_gone,
            '__count': 0,
            '__extra_domain': [('x_ripeness_id', '=', self.ripeness_gone[0])],
        }]
        self.assertEqual(groups, expected, 'should include 2 empty ripeness stages')

    def test_rec_name_deletion(self):
        """Check that deleting 'x_name' does not crash."""
        record = self.env['x_bananas'].create({'x_name': "Ifan Ben-Mezd"})
        self.assertEqual(record._rec_name, 'x_name')
        ClassRecord = self.registry[record._name]
        self.assertEqual(self.registry.field_depends[ClassRecord.display_name], ('x_name',))
        self.assertEqual(record.display_name, "Ifan Ben-Mezd")

        # unlinking x_name should fixup _rec_name and display_name
        self.env['ir.model.fields']._get('x_bananas', 'x_name').unlink()
        record = self.env['x_bananas'].browse(record.id)
        self.assertEqual(record._rec_name, None)
        self.assertEqual(self.registry.field_depends[ClassRecord.display_name], ())
        self.assertEqual(record.display_name, f"x_bananas,{record.id}")

    def test_monetary_currency_field(self):
        fields_value = [
            Command.create({'name': 'x_monetary', 'ttype': 'monetary', 'field_description': 'Monetary', 'currency_field': 'test'}),
        ]
        with self.assertRaises(ValidationError):
            self.env['ir.model'].create({
                'name': 'Paper Company Model',
                'model': 'x_paper_model',
                'field_id': fields_value,
            })

        fields_value = [
            Command.create({'name': 'x_monetary', 'ttype': 'monetary', 'field_description': 'Monetary', 'currency_field': 'x_falsy_currency'}),
            Command.create({'name': 'x_falsy_currency', 'ttype': 'one2many', 'field_description': 'Currency', 'relation': 'res.currency'}),
        ]
        with self.assertRaises(ValidationError):
            self.env['ir.model'].create({
                'name': 'Paper Company Model',
                'model': 'x_paper_model',
                'field_id': fields_value,
            })

        fields_value = [
            Command.create({'name': 'x_monetary', 'ttype': 'monetary', 'field_description': 'Monetary', 'currency_field': 'x_falsy_currency'}),
            Command.create({'name': 'x_falsy_currency', 'ttype': 'many2one', 'field_description': 'Currency', 'relation': 'res.partner'}),
        ]
        with self.assertRaises(ValidationError):
            self.env['ir.model'].create({
                'name': 'Paper Company Model',
                'model': 'x_paper_model',
                'field_id': fields_value,
            })

        fields_value = [
            Command.create({'name': 'x_monetary', 'ttype': 'monetary', 'field_description': 'Monetary', 'currency_field': 'x_good_currency'}),
            Command.create({'name': 'x_good_currency', 'ttype': 'many2one', 'field_description': 'Currency', 'relation': 'res.currency'}),
        ]
        model = self.env['ir.model'].create({
            'name': 'Paper Company Model',
            'model': 'x_paper_model',
            'field_id': fields_value,
        })
        monetary_field = model.field_id.search([['name', 'ilike', 'x_monetary']])
        self.assertEqual(len(monetary_field), 1,
                         "Should have the monetary field in the created ir.model")
        self.assertEqual(monetary_field.currency_field, "x_good_currency",
                         "The currency field in monetary should have x_good_currency as name")
