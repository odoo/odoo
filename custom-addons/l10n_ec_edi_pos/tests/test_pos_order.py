from .common import TestEcEdiPosCommon

import lxml
from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tools import file_open
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEcPos(TestEcEdiPosCommon, TestAccountReportsCommon):

    @freeze_time('2024-01-01')
    def test_pos_multi_payments_invoice_xml(self):
        """Asserts that invoices created from orders with two or more payments have the correct XML payment data."""
        with self.with_pos_session() as _session:
            multi_payments_order = self._create_order({
                'pos_order_lines_ui_args': [(self.product_a, 1)],
                'payments': [(self.cash_pm1, 575.0), (self.bank_pm1, 575.0)],
                'customer': self.partner_a,
            })
            multi_payments_order.action_pos_order_invoice()
            self.assertEqual(multi_payments_order.account_move.l10n_ec_sri_payment_id.code, "mpm", "PoS orders with multiple payments should have Multiple Payment Methods (PoS) as their SRI payment method.")

            invoice = multi_payments_order.account_move
            generated_file, errors = self.env['account.edi.format'].with_context(skip_xsd=True)._l10n_ec_generate_xml(invoice)
            self.assertFalse(errors)
            self.assertTrue(generated_file)
            with file_open('l10n_ec_edi_pos/tests/data/expected_document.xml', 'rt') as f:
                expected_xml = lxml.etree.fromstring(f.read().encode())
            self.assertXmlTreeEqual(lxml.etree.fromstring(generated_file.encode()), expected_xml)
