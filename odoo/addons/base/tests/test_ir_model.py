# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError
from psycopg2.errors import NotNullViolation

from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, TransactionCase, HttpCase, tagged
from odoo.tools import mute_logger
from odoo import Command


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestXMLID(TransactionCase):
    def get_data(self, xml_id):
        """ Return the 'ir.model.data' record corresponding to ``xml_id``. """
        module, suffix = xml_id.split('.', 1)
        domain = [('module', '=', module), ('name', '=', suffix)]
        return self.env['ir.model.data'].search(domain)

    def test_create(self):
        model = self.env['res.partner.category']
        xml_id = 'test_convert.category_foo'

        # create category (flag 'noupdate' should be False by default)
        data = dict(xml_id=xml_id, values={'name': 'Foo'})
        category = model._load_records([data])
        self.assertEqual(category, self.env.ref(xml_id, raise_if_not_found=False))
        self.assertEqual(category.name, 'Foo')
        self.assertEqual(self.get_data(xml_id).noupdate, False)

        # update category
        data = dict(xml_id=xml_id, values={'name': 'Bar'})
        category1 = model._load_records([data], update=True)
        self.assertEqual(category, category1)
        self.assertEqual(category.name, 'Bar')
        self.assertEqual(self.get_data(xml_id).noupdate, False)

        # update category
        data = dict(xml_id=xml_id, values={'name': 'Baz'}, noupdate=True)
        category2 = model._load_records([data], update=True)
        self.assertEqual(category, category2)
        self.assertEqual(category.name, 'Baz')
        self.assertEqual(self.get_data(xml_id).noupdate, False)

    def test_create_noupdate(self):
        model = self.env['res.partner.category']
        xml_id = 'test_convert.category_foo'

        # create category
        data = dict(xml_id=xml_id, values={'name': 'Foo'}, noupdate=True)
        category = model._load_records([data])
        self.assertEqual(category, self.env.ref(xml_id, raise_if_not_found=False))
        self.assertEqual(category.name, 'Foo')
        self.assertEqual(self.get_data(xml_id).noupdate, True)

        # update category
        data = dict(xml_id=xml_id, values={'name': 'Bar'}, noupdate=False)
        category1 = model._load_records([data], update=True)
        self.assertEqual(category, category1)
        self.assertEqual(category.name, 'Foo')
        self.assertEqual(self.get_data(xml_id).noupdate, True)

        # update category
        data = dict(xml_id=xml_id, values={'name': 'Baz'}, noupdate=True)
        category2 = model._load_records([data], update=True)
        self.assertEqual(category, category2)
        self.assertEqual(category.name, 'Foo')
        self.assertEqual(self.get_data(xml_id).noupdate, True)

    def test_create_noupdate_multi(self):
        model = self.env['res.partner.category']
        data_list = [
            dict(xml_id='test_convert.category_foo', values={'name': 'Foo'}, noupdate=True),
            dict(xml_id='test_convert.category_bar', values={'name': 'Bar'}, noupdate=True),
        ]

        # create category
        categories = model._load_records(data_list)
        foo = self.env.ref('test_convert.category_foo')
        bar = self.env.ref('test_convert.category_bar')
        self.assertEqual(categories, foo + bar)
        self.assertEqual(foo.name, 'Foo')
        self.assertEqual(bar.name, 'Bar')

        # check data
        self.assertEqual(self.get_data('test_convert.category_foo').noupdate, True)
        self.assertEqual(self.get_data('test_convert.category_bar').noupdate, True)

    def test_create_order(self):
        model = self.env['res.partner.category']
        data_list = [
            dict(xml_id='test_convert.category_foo', values={'name': 'Foo'}),
            dict(xml_id='test_convert.category_bar', values={'name': 'Bar'}, noupdate=True),
            dict(xml_id='test_convert.category_baz', values={'name': 'Baz'}),
        ]

        # create categories
        foo = model._load_records([data_list[0]])
        bar = model._load_records([data_list[1]])
        baz = model._load_records([data_list[2]])
        self.assertEqual(foo.name, 'Foo')
        self.assertEqual(bar.name, 'Bar')
        self.assertEqual(baz.name, 'Baz')

        # update them, and check the order of result
        for data in data_list:
            data['values']['name'] += 'X'
        cats = model._load_records(data_list, update=True)
        self.assertEqual(list(cats), [foo, bar, baz])
        self.assertEqual(foo.name, 'FooX')
        self.assertEqual(bar.name, 'Bar')
        self.assertEqual(baz.name, 'BazX')

    def test_create_inherits(self):
        model = self.env['res.users']
        xml_id = 'test_convert.user_foo'
        par_xml_id = xml_id + '_res_partner'

        # create user
        user = model._load_records([dict(xml_id=xml_id, values={'name': 'Foo', 'login': 'foo'})])
        self.assertEqual(user, self.env.ref(xml_id, raise_if_not_found=False))
        self.assertEqual(user.partner_id, self.env.ref(par_xml_id, raise_if_not_found=False))
        self.assertEqual(user.name, 'Foo')
        self.assertEqual(user.login, 'foo')

    def test_recreate(self):
        model = self.env['res.partner.category']
        xml_id = 'test_convert.category_foo'
        data = dict(xml_id=xml_id, values={'name': 'Foo'})

        # create category
        category = model._load_records([data])
        self.assertEqual(category, self.env.ref(xml_id, raise_if_not_found=False))
        self.assertEqual(category.name, 'Foo')

        # suppress category
        category.unlink()
        self.assertFalse(self.env.ref(xml_id, raise_if_not_found=False))

        # update category, this should recreate it
        category = model._load_records([data], update=True)
        self.assertEqual(category, self.env.ref(xml_id, raise_if_not_found=False))
        self.assertEqual(category.name, 'Foo')

    def test_create_xmlids(self):
        # create users and assign them xml ids
        foo, bar = self.env['res.users']._load_records([{
            'xml_id': 'test_convert.foo',
            'values': {'name': 'Foo', 'login': 'foo'},
            'noupdate': True,
        }, {
            'xml_id': 'test_convert.bar',
            'values': {'name': 'Bar', 'login': 'bar'},
            'noupdate': True,
        }])

        self.assertEqual(foo, self.env.ref('test_convert.foo', raise_if_not_found=False))
        self.assertEqual(bar, self.env.ref('test_convert.bar', raise_if_not_found=False))

        self.assertEqual(foo.partner_id, self.env.ref('test_convert.foo_res_partner', raise_if_not_found=False))
        self.assertEqual(bar.partner_id, self.env.ref('test_convert.bar_res_partner', raise_if_not_found=False))

        self.assertEqual(self.get_data('test_convert.foo').noupdate, True)
        self.assertEqual(self.get_data('test_convert.bar').noupdate, True)

    @mute_logger('odoo.sql_db', 'odoo.addons.base.models.ir_model')
    def test_create_external_id_with_space(self):
        model = self.env['res.partner.category']
        data_list = [{
            'xml_id': 'test_convert.category_with space',
            'values': {'name': 'Bar'},
        }]
        with self.assertRaisesRegex(IntegrityError, 'ir_model_data_name_nospaces'):
            model._load_records(data_list)

    def test_update_xmlid(self):
        def assert_xmlid(xmlid, value, message):
            expected_values = (value._name, value.id)
            with self.assertQueryCount(0):
                self.assertEqual(self.env['ir.model.data']._xmlid_lookup(xmlid), expected_values, message)
            module, name = xmlid.split('.')
            self.env.cr.execute("SELECT model, res_id FROM ir_model_data where module=%s and name=%s", [module, name])
            self.assertEqual((value._name, value.id), self.env.cr.fetchone(), message)

        xmlid = 'base.test_xmlid'
        records = self.env['ir.model.data'].search([], limit=6)
        with self.assertQueryCount(1):
            self.env['ir.model.data']._update_xmlids([
                {'xml_id': xmlid, 'record': records[0]},
            ])
        assert_xmlid(xmlid, records[0], f'The xmlid {xmlid} should have been created with record {records[0]}')

        with self.assertQueryCount(1):
            self.env['ir.model.data']._update_xmlids([
                {'xml_id': xmlid, 'record': records[1]},
            ], update=True)
        assert_xmlid(xmlid, records[1], f'The xmlid {xmlid} should have been updated with record {records[1]}')

        with self.assertQueryCount(1):
            self.env['ir.model.data']._update_xmlids([
                {'xml_id': xmlid, 'record': records[2]},
            ])
        assert_xmlid(xmlid, records[2], f'The xmlid {xmlid} should have been updated with record {records[1]}')

        # noupdate case
        # note: this part is mainly there to avoid breaking the current behaviour, not asserting that it makes sence
        xmlid = 'base.test_xmlid_noupdates'
        with self.assertQueryCount(1):
            self.env['ir.model.data']._update_xmlids([
                {'xml_id': xmlid, 'record': records[3], 'noupdate':True}, # record created as noupdate
            ])

        assert_xmlid(xmlid, records[3], f'The xmlid {xmlid} should have been created for record {records[2]}')

        with self.assertQueryCount(1):
            self.env['ir.model.data']._update_xmlids([
                {'xml_id': xmlid, 'record': records[4]},
            ], update=True)
        assert_xmlid(xmlid, records[3], f'The xmlid {xmlid} should not have been updated (update mode)')

        with self.assertQueryCount(1):
            self.env['ir.model.data']._update_xmlids([
                {'xml_id': xmlid, 'record': records[5]},
            ])
        assert_xmlid(xmlid, records[5], f'The xmlid {xmlid} should have been updated with record (not an update) {records[1]}')


