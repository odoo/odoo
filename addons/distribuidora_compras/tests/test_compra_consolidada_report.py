from datetime import date, datetime

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCompraConsolidadaReport(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product = self.env['product.product'].create({'name': 'Papa', 'list_price': 500.0})
        self.partner = self.env['res.partner'].create({'name': 'Cliente Test'})
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'commitment_date': datetime(2026, 7, 20, 15, 0, 0),  # lunes
        })
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_uom_qty': 6,
        })
        order.action_confirm()

    def test_report_renders_consolidated_quantity(self):
        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_entrega': date(2026, 7, 20),
        })
        html, _report_type = self.env['ir.actions.report']._render_qweb_html(
            'distribuidora_compras.action_report_compra_consolidada', wizard.ids
        )
        content = html.decode()
        self.assertIn('Papa', content)
        self.assertIn('6.0', content)

    def test_report_renders_empty_notice_when_no_orders(self):
        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_entrega': date(2099, 1, 1),
        })
        html, _report_type = self.env['ir.actions.report']._render_qweb_html(
            'distribuidora_compras.action_report_compra_consolidada', wizard.ids
        )
        content = html.decode()
        self.assertIn('No hay pedidos confirmados', content)
