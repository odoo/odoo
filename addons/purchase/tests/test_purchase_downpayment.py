#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
import uuid

from odoo import Command
from odoo.addons.purchase.tests.test_purchase_invoice import TestPurchaseToInvoiceCommon
from odoo.tests import tagged, Form


@tagged('-at_install', 'post_install')
class TestPurchaseDownpayment(TestPurchaseToInvoiceCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()
        cls.other_currency = cls.setup_other_currency('EUR')
        cls.env.user.groups_id += cls.env.ref('purchase.group_down_payment')

        PurchaseOrder = cls.env['purchase.order'].with_context(tracking_disable=True)

        cls.tax_account = cls.env['account.account'].search([('account_type', '=', 'asset_current')], limit=1)
        cls.tax_10 = cls.create_tax(10)
        cls.tax_15 = cls.create_tax(15)

        # create a generic Purchase Order with all classical products and empty pricelist
        cls.purchase_order = PurchaseOrder.create({
            'partner_id': cls.partner_a.id,
        })
        cls.pol_product_order = cls.env['purchase.order.line'].create({
            'name': cls.product_order.name,
            'product_id': cls.product_order.id,
            'product_qty': 2,
            'product_uom': cls.product_order.uom_id.id,
            'price_unit': 100,
            'order_id': cls.purchase_order.id,
            'tax_ids': False,
        })
        cls.pol_serv_deliver = cls.env['purchase.order.line'].create({
            'name': cls.service_deliver.name,
            'product_id': cls.service_deliver.id,
            'product_qty': 2,
            'product_uom': cls.service_deliver.uom_id.id,
            'price_unit': 100,
            'order_id': cls.purchase_order.id,
            'tax_ids': False,
        })
        cls.pol_serv_order = cls.env['purchase.order.line'].create({
            'name': cls.service_order.name,
            'product_id': cls.service_order.id,
            'product_qty': 2,
            'product_uom': cls.service_order.uom_id.id,
            'price_unit': 100,
            'order_id': cls.purchase_order.id,
            'tax_ids': False,
        })
        cls.pol_product_deliver = cls.env['purchase.order.line'].create({
            'name': cls.product_deliver.name,
            'product_id': cls.product_deliver.id,
            'product_qty': 2,
            'product_uom': cls.product_deliver.uom_id.id,
            'price_unit': 100,
            'order_id': cls.purchase_order.id,
            'tax_ids': False,
        })

        cls.expense_account = cls.company_data['default_account_expense']
        cls.payable_account = cls.company_data['default_account_payable']

    @classmethod
    def create_tax(cls, amount, values=None):
        vals = {
            'name': f'Tax {amount} {uuid.uuid4()}',
            'amount_type': 'percent',
            'amount': amount,
            'type_tax_use': 'purchase',
            'repartition_line_ids': [
                Command.create({'document_type': 'invoice', 'repartition_type': 'base'}),
                Command.create({'document_type': 'invoice', 'repartition_type': 'tax', 'account_id': cls.tax_account.id}),
                Command.create({'document_type': 'refund', 'repartition_type': 'base'}),
                Command.create({'document_type': 'refund', 'repartition_type': 'tax', 'account_id': cls.tax_account.id}),
            ]
        }
        if values:
            vals.update(values)
        return cls.env['account.tax'].create(vals)

    @classmethod
    def make_downpayment(cls, purchase_order, method='percentage', amount=50.0):
        cls.env['purchase.advance.payment.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': [purchase_order.id],
            'active_id': purchase_order.id,
            'default_journal_id': cls.company_data['default_journal_purchase'].id,
        }).create({
            'advance_payment_method': method,
            'amount' if method == 'percentage' else 'fixed_amount': amount,
        }).create_invoices()
        purchase_order.button_confirm()

    def _assert_invoice_lines_values(self, lines, expected):
        return self.assertRecordValues(lines, [dict(zip(expected[0], x)) for x in expected[1:]])

    def test_downpayment_fixed_tax_incl(self):
        """
            Check if DP PO line is created and the total amount of the final invoice is equal to the POs total amount.
        """
        self.purchase_order.button_confirm()
        self.assertEqual(len(self.purchase_order.account_move_ids), 0, "No invoices should have been made yet")
        self.make_downpayment(self.purchase_order, method='fixed')
        self.make_downpayment(self.purchase_order, method='fixed')
        self.assertEqual(len(self.purchase_order.account_move_ids), 2, 'Invoice should be created for the PO')
        downpayment_line = self.purchase_order.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)
        self.assertEqual(len(downpayment_line), 2, '2 PO lines for downpayments should be created in PO')

        # Update received quantity of PO lines
        self.pol_serv_deliver.qty_received = 2
        self.pol_product_deliver.qty_received = 2

        # Final invoice
        self.make_downpayment(self.purchase_order, method='delivered')

        self.assertEqual(len(self.purchase_order.account_move_ids), 3, 'Invoice should be created for the PO')
        invoice = max(self.purchase_order.account_move_ids)
        self.assertEqual(len(invoice.invoice_line_ids.filtered(lambda l: not (l.display_type == 'line_section' and l.name == "Down Payments"))),
                         len(self.purchase_order.order_line.filtered(lambda l: not (l.display_type == 'line_section' and l.name == "Down Payments"))), 'All lines should be invoiced')
        self.assertEqual(len(invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'line_section' and l.name == "Down Payments")), 1, 'A single section for downpayments should be present')
        self.assertEqual(invoice.amount_total, self.purchase_order.amount_total - sum(downpayment_line.mapped('price_unit')), 'Downpayment should be applied')

    def test_downpayment_validation(self):
        """
            Check if invoice from DP can be validated.
        """
        self.env.company.po_lock = 'lock'
        self.purchase_order.button_confirm()
        self.assertEqual(len(self.purchase_order.account_move_ids), 0, "No invoices should have been made yet")
        self.make_downpayment(self.purchase_order, amount=10)
        self.assertEqual(len(self.purchase_order.account_move_ids), 1, 'Invoice should be created for the PO')

        # Update delivered quantity of PO lines
        self.pol_serv_deliver.qty_received = 2
        self.pol_product_deliver.qty_received = 2

        self.purchase_order.account_move_ids.invoice_date = datetime.datetime.today()
        self.purchase_order.account_move_ids.action_post()

    def test_downpayment_line_remains_on_PO(self):
        """
           Check DP PO line is created and remains unchanged even if everything is invoiced
        """
        # Single line PO
        self.pol_serv_deliver.unlink()
        self.pol_serv_order.unlink()
        self.pol_product_deliver.unlink()
        self.pol_product_order.product_qty = 5

        self.purchase_order.button_confirm()

        # Update delivered quantity of PO line
        self.pol_product_order.qty_received = 5

        self.make_downpayment(self.purchase_order, method='fixed')
        self.make_downpayment(self.purchase_order, method='delivered')

        downpayment_line = self.purchase_order.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)
        self.assertEqual(downpayment_line[0].price_unit, 50, 'The down payment unit price should not change on PO')
        self.purchase_order.account_move_ids.invoice_date = datetime.datetime.today()
        self.purchase_order.account_move_ids.action_post()
        self.assertEqual(downpayment_line[0].price_unit, 50, 'The down payment unit price should not change on PO')

    def test_downpayment_fixed_amount_with_zero_total_amount(self):
        """
            Check that DP should be zero if the total PO amount is zero.
        """
        # PO with one line and amount total is zero
        self.pol_serv_deliver.unlink()
        self.pol_serv_order.unlink()
        self.pol_product_deliver.unlink()
        self.pol_product_order.product_qty = 5
        self.pol_product_order.price_unit = 0

        self.purchase_order.button_confirm()
        self.purchase_order.order_line.qty_received = 5
        self.make_downpayment(self.purchase_order, method='fixed')
        self.assertEqual(self.purchase_order.order_line[2].price_unit, 0.0, 'The down payment amount should be 0.0')

    def test_downpayment_percentage_tax_incl(self):
        """
            Test invoice with a percentage downpayment and an included tax.
            Check that the total amount of the invoice is correct and equal to the PO total amount.
        """
        self.purchase_order.button_confirm()
        self.make_downpayment(self.purchase_order)

        self.assertEqual(len(self.purchase_order.account_move_ids), 1, 'Invoice should be created for the PO')
        downpayment_line = self.purchase_order.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)
        self.assertEqual(len(downpayment_line), 1, 'PO line downpayment should be created on PO')
        self.assertEqual(downpayment_line.price_unit, self.purchase_order.amount_total / 2, 'Downpayment line on the PO should have the correct amount')

        invoice = self.purchase_order.account_move_ids[0]
        downpayment_aml = invoice.line_ids.filtered(lambda l: not (l.display_type == 'line_section' and l.name == "Down Payments"))[0]
        self.assertEqual(downpayment_aml.price_total, self.purchase_order.amount_total / 2, 'Downpayment should have the correct tax included amount on the downpayment invoice')
        self.assertEqual(downpayment_aml.price_unit, self.purchase_order.amount_total / 2, 'Downpayment should have the correct unit price on the downpayment invoice')
        self.purchase_order.account_move_ids.invoice_date = datetime.datetime.today()
        self.purchase_order.account_move_ids.action_post()
        self.assertEqual(downpayment_line.price_unit, self.purchase_order.amount_total / 2, 'Downpayment line on the PO should have the correct amount after posting the downpayment invoice')

    def test_downpayment_invoice_and_partial_credit_note(self):
        """
            Test for correct behavior in the following flow:
            1. Create and post a down payment on a PO.
            2. Create and post a (partial) credit note for this down payment invoice
            The down payment line on the PO should have its amount reduced by the amount that was credited.
        """
        self.purchase_order.button_confirm()

        self.make_downpayment(self.purchase_order, method='fixed', amount=100)

        # Ensure the downpayment line on the purchase order is correctly set to 100
        downpayment_line = self.purchase_order.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)
        self.assertEqual(downpayment_line.price_unit, 100)

        # post the downpayment invoice and ensure the downpayment_line amount is still 100
        self.purchase_order.account_move_ids.invoice_date = datetime.datetime.today()
        self.purchase_order.account_move_ids.action_post()
        self.assertEqual(downpayment_line.price_unit, 100)

        # Create a credit note for a part of the downpayment invoice and post it
        po_invoice = max(self.purchase_order.account_move_ids)
        credit_note_wizard = self.env['account.move.reversal'].with_context(
            {'active_ids': [po_invoice.id], 'active_id': po_invoice.id, 'active_model': 'account.move'}).create({
            'reason': 'no reason',
            'journal_id': po_invoice.journal_id.id,
            'date': '2020-02-01',
        })
        reversal_action = credit_note_wizard.refund_moves()
        reverse_move = self.env['account.move'].browse(reversal_action['res_id'])
        with Form(reverse_move) as form_reverse:
            with form_reverse.invoice_line_ids.edit(0) as line_form:
                line_form.price_unit = 20.0
        reverse_move.action_post()
        self.assertEqual(downpayment_line.price_unit, 80,
                         "The downpayment line amount should be equal to the sum of the invoice and credit note amount")

    def test_multi_company_invoice(self):
        """
            Checks that the company of the invoices generated in a multi-company environment using the
           'purchase.advance.payment.wizard' wizard matches the company of the PO and not with the current company.
        """
        po_company_id = self.purchase_order.company_id.id
        yet_another_company_id = self.company_data_2['company'].id
        po_for_downpayment = self.purchase_order.copy()

        context = {
            'active_model': 'purchase.order',
            'active_ids': [self.purchase_order.id],
            'active_id': self.purchase_order.id,
            'default_journal_id': self.company_data['default_journal_purchase'].id,
            'allowed_company_ids': [yet_another_company_id, self.env.company.id],
            'company_id': yet_another_company_id,
        }
        context_for_downpayment = context.copy()
        context_for_downpayment.update(active_ids=[po_for_downpayment.id], active_id=po_for_downpayment.id)

        # Make sure the invoice is not created with a journal in the context
        # Because it makes the test always succeed (by using the journal company instead of the env company)
        no_journal_ctxt = dict(context)
        no_journal_ctxt.pop('default_journal_id', None)
        no_journal_ctxt.pop('journal_id', None)

        self.purchase_order.with_context(context).button_confirm()
        payment = self.env['purchase.advance.payment.wizard'].with_context(no_journal_ctxt).create({
            'advance_payment_method': 'percentage',
            'amount': 50,
        })
        payment.create_invoices()
        self.assertEqual(self.purchase_order.account_move_ids[0].company_id.id, po_company_id, "The company of the invoice should be the same as the one from the PO")

        po_for_downpayment.with_context(context_for_downpayment).button_confirm()
        downpayment = self.env['purchase.advance.payment.wizard'].with_context(context_for_downpayment).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 50,
        })
        downpayment.create_invoices()
        self.assertEqual(po_for_downpayment.account_move_ids[0].company_id.id, po_company_id, "The company of the downpayment invoice should be the same as the one from the PO")

    def test_refund_invoice_with_downpayment(self):
        """
            Check that refunding invoices for POs with downpayments works as expected for the following flow:
            1. We create and post a down payment on a PO.
            2. We create and post a final invoice for the remaining amount to be paid on the PO.
            3. We create and post a credit note for the final invoice.
        """
        self.pol_serv_deliver.unlink()
        self.pol_serv_order.unlink()
        self.pol_product_deliver.unlink()
        self.pol_product_order.product_qty = 5
        self.pol_product_order.price_unit = 235

        self.assertRecordValues(self.pol_product_order, [{
            'price_unit': 235.0,
            'discount': 0.0,
            'product_qty': 5.0,
            'qty_to_invoice': 0.0,
        }])
        self.assertEqual(self.purchase_order.invoice_status, 'no')
        self.purchase_order.button_confirm()

        self.assertEqual(self.pol_product_order.qty_to_invoice, 5.0)
        self.assertEqual(self.purchase_order.invoice_status, 'to invoice')

        self.make_downpayment(self.purchase_order)
        # order_line[1] is the down payment section
        pol_downpayment = self.purchase_order.order_line[2]
        dp_invoice = self.purchase_order.account_move_ids[0]
        dp_invoice.invoice_date = datetime.datetime.today()
        self.purchase_order.account_move_ids.invoice_date = datetime.datetime.today()
        self.purchase_order.account_move_ids.action_post()

        self.assertRecordValues(pol_downpayment, [{
            'price_unit': 587.5,
            'discount': 0.0,
            'product_qty': 0.0,
            'qty_invoiced': 1.0,
            'qty_to_invoice': -1.0,
        }])
        self.assertEqual(self.purchase_order.invoice_status, 'to invoice')

        self.make_downpayment(self.purchase_order, method='delivered')

        po_invoice = max(self.purchase_order.account_move_ids)
        self.assertEqual(len(po_invoice.invoice_line_ids.filtered(lambda l: not (l.display_type == 'line_section' and l.name == "Down Payments"))),
                         len(self.purchase_order.order_line.filtered(lambda l: not (l.display_type == 'line_section' and l.name == "Down Payments"))), 'All lines should be invoiced')
        self.assertEqual(len(po_invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'line_section' and l.name == "Down Payments")), 1, 'A single section for downpayments should be present')
        self.assertEqual(po_invoice.amount_total, self.purchase_order.amount_total - pol_downpayment.price_unit, 'Downpayment should be applied')
        po_invoice.invoice_date = datetime.datetime.today()
        po_invoice.action_post()

        credit_note_wizard = self.env['account.move.reversal'].with_context({'active_ids': [po_invoice.id], 'active_id': po_invoice.id, 'active_model': 'account.move'}).create({
            'reason': 'reason test refund with downpayment',
            'journal_id': po_invoice.journal_id.id,
        })
        credit_note_wizard.refund_moves()
        invoice_refund = self.purchase_order.account_move_ids.sorted(key=lambda inv: inv.id, reverse=False)[-1]
        invoice_refund.invoice_date = datetime.datetime.today()
        invoice_refund.action_post()

        self.assertEqual(self.pol_product_order.qty_to_invoice, 5.0, "The refund should make it so the quantity to invoice is the ordered quantity")
        self.assertEqual(self.pol_product_order.qty_invoiced, 0.0, "The qty invoiced should be zero since the refund cancels the previously invoiced amount")
        self.assertEqual(len(self.pol_product_order.account_move_line_ids), 2, "The product line is invoiced, so it should be linked to 2 invoice lines (invoice and refund)")
        self.assertEqual(pol_downpayment.qty_invoiced, 1.0, "The qty invoiced should remain 1 since the refund was only for the ordered product, not the downpayment")
        self.assertEqual(pol_downpayment.qty_to_invoice, -1.0, "Downpayment was invoiced separately and should still count as invoiced after refund of the product line. Since the ordered qty is 0 for down payments, this means -1 is remaining to invoice.")
        self.assertEqual(len(pol_downpayment.account_move_line_ids), 3, "The down payment line is invoiced, so it should be linked to 3 invoice lines (downpayment invoice, partial invoice and refund)")

    def test_tax_and_account_breakdown(self):
        """
            Test to check if down payments are properly broken down per tax.
        """
        expense_acc_2 = self.expense_account.copy()
        self.purchase_order.order_line[1].product_id.product_tmpl_id.property_account_expense_id = expense_acc_2

        self.purchase_order.order_line[0].tax_ids = self.tax_15 + self.tax_10
        self.purchase_order.order_line[1].tax_ids = self.tax_10
        self.purchase_order.order_line[2].tax_ids = self.tax_10
        self.make_downpayment(self.purchase_order)
        invoice = self.purchase_order.account_move_ids
        down_pay_amt = -self.purchase_order.amount_total / 2
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                      'balance',     'price_total'],
            # base lines
            [self.expense_account.id,    (self.tax_15 + self.tax_10).ids, 100,          125],
            [expense_acc_2.id,           self.tax_10.ids,                 100,          110],
            [self.expense_account.id,    self.tax_10.ids,                 100,          110],
            [self.expense_account.id,    self.env['account.tax'],         100,          100],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],         30,           0],
            [self.tax_account.id,        self.env['account.tax'],         15,           0],
            # receivable
            [self.payable_account.id,    self.env['account.tax'],         down_pay_amt, 0],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_breakdown_other_currency(self):
        self.purchase_order.currency_id = self.other_currency  # rate = 2.0
        self.purchase_order.order_line[0].tax_ids = self.tax_15 + self.tax_10
        self.purchase_order.order_line[1].tax_ids = self.tax_10
        self.purchase_order.order_line[2].tax_ids = self.tax_10
        self.make_downpayment(self.purchase_order)
        invoice = self.purchase_order.account_move_ids
        down_pay_amt = -self.purchase_order.amount_total / 2
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                      'balance',           'price_total'],
            # base lines
            [self.expense_account.id,    (self.tax_15 + self.tax_10).ids, 50,                 125],
            [self.expense_account.id,    self.tax_10.ids,                 100,                220],
            [self.expense_account.id,    self.env['account.tax'],         50,                 100],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],         15,                 0],
            [self.tax_account.id,        self.env['account.tax'],         7.5,                0],
            # receivable
            [self.payable_account.id,    self.env['account.tax'],         down_pay_amt / 2.0, 0],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_breakdown_fixed_payment_method(self):
        self.purchase_order.order_line[0].tax_ids = self.tax_15 + self.tax_10
        self.purchase_order.order_line[1].tax_ids = self.tax_10
        self.purchase_order.order_line[2].tax_ids = self.tax_10
        self.make_downpayment(self.purchase_order, method='fixed', amount=222.5)
        invoice = self.purchase_order.account_move_ids
        down_pay_amt = -222.5
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                      'balance',     'price_total'],
            # base lines
            [self.expense_account.id,    (self.tax_15 + self.tax_10).ids, 50,           62.5],
            [self.expense_account.id,    self.tax_10.ids,                 100,          110],
            [self.expense_account.id,    self.env['account.tax'],         50,           50],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],         15,           0],
            [self.tax_account.id,        self.env['account.tax'],         7.5,          0],
            # receivable
            [self.payable_account.id,    self.env['account.tax'],         down_pay_amt, 0],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_breakdown_fixed_payment_method_with_taxes_on_all_lines(self):
        self.purchase_order.order_line[0].tax_ids = self.tax_15
        self.purchase_order.order_line[1].tax_ids = self.tax_10
        self.purchase_order.order_line[2].tax_ids = self.tax_10
        self.purchase_order.order_line[3].tax_ids = self.tax_10
        self.make_downpayment(self.purchase_order, method='fixed', amount=222.5)
        invoice = self.purchase_order.account_move_ids
        down_pay_amt = -222.5
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',              'balance',     'price_total'],
            # base lines
            [self.expense_account.id,    self.tax_15.ids,         50,           57.5],
            [self.expense_account.id,    self.tax_10.ids,         150,          165],
            # taxes
            [self.tax_account.id,        self.env['account.tax'], 7.5,          0],
            [self.tax_account.id,        self.env['account.tax'], 15,           0],
            # receivable
            [self.payable_account.id,    self.env['account.tax'], down_pay_amt, 0],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_price_include_breakdown(self):
        tax_10_incl = self.create_tax(10, {'price_include': True})
        self.purchase_order.order_line[0].tax_ids = tax_10_incl + self.tax_10
        self.purchase_order.order_line[1].tax_ids = self.tax_10
        self.purchase_order.order_line[2].tax_ids = self.tax_10
        self.make_downpayment(self.purchase_order)
        invoice = self.purchase_order.account_move_ids
        down_pay_amt = -self.purchase_order.amount_total / 2
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                       'balance',    'price_total'],
            # base lines
            [self.expense_account.id,    (tax_10_incl + self.tax_10).ids,  90.91,       109.09],
            [self.expense_account.id,    self.tax_10.ids,                  200,         220],
            [self.expense_account.id,    self.env['account.tax'],          100,         100],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],          29.09,       0],
            [self.tax_account.id,        self.env['account.tax'],          9.09,        0],
            # receivable
            [self.payable_account.id,    self.env['account.tax'],          down_pay_amt, 0],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_price_include_include_base_amount_breakdown(self):
        tax_10_pi_ba = self.create_tax(10, {'price_include': True, 'include_base_amount': True})
        self.tax_10.sequence = 2
        self.purchase_order.order_line[0].tax_ids = tax_10_pi_ba + self.tax_10
        self.purchase_order.order_line[1].tax_ids = self.tax_10
        self.purchase_order.order_line[2].tax_ids = self.tax_10
        self.make_downpayment(self.purchase_order)
        invoice = self.purchase_order.account_move_ids
        down_pay_amt = -self.purchase_order.amount_total / 2
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                       'balance',     'price_total'],
            # base lines
            [self.expense_account.id,    (tax_10_pi_ba + self.tax_10).ids, 90.91,        110],
            [self.expense_account.id,    self.tax_10.ids,                  200,          220],
            [self.expense_account.id,    self.env['account.tax'],          100,          100],
            # taxes
            [self.tax_account.id,        self.tax_10.ids,                  9.09,         0],
            [self.tax_account.id,        self.env['account.tax'],          30,           0],
            # receivable
            [self.payable_account.id,    self.env['account.tax'],          down_pay_amt, 0],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_breakdown_with_discount(self):
        self.purchase_order.order_line[0].tax_ids = self.tax_10
        self.purchase_order.order_line[1].tax_ids = self.tax_10
        self.purchase_order.order_line[1].discount = 25.0
        self.purchase_order.order_line[2].tax_ids = self.tax_15
        self.make_downpayment(self.purchase_order)
        invoice = self.purchase_order.account_move_ids
        down_pay_amt = -self.purchase_order.amount_total / 2
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',               'balance',    'price_total'],
            # base lines
            [self.expense_account.id,    self.tax_10.ids,         175,          192.5],
            [self.expense_account.id,    self.tax_15.ids,         100,          115],
            [self.expense_account.id,    self.env['account.tax'], 100,          100],
            # taxes
            [self.tax_account.id,        self.env['account.tax'], 17.5,         0],
            [self.tax_account.id,        self.env['account.tax'], 15,           0],
            # receivable
            [self.payable_account.id,    self.env['account.tax'], down_pay_amt, 0],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_price_include_include_base_amount_breakdown_with_discount(self):
        tax_10_pi_ba = self.create_tax(10, {'price_include': True, 'include_base_amount': True})
        self.tax_10.sequence = 2
        self.purchase_order.order_line[0].tax_ids = tax_10_pi_ba + self.tax_10
        self.purchase_order.order_line[0].discount = 25.0
        self.purchase_order.order_line[1].tax_ids = self.tax_10
        self.purchase_order.order_line[2].tax_ids = self.tax_10
        self.make_downpayment(self.purchase_order)
        invoice = self.purchase_order.account_move_ids
        down_pay_amt = -self.purchase_order.amount_total / 2
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                       'balance',     'price_total'],
            # base lines
            [self.expense_account.id,    (tax_10_pi_ba + self.tax_10).ids, 68.18,        82.5],
            [self.expense_account.id,    self.tax_10.ids,                  200,          220],
            [self.expense_account.id,    self.env['account.tax'],          100,          100],
            # taxes
            [self.tax_account.id,        self.tax_10.ids,                  6.82,         0],
            [self.tax_account.id,        self.env['account.tax'],          27.5,         0],
            # receivable
            [self.payable_account.id,    self.env['account.tax'],          down_pay_amt, 0],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_fixed_amount_breakdown(self):
        tax_10_fix_a = self.create_tax(10, {'amount_type': 'fixed', 'include_base_amount': True})
        tax_10_fix_b = self.create_tax(10, {'amount_type': 'fixed', 'include_base_amount': True})
        tax_10_fix_c = self.create_tax(10, {'amount_type': 'fixed'})
        tax_10_a = self.tax_10
        tax_10_b = self.create_tax(10)
        tax_group_1 = self.env['account.tax'].create({
            'name': "Tax Group",
            'amount_type': 'group',
            'children_tax_ids': [Command.set((tax_10_fix_a + tax_10_a + tax_10_fix_b + tax_10_b).ids)],
            'type_tax_use': 'purchase',
        })
        tax_group_2 = self.env['account.tax'].create({
            'name': "Tax Group 2",
            'amount_type': 'group',
            'children_tax_ids': [Command.set((tax_10_fix_c + tax_10_a).ids)],
            'type_tax_use': 'purchase',
        })
        self.purchase_order.order_line[0].tax_ids = tax_group_1
        self.purchase_order.order_line[1].tax_ids = tax_group_2
        self.purchase_order.order_line[2].tax_ids = tax_10_a
        self.make_downpayment(self.purchase_order)

        # Line 1: 200 + 80 = 284
        # Line 2: 200 + 40 = 240
        # Line 3: 200 + 20 = 220
        # Line 4: 200
        # Total: 944

        invoice = self.purchase_order.account_move_ids
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                 'balance',    'price_total'],
            # base lines
            [self.expense_account.id,    (tax_10_a + tax_10_b).ids, 110,          132],
            [self.expense_account.id,    tax_10_b.ids,              10,           11],
            [self.expense_account.id,    tax_10_a.ids,              200,          220],
            [self.expense_account.id,    self.env['account.tax'],   110,          110],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],   31,           0],
            [self.tax_account.id,        self.env['account.tax'],   12,           0],
            # receivable
            [self.payable_account.id,    self.env['account.tax'], -473,         0],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_analytic_distribution(self):
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test'})
        an_acc_01 = str(self.env['account.analytic.account'].create({'name': 'Account 01', 'plan_id': analytic_plan.id}).id)
        an_acc_02 = str(self.env['account.analytic.account'].create({'name': 'Account 02', 'plan_id': analytic_plan.id}).id)
        self.purchase_order.order_line[0].tax_ids = self.tax_15 + self.tax_10
        self.purchase_order.order_line[0].analytic_distribution = {an_acc_01: 100}
        self.purchase_order.order_line[1].tax_ids = self.tax_10
        self.purchase_order.order_line[1].analytic_distribution = {an_acc_01: 50, an_acc_02: 50}
        self.purchase_order.order_line[2].tax_ids = self.tax_10
        self.purchase_order.order_line[2].analytic_distribution = {an_acc_01: 100}
        self.make_downpayment(self.purchase_order)
        invoice = self.purchase_order.account_move_ids
        down_pay_amt = -self.purchase_order.amount_total / 2
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                      'balance',     'price_total', 'analytic_distribution'],
            # base lines
            [self.expense_account.id,    (self.tax_15 + self.tax_10).ids, 100,          125,           {an_acc_01: 100}],
            [self.expense_account.id,    self.tax_10.ids,                 100,          110,           {an_acc_01: 50, an_acc_02: 50}],
            [self.expense_account.id,    self.tax_10.ids,                 100,          110,           {an_acc_01: 100}],
            [self.expense_account.id,    self.env['account.tax'],         100,          100, False],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],         30,           0, False],
            [self.tax_account.id,        self.env['account.tax'],         15,           0, False],
            # receivable
            [self.payable_account.id,    self.env['account.tax'],         down_pay_amt, 0, False],
        ]

        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_tax_fixed_amount_analytic_distribution(self):
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test'})
        an_acc_01 = str(self.env['account.analytic.account'].create({'name': 'Account 01', 'plan_id': analytic_plan.id}).id)
        an_acc_02 = str(self.env['account.analytic.account'].create({'name': 'Account 02', 'plan_id': analytic_plan.id}).id)
        tax_10_fix_a = self.create_tax(10, {'amount_type': 'fixed', 'include_base_amount': True})
        tax_10_fix_b = self.create_tax(10, {'amount_type': 'fixed', 'include_base_amount': True})
        tax_10_fix_c = self.create_tax(10, {'amount_type': 'fixed'})
        tax_10_a = self.tax_10
        tax_10_b = self.create_tax(10)
        tax_group_1 = self.env['account.tax'].create({
            'name': "Tax Group",
            'amount_type': 'group',
            'children_tax_ids': [Command.set((tax_10_fix_a + tax_10_a + tax_10_fix_b + tax_10_b).ids)],
            'type_tax_use': 'purchase',
        })
        tax_group_2 = self.env['account.tax'].create({
            'name': "Tax Group 2",
            'amount_type': 'group',
            'children_tax_ids': [Command.set((tax_10_fix_c + tax_10_a).ids)],
            'type_tax_use': 'purchase',
        })
        self.purchase_order.order_line[0].tax_ids = tax_group_1
        self.purchase_order.order_line[0].analytic_distribution = {an_acc_01: 50, an_acc_02: 50}
        self.purchase_order.order_line[1].tax_ids = tax_group_2
        self.purchase_order.order_line[2].tax_ids = tax_10_a
        self.make_downpayment(self.purchase_order)

        # Line 1: 200 + 80 = 284
        # Line 2: 200 + 40 = 240
        # Line 3: 200 + 20 = 220
        # Line 4: 200
        # Total: 944

        invoice = self.purchase_order.account_move_ids
        # pylint: disable=C0326
        expected = [
            # keys
            ['account_id',               'tax_ids',                 'balance',    'price_total', 'analytic_distribution'],
            # base lines
            [self.expense_account.id,    (tax_10_a + tax_10_b).ids, 110,          132,            {an_acc_01: 50, an_acc_02: 50}],
            [self.expense_account.id,    tax_10_b.ids,              10,           11,             {an_acc_01: 50, an_acc_02: 50}],
            [self.expense_account.id,    tax_10_a.ids,              200,          220, False],
            [self.expense_account.id,    self.env['account.tax'],   110,          110, False],
            # taxes
            [self.tax_account.id,        self.env['account.tax'],   31,           0, False],
            [self.tax_account.id,        self.env['account.tax'],   12,           0, False],
            # receivable
            [self.payable_account.id,    self.env['account.tax'], -473,          0, False],
        ]
        self._assert_invoice_lines_values(invoice.line_ids, expected)

    def test_downpayment_line_name(self):
        """ Test downpayment's PO line name is updated when invoice is posted. """
        self.make_downpayment(self.purchase_order, method='fixed')
        dp_line = self.purchase_order.order_line.filtered(
            lambda pol: pol.is_downpayment and not pol.display_type
        )
        dp_line.name = 'whatever'
        self.purchase_order.account_move_ids.invoice_date = datetime.datetime.today()
        self.purchase_order.account_move_ids.action_post()

        self.assertNotEqual(
            dp_line.name, 'whatever',
            "DP line's description should be recomputed when the linked invoice is posted",
        )
