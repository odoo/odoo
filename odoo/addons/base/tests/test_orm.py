# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo.exceptions import AccessError, MissingError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestORM(TransactionCase):
    """ test special behaviors of ORM CRUD functions """

    @mute_logger('odoo.models')
    def test_access_deleted_records(self):
        """ Verify that accessing deleted records works as expected """
        p1 = self.env['res.partner'].create({'name': 'W'})
        p2 = self.env['res.partner'].create({'name': 'Y'})
        p1.unlink()

        # read() is expected to skip deleted records because our API is not
        # transactional for a sequence of search()->read() performed from the
        # client-side... a concurrent deletion could therefore cause spurious
        # exceptions even when simply opening a list view!
        # /!\ Using unprileged user to detect former side effects of ir.rules!
        user = self.env['res.users'].create({
            'name': 'test user',
            'login': 'test2',
            'groups_id': [(6, 0, [self.ref('base.group_user')])],
        })
        ps = (p1 + p2).with_user(user)
        self.assertEqual([{'id': p2.id, 'name': 'Y'}], ps.read(['name']), "read() should skip deleted records")
        self.assertEqual([], ps[0].read(['name']), "read() should skip deleted records")

        # Deleting an already deleted record should be simply ignored
        self.assertTrue(p1.unlink(), "Re-deleting should be a no-op")

    @mute_logger('odoo.models')
    def test_access_partial_deletion(self):
        """ Check accessing a record from a recordset where another record has been deleted. """
        Model = self.env['res.country']
        self.assertTrue(type(Model).display_name.automatic, "test assumption not satisfied")

        # access regular field when another record from the same prefetch set has been deleted
        records = Model.create([{'name': name} for name in ('Foo', 'Bar', 'Baz')])
        for record in records:
            record.name
            record.unlink()

        # access computed field when another record from the same prefetch set has been deleted
        records = Model.create([{'name': name} for name in ('Foo', 'Bar', 'Baz')])
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
            'groups_id': [(6, 0, [self.ref('base.group_user')])],
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

    def test_exists(self):
        partner = self.env['res.partner']

        # check that records obtained from search exist
        recs = partner.search([])
        self.assertTrue(recs)
        self.assertEqual(recs.exists(), recs)

        # check that there is no record with id 0
        recs = partner.browse([0])
        self.assertFalse(recs.exists())

    def test_groupby_date(self):
        partners_data = dict(
            A='2012-11-19',
            B='2012-12-17',
            C='2012-12-31',
            D='2013-01-07',
            E='2013-01-14',
            F='2013-01-28',
            G='2013-02-11',
        )

        partner_ids = []
        partner_ids_by_day = defaultdict(list)
        partner_ids_by_month = defaultdict(list)
        partner_ids_by_year = defaultdict(list)

        partners = self.env['res.partner']
        for name, date in partners_data.items():
            p = partners.create(dict(name=name, date=date))
            partner_ids.append(p.id)
            partner_ids_by_day[date].append(p.id)
            partner_ids_by_month[date.rsplit('-', 1)[0]].append(p.id)
            partner_ids_by_year[date.split('-', 1)[0]].append(p.id)

        def read_group(interval):
            domain = [('id', 'in', partner_ids)]
            result = {}
            for grp in partners.read_group(domain, ['date'], ['date:' + interval]):
                result[grp['date:' + interval]] = partners.search(grp['__domain'])
            return result

        self.assertEqual(len(read_group('day')), len(partner_ids_by_day))
        self.assertEqual(len(read_group('month')), len(partner_ids_by_month))
        self.assertEqual(len(read_group('year')), len(partner_ids_by_year))

        res = partners.read_group([('id', 'in', partner_ids)], ['date'],
                                  ['date:month', 'date:day'], lazy=False)
        self.assertEqual(len(res), len(partner_ids))

        # combine groupby and orderby
        months = ['February 2013', 'January 2013', 'December 2012', 'November 2012']
        res = partners.read_group([('id', 'in', partner_ids)], ['date'],
                                  groupby=['date:month'], orderby='date:month DESC')
        self.assertEqual([item['date:month'] for item in res], months)

        # order by date should reorder by date:month
        res = partners.read_group([('id', 'in', partner_ids)], ['date'],
                                  groupby=['date:month'], orderby='date DESC')
        self.assertEqual([item['date:month'] for item in res], months)

        # order by date should reorder by date:day
        days = ['11 Feb 2013', '28 Jan 2013', '14 Jan 2013', '07 Jan 2013',
                '31 Dec 2012', '17 Dec 2012', '19 Nov 2012']
        res = partners.read_group([('id', 'in', partner_ids)], ['date'],
                                  groupby=['date:month', 'date:day'],
                                  orderby='date DESC', lazy=False)
        self.assertEqual([item['date:day'] for item in res], days)

    def test_write_duplicate(self):
        p1 = self.env['res.partner'].create({'name': 'W'})
        (p1 + p1).write({'name': 'X'})

    def test_m2m_store_trigger(self):
        group_user = self.env.ref('base.group_user')

        user = self.env['res.users'].create({
            'name': 'test',
            'login': 'test_m2m_store_trigger',
            'groups_id': [(6, 0, [])],
        })
        self.assertTrue(user.share)

        group_user.write({'users': [(4, user.id)]})
        self.assertFalse(user.share)

        group_user.write({'users': [(3, user.id)]})
        self.assertTrue(user.share)

    @mute_logger('odoo.models')
    def test_unlink_with_property(self):
        """ Verify that unlink removes the related ir.property as unprivileged user """
        user = self.env['res.users'].create({
            'name': 'Justine Bridou',
            'login': 'saucisson',
            'groups_id': [(6, 0, [self.ref('base.group_partner_manager')])],
        })
        p1 = self.env['res.partner'].with_user(user).create({'name': 'Zorro'})
        p1_prop = self.env['ir.property'].with_user(user).create({
            'name': 'Slip en laine',
            'res_id': 'res.partner,{}'.format(p1.id),
            'fields_id': self.env['ir.model.fields'].search([
                ('model', '=', 'res.partner'), ('name', '=', 'ref')], limit=1).id,
            'value_text': 'Nain poilu',
            'type': 'char',
        })

        # Unlink with unprivileged user
        p1.unlink()

        # ir.property is deleted
        self.assertEqual(
            p1_prop.exists(), self.env['ir.property'], 'p1_prop should have been deleted')

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
                (0, 0, {'name': 'North Foo', 'code': 'NF'}),
                (0, 0, {'name': 'South Foo', 'code': 'SF'}),
                (0, 0, {'name': 'West Foo', 'code': 'WF'}),
                (0, 0, {'name': 'East Foo', 'code': 'EF'}),
            ],
        }, {
            'name': 'Bar',
            'state_ids': [
                (0, 0, {'name': 'North Bar', 'code': 'NB'}),
                (0, 0, {'name': 'South Bar', 'code': 'SB'}),
            ],
        }]
        foo, bar = self.env['res.country'].create(vals_list)
        self.assertEqual(foo.name, 'Foo')
        self.assertCountEqual(foo.mapped('state_ids.code'), ['NF', 'SF', 'WF', 'EF'])
        self.assertEqual(bar.name, 'Bar')
        self.assertCountEqual(bar.mapped('state_ids.code'), ['NB', 'SB'])


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
        del foo_before['__last_update']
        del foo_before['create_date']
        del foo_before['write_date']
        user_bar = user_foo.copy({'login': 'bar'})
        foo_after, = user_foo.read()
        del foo_after['__last_update']
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
        del foo_before['__last_update']
        del foo_before['create_date']
        del foo_before['write_date']
        del foo_before['login_date']
        partners_before = self.env['res.partner'].search([])
        user_bar = user_foo.copy({'partner_id': partner_bar.id, 'login': 'bar'})
        foo_after, = user_foo.read()
        del foo_after['__last_update']
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


