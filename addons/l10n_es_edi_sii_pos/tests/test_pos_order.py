import datetime
from contextlib import contextmanager

from odoo.tests import tagged

from .common import TestL10nEsEdiSiiPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEsEdiSiiPosOrder(TestL10nEsEdiSiiPosCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        cls.fakenow = datetime.datetime(2025, 1, 1)
        cls.enterClassContext(cls.mock_datetime_and_now(cls.fakenow))

    @contextmanager
    def with_pos_session(self):
        session = self.open_new_session(0.0)
        yield session
        cash_pm = self.config._get_cash_payment_method()
        session.close_session_from_ui({cash_pm.id: 0})

    def _create_order(self, pos_order_ui_args=None, **data):
        order_data = self.create_ui_order_data(
            pos_order_ui_args=pos_order_ui_args or {}, **data)
        results = self.env['pos.order'].sync_from_ui([order_data])
        return self.env['pos.order'].browse(results['pos.order'][0]['id'])

    def _create_sale(self, **extra):
        return self._create_order(
            pos_order_lines_ui_args=[(self.product, 1.0)],
            payments=[(self.bank_pm1, 121.0)],
            **extra,
        )

    def test_refund_is_invoiced_as_r5(self):
        with self.with_pos_session():
            order = self._create_sale()
            refund = self.env['pos.order'].browse(order.refund()['res_id'])
            payment_context = {'active_ids': refund.ids, 'active_id': refund.id}
            self.env['pos.make.payment'].with_context(**payment_context).create({
                'amount': refund.amount_total,
                'payment_method_id': self.bank_pm1.id,
            }).with_context(**payment_context).check()

        credit_note = refund.account_move
        self.assertTrue(credit_note, "El reembolso debe generar una factura")
        self.assertEqual(credit_note.move_type, 'out_refund')
        self.assertEqual(credit_note.l10n_es_invoice_type, 'R5')
        self.assertEqual(credit_note.partner_id, self.env.ref('l10n_es.partner_simplified'))

    def test_refund_with_explicit_reason_keeps_it(self):
        with self.with_pos_session():
            order = self._create_sale()
            refund = self.env['pos.order'].browse(order.refund()['res_id'])
            refund.l10n_es_invoice_type = 'R1'
            vals = refund._prepare_invoice_vals()
        self.assertEqual(vals['l10n_es_invoice_type'], 'R1')

    def test_closing_move_is_f4_with_range(self):
        with self.with_pos_session():
            orders = self.env['pos.order']
            for _ in range(3):
                orders |= self._create_sale()

        closing_move = self.pos_session.sale_move_ids
        self.assertEqual(len(closing_move), 1)
        self.assertEqual(closing_move.l10n_es_invoice_type, 'F4')
        ordered = orders.sorted('sequence_number')
        self.assertEqual(closing_move.first_invoice, ordered[0].pos_reference)
        self.assertEqual(closing_move.last_invoice, ordered[-1].pos_reference)

    def test_closing_move_excludes_invoiced_orders(self):
        with self.with_pos_session():
            self._create_sale(is_invoiced=True, customer=self.partner_b)
            first = self._create_sale()
            last = self._create_sale()
            self._create_sale(is_invoiced=True, customer=self.partner_b)
        closing_move = self.pos_session.sale_move_ids
        self.assertEqual(closing_move.first_invoice, first.pos_reference)
        self.assertEqual(closing_move.last_invoice, last.pos_reference)

    def test_closing_move_payload_f4(self):
        with self.with_pos_session():
            for _ in range(2):
                self._create_sale()

        closing_move = self.pos_session.sale_move_ids
        info = closing_move._l10n_es_edi_get_invoices_info()[0]
        id_factura = info['IDFactura']
        self.assertEqual(id_factura['NumSerieFacturaEmisor'], closing_move.first_invoice[:60])
        self.assertEqual(id_factura['NumSerieFacturaEmisorResumenFin'], closing_move.last_invoice[:60])
        self.assertEqual(info['FacturaExpedida']['TipoFactura'], 'F4')
        self.assertNotIn('Contraparte', info['FacturaExpedida'])