@tagged('-at_install', 'post_install')
class TestIrModelEdition(TransactionCase):
    def test_new_ir_model_fields_related(self):
        """Check that related field are handled correctly on new field"""
        model = self.env['ir.model'].create({
            'name': 'Bananas',
            'model': 'x_bananas'
        })
        with self.debug_mode():
            form = Form(self.env['ir.model.fields'].with_context(default_model_id=model.id))
            form.related = 'id'
            self.assertEqual(form.ttype, 'integer')

    def test_delete_manual_models_with_base_fields(self):
        model = self.env["ir.model"].create({
            "model": "x_test_base_delete",
            "name": "test base delete",
            "field_id": [
                Command.create({
                    "name": "x_my_field",
                    "ttype": "char",
                }),
                Command.create({
                  "name": "active",
                  "ttype": "boolean",
                  "state": "base",
                })
            ]
        })
        model2 = self.env["ir.model"].create({
            "model": "x_test_base_delete2",
            "name": "test base delete2",
            "field_id": [
                Command.create({
                    "name": "x_my_field2",
                    "ttype": "char",
                }),
                Command.create({
                  "name": "active",
                  "ttype": "boolean",
                  "state": "base",
                })
            ]
        })
        self.assertTrue(model.exists())
        self.assertTrue(model2.exists())

        self.env["ir.model"].browse(model.ids + model2.ids).unlink()
        self.assertFalse(model.exists())
        self.assertFalse(model2.exists())

    @mute_logger('odoo.sql_db')
    def test_ir_model_fields_name_create(self):
        model = self.env['ir.model'].create({
            'name': 'Bananas',
            'model': 'x_bananas'
        })
        # Quick create an ir_model_field should not be possible
        # It should be raise a ValidationError
        with self.assertRaises(NotNullViolation):
            self.env['ir.model.fields'].name_create("field_name")

        # But with default_ we should be able to name_create
        self.env['ir.model.fields'].with_context(
            default_model_id=model.id,
            default_model=model.name,
            default_ttype="char"
        ).name_create("field_name")


