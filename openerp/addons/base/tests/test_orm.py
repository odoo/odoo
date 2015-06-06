from collections import defaultdict
from openerp.tools import mute_logger
from openerp.tests import common

UID = common.ADMIN_USER_ID


class TestORM(common.TransactionCase):
    """ test special behaviors of ORM CRUD functions
    
        TODO: use real Exceptions types instead of Exception """

    def setUp(self):
        super(TestORM, self).setUp()
        cr, uid = self.cr, self.uid
        self.partner = self.registry('res.partner')
        self.users = self.registry('res.users')
        self.p1 = self.partner.name_create(cr, uid, 'W')[0]
        self.p2 = self.partner.name_create(cr, uid, 'Y')[0]
        self.ir_rule = self.registry('ir.rule')

        # sample unprivileged user
        employee_gid = self.ref('base.group_user')
        self.uid2 = self.users.create(cr, uid, {'name': 'test user', 'login': 'test', 'groups_id': [4,employee_gid]})

    @mute_logger('openerp.models')
    def testAccessDeletedRecords(self):
        """ Verify that accessing deleted records works as expected """
        cr, uid, uid2, p1, p2 = self.cr, self.uid, self.uid2, self.p1, self.p2
        self.partner.unlink(cr, uid, [p1])

        # read() is expected to skip deleted records because our API is not
        # transactional for a sequence of search()->read() performed from the
        # client-side... a concurrent deletion could therefore cause spurious
        # exceptions even when simply opening a list view!
        # /!\ Using unprileged user to detect former side effects of ir.rules!
        self.assertEqual([{'id': p2, 'name': 'Y'}], self.partner.read(cr, uid2, [p1,p2], ['name']), "read() should skip deleted records")
        self.assertEqual([], self.partner.read(cr, uid2, [p1], ['name']), "read() should skip deleted records")

        # Deleting an already deleted record should be simply ignored
        self.assertTrue(self.partner.unlink(cr, uid, [p1]), "Re-deleting should be a no-op")

        # Updating an already deleted record should raise, even as admin
        with self.assertRaises(Exception):
            self.partner.write(cr, uid, [p1], {'name': 'foo'})

    @mute_logger('openerp.models')
    def testAccessFilteredRecords(self):
        """ Verify that accessing filtered records works as expected for non-admin user """
        cr, uid, uid2, p1, p2 = self.cr, self.uid, self.uid2, self.p1, self.p2
        partner_model = self.registry('ir.model').search(cr, uid, [('model','=','res.partner')])[0]
        self.ir_rule.create(cr, uid, {'name': 'Y is invisible',
                                      'domain_force': [('id', '!=', p1)],
                                      'model_id': partner_model})
        # search as unprivileged user
        partners = self.partner.search(cr, uid2, [])
        self.assertFalse(p1 in partners, "W should not be visible...")
        self.assertTrue(p2 in partners, "... but Y should be visible")

        # read as unprivileged user
        with self.assertRaises(Exception):
            self.partner.read(cr, uid2, [p1], ['name'])
        # write as unprivileged user
        with self.assertRaises(Exception):
            self.partner.write(cr, uid2, [p1], {'name': 'foo'})
        # unlink as unprivileged user
        with self.assertRaises(Exception):
            self.partner.unlink(cr, uid2, [p1])

        # Prepare mixed case 
        self.partner.unlink(cr, uid, [p2])
        # read mixed records: some deleted and some filtered
        with self.assertRaises(Exception):
            self.partner.read(cr, uid2, [p1,p2], ['name'])
        # delete mixed records: some deleted and some filtered
        with self.assertRaises(Exception):
            self.partner.unlink(cr, uid2, [p1,p2])

    def test_multi_read(self):
        record_id = self.partner.create(self.cr, UID, {'name': 'MyPartner1'})
        records = self.partner.read(self.cr, UID, [record_id])
        self.assertIsInstance(records, list)

    def test_one_read(self):
        record_id = self.partner.create(self.cr, UID, {'name': 'MyPartner1'})
        record = self.partner.read(self.cr, UID, record_id)
        self.assertIsInstance(record, dict)

    @mute_logger('openerp.models')
    def test_search_read(self):
        # simple search_read
        self.partner.create(self.cr, UID, {'name': 'MyPartner1'})
        found = self.partner.search_read(self.cr, UID, [['name', '=', 'MyPartner1']], ['name'])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['name'], 'MyPartner1')
        self.assertTrue('id' in found[0])

        # search_read correct order
        self.partner.create(self.cr, UID, {'name': 'MyPartner2'})
        found = self.partner.search_read(self.cr, UID, [['name', 'like', 'MyPartner']], ['name'], order="name")
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]['name'], 'MyPartner1')
        self.assertEqual(found[1]['name'], 'MyPartner2')
        found = self.partner.search_read(self.cr, UID, [['name', 'like', 'MyPartner']], ['name'], order="name desc")
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]['name'], 'MyPartner2')
        self.assertEqual(found[1]['name'], 'MyPartner1')

        # search_read that finds nothing
        found = self.partner.search_read(self.cr, UID, [['name', '=', 'Does not exists']], ['name'])
        self.assertEqual(len(found), 0)

    def test_exists(self):
        partner = self.partner.browse(self.cr, UID, [])

        # check that records obtained from search exist
        recs = partner.search([])
        self.assertTrue(recs)
        self.assertEqual(recs.exists(), recs)

        # check that there is no record with id 0
        recs = partner.browse([0])
        self.assertFalse(recs.exists())

    def test_groupby_date(self):
        partners = dict(
            A='2012-11-19',
            B='2012-12-17',
            C='2012-12-31',
            D='2013-01-07',
            E='2013-01-14',
            F='2013-01-28',
            G='2013-02-11',
        )

        all_partners = []
        partners_by_day = defaultdict(set)
        partners_by_month = defaultdict(set)
        partners_by_year = defaultdict(set)

        for name, date in partners.items():
            p = self.partner.create(self.cr, UID, dict(name=name, date=date))
            all_partners.append(p)
            partners_by_day[date].add(p)
            partners_by_month[date.rsplit('-', 1)[0]].add(p)
            partners_by_year[date.split('-', 1)[0]].add(p)

        def read_group(interval, domain=None):
            main_domain = [('id', 'in', all_partners)]
            if domain:
                domain = ['&'] + main_domain + domain
            else:
                domain = main_domain

            rg = self.partner.read_group(self.cr, self.uid, domain, ['date'], 'date' + ':' + interval)
            result = {}
            for r in rg:
                result[r['date:' + interval]] = set(self.partner.search(self.cr, self.uid, r['__domain']))
            return result

        self.assertEqual(len(read_group('day')), len(partners_by_day))
        self.assertEqual(len(read_group('month')), len(partners_by_month))
        self.assertEqual(len(read_group('year')), len(partners_by_year))

        rg = self.partner.read_group(self.cr, self.uid, [('id', 'in', all_partners)], 
                        ['date'], ['date:month', 'date:day'], lazy=False)
        self.assertEqual(len(rg), len(all_partners))


