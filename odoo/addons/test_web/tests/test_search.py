from odoo.tests import tagged, TransactionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestNonIntId(TransactionCase):
    def test_query_non_int(self):
        records = self.env['test_orm.view.str.id'].search([('name', '=', 'test')])
        self.assertEqual(records.id, 'hello')
        records.invalidate_model()
        self.assertEqual(records.name, 'test')

    def test_query_non_int_read_group(self):
        result = self.env['test_orm.view.str.id'].formatted_read_group([], ['name'], ['__count'])
        self.assertEqual(result, [{'name': 'test', '__count': 1, '__extra_domain': [('name', '=', 'test')]}])
        result = self.env['test_orm.view.str.id'].formatted_read_group([], [], ['name:count'])
        self.assertEqual(result, [{'name:count': 1, '__extra_domain': [(1, '=', 1)]}])
