from odoo.tests.common import TransactionCase


class TestResCompany(TransactionCase):
    def test_create_warehouse_default_code(self):
        code = 'TEST'
        company = self.env['res.company'].with_context(default_code=code).create({
            'name': 'name',
        })
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company.id)])
        self.assertEqual(code, warehouse.code)
        sequences = self.env['ir.sequence'].search([('company_id', '=', company.id), ('code', '=', code)])
        self.assertEqual([], list(sequences), 'warehouse default_code should not overwrite sequence codes')