class TestInherits(common.TransactionCase):
    """ test the behavior of the orm for models that use _inherits;
        specifically: res.users, that inherits from res.partner
    """

    def setUp(self):
        super(TestInherits, self).setUp()
        self.partner = self.registry('res.partner')
        self.user = self.registry('res.users')

    def test_default(self):
        """ `default_get` cannot return a dictionary or a new id """
        defaults = self.user.default_get(self.cr, UID, ['partner_id'])
        if 'partner_id' in defaults:
            self.assertIsInstance(defaults['partner_id'], (bool, int, long))

    def test_create(self):
        """ creating a user should automatically create a new partner """
        partners_before = self.partner.search(self.cr, UID, [])
        foo_id = self.user.create(self.cr, UID, {'name': 'Foo', 'login': 'foo', 'password': 'foo'})
        foo = self.user.browse(self.cr, UID, foo_id)

        self.assertNotIn(foo.partner_id.id, partners_before)

    def test_create_with_ancestor(self):
        """ creating a user with a specific 'partner_id' should not create a new partner """
        par_id = self.partner.create(self.cr, UID, {'name': 'Foo'})
        partners_before = self.partner.search(self.cr, UID, [])
        foo_id = self.user.create(self.cr, UID, {'partner_id': par_id, 'login': 'foo', 'password': 'foo'})
        partners_after = self.partner.search(self.cr, UID, [])

        self.assertEqual(set(partners_before), set(partners_after))

        foo = self.user.browse(self.cr, UID, foo_id)
        self.assertEqual(foo.name, 'Foo')
        self.assertEqual(foo.partner_id.id, par_id)

    @mute_logger('openerp.models')
    def test_read(self):
        """ inherited fields should be read without any indirection """
        foo_id = self.user.create(self.cr, UID, {'name': 'Foo', 'login': 'foo', 'password': 'foo'})
        foo_values, = self.user.read(self.cr, UID, [foo_id])
        partner_id = foo_values['partner_id'][0]
        partner_values, = self.partner.read(self.cr, UID, [partner_id])
        self.assertEqual(foo_values['name'], partner_values['name'])

        foo = self.user.browse(self.cr, UID, foo_id)
        self.assertEqual(foo.name, foo.partner_id.name)

    @mute_logger('openerp.models')
    def test_copy(self):
        """ copying a user should automatically copy its partner, too """
        foo_id = self.user.create(self.cr, UID, {
            'name': 'Foo',
            'login': 'foo',
            'password': 'foo',
            'supplier': True,
        })
        foo_before, = self.user.read(self.cr, UID, [foo_id])
        del foo_before['__last_update']
        bar_id = self.user.copy(self.cr, UID, foo_id, {
            'login': 'bar',
            'password': 'bar',
        })
        foo_after, = self.user.read(self.cr, UID, [foo_id])
        del foo_after['__last_update']

        self.assertEqual(foo_before, foo_after)

        foo, bar = self.user.browse(self.cr, UID, [foo_id, bar_id])
        self.assertEqual(bar.name, 'Foo (copy)')
        self.assertEqual(bar.login, 'bar')
        self.assertEqual(foo.supplier, bar.supplier)
        self.assertNotEqual(foo.id, bar.id)
        self.assertNotEqual(foo.partner_id.id, bar.partner_id.id)

    @mute_logger('openerp.models')
    def test_copy_with_ancestor(self):
        """ copying a user with 'parent_id' in defaults should not duplicate the partner """
        foo_id = self.user.create(self.cr, UID, {'name': 'Foo', 'login': 'foo', 'password': 'foo',
                                                 'login_date': '2016-01-01', 'signature': 'XXX'})
        par_id = self.partner.create(self.cr, UID, {'name': 'Bar'})

        foo_before, = self.user.read(self.cr, UID, [foo_id])
        del foo_before['__last_update']
        partners_before = self.partner.search(self.cr, UID, [])
        bar_id = self.user.copy(self.cr, UID, foo_id, {'partner_id': par_id, 'login': 'bar'})
        foo_after, = self.user.read(self.cr, UID, [foo_id])
        del foo_after['__last_update']
        partners_after = self.partner.search(self.cr, UID, [])

        self.assertEqual(foo_before, foo_after)
        self.assertEqual(set(partners_before), set(partners_after))

        foo, bar = self.user.browse(self.cr, UID, [foo_id, bar_id])
        self.assertNotEqual(foo.id, bar.id)
        self.assertEqual(bar.partner_id.id, par_id)
        self.assertEqual(bar.login, 'bar', "login is given from copy parameters")
        self.assertFalse(bar.login_date, "login_date should not be copied from original record")
        self.assertEqual(bar.name, 'Bar', "name is given from specific partner")
        self.assertEqual(bar.signature, foo.signature, "signature should be copied")



