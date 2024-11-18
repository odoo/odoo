# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger
from odoo import Command


class TestORM(TransactionCase):
    """ test special behaviors of ORM CRUD functions """

    @mute_logger('odoo.models')
    def test_access_deleted_records(self):
        """ Verify that accessing deleted records works as expected """
        c1 = self.env['res.partner.category'].create({'name': 'W'})
        c2 = self.env['res.partner.category'].create({'name': 'Y'})
        c1.unlink()

        # read() is expected to skip deleted records because our API is not
        # transactional for a sequence of search()->read() performed from the
        # client-side... a concurrent deletion could therefore cause spurious
        # exceptions even when simply opening a list view!
        # /!\ Using unprileged user to detect former side effects of ir.rules!
        user = self.env['res.users'].create({
            'name': 'test user',
            'login': 'test2',
            'groups_id': [Command.set([self.ref('base.group_user')])],
        })
        cs = (c1 + c2).with_user(user)
        self.assertEqual([{'id': c2.id, 'name': 'Y'}], cs.read(['name']), "read() should skip deleted records")
        self.assertEqual([], cs[0].read(['name']), "read() should skip deleted records")

        # Deleting an already deleted record should be simply ignored
        self.assertTrue(c1.unlink(), "Re-deleting should be a no-op")

    @mute_logger('odoo.models')
    def test_access_partial_deletion(self):
        """ Check accessing a record from a recordset where another record has been deleted. """
        Model = self.env['res.country']
        display_name_field = Model._fields['display_name']
        self.assertTrue(display_name_field.compute and not display_name_field.store, "test assumption not satisfied")

        # access regular field when another record from the same prefetch set has been deleted
        records = Model.create([{'name': name[0], 'code': name[1]} for name in (['Foo', 'ZV'], ['Bar', 'ZX'], ['Baz', 'ZY'])])
        for record in records:
            record.name
            record.unlink()

        # access computed field when another record from the same prefetch set has been deleted
        records = Model.create([{'name': name[0], 'code': name[1]} for name in (['Foo', 'ZV'], ['Bar', 'ZX'], ['Baz', 'ZY'])])
        for record in records:
            record.display_name
            record.unlink()

    @mute_logger('odoo.models', 'odoo.addons.base.models.ir_rule')
    def test_access_filtered_records(self):
        """ Verify that accessing filtered records works as expected for non-admin user """
        p1 = self.env['res.partner'].create({'name': 'W'})
        p2 = self.env['res.partner'].create({'name': 'Y'})
        user = self.env['res.users'].create({
            'name': 'test user',
            'login': 'test2',
            'groups_id': [Command.set([self.ref('base.group_user')])],
        })

        partner_model = self.env['ir.model'].search([('model','=','res.partner')])
        self.env['ir.rule'].create({
            'name': 'Y is invisible',
            'domain_force': [('id', '!=', p1.id)],
            'model_id': partner_model.id,
        })

        # search as unprivileged user
        partners = self.env['res.partner'].with_user(user).search([])
        self.assertNotIn(p1, partners, "W should not be visible...")
        self.assertIn(p2, partners, "... but Y should be visible")

        # read as unprivileged user
        with self.assertRaises(AccessError):
            p1.with_user(user).read(['name'])
        # write as unprivileged user
        with self.assertRaises(AccessError):
            p1.with_user(user).write({'name': 'foo'})
        # unlink as unprivileged user
        with self.assertRaises(AccessError):
            p1.with_user(user).unlink()

        # Prepare mixed case 
        p2.unlink()
        # read mixed records: some deleted and some filtered
        with self.assertRaises(AccessError):
            (p1 + p2).with_user(user).read(['name'])
        # delete mixed records: some deleted and some filtered
        with self.assertRaises(AccessError):
            (p1 + p2).with_user(user).unlink()

    def test_read(self):
        partner = self.env['res.partner'].create({'name': 'MyPartner1'})
        result = partner.read()
        self.assertIsInstance(result, list)

    @mute_logger('odoo.models')
    def test_search_read(self):
        partner = self.env['res.partner']

        # simple search_read
        partner.create({'name': 'MyPartner1'})
        found = partner.search_read([('name', '=', 'MyPartner1')], ['name'])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['name'], 'MyPartner1')
        self.assertIn('id', found[0])

        # search_read correct order
        partner.create({'name': 'MyPartner2'})
        found = partner.search_read([('name', 'like', 'MyPartner')], ['name'], order="name")
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]['name'], 'MyPartner1')
        self.assertEqual(found[1]['name'], 'MyPartner2')
        found = partner.search_read([('name', 'like', 'MyPartner')], ['name'], order="name desc")
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]['name'], 'MyPartner2')
        self.assertEqual(found[1]['name'], 'MyPartner1')

        # search_read that finds nothing
        found = partner.search_read([('name', '=', 'Does not exists')], ['name'])
        self.assertEqual(len(found), 0)

        # search_read with an empty array of fields
        found = partner.search_read([], [], limit=1)
        self.assertEqual(len(found), 1)
        self.assertTrue(field in list(found[0]) for field in ['id', 'name', 'display_name', 'email'])

        # search_read without fields
        found = partner.search_read([], False, limit=1)
        self.assertEqual(len(found), 1)
        self.assertTrue(field in list(found[0]) for field in ['id', 'name', 'display_name', 'email'])

    @mute_logger('odoo.sql_db')
    def test_exists(self):
        partner = self.env['res.partner']

        # check that records obtained from search exist
        recs = partner.search([])
        self.assertTrue(recs)
        self.assertEqual(recs.exists(), recs)

        # check that new records exist by convention
        recs = partner.new({})
        self.assertTrue(recs.exists())

        # check that there is no record with id 0
        recs = partner.browse([0])
        self.assertFalse(recs.exists())

    def test_write_duplicate(self):
        p1 = self.env['res.partner'].create({'name': 'W'})
        (p1 + p1).write({'name': 'X'})

    def test_m2m_store_trigger(self):
        group_user = self.env.ref('base.group_user')

        user = self.env['res.users'].create({
            'name': 'test',
            'login': 'test_m2m_store_trigger',
            'groups_id': [Command.set([])],
        })
        self.assertTrue(user.share)

        group_user.write({'users': [Command.link(user.id)]})
        self.assertFalse(user.share)

        group_user.write({'users': [Command.unlink(user.id)]})
        self.assertTrue(user.share)

    def test_create_multi(self):
        """ create for multiple records """
        # assumption: 'res.bank' does not override 'create'
        vals_list = [{'name': name} for name in ('Foo', 'Bar', 'Baz')]
        vals_list[0]['email'] = 'foo@example.com'
        for vals in vals_list:
            record = self.env['res.bank'].create(vals)
            self.assertEqual(len(record), 1)
            self.assertEqual(record.name, vals['name'])
            self.assertEqual(record.email, vals.get('email', False))

        records = self.env['res.bank'].create([])
        self.assertFalse(records)

        records = self.env['res.bank'].create(vals_list)
        self.assertEqual(len(records), len(vals_list))
        for record, vals in zip(records, vals_list):
            self.assertEqual(record.name, vals['name'])
            self.assertEqual(record.email, vals.get('email', False))

        # create countries and states
        vals_list = [{
            'name': 'Foo',
            'state_ids': [
                Command.create({'name': 'North Foo', 'code': 'NF'}),
                Command.create({'name': 'South Foo', 'code': 'SF'}),
                Command.create({'name': 'West Foo', 'code': 'WF'}),
                Command.create({'name': 'East Foo', 'code': 'EF'}),
            ],
            'code': 'ZV',
        }, {
            'name': 'Bar',
            'state_ids': [
                Command.create({'name': 'North Bar', 'code': 'NB'}),
                Command.create({'name': 'South Bar', 'code': 'SB'}),
            ],
            'code': 'ZX',
        }]
        foo, bar = self.env['res.country'].create(vals_list)
        self.assertEqual(foo.name, 'Foo')
        self.assertCountEqual(foo.state_ids.mapped('code'), ['NF', 'SF', 'WF', 'EF'])
        self.assertEqual(bar.name, 'Bar')
        self.assertCountEqual(bar.state_ids.mapped('code'), ['NB', 'SB'])