@tagged('test_eval_context')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestEvalContext(TransactionCase):

    def test_module_usage(self):
        self.env['ir.model.fields'].create({
            'name': 'x_foo_bar_baz',
            'model_id': self.env['ir.model'].search([('model', '=', 'res.partner')]).id,
            'field_description': 'foo',
            'ttype': 'integer',
            'store': False,
            'depends': 'name',
            'compute': ("time.time()\ndatetime.datetime.now()\n"
                        "dateutil.relativedelta.relativedelta(hours=1)")
        })
        self.env['res.partner'].create({'name': 'foo'}).x_foo_bar_baz

@tagged('-at_install', 'post_install')
class TestIrModelFieldsTranslation(HttpCase):
    def test_ir_model_fields_translation(self):
        # If not enabled (like in demo data), landing on res.config will try
        # to disable module_sale_quotation_builder and raise an warning
        group_order_template = self.env.ref('sale_management.group_sale_order_template', raise_if_not_found=False)
        if group_order_template:
            self.env.ref('base.group_user').write({"implied_ids": [(4, group_order_template.id)]})

        # modify en_US translation
        field = self.env['ir.model.fields'].search([('model_id.model', '=', 'res.users'), ('name', '=', 'login')])
        self.assertEqual(field.with_context(lang='en_US').field_description, 'Login')
        # check the name column of res.users is displayed as 'Login'
        self.start_tour("/odoo", 'ir_model_fields_translation_en_tour', login="admin")
        field.update_field_translations('field_description', {'en_US': 'Login2'})
        # check the name column of res.users is displayed as 'Login2'
        self.start_tour("/odoo", 'ir_model_fields_translation_en_tour2', login="admin")

        # modify fr_FR translation
        self.env['res.lang']._activate_lang('fr_FR')
        field = self.env['ir.model.fields'].search([('model_id.model', '=', 'res.users'), ('name', '=', 'login')])
        field.update_field_translations('field_description', {'fr_FR': 'Identifiant'})
        self.assertEqual(field.with_context(lang='fr_FR').field_description, 'Identifiant')
        admin = self.env['res.users'].search([('login', '=', 'admin')], limit=1)
        admin.lang = 'fr_FR'
        # check the name column of res.users is displayed as 'Identifiant'
        self.start_tour("/odoo", 'ir_model_fields_translation_fr_tour', login="admin")
        field.update_field_translations('field_description', {'fr_FR': 'Identifiant2'})
        # check the name column of res.users is displayed as 'Identifiant2'
        self.start_tour("/odoo", 'ir_model_fields_translation_fr_tour2', login="admin")


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestIrModelInherit(TransactionCase):
    def test_inherit(self):
        imi = self.env["ir.model.inherit"].search([("model_id.model", "=", "ir.actions.server")])
        self.assertEqual(len(imi), 1)
        self.assertEqual(imi.parent_id.model, "ir.actions.actions")
        self.assertFalse(imi.parent_field_id)

    def test_inherits(self):
        imi = self.env["ir.model.inherit"].search(
            [("model_id.model", "=", "res.users"), ("parent_field_id", "!=", False)]
        )
        self.assertEqual(len(imi), 1)
        self.assertEqual(imi.parent_id.model, "res.partner")
        self.assertEqual(imi.parent_field_id.name, "partner_id")


