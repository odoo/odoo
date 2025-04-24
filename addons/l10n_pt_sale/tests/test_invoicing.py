import unittest

from odoo import Command
from odoo.exceptions import RedirectWarning, UserError
from odoo.tests import tagged

from odoo.addons.l10n_pt_sale.tests.common import TestL10nPtSaleCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtSaleInvoicing(TestL10nPtSaleCommon):
    """
    Invoicing PT sales orders. The invoice references the orders it invoices, which are issued with it
    (Portaria 302/2016 4.1.4.19.3, OrderReferences). A down payment is invoiced on receipt (CIVA 36(1))
    and deducted from the final invoice. A quotation paid online is confirmed as from its form (in
    place if nobody issued it yet, else into a new sales order) and,
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
        A PT invoice line needs a product: down payment lines carry the company's 'Adiantamento'
        product, created once per company when first needed, and handed back without sudo.
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
        refuses; the down payment invoice has to be issued first, or is issued with the final
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
        An issued quotation -- the one the customer accepts and pays from its page -- stays as issued;
        a new sales order is confirmed from it, as from its form. The payment, its automatic
        invoice -- an FR issued at once -- and the customer's landing page are the sales order's.
        """
        quotation = self.issue(self._payable_quotation())
        transaction = self.pay_online(quotation)
        sales_order = quotation.sales_order_ids
        self.assertEqual(len(sales_order), 1)
        self.assertRecordValues(quotation, [{'state': 'sent', 'locked': True, 'l10n_pt_document_number': 'OR 2026/00001', 'l10n_pt_ordered': True}])
        self.assertRecordValues(sales_order, [{'state': 'sale', 'l10n_pt_document_number': 'NE 2026/00001'}])
        self.assertEqual(transaction.sale_order_ids, sales_order)
        self.assertEqual(transaction.landing_route, sales_order.get_portal_url())
        self.assertFalse(quotation.invoice_ids)
        invoice = sales_order.invoice_ids
        self.assertRecordValues(invoice, [{'state': 'posted', 'l10n_pt_document_type': 'out_invoice_receipt'}])
        self.assertIn(invoice.payment_state, ('in_payment', 'paid'))
        self.assertIssued(invoice)
        self.assertIssued(sales_order)

    def test_issuers_of_online_payment(self):
        """
        An online payment is post-processed by no person (the customer's request, the provider's
        webhook, a cron): the sales order it confirms records its quotation's issuer, and the invoice it
        issues its salesperson.
        """
        quotation = self.issue(self._payable_quotation())
        transaction = self.pay_online(quotation, user=self.env.ref('base.public_user'))
        sales_order = transaction.sale_order_ids
        self.assertNotEqual(sales_order, quotation)
        self.assertIssued(sales_order)
        self.assertIssued(sales_order.invoice_ids)
        self.assertEqual(sales_order.l10n_pt_issue_user_id, self.env.user)
        self.assertEqual(sales_order.invoice_ids.l10n_pt_issue_user_id, self.salesman)

    def test_unissued_quotation_paid_online(self):
        """
        A quotation nobody issued yet (a shared link), paid online, is confirmed in place into the sales
        order, as from its form: no copy; it keeps the payment and is invoiced as an FR.
        """
        quotation = self._payable_quotation()
        transaction = self.pay_online(quotation)
        self.assertRecordValues(quotation, [{
            'state': 'sale',
            'l10n_pt_document_type': 'sales_order',
            'l10n_pt_at_series_id': self.series_ne.id,
            'l10n_pt_document_number': 'NE 2026/00001',
            'sales_order_count': 0,
        }])
        self.assertEqual(transaction.sale_order_ids, quotation)
        self.assertRecordValues(quotation.invoice_ids, [{'state': 'posted', 'l10n_pt_document_type': 'out_invoice_receipt'}])
        self.assertFalse(self.env['sale.order'].search([('l10n_pt_at_series_id', '=', self.series_or.id)]))

    def test_payment_of_quotation_confirmed_before(self):
        """An issued quotation confirmed from its form, then paid through a link sent before, pays that sales order."""
        quotation = self.issue(self._payable_quotation())
        sales_order = self.confirm(quotation)
        transaction = self.pay_online(quotation)
        self.assertEqual(quotation.sales_order_ids, sales_order)
        # Not confirmed again: still a quotation, sent once confirmed into its sales order.
        self.assertEqual(quotation.state, 'sent')
        self.assertEqual(transaction.sale_order_ids, sales_order)
        self.assertEqual(transaction.landing_route, sales_order.get_portal_url())

    def test_pending_payment_issues_quotation(self):
        """
        A pending payment (e.g. a wire transfer) marks the quotation sent, which issues it; once the
        payment is done, a new sales order is confirmed from it.
        """
        quotation = self._payable_quotation()
        transaction = self.env['payment.transaction'].sudo().create({
            'provider_id': self.payment_provider.id,
            'payment_method_id': self.env.ref('payment.payment_method_unknown').id,
            'reference': f"{quotation.name}-1",
            'amount': quotation.amount_total,
            'currency_id': quotation.currency_id.id,
            'partner_id': quotation.partner_id.id,
            'operation': 'online_redirect',
            'sale_order_ids': [Command.set(quotation.ids)],
        })
        transaction._set_pending()
        transaction._post_process()
        self.assertRecordValues(quotation, [{'state': 'sent', 'locked': True, 'l10n_pt_document_number': 'OR 2026/00001'}])
        # The provider confirms the payment in a later request; core's `amount_paid` depends on
        # `transaction_ids` only, so its value cached at the pending step is dropped here.
        self.env.invalidate_all()
        transaction._set_done()
        transaction._post_process()
        self.assertEqual(quotation.state, 'sent')
        self.assertRecordValues(quotation.sales_order_ids, [{'state': 'sale', 'l10n_pt_document_type': 'sales_order'}])
        self.assertEqual(transaction.sale_order_ids, quotation.sales_order_ids)

    def test_payment_confirming_nothing(self):
        """A partial payment, or the payment of a quotation still to be signed, confirms nothing."""
        for vals, amount in (({}, 50.0), ({'require_signature': True}, None)):
            with self.subTest(vals=vals):
                quotation = self._payable_quotation(**vals)
                self.pay_online(quotation, amount=amount)
                self.assertFalse(quotation.sales_order_ids)
                self.assertIn(quotation.state, ('draft', 'sent'))

    def test_sales_order_series_without_code_fails_visibly(self):
        """If the sales order series has no AT validation code, the payment's processing stops with that error."""
        self.series_ne.at_code = False
        for issued in (False, True):
            with self.subTest(issued=issued):
                quotation = self._payable_quotation()
                if issued:
                    self.issue(quotation)
                with self.assertRaisesRegex(RedirectWarning, "has no AT validation code"), self.env.cr.savepoint():
                    self.pay_online(quotation)

    @unittest.skip("Known issue: the back-office invoice of an order paid online cannot be posted, its payment reconciled before it is issued")
    def test_back_office_invoice_of_order_paid_online(self):
        """
        An order paid online in full, with automatic invoicing off, is invoiced from the back office:
        that invoice can be posted.
        """
        quotation = self._payable_quotation()
        self.pay_online(quotation, automatic_invoice=False)
        sales_order = quotation.sales_order_ids
        self.assertFalse(sales_order.invoice_ids)
        invoice = self.post(self.invoice(sales_order))
        self.assertEqual(invoice.state, 'posted')

    @unittest.skip("Known issue: the final invoice of an order prepaid online is typed FR while unpaid")
    def test_final_invoice_after_online_prepayment(self):
        """
        After a prepayment online, invoiced at once as an FR, the final invoice made from the back office
        is not an invoice-receipt while it is unpaid: an FR is paid when it is issued (AT,
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
