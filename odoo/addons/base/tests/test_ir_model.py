# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError
from psycopg2.errors import NotNullViolation

from odoo.exceptions import ValidationError
from odoo.tests import Form, TransactionCase, HttpCase, tagged
from odoo.tools import mute_logger
from odoo import Command


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
