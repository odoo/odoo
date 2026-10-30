import unittest

from odoo.exceptions import UserError, ValidationError
from odoo.tests import new_test_user, tagged

from odoo.addons.l10n_pt_pos.tests.common import TestL10nPtPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtPosOrder(TestL10nPtPosCommon):
    """
    The fiscal document of a PT PoS sale is its invoice, issued as the order is synced: an
    invoice-receipt (FR) when the customer is identified, a simplified invoice (FS, CIVA art. 40)
    when it is not and the sale is within the FS limit, a credit note (NC) against the original
    document for a refund (Despacho 8632/2014 2.1.1; FAQ 0899).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.session = cls.open_session()

    # -------------------------------------------------------------------------
    # Documents
    # -------------------------------------------------------------------------

    def test_identified_customer_invoice_receipt(self):
        """A paid sale to an identified customer is an FR, issued at sync, as the cashier."""
        order = self.sell(partner=self.partner_pt)
        invoice = order.account_move
        self.assertRecordValues(invoice, [{
            'move_type': 'out_invoice',
            'l10n_pt_document_type': 'out_invoice_receipt',
            'l10n_pt_at_series_id': self.series_fr.id,
            'partner_id': self.partner_pt.id,
            'amount_total': 12.3,
            'name': 'FR 2026/00001',
            'l10n_pt_issue_user_id': self.cashier.id,
        }])
        self.assertIssued(invoice)
        self.assertIn(invoice.payment_state, ('paid', 'in_payment'))
        self.assertEqual(self.signing.calls['sign_records'], 1)

    def test_anonymous_sale_simplified_invoice(self):
        """
        A sale without customer, or to the generic 'Consumidor final', within the FS limit is an FS to
        'Consumidor final' (PT-23).
        """
        anonymous = self.sell()
        final_consumer = self.sell(partner=self.final_consumer)
        for order in anonymous + final_consumer:
            self.assertEqual(order.partner_id, self.final_consumer)
            self.assertRecordValues(order.account_move, [{
                'move_type': 'out_receipt',
                'l10n_pt_document_type': 'out_receipt',
                'l10n_pt_at_series_id': self.series_fs.id,
                'partner_id': self.final_consumer.id,
            }])
            self.assertIssued(order.account_move)
        self.assertEqual((anonymous + final_consumer).account_move.mapped('name'), ['FS 2026/00001', 'FS 2026/00002'])

    def test_simplified_invoice_limit(self):
        """
        An anonymous sale above the FS limit, 1000 EUR for goods and 100 EUR as soon as a service is
        sold (CIVA art. 40(1)), is an FR to 'Consumidor final' (PT-23); an identified customer gets an
        FR at any amount.
        """
        for lines, partner, document_type in (
            ([(self.product_goods, 81)], None, 'out_receipt'),                          # 996.30
            ([(self.product_goods, 82)], None, 'out_invoice_receipt'),                  # 1008.60
            ([(self.product_pos_service, 8)], None, 'out_receipt'),                     # 98.40
            ([(self.product_pos_service, 9)], self.final_consumer, 'out_invoice_receipt'),  # 110.70
            ([(self.product_goods, 8), (self.product_pos_service, 1)], None, 'out_invoice_receipt'),  # 110.70
            ([(self.product_goods, 1)], self.partner_pt, 'out_invoice_receipt'),
            ([(self.product_goods, 82)], self.partner_pt, 'out_invoice_receipt'),
        ):
            with self.subTest(lines=lines, partner=partner and partner.name):
                order = self.sell(lines, partner)
                self.assertEqual(order.account_move.l10n_pt_document_type, document_type)
                self.assertEqual(order.account_move.partner_id, partner or self.final_consumer)
                self.assertIssued(order.account_move)

    def test_pay_later_invoice(self):
        """
        A sale charged to the customer's account is not paid at issue: an invoice (FT), issued at sync,
        not an invoice-receipt (FAQ 0899, PT-136).
        """
        order = self.sell(partner=self.partner_pt, payments=[(self.customer_account_method, 12.3)])
        self.assertRecordValues(order.account_move, [{
            'l10n_pt_document_type': 'out_invoice',
            'l10n_pt_at_series_id': self.series_ft.id,
            'payment_state': 'not_paid',
        }])
        self.assertIssued(order.account_move)

    @unittest.skip("PT-137 (todo): only the till forces invoicing; a PT order synced without it gets no document")
    def test_sale_not_to_invoice(self):
        """
        Every PT sale gets its fiscal document (CIVA art. 29(1)(b)), whatever the till sends: an order
        synced without invoicing is invoiced and issued all the same.
        """
        order = self.sell(to_invoice=False)
        self.assertEqual(order.account_move.l10n_pt_document_type, 'out_receipt')
        self.assertIssued(order.account_move)

    # -------------------------------------------------------------------------
    # Refunds
    # -------------------------------------------------------------------------

    def test_refund_credit_note(self):
        """A refund at the till is an NC against the FS or FR it refunds, issued at sync."""
        for partner in (None, self.partner_pt):
            with self.subTest(partner=partner and partner.name):
                order = self.sell([(self.product_goods, 3)], partner)
                refund = self.refund(order, qty=1)
                self.assertRecordValues(refund.account_move, [{
                    'move_type': 'out_refund',
                    'l10n_pt_document_type': 'out_refund',
                    'l10n_pt_at_series_id': self.series_nc.id,
                    'reversed_entry_id': order.account_move.id,
                    'partner_id': order.account_move.partner_id.id,
                    'amount_total': 12.3,
                }])
                self.assertIssued(refund.account_move)

    # -------------------------------------------------------------------------
    # Lines
    # -------------------------------------------------------------------------

    def test_line_discount_kept(self):
        """The invoice of a discounted sale totals what was paid: the line discount is its own (PT-29)."""
        order = self.sell([(self.product_goods, 2, 10.0)])
        self.assertAlmostEqual(order.amount_total, 22.14)
        self.assertRecordValues(order.account_move, [{'amount_total': 22.14}])
        self.assertRecordValues(order.account_move.invoice_line_ids, [{'l10n_pt_line_discount': 10.0, 'discount': 10.0}])

    def test_line_without_tax_refused(self):
        """A line without tax cannot be issued: the sale is refused at sync, and nothing is recorded."""
        data = self.order_data([{'product_id': self.product_goods.id, 'qty': 1, 'tax_ids': []}])
        with self.assertRaisesRegex(ValidationError, "without VAT tax"), self.env.cr.savepoint():
            self.sync(data)
        self.assertFalse(self.env['pos.order'].search([('uuid', '=', data['uuid'])]))

    # -------------------------------------------------------------------------
    # Session
    # -------------------------------------------------------------------------

    def test_session_closing(self):
        """
        Closing the session leaves the issued invoices as they were. The card takings are booked as one
        payment of the bank journal, which takes a receipt number (RG) without customer or invoice, though
        the FR already receipts that money: pinned to today's behaviour until PT-140 is answered.
        """
        orders = self.sell() + self.sell(partner=self.partner_pt, payments=[(self.card_method, 12.3)])
        signatures = orders.account_move.mapped('inalterable_hash')
        self.session.action_pos_session_closing_control()
        self.assertEqual(self.session.state, 'closed')
        self.assertEqual(orders.account_move.mapped('inalterable_hash'), signatures)
        self.assertChainVerified(orders.account_move)
        self.assertRecordValues(self.env['account.payment'].search([('l10n_pt_at_series_id', '!=', False)]), [{
            'pos_payment_method_id': self.card_method.id,
            'amount': 12.3,
            'partner_id': False,
            'l10n_pt_at_series_id': self.series_rg.id,
            'l10n_pt_document_number': 'RG 2026/00001',
        }])

    # -------------------------------------------------------------------------
    # Master data
    # -------------------------------------------------------------------------

    def test_customer_nif_locked_by_pos_document(self):
        """
        A customer's NIF can be entered while empty or generic, but not changed once a document was
        issued to it (Despacho 8632/2014 3.3.4), a PoS sale included.
        """
        partner = self.env['res.partner'].create({'name': 'Cliente Loja', 'company_id': self.company_pt.id})
        partner.vat = 'PT123456789'
        partner.vat = '999999990'
        self.sell(partner=partner)
        partner.vat = 'PT123456789'
        with self.assertRaisesRegex(UserError, "cannot change the VAT number"):
            partner.vat = 'PT987654321'

    def test_product_name_locked_by_pos_sale(self):
        """
        A product's name cannot change once sold in a PT PoS (Despacho 8632/2014 3.3.5), whoever renames
        it; a user without PoS rights still renames a product never sold (PT-124).
        """
        product_manager = new_test_user(self.env, login='pt_product_manager', groups='base.group_user,product.group_product_manager')
        self.product_goods.name = 'Caneca azul'
        self.sell()
        with self.assertRaisesRegex(UserError, "modify the name of a product"):
            self.product_goods.with_user(product_manager).name = 'Caneca verde'
        self.product_pos_service.with_user(product_manager).name = 'Embrulho de Natal'
        self.assertEqual(self.product_pos_service.name, 'Embrulho de Natal')
