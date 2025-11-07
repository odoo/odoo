from odoo.tests import tagged, TransactionCase


@tagged('at_install', '-post_install')
class TestCreate(TransactionCase):
    def test_create_multi(self):
        """ create for multiple records """
        vals_list = [{'foo': foo} for foo in ('Foo', 'Bar', 'Baz')]
        vals_list[0]['text'] = 'TEXT EXAMPLE'
        for vals in vals_list:
            record = self.env['test_orm.mixed'].create(vals)
            self.assertEqual(len(record), 1)
            self.assertEqual(record.foo, vals['foo'])
            self.assertEqual(record.text, vals.get('text', False))

        records = self.env['test_orm.mixed'].create([])
        self.assertFalse(records)

        records = self.env['test_orm.mixed'].create(vals_list)
        self.assertEqual(len(records), len(vals_list))
        for record, vals in zip(records, vals_list):
            self.assertEqual(record.foo, vals['foo'])
            self.assertEqual(record.text, vals.get('text', False))