class TestCommonCustomFields(TransactionCase):
    MODEL = 'res.partner'
    COMODEL = 'res.users'

    def setUp(self):
        # check that the registry is properly reset
        fnames = set(self.registry[self.MODEL]._fields)

        @self.addCleanup
        def check_registry():
            assert set(self.registry[self.MODEL]._fields) == fnames

        self.addCleanup(self.registry.reset_changes)
        self.addCleanup(self.registry.clear_all_caches)

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
            'arch': '<list string="X"><field name="%s"/></list>' % name,
        })


@tagged('at_install', '-post_install')
class TestCustomFields(TestCommonCustomFields):
    def test_create_custom(self):
        """ custom field names must be start with 'x_' """
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.create_field('xyz')

    def test_rename_custom(self):
        """ custom field names must be start with 'x_' """
        field = self.create_field('x_xyz')
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            field.name = 'xyz'

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
        """ one cannot delete a non-custom field expect for uninstallation """
        field = self.env['ir.model.fields']._get(self.MODEL, 'ref')
        self.assertTrue(field)

        with self.assertRaisesRegex(UserError, 'This column contains module data'):
            field.unlink()

        # but it works in the context of uninstalling a module
        field.with_context(force_delete=True).unlink()

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
        m2o_field.with_context(force_delete=True).unlink()
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
        field.with_context(force_delete=True).unlink()
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
        # class ResPartner(models.Model)
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
        self.env.flush_all()

        # create a non-computed field, and assert how many queries it takes
        model_id = self.env['ir.model']._get_id('res.partner')
        query_count = 51
        with self.assertQueryCount(query_count):
            self.env.registry.clear_cache()
            self.env['ir.model.fields'].create({
                'model_id': model_id,
                'name': 'x_oh_box',
                'field_description': 'x_oh_box',
                'ttype': 'char',
                'store': True,
            })

        # same with a related field, it only takes 8 extra queries
        with self.assertQueryCount(query_count + 8):
            self.env.registry.clear_cache()
            self.env['ir.model.fields'].create({
                'model_id': model_id,
                'name': 'x_oh_boy',
                'field_description': 'x_oh_boy',
                'ttype': 'char',
                'related': 'country_id.code',
                'store': True,
            })

        # check the computed values
        for partner in partners:
            self.assertEqual(partner.x_oh_boy, partner.country_id.code)

    def test_relation_of_a_custom_field(self):
        """ change the relation model of a custom field """
        model = self.env['ir.model'].search([('model', '=', self.MODEL)])
        field = self.env['ir.model.fields'].create({
            'name': 'x_foo',
            'model_id': model.id,
            'field_description': 'x_foo',
            'ttype': 'many2many',
            'relation': self.COMODEL,
        })

        # change the relation
        with self.assertRaises(ValidationError):
            field.relation = 'foo'

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


class TestCustomFieldsPostInstall(TestCommonCustomFields):
    def test_add_field_valid(self):
        """ custom field names must start with 'x_', even when bypassing the constraints

        If a user bypasses all constraints to add a custom field not starting by `x_`,
        it must not be loaded in the registry.

        This is to forbid users to override class attributes.
        """
        field = self.create_field('x_foo')
        # Drop the SQL constraint, to bypass it,
        # as a user could do through a SQL shell or a `cr.execute` in a server action
        self.env.cr.execute("ALTER TABLE ir_model_fields DROP CONSTRAINT ir_model_fields_name_manual_field")
        self.env.cr.execute("UPDATE ir_model_fields SET name = 'foo' WHERE id = %s", [field.id])
        with self.assertLogs('odoo.registry') as log_catcher:
            # Trick to reload the registry. The above rename done through SQL didn't reload the registry. This will.
            self.env.registry._setup_models__(self.cr, [self.MODEL])
            self.assertIn(
                f'The field `{field.name}` is not defined in the `{field.model}` Python class', log_catcher.output[0]
            )
