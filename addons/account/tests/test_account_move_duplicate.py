from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import Form, tagged

@tagged('post_install', '-at_install')
class TestAccountMoveDuplicate(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.invoice = cls.init_invoice('in_invoice', products=cls.product_a + cls.product_b)

    def test_in_invoice_single_duplicate_reference(self):
        """ Ensure duplicated ref are computed correctly in this simple case (in_invoice)"""
        bill_1 = self.invoice
        bill_1.ref = 'a unique supplier reference that will be copied'
        bill_2 = bill_1.copy(default={'invoice_date': bill_1.invoice_date})
        # ensure no Error is raised
        bill_2.ref = bill_1.ref
        self.assertRecordValues(bill_2, [{'duplicated_ref_ids': bill_1.ids}])

    def test_out_invoice_single_duplicate_reference(self):
        """
            Ensure duplicated move are computed correctly in this simple case (out_invoice).
            For it to be a duplicate, the partner, the invoice date and the amount total must be the same.
        """
        invoice_1 = self.init_invoice(
            move_type='out_invoice',
            products=self.product_a,
            invoice_date='2023-01-01'
        )
        invoice_2 = invoice_1.copy(default={'invoice_date': invoice_1.invoice_date})
        self.assertRecordValues(invoice_2, [{'duplicated_ref_ids': invoice_1.ids}])

        # Different date but same product and same partner, no duplicate
        invoice_3 = invoice_1.copy(default={'invoice_date': '2023-12-31'})
        self.assertRecordValues(invoice_3, [{'duplicated_ref_ids': []}])

        # Different product and same partner and same date, no duplicate
        invoice_4 = invoice_1 = self.init_invoice(
            move_type='out_invoice',
            products=self.product_b,
            invoice_date='2023-01-01'
        )
        self.assertRecordValues(invoice_4, [{'duplicated_ref_ids': []}])

    def test_in_invoice_single_duplicate_reference_with_form(self):
        """ Ensure duplicated ref are computed correctly with UI's NEW_ID"""
        invoice_1 = self.invoice
        invoice_1.ref = 'a unique supplier reference that will be copied'
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = invoice_1.invoice_date
        move_form.ref = invoice_1.ref
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_b
        invoice_2 = move_form.save()
        self.assertRecordValues(invoice_2, [{'duplicated_ref_ids': invoice_1.ids}])

    def test_in_invoice_multiple_duplicate_reference_batch(self):
        """ Ensure duplicated ref are computed correctly even when updated in batch"""
        invoice_1 = self.invoice
        invoice_1.ref = 'a unique supplier reference that will be copied'
        invoice_2 = invoice_1.copy(default={'invoice_date': invoice_1.invoice_date})
        invoice_3 = invoice_1.copy(default={'invoice_date': invoice_1.invoice_date})

        # reassign to trigger the compute method
        invoices = invoice_1 + invoice_2 + invoice_3
        invoices.ref = invoice_1.ref
        self.assertRecordValues(invoices, [
            {'duplicated_ref_ids': (invoice_2 + invoice_3).ids},
            {'duplicated_ref_ids': (invoice_1 + invoice_3).ids},
            {'duplicated_ref_ids': (invoice_1 + invoice_2).ids},
        ])

    def test_in_invoice_single_duplicate_reference_diff_date(self):
        """ Ensure duplicated ref are computed correctly for different dates"""
        bill1 = self.invoice.copy({'invoice_date': self.invoice.invoice_date})
        bill1.ref = 'bill1'

        # Same ref but different year -> Not duplicated
        bill2 = bill1.copy({'invoice_date': '2020-01-01'})
        bill2.ref = bill1.ref
        self.assertFalse(bill1.duplicated_ref_ids)
        self.assertFalse(bill2.duplicated_ref_ids)

        # Same ref and same year -> Duplicated
        bill3 = bill1.copy({'invoice_date': f"{bill1.invoice_date.year}-04-11"})
        bill3.ref = bill1.ref
        self.assertEqual(bill3.duplicated_ref_ids, bill1)

        # Even after posting
        bill3.action_post()
        self.assertEqual(bill3.duplicated_ref_ids, bill1)

        # Same ref and no invoice date -> Duplicated
        bill4 = self.invoice.copy()
        bill4.ref = "bill4"
        bill5 = bill4.copy()
        bill5.ref = bill4.ref
        self.assertEqual(bill5.duplicated_ref_ids, bill4)
