import os
import unittest2
import openerp

UID = 1
DB = os.environ['OPENERP_DATABASE']

CREATE = lambda values: (0, False, values)
UPDATE = lambda id, values: (1, id, values)
LINK_TO = lambda id: (4, id, False)


def setUpModule():
    openerp.tools.config['addons_path'] = os.environ['OPENERP_ADDONS_PATH']

class TestO2MSerialization(unittest2.TestCase):
    def setUp(self):
        self.cr = openerp.modules.registry.RegistryManager.get(DB).db.cursor()
        self.partner = openerp.modules.registry.RegistryManager.get(DB)['res.partner']
        self.address = openerp.modules.registry.RegistryManager.get(DB)['res.partner.address']
    def tearDown(self):
        self.cr.rollback()
        self.cr.close()

    def test_no_command(self):
        " empty list of commands yields an empty list of records "
        results = list(self.partner.serialize_o2m_commands(self.cr, UID, 'address', []))

        self.assertEqual(results, [])

    def test_CREATE_commands(self):
        " returns the VALUES dict as-is "
        results = list(self.partner.serialize_o2m_commands(
            self.cr, UID, 'address',
            map(CREATE, [{'foo': 'bar'}, {'foo': 'baz'}, {'foo': 'baq'}])))
        self.assertEqual(results, [
            {'foo': 'bar'},
            {'foo': 'baz'},
            {'foo': 'baq'}
        ])

    def test_LINK_TO_command(self):
        " reads the records from the database, records are returned with their ids. "
        ids = [
            self.address.create(self.cr, UID, {'name': 'foo'}),
            self.address.create(self.cr, UID, {'name': 'bar'}),
            self.address.create(self.cr, UID, {'name': 'baz'})
        ]
        commands = map(LINK_TO, ids)

        results = list(self.partner.serialize_o2m_commands(self.cr, UID, 'address', commands, ['name']))

        self.assertEqual(results, [
            {'id': ids[0], 'name': 'foo'},
            {'id': ids[1], 'name': 'bar'},
            {'id': ids[2], 'name': 'baz'}
        ])

    def test_bare_ids_command(self):
        " same as the equivalent LINK_TO commands "
        ids = [
            self.address.create(self.cr, UID, {'name': 'foo'}),
            self.address.create(self.cr, UID, {'name': 'bar'}),
            self.address.create(self.cr, UID, {'name': 'baz'})
        ]

        results = list(self.partner.serialize_o2m_commands(self.cr, UID, 'address', ids, ['name']))

        self.assertEqual(results, [
            {'id': ids[0], 'name': 'foo'},
            {'id': ids[1], 'name': 'bar'},
            {'id': ids[2], 'name': 'baz'}
        ])

    def test_UPDATE_command(self):
        " take the in-db records and merge the provided information in "
        id_foo = self.address.create(self.cr, UID, {'name': 'foo'})
        id_bar = self.address.create(self.cr, UID, {'name': 'bar'})
        id_baz = self.address.create(self.cr, UID, {'name': 'baz', 'city': 'tag'})

        results = list(self.partner.serialize_o2m_commands(
            self.cr, UID, 'address', [
                LINK_TO(id_foo),
                UPDATE(id_bar, {'name': 'qux', 'city': 'tagtag'}),
                UPDATE(id_baz, {'name': 'quux'})
            ], ['name', 'city']))

        self.assertEqual(results, [
            {'id': id_foo, 'name': 'foo', 'city': False},
            {'id': id_bar, 'name': 'qux', 'city': 'tagtag'},
            {'id': id_baz, 'name': 'quux', 'city': 'tag'}
        ])

    def test_mixed_commands(self):
        ids = [
            self.address.create(self.cr, UID, {'name': name})
            for name in ['NObar', 'baz', 'qux', 'NOquux', 'NOcorge', 'garply']
        ]

        results = list(self.partner.serialize_o2m_commands(
            self.cr, UID, 'address', [
                CREATE({'name': 'foo'}),
                UPDATE(ids[0], {'name': 'bar'}),
                LINK_TO(ids[1]),
                LINK_TO(ids[2]),
                UPDATE(ids[3], {'name': 'quux',}),
                UPDATE(ids[4], {'name': 'corge'}),
                CREATE({'name': 'grault'}),
                LINK_TO(ids[5])
            ], ['name']))

        self.assertEqual(results, [
            {'name': 'foo'},
            {'id': ids[0], 'name': 'bar'},
            {'id': ids[1], 'name': 'baz'},
            {'id': ids[2], 'name': 'qux'},
            {'id': ids[3], 'name': 'quux'},
            {'id': ids[4], 'name': 'corge'},
            {'name': 'grault'},
            {'id': ids[5], 'name': 'garply'}
        ])
