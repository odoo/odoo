from openerp.tests import common


class test_orm(common.TransactionCase):

    def test_long_table_alias(self):
        self.env['res.users'].search([('name', '=', 'test')])