class TestInherits(TransactionCase):
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


@tagged('post_install', '-at_install')
class TestCompanyDependent(TransactionCase):
    def test_orm_ondelete_cascade(self):
        # model_A
        #  | field_a                           company dependent many2one is
        #  | company dependent many2one        stored as jsonb and doesn't
        #  v                                   have db ON DELETE action
        # model_B
        #  | field_b                           if a row for model_B is deleted
        #  | many2one (ondelete='cascade')     because of ON DELETE CASCADE,
        #  v                                   model_A will reference a deleted
        # model_C                              row and have MissingError
        #  | field_c
        #  | many2one (ondelete='cascade')     this test asks you to move the
        #  v                                   ON DELETE CASCADE logic to ORM
        # model_D                              and remove ondelete='cascade'
        #
        # Note:
        # the test doesn't force developers to remove ondelete='cascade' for
        # model_C if model_C is not referenced by another company dependent
        # many2one field. But usually it is needed, unless you can accept
        # the value of field_b to be an empty recordset of model_C
        #
        for model in self.env.registry.values():
            for field in model._fields.values():
                if field.company_dependent and field.type == 'many2one':
                    for comodel_field in self.env[field.comodel_name]._fields.values():
                        self.assertFalse(
                            comodel_field.type == 'many2one' and comodel_field.ondelete == 'cascade',
                            (f'when a row for {comodel_field.comodel_name} is deleted, a row for {comodel_field.model_name} '
                             f'may also be deleted for sake of on delete cascade field {comodel_field}, which may '
                             f'cause MissingError for a company dependent many2one field {field} in the future. '
                             f'Please override the unlink method of {comodel_field.comodel_name} and do the ORM on '
                             f'delete cascade logic and remove/override the ondelete="cascade" of {comodel_field}')
                        )