CREATE = lambda values: (0, False, values)
UPDATE = lambda id, values: (1, id, values)
DELETE = lambda id: (2, id, False)
FORGET = lambda id: (3, id, False)
LINK_TO = lambda id: (4, id, False)
DELETE_ALL = lambda: (5, False, False)
REPLACE_WITH = lambda ids: (6, False, ids)

def sorted_by_id(list_of_dicts):
    "sort dictionaries by their 'id' field; useful for comparisons"
    return sorted(list_of_dicts, key=lambda d: d.get('id'))

class TestO2MSerialization(common.TransactionCase):
    """ test the orm method 'write' on one2many fields """

    def setUp(self):
        super(TestO2MSerialization, self).setUp()
        self.partner = self.registry('res.partner')

    def test_no_command(self):
        " empty list of commands yields an empty list of records "
        results = self.partner.resolve_2many_commands(
            self.cr, UID, 'child_ids', [])

        self.assertEqual(results, [])

    def test_CREATE_commands(self):
        " returns the VALUES dict as-is "
        values = [{'foo': 'bar'}, {'foo': 'baz'}, {'foo': 'baq'}]
        results = self.partner.resolve_2many_commands(
            self.cr, UID, 'child_ids', map(CREATE, values))

        self.assertEqual(results, values)

    def test_LINK_TO_command(self):
        " reads the records from the database, records are returned with their ids. "
        ids = [
            self.partner.create(self.cr, UID, {'name': 'foo'}),
            self.partner.create(self.cr, UID, {'name': 'bar'}),
            self.partner.create(self.cr, UID, {'name': 'baz'})
        ]
        commands = map(LINK_TO, ids)

        results = self.partner.resolve_2many_commands(
            self.cr, UID, 'child_ids', commands, ['name'])

        self.assertEqual(sorted_by_id(results), sorted_by_id([
            {'id': ids[0], 'name': 'foo'},
            {'id': ids[1], 'name': 'bar'},
            {'id': ids[2], 'name': 'baz'}
        ]))

    def test_bare_ids_command(self):
        " same as the equivalent LINK_TO commands "
        ids = [
            self.partner.create(self.cr, UID, {'name': 'foo'}),
            self.partner.create(self.cr, UID, {'name': 'bar'}),
            self.partner.create(self.cr, UID, {'name': 'baz'})
        ]

        results = self.partner.resolve_2many_commands(
            self.cr, UID, 'child_ids', ids, ['name'])

        self.assertEqual(sorted_by_id(results), sorted_by_id([
            {'id': ids[0], 'name': 'foo'},
            {'id': ids[1], 'name': 'bar'},
            {'id': ids[2], 'name': 'baz'}
        ]))

    def test_UPDATE_command(self):
        " take the in-db records and merge the provided information in "
        id_foo = self.partner.create(self.cr, UID, {'name': 'foo'})
        id_bar = self.partner.create(self.cr, UID, {'name': 'bar'})
        id_baz = self.partner.create(self.cr, UID, {'name': 'baz', 'city': 'tag'})

        results = self.partner.resolve_2many_commands(
            self.cr, UID, 'child_ids', [
                LINK_TO(id_foo),
                UPDATE(id_bar, {'name': 'qux', 'city': 'tagtag'}),
                UPDATE(id_baz, {'name': 'quux'})
            ], ['name', 'city'])

        self.assertEqual(sorted_by_id(results), sorted_by_id([
            {'id': id_foo, 'name': 'foo', 'city': False},
            {'id': id_bar, 'name': 'qux', 'city': 'tagtag'},
            {'id': id_baz, 'name': 'quux', 'city': 'tag'}
        ]))

    def test_DELETE_command(self):
        " deleted records are not returned at all. "
        ids = [
            self.partner.create(self.cr, UID, {'name': 'foo'}),
            self.partner.create(self.cr, UID, {'name': 'bar'}),
            self.partner.create(self.cr, UID, {'name': 'baz'})
        ]
        commands = [DELETE(ids[0]), DELETE(ids[1]), DELETE(ids[2])]

        results = self.partner.resolve_2many_commands(
            self.cr, UID, 'child_ids', commands, ['name'])

        self.assertEqual(results, [])

    def test_mixed_commands(self):
        ids = [
            self.partner.create(self.cr, UID, {'name': name})
            for name in ['NObar', 'baz', 'qux', 'NOquux', 'NOcorge', 'garply']
        ]

        results = self.partner.resolve_2many_commands(
            self.cr, UID, 'child_ids', [
                CREATE({'name': 'foo'}),
                UPDATE(ids[0], {'name': 'bar'}),
                LINK_TO(ids[1]),
                DELETE(ids[2]),
                UPDATE(ids[3], {'name': 'quux',}),
                UPDATE(ids[4], {'name': 'corge'}),
                CREATE({'name': 'grault'}),
                LINK_TO(ids[5])
            ], ['name'])

        self.assertEqual(sorted_by_id(results), sorted_by_id([
            {'name': 'foo'},
            {'id': ids[0], 'name': 'bar'},
            {'id': ids[1], 'name': 'baz'},
            {'id': ids[3], 'name': 'quux'},
            {'id': ids[4], 'name': 'corge'},
            {'name': 'grault'},
            {'id': ids[5], 'name': 'garply'}
        ]))

    def test_LINK_TO_pairs(self):
        "LINK_TO commands can be written as pairs, instead of triplets"
        ids = [
            self.partner.create(self.cr, UID, {'name': 'foo'}),
            self.partner.create(self.cr, UID, {'name': 'bar'}),
            self.partner.create(self.cr, UID, {'name': 'baz'})
        ]
        commands = map(lambda id: (4, id), ids)

        results = self.partner.resolve_2many_commands(
            self.cr, UID, 'child_ids', commands, ['name'])

        self.assertEqual(sorted_by_id(results), sorted_by_id([
            {'id': ids[0], 'name': 'foo'},
            {'id': ids[1], 'name': 'bar'},
            {'id': ids[2], 'name': 'baz'}
        ]))

    def test_singleton_commands(self):
        "DELETE_ALL can appear as a singleton"
        results = self.partner.resolve_2many_commands(
            self.cr, UID, 'child_ids', [DELETE_ALL()], ['name'])

        self.assertEqual(results, [])

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
