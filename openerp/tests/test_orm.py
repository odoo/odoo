import unittest2

import openerp
import common

UID = common.ADMIN_USER_ID
DB = common.DB

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

    def setUp(self):
        super(TestO2MSerialization, self).setUp()
        self.partner = self.registry('res.partner')

    def test_no_command(self):
        " empty list of commands yields an empty list of records "
        results = self.partner.resolve_2many_commands(
            self.cr, UID, 'address', [])

        self.assertEqual(results, [])

    def test_CREATE_commands(self):
        " returns the VALUES dict as-is "
        values = [{'foo': 'bar'}, {'foo': 'baz'}, {'foo': 'baq'}]
        results = self.partner.resolve_2many_commands(
            self.cr, UID, 'address', map(CREATE, values))

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
            self.cr, UID, 'address', commands, ['name'])

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
            self.cr, UID, 'address', ids, ['name'])

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
            self.cr, UID, 'address', [
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
            self.cr, UID, 'address', commands, ['name'])

        self.assertEqual(results, [])

    def test_mixed_commands(self):
        ids = [
            self.partner.create(self.cr, UID, {'name': name})
            for name in ['NObar', 'baz', 'qux', 'NOquux', 'NOcorge', 'garply']
        ]

        results = self.partner.resolve_2many_commands(
            self.cr, UID, 'address', [
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
            self.cr, UID, 'address', commands, ['name'])

        self.assertEqual(sorted_by_id(results), sorted_by_id([
            {'id': ids[0], 'name': 'foo'},
            {'id': ids[1], 'name': 'bar'},
            {'id': ids[2], 'name': 'baz'}
        ]))

    def test_singleton_commands(self):
        "DELETE_ALL can appear as a singleton"
        results = self.partner.resolve_2many_commands(
            self.cr, UID, 'address', [DELETE_ALL()], ['name'])

        self.assertEqual(results, [])

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
