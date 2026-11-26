# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from .common import TestL10nEsEdiPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEsEdiPosOrderReceipt(TestL10nEsEdiPosCommon):

    def test_receipt_simplified_invoice(self):
        self.open_new_session(0.0)
        order = self._create_sale()

        data = order.order_receipt_generate_data()
        self.assertTrue(data['conditions']['l10n_es_pos_edi'])
        self.assertTrue(data['conditions']['l10n_es_pos_invoice_name'])
        self.assertTrue(data['conditions']['l10n_es_pos_simplified_invoice'])
        self.assertEqual(data['extra_data']['l10n_es_pos_invoice_name'], order._l10n_es_pos_get_simplified_invoice_name())

    def test_receipt_invoice(self):
        self.open_new_session(0.0)
        order = self._create_sale(is_invoiced=True, customer=self.partner_b)

        data = order.order_receipt_generate_data()
        self.assertTrue(data['conditions']['l10n_es_pos_invoice_name'])
        self.assertFalse(data['conditions']['l10n_es_pos_simplified_invoice'])
        self.assertEqual(data['extra_data']['l10n_es_pos_invoice_name'], order.account_move.name)

    def test_receipt_draft(self):
        """ A draft (e.g. the bill of an open restaurant table) has no number yet. """
        self.open_new_session(0.0)
        draft = self._create_draft()

        data = draft.order_receipt_generate_data()
        self.assertTrue(data['conditions']['l10n_es_pos_edi'])
        self.assertFalse(data['conditions']['l10n_es_pos_invoice_name'])

    def test_receipt_hides_simplified_invoice_partner(self):
        self.open_new_session(0.0)
        order = self._create_sale(customer=self.env.ref('l10n_es.partner_simplified'))

        data = order.order_receipt_generate_data()
        self.assertFalse(data['partner'])

    def test_receipt_without_fiscal_mode(self):
        self.open_new_session(0.0)
        with self._patch_fiscal_mode(False):
            order = self._create_sale()
            data = order.order_receipt_generate_data()

        self.assertNotIn('l10n_es_pos_edi', data['conditions'])
        self.assertNotIn('l10n_es_pos_invoice_name', data['conditions'])

    def test_receipt_simplified_credit_note(self):
        self.open_new_session(0.0)
        refund = self._create_refund(self._create_sale())

        data = refund.order_receipt_generate_data()
        self.assertTrue(data['conditions']['l10n_es_pos_invoice_name'])
        self.assertTrue(data['conditions']['l10n_es_pos_simplified_credit_note'])
        self.assertFalse(data['conditions']['l10n_es_pos_simplified_invoice'])
        self.assertEqual(data['extra_data']['l10n_es_pos_invoice_name'], refund._l10n_es_pos_get_simplified_invoice_name())
