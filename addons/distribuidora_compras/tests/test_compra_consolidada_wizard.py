from datetime import date, datetime

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCompraConsolidadaWizard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product = self.env['product.product'].create({'name': 'Papa', 'list_price': 500.0})
        self.partner = self.env['res.partner'].create({'name': 'Cliente Test'})

    def _create_confirmed_order(self, product, qty, order_date):
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': product.id,
            'product_uom_qty': qty,
        })
        order.action_confirm()
        # action_confirm sobreescribe date_order con la hora de confirmacion;
        # lo fijamos despues para simular un pedido confirmado en una fecha concreta.
        order.date_order = order_date
        return order

    def test_sums_quantities_across_confirmed_orders_same_date(self):
        order_date = datetime(2026, 7, 20, 15, 0, 0)
        self._create_confirmed_order(self.product, 2, order_date)
        self._create_confirmed_order(self.product, 3, order_date)
        self._create_confirmed_order(self.product, 5, order_date)

        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_pedido': order_date.date(),
        })
        lines = wizard._get_consolidated_lines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['product'], self.product)
        self.assertEqual(lines[0]['qty'], 10)
        self.assertEqual(lines[0]['uom'], self.product.uom_id.name)

    def test_excludes_orders_with_different_order_date(self):
        self._create_confirmed_order(self.product, 2, datetime(2026, 7, 20, 15, 0, 0))
        self._create_confirmed_order(self.product, 100, datetime(2026, 7, 22, 15, 0, 0))

        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_pedido': date(2026, 7, 20),
        })
        lines = wizard._get_consolidated_lines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['qty'], 2)

    def test_excludes_unconfirmed_orders(self):
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_uom_qty': 7,
        })
        # No se confirma: queda en borrador, con date_order de creacion.

        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_pedido': fields.Datetime.context_timestamp(order, order.date_order).date(),
        })

        self.assertEqual(wizard._get_consolidated_lines(), [])

    def test_no_orders_for_date_returns_empty_list(self):
        wizard = self.env['distribuidora.compra.consolidada.wizard'].create({
            'fecha_pedido': date(2099, 1, 1),
        })
        self.assertEqual(wizard._get_consolidated_lines(), [])

    def test_uses_costa_rica_local_date_not_utc(self):
        # 2026-07-21 02:00 UTC == 2026-07-20 20:00 America/Costa_Rica (lunes de noche).
        # Si la comparacion usara el dia UTC crudo, este pedido quedaria en "martes"
        # y no se incluiria al pedir la lista del lunes 2026-07-20.
        self._create_confirmed_order(self.product, 4, datetime(2026, 7, 21, 2, 0, 0))

        wizard = self.env['distribuidora.compra.consolidada.wizard'].with_context(
            tz='America/Costa_Rica'
        ).create({
            'fecha_pedido': date(2026, 7, 20),
        })
        lines = wizard._get_consolidated_lines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['qty'], 4)
