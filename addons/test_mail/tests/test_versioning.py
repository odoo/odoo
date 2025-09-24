from odoo.tests.common import TransactionCase
from odoo.addons.mail.tools.discuss import Store


class TestVersioningModelsMixin(TransactionCase):
    def test_basic_versioning_model(self):
        foo = self.env['foo.model'].create({
            'name': 'Test Foo',
        })
        self.assertEqual(foo.version, 1)
        foo.write({'name': 'Updated Test Foo'})
        self.assertEqual(foo.version, 2)

    def test_versioning_with_relational_field(self):
        foo = self.env["foo.model"].create(
            [
                {
                    "name": "Test Foo",
                },
                {
                    "name": "Another Test Foo",
                },
            ]
        )
        bar = self.env['bar.model'].create({
            'name': 'Test Bar',
            'foo_id': foo[0].id,
        })
        self.assertEqual(len(bar._get_versioning_sequence()), 0)
        self.assertEqual(bar.version, 1)
        bar.write({'name': 'Updated Test Bar'})
        self.assertEqual(len(bar._get_versioning_sequence()), 1)
        self.assertEqual(bar.version, 2)
        foo[0].name = "Modified Foo"
        self.assertEqual(foo[0].version, 2)
        self.assertEqual(foo[1].version, 1)
        self.assertEqual(bar.version, 2)
        bar.foo_id = foo[1]
        self.assertEqual(bar.version, 3)
        self.assertEqual(foo[1].version, 1)

    def test_versioning_in_store(self):
        foo = self.env['foo.model'].create({
            'name': 'Test Foo',
        })
        store = Store()
        store.add(foo, [])
        store_data = store.get_result()
        foo_data = next(filter(lambda r: r["id"] == foo.id, store_data['foo.model']))
        self.assertEqual(foo_data['version'], 1)

    def test_versioning_in_store_with_fields(self):
        foo = self.env['foo.model'].create({
            'name': 'Test Foo',
        })
        foo.name = "Changed Name"
        store = Store()
        store.add(foo, ['name'])
        store_data = store.get_result()
        foo_data = next(filter(lambda r: r["id"] == foo.id, store_data['foo.model']))
        self.assertEqual(foo_data['version'], 2)
        self.assertEqual(foo_data['name'], "Changed Name")
