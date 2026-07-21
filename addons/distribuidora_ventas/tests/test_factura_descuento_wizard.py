from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestFacturaDescuentoWizard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.tax = self.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        self.product = self.env['product.product'].create({
            'name': 'Producto Test Descuento',
            'list_price': 1000.0,
            'taxes_id': [(6, 0, self.tax.ids)],
        })
        self.partner = self.env['res.partner'].create({'name': 'Cliente Test Descuento'})
        self.move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 2,
                'price_unit': 1000.0,
                'tax_ids': [(6, 0, self.tax.ids)],
            })],
        })

    def test_applies_percentage_discount_with_correct_taxes(self):
        self.assertEqual(self.move.amount_untaxed, 2000.0)
        wizard = self.env['distribuidora.factura.descuento.wizard'].create({
            'move_id': self.move.id,
            'porcentaje': 10.0,
        })
        wizard.action_aplicar()

        self.assertEqual(self.move.amount_untaxed, 1800.0)
        self.assertEqual(self.move.amount_tax, 270.0)
        self.assertEqual(self.move.amount_total, 2070.0)
        discount_lines = self.move.invoice_line_ids.filtered(
            lambda l: l.product_id == self.move.company_id.sale_discount_product_id
        )
        self.assertEqual(len(discount_lines), 1)
        self.assertEqual(discount_lines.price_unit, -200.0)

    def test_rejects_percentage_over_100(self):
        with self.assertRaises(ValidationError):
            self.env['distribuidora.factura.descuento.wizard'].create({
                'move_id': self.move.id,
                'porcentaje': 150.0,
            })

    def test_rejects_zero_percentage(self):
        with self.assertRaises(ValidationError):
            self.env['distribuidora.factura.descuento.wizard'].create({
                'move_id': self.move.id,
                'porcentaje': 0.0,
            })

    def test_move_id_defaults_from_active_id_context(self):
        wizard = self.env['distribuidora.factura.descuento.wizard'].with_context(
            active_id=self.move.id
        ).create({'porcentaje': 10.0})
        self.assertEqual(wizard.move_id, self.move)
