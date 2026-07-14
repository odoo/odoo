# addons/distribuidora_ventas/tests/test_invoice_from_order_quantity.py
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestInvoiceFromOrderQuantity(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product = self.env['product.product'].create({
            'name': 'Papa',
            'list_price': 500.0,
        })
        self.partner = self.env['res.partner'].create({'name': 'Cliente Test'})

    def test_new_consu_product_defaults_to_order_invoice_policy(self):
        self.assertEqual(self.product.type, 'consu')
        self.assertEqual(self.product.invoice_policy, 'order')

    def test_invoice_uses_corrected_line_quantity_not_original(self):
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_uom_qty': 5,
        })
        order.action_confirm()
        self.assertFalse(order.locked)

        # El colaborador corrige la cantidad siguiendo la hoja de papel:
        # se pidieron 5 kg, solo se pudieron entregar 3 kg.
        line.product_uom_qty = 3

        invoices = order._create_invoices()
        invoice_line = invoices.invoice_line_ids.filtered(lambda l: l.product_id == self.product)
        self.assertEqual(invoice_line.quantity, 3)
