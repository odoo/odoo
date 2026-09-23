from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountMoveDuplicate(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.invoice = cls.init_invoice(
            "in_invoice", products=cls.product_a + cls.product_b
        )

    def test_in_invoice_single_duplicate_reference(self):
        bill_1 = self.invoice
        bill_1.ref = "a unique supplier reference that will be copied"
        bill_2 = bill_1.copy(default={"invoice_date": bill_1.invoice_date})
        bill_2.ref = bill_1.ref
        self.assertRecordValues(bill_2, [{"duplicated_ref_ids": bill_1.ids}])

    def test_out_invoice_single_duplicate_reference(self):
        invoice_1 = self.init_invoice(
            move_type="out_invoice", products=self.product_a, invoice_date="2023-01-01"
        )
        invoice_2 = invoice_1.copy(default={"invoice_date": invoice_1.invoice_date})
        self.assertRecordValues(invoice_2, [{"duplicated_ref_ids": invoice_1.ids}])

        invoice_3 = invoice_1.copy(default={"invoice_date": "2023-12-31"})
        self.assertRecordValues(invoice_3, [{"duplicated_ref_ids": []}])

        invoice_4 = invoice_1 = self.init_invoice(
            move_type="out_invoice", products=self.product_b, invoice_date="2023-01-01"
        )
        self.assertRecordValues(invoice_4, [{"duplicated_ref_ids": []}])

    def test_in_invoice_single_duplicate_reference_with_form(self):
        invoice_1 = self.invoice
        invoice_1.ref = "a unique supplier reference that will be copied"
        move_form = Form(
            self.env["account.move"].with_context(default_move_type="in_invoice")
        )
        move_form.partner_id = self.partner_a
        move_form.invoice_date = invoice_1.invoice_date
        move_form.ref = invoice_1.ref
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_b
        invoice_2 = move_form.save()
        self.assertRecordValues(invoice_2, [{"duplicated_ref_ids": invoice_1.ids}])

    def test_in_invoice_multiple_duplicate_reference_batch(self):
        invoice_1 = self.invoice
        invoice_1.ref = "a unique supplier reference that will be copied"
        invoice_2 = invoice_1.copy(default={"invoice_date": invoice_1.invoice_date})
        invoice_3 = invoice_1.copy(default={"invoice_date": invoice_1.invoice_date})

        invoices = invoice_1 + invoice_2 + invoice_3
        invoices.ref = invoice_1.ref
        self.assertRecordValues(
            invoices,
            [
                {"duplicated_ref_ids": (invoice_2 + invoice_3).ids},
                {"duplicated_ref_ids": (invoice_1 + invoice_3).ids},
                {"duplicated_ref_ids": (invoice_1 + invoice_2).ids},
            ],
        )

    def test_in_invoice_multiple_duplicate_reference_batch_in_edit_mode(self):
        invoice_1 = self.invoice
        invoice_1.ref = "a unique supplier reference that will be copied"
        invoice_2 = invoice_1.copy(default={"invoice_date": invoice_1.invoice_date})
        invoices_new = self.env["account.move"].browse(
            [
                self.env["account.move"].new(origin=inv).id
                for inv in (invoice_1, invoice_2)
            ]
        )
        invoices_new.ref = invoice_1.ref
        self.assertRecordValues(
            invoices_new,
            [
                {"duplicated_ref_ids": (invoices_new[1]).ids},
                {"duplicated_ref_ids": (invoices_new[0]).ids},
            ],
        )

    def test_in_invoice_single_duplicate_reference_diff_date(self):
        bill1 = self.invoice.copy({"invoice_date": self.invoice.invoice_date})
        bill1.ref = "bill1"

        bill2 = bill1.copy({"invoice_date": "2020-01-01"})
        bill2.ref = bill1.ref
        self.assertNotIn(bill1, bill2.duplicated_ref_ids)
        self.assertNotIn(bill2, bill1.duplicated_ref_ids)

        bill3 = bill1.copy({"invoice_date": f"{bill1.invoice_date.year}-04-11"})
        bill3.ref = bill1.ref
        self.assertEqual(bill3.duplicated_ref_ids, bill1)

        bill3.action_post()
        self.assertEqual(bill3.duplicated_ref_ids, bill1)

        bill4 = self.invoice.copy()
        bill4.ref = "bill4"
        bill5 = bill4.copy()
        bill5.ref = bill4.ref
        self.assertEqual(bill5.duplicated_ref_ids, bill4)

    def test_in_invoice_single_duplicate_no_reference(self):
        bill1 = self.invoice.copy({"invoice_date": "2020-01-01"})
        bill2 = bill1.copy()

        all_bills = bill1 + bill2
        all_bills.invoice_date = self.invoice.invoice_date

        self.assertIn(bill1, bill2.duplicated_ref_ids)
        self.assertIn(bill2, bill1.duplicated_ref_ids)

        bill1.update({"ref": "bill1 ref"})
        bill2.update({"ref": bill2.ref})
        self.assertIn(bill1, bill2.duplicated_ref_ids)
        self.assertIn(bill2, bill1.duplicated_ref_ids)

        bill1.update({"ref": bill1.ref})
        bill2.update({"ref": "bill2 ref"})
        self.assertIn(bill1, bill2.duplicated_ref_ids)
        self.assertIn(bill2, bill1.duplicated_ref_ids)

    def test_duplicate_reference_hides_unreadable_moves(self):
        invoice_1 = self.init_invoice(
            move_type="out_invoice", products=self.product_a, invoice_date="2023-01-01"
        )
        invoice_2 = invoice_1.copy(default={"invoice_date": invoice_1.invoice_date})
        (invoice_1 + invoice_2).ref = False
        self.assertRecordValues(invoice_2, [{"duplicated_ref_ids": invoice_1.ids}])

        self.env["ir.access"].create(
            {
                "name": "hide invoice_1",
                "model_id": self.env["ir.model"]._get_id("account.move"),
                "group_id": self.env.ref("base.group_everyone").id,
                "kind": "guard",
                "operation": "r",
                "domain": f"[('id', '!=', {invoice_1.id})]",
            }
        )

        billing_user = self.env["res.users"].create(
            {
                "name": "Billing only",
                "login": "billing_only_dup",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, self.env.company.ids)],
                "group_ids": [
                    (6, 0, self.env.ref("account.group_account_invoice").ids)
                ],
            }
        )

        restricted = invoice_2.with_user(billing_user)
        restricted.invalidate_recordset(["duplicated_ref_ids"])
        self.assertFalse(
            restricted.duplicated_ref_ids,
            "an unreadable duplicate must be filtered out",
        )
        self.assertTrue(restricted.display_name)
