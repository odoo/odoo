import unittest

from odoo.exceptions import RedirectWarning, UserError
from odoo.tests import tagged

from odoo.addons.l10n_pt_sale.tests.common import TestL10nPtSaleCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtSaleInvoicing(TestL10nPtSaleCommon):
    """
    Invoicing PT sales orders. The invoice references the orders it invoices, which are issued with it
    (Portaria 302/2016 4.1.4.19.3, OrderReferences). A down payment is invoiced on receipt (CIVA 36(1))
    and deducted from the final invoice. An order paid online is confirmed as from its form (D-6) and,
    with automatic invoicing, invoiced at once as an invoice-receipt (FR) handed to the customer, so
    issued as it is posted (FAQ 0899).
    """

    # -------------------------------------------------------------------------
    # Invoicing
    # -------------------------------------------------------------------------

    def test_invoice_carries_discounts(self):
        """The invoice of an order keeps its line and global discounts, and its amounts."""
        quotation = self.make_order(
            lines=[{'price_unit': 1234.568, 'l10n_pt_line_discount': 10.0}, {'price_unit': 756.81}],
            l10n_pt_global_discount=10.0,
        )
        sales_order = self.confirm(quotation)
        invoice = self.invoice(sales_order)
        self.assertIssued(sales_order)
        self.assertRecordValues(invoice, [{
            'l10n_pt_global_discount': 10.0,
            'amount_untaxed': 1681.13,
            'amount_tax': 386.66,
            'amount_total': sales_order.amount_total,
        }])
        self.assertRecordValues(invoice.invoice_line_ids, [
            {'l10n_pt_line_discount': 10.0, 'discount': 19.0, 'price_subtotal': 1000.0},
            {'l10n_pt_line_discount': 0.0, 'discount': 10.0, 'price_subtotal': 681.13},
        ])
        self.issue(self.post(invoice))
        self.assertIssued(invoice)

    # -------------------------------------------------------------------------
    # Down payments
    # -------------------------------------------------------------------------

    def _down_payment_lines(self, invoice):
        return invoice.invoice_line_ids.filtered(lambda line: line.is_downpayment and line.display_type == 'product')

    def test_down_payment_product(self):
        """
        A PT invoice line needs a product (D-4): down payment lines carry the company's 'Adiantamento'
        product, created once per company when first needed, and handed back without sudo (PT-103).
        """
        self.assertFalse(self.company_pt.l10n_pt_down_payment_product_id)
        product = self.company_pt.with_user(self.salesman)._l10n_pt_get_down_payment_product()
        self.assertFalse(product.env.su)
        self.assertEqual(product.env.uid, self.salesman.id)
        self.assertRecordValues(product, [{
            'name': 'Adiantamento',
            'default_code': 'ADIANTAMENTO',
            'company_id': self.company_pt.id,
            'sale_ok': False,
        }])
        self.assertEqual(self.company_pt._l10n_pt_get_down_payment_product(), product)
        self.assertNotEqual(self.company_pt_2._l10n_pt_get_down_payment_product(), product)

        sales_order = self.confirm(self.make_order())
        down_payment = self.invoice(sales_order, 'percentage', 30)
        self.assertEqual(self._down_payment_lines(down_payment).product_id, product)
        self.issue(self.post(down_payment))
        self.assertRecordValues(down_payment, [{'amount_total': 36.9}])

    def test_final_invoice_deducts_down_payment(self):
        """
        The final invoice deducts the down payment as a negative line, which a PT invoice otherwise
        refuses (PT-127); the down payment invoice has to be issued first, or is issued with the final
        invoice when that one is handed out at once (`l10n_pt_issue_automatically`).
        """
        for automatically in (False, True):
            with self.subTest(automatically=automatically):
                sales_order = self.confirm(self.make_order())
                down_payment = self.post(self.invoice(sales_order, 'percentage', 30))
                final = self.invoice(sales_order)
                self.assertRecordValues(self._down_payment_lines(final), [{'quantity': -1.0, 'price_unit': 30.0}])
                self.assertEqual(final.amount_total, 86.1)
                if automatically:
                    self.post(final.with_context(l10n_pt_issue_automatically=True))
                    self.assertIssued(down_payment + final)
                else:
                    with self.assertRaisesRegex(UserError, "A final invoice needs these invoices to be issued first"), self.env.cr.savepoint():
                        self.post(final)
                    self.issue(down_payment)
                    self.issue(self.post(final))
                    self.assertIssued(final)

    # -------------------------------------------------------------------------
    # Online payment
    # -------------------------------------------------------------------------

    def _payable_quotation(self, **vals):
        return self.make_order(**{'require_signature': False, 'require_payment': True, 'prepayment_percent': 1.0, **vals})

    def test_quotation_paid_online(self):
        """
        A quotation paid online stays the quotation issued; a new sales order is confirmed from it, as
        from its form (D-6). The payment, its automatic invoice -- an FR issued at once -- and the
        customer's landing page are the sales order's (PT-106, PT-105).
        """
        quotation = self._payable_quotation()
        transaction = self.pay_online(quotation)
        sales_order = quotation.sales_order_ids
        self.assertEqual(len(sales_order), 1)
        self.assertRecordValues(quotation, [{'state': 'draft', 'locked': True, 'l10n_pt_document_number': 'OR 2026/00001'}])
        self.assertRecordValues(sales_order, [{'state': 'sale', 'l10n_pt_document_number': 'NE 2026/00001'}])
        self.assertEqual(transaction.sale_order_ids, sales_order)
        self.assertEqual(transaction.landing_route, sales_order.get_portal_url())
        self.assertFalse(quotation.invoice_ids)
        invoice = sales_order.invoice_ids
        self.assertRecordValues(invoice, [{'state': 'posted', 'l10n_pt_document_type': 'out_invoice_receipt'}])
        self.assertIn(invoice.payment_state, ('in_payment', 'paid'))
        self.assertIssued(invoice)
        self.assertIssued(sales_order)

    def test_payment_of_quotation_confirmed_before(self):
        """A quotation confirmed from its form, then paid through a link sent before, pays that sales order (PT-106)."""
        quotation = self._payable_quotation()
        sales_order = self.confirm(quotation)
        transaction = self.pay_online(quotation)
        self.assertEqual(quotation.sales_order_ids, sales_order)
        self.assertEqual(quotation.state, 'draft')
        self.assertEqual(transaction.sale_order_ids, sales_order)
        self.assertEqual(transaction.landing_route, sales_order.get_portal_url())

    def test_payment_confirming_nothing(self):
        """A partial payment, or the payment of a quotation still to be signed, confirms nothing."""
        for vals, amount in (({}, 50.0), ({'require_signature': True}, None)):
            with self.subTest(vals=vals):
                quotation = self._payable_quotation(**vals)
                self.pay_online(quotation, amount=amount)
                self.assertFalse(quotation.sales_order_ids)
                self.assertIn(quotation.state, ('draft', 'sent'))

    def test_sales_order_series_without_code_fails_visibly(self):
        """If the sales order series has no AT validation code, the payment's processing stops with that error (PT-106)."""
        self.series_ne.at_code = False
        quotation = self._payable_quotation()
        with self.assertRaisesRegex((RedirectWarning, UserError), "has no AT validation code"), self.env.cr.savepoint():
            self.pay_online(quotation)

    @unittest.skip("PT-86 (decision pending): the back-office invoice of an order paid online cannot be posted, its payment reconciled before it is issued")
    def test_back_office_invoice_of_order_paid_online(self):
        """
        An order paid online in full, with automatic invoicing off, is invoiced from the back office:
        that invoice can be posted (PT-86). FR, or FT and a receipt, waits on the human's decision.
        """
        quotation = self._payable_quotation()
        self.pay_online(quotation, automatic_invoice=False)
        sales_order = quotation.sales_order_ids
        self.assertFalse(sales_order.invoice_ids)
        invoice = self.post(self.invoice(sales_order))
        self.assertEqual(invoice.state, 'posted')

    @unittest.skip("PT-86 (decision pending): the final invoice of an order prepaid online is typed FR while unpaid")
    def test_final_invoice_after_online_prepayment(self):
        """
        After a prepayment online, invoiced at once as an FR, the final invoice made from the back office
        is not an invoice-receipt while it is unpaid: an FR is paid when it is issued (PT-86; AT,
        'Guia de utilização Faturas e Recibos').
        """
        quotation = self._payable_quotation(prepayment_percent=0.3)
        self.pay_online(quotation, amount=round(quotation.amount_total * 0.3, 2))
        sales_order = quotation.sales_order_ids
        down_payment = sales_order.invoice_ids
        self.assertRecordValues(down_payment, [{'state': 'posted', 'l10n_pt_document_type': 'out_invoice_receipt'}])
        final = self.post(self.invoice(sales_order))
        self.assertTrue(final.amount_residual)
        self.assertNotEqual(final.l10n_pt_document_type, 'out_invoice_receipt')