CREATE = lambda values: (0, False, values)
UPDATE = lambda id, values: (1, id, values)
DELETE = lambda id: (2, id, False)
FORGET = lambda id: (3, id, False)
LINK_TO = lambda id: (4, id, False)
DELETE_ALL = lambda: (5, False, False)
REPLACE_WITH = lambda ids: (6, False, ids)


class TestO2MSerialization(TransactionCase):
    """ test the orm method 'write' on one2many fields """

    def setUp(self):
        super(TestO2MSerialization, self).setUp()
        self.partner = self.registry('res.partner')

    def test_no_command(self):
        " empty list of commands yields an empty list of records "
        results = self.env['res.partner'].resolve_2many_commands('child_ids', [])
        self.assertEqual(results, [])

    def test_CREATE_commands(self):
        " returns the VALUES dict as-is "
        values = [{'foo': 'bar'}, {'foo': 'baz'}, {'foo': 'baq'}]
        results = self.env['res.partner'].resolve_2many_commands('child_ids', [CREATE(v) for v in values])
        self.assertEqual(results, values)

    def test_LINK_TO_command(self):
        " reads the records from the database, records are returned with their ids. "
        ids = [
            self.env['res.partner'].create({'name': 'foo'}).id,
            self.env['res.partner'].create({'name': 'bar'}).id,
            self.env['res.partner'].create({'name': 'baz'}).id,
        ]
        commands = [LINK_TO(v) for v in ids]

        results = self.env['res.partner'].resolve_2many_commands('child_ids', commands, ['name'])
        self.assertItemsEqual(results, [
            {'id': ids[0], 'name': 'foo'},
            {'id': ids[1], 'name': 'bar'},
            {'id': ids[2], 'name': 'baz'},
        ])

    def test_bare_ids_command(self):
        " same as the equivalent LINK_TO commands "
        ids = [
            self.env['res.partner'].create({'name': 'foo'}).id,
            self.env['res.partner'].create({'name': 'bar'}).id,
            self.env['res.partner'].create({'name': 'baz'}).id,
        ]

        results = self.env['res.partner'].resolve_2many_commands('child_ids', ids, ['name'])
        self.assertItemsEqual(results, [
            {'id': ids[0], 'name': 'foo'},
            {'id': ids[1], 'name': 'bar'},
            {'id': ids[2], 'name': 'baz'},
        ])

    def test_UPDATE_command(self):
        " take the in-db records and merge the provided information in "
        foo = self.env['res.partner'].create({'name': 'foo'})
        bar = self.env['res.partner'].create({'name': 'bar'})
        baz = self.env['res.partner'].create({'name': 'baz', 'city': 'tag'})
        commands = [
            LINK_TO(foo.id),
            UPDATE(bar.id, {'name': 'qux', 'city': 'tagtag'}),
            UPDATE(baz.id, {'name': 'quux'}),
        ]

        results = self.env['res.partner'].resolve_2many_commands('child_ids', commands, ['name', 'city'])
        self.assertItemsEqual(results, [
            {'id': foo.id, 'name': 'foo', 'city': False},
            {'id': bar.id, 'name': 'qux', 'city': 'tagtag'},
            {'id': baz.id, 'name': 'quux', 'city': 'tag'},
        ])

    def test_DELETE_command(self):
        " deleted records are not returned at all. "
        ids = [
            self.env['res.partner'].create({'name': 'foo'}).id,
            self.env['res.partner'].create({'name': 'bar'}).id,
            self.env['res.partner'].create({'name': 'baz'}).id,
        ]
        commands = [DELETE(v) for v in ids]

        results = self.env['res.partner'].resolve_2many_commands('child_ids', commands, ['name'])
        self.assertEqual(results, [])

    def test_mixed_commands(self):
        ids = [
            self.env['res.partner'].create({'name': name}).id
            for name in ['NObar', 'baz', 'qux', 'NOquux', 'NOcorge', 'garply']
        ]
        commands = [
            CREATE({'name': 'foo'}),
            UPDATE(ids[0], {'name': 'bar'}),
            LINK_TO(ids[1]),
            DELETE(ids[2]),
            UPDATE(ids[3], {'name': 'quux',}),
            UPDATE(ids[4], {'name': 'corge'}),
            CREATE({'name': 'grault'}),
            LINK_TO(ids[5]),
        ]

        results = self.env['res.partner'].resolve_2many_commands('child_ids', commands, ['name'])
        self.assertItemsEqual(results, [
            {'name': 'foo'},
            {'id': ids[0], 'name': 'bar'},
            {'id': ids[1], 'name': 'baz'},
            {'id': ids[3], 'name': 'quux'},
            {'id': ids[4], 'name': 'corge'},
            {'name': 'grault'},
            {'id': ids[5], 'name': 'garply'},
        ])

    def test_LINK_TO_pairs(self):
        "LINK_TO commands can be written as pairs, instead of triplets"
        ids = [
            self.env['res.partner'].create({'name': 'foo'}).id,
            self.env['res.partner'].create({'name': 'bar'}).id,
            self.env['res.partner'].create({'name': 'baz'}).id,
        ]
        commands = [(4, id) for id in ids]

        results = self.env['res.partner'].resolve_2many_commands('child_ids', commands, ['name'])
        self.assertItemsEqual(results, [
            {'id': ids[0], 'name': 'foo'},
            {'id': ids[1], 'name': 'bar'},
            {'id': ids[2], 'name': 'baz'},
        ])

    def test_singleton_commands(self):
        "DELETE_ALL can appear as a singleton"
        commands = [DELETE_ALL()]
        results = self.env['res.partner'].resolve_2many_commands('child_ids', commands, ['name'])
        self.assertEqual(results, [])
