from contextlib import contextmanager

from odoo.addons.l10n_mx_edi.tests.common import TestMxEdiCommon
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


class TestMxEdiPosCommon(TestMxEdiCommon, TestPoSCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config

        cls.product.write({
            'categ_id': cls.categ_basic.id,
            'available_in_pos': True,
        })

        cls.bank_pm1.l10n_mx_edi_payment_method_id = cls.payment_method_efectivo

    @contextmanager
    def with_pos_session(self):
        session = self.open_new_session(0.0)
        yield session
        session.post_closing_cash_details(0.0)
        session.close_session_from_ui()

    @contextmanager
    def create_and_invoice_order(self):
        # create order without customer
        with self.with_pos_session() as _session:
            order = self._create_order({
                'pos_order_lines_ui_args': [(self.product, 10)],
                'payments': [(self.bank_pm1, 11600.0)],
            })
        self.assertTrue(order.l10n_mx_edi_cfdi_to_public)
        yield order
        # invoice order
        action = order._generate_pos_order_invoice()
        invoice = self.env['account.move'].browse(action['res_id'])
        # generate CFDI
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()

    def _create_order(self, ui_data):
        order_data = self.create_ui_order_data(**ui_data)
        results = self.env['pos.order'].sync_from_ui([order_data])
        return self.env['pos.order'].browse(results['pos.order'][0]['id'])

    def _assert_order_cfdi(self, order, filename):
        document = order.l10n_mx_edi_document_ids.filtered(lambda x: x.state == 'invoice_sent')[:1]
        self.assertTrue(document)
        self._assert_document_cfdi(document, filename)

    def _assert_global_invoice_cfdi_from_orders(self, orders, filename):
        document = orders.l10n_mx_edi_document_ids.filtered(lambda x: x.state == 'ginvoice_sent')[:1]
        self.assertTrue(document)
        self._assert_document_cfdi(document, filename)
