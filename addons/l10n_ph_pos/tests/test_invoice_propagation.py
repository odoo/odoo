# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.l10n_ph_pos.tests.common import TestPosDiscountPrivilegeCommon

SC_SECTION = "ID HOLDER Juan Dela Cruz - ID Type: Senior Citizen ID - ID#: SC-1"
PWD_SECTION = "ID HOLDER Abigail Dela Cruz - ID Type: Person with Disability ID - ID#: PWD-1"


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPosInvoicePropagation(TestPosDiscountPrivilegeCommon):
    """
    Coverage of pos.order._prepare_account_move_line_data_from_base_line:
    privileged POS lines must carry their privilege onto the invoice line
    (mirrors SaleOrderLine._prepare_invoice_line), grouped into one
    line_section per ID holder plus one for the regular share.
    """

    def _create_invoice(self, order):
        """The customer invoice of ``order``, as created when it is invoiced."""
        return self.env["account.move"].sudo().create(order._prepare_invoice_vals())

    def _invoice_line_vals(self, display_type, name, privilege=None, holder=False, qty=0.0):
        return {
            "display_type": display_type,
            "name": name,
            "quantity": qty,
            "l10n_ph_discount_privilege_id": privilege.id if privilege else False,
            "l10n_ph_holder_name": holder,
        }

    def _product_vals(self, qty, privilege=None, holder=False):
        return self._invoice_line_vals("product", False, privilege, holder, qty)

    def test_no_holders_falls_through_unchanged(self):
        invoice = self._create_invoice(self._create_order([(self.pizza, 1.0)]))
        self.assertRecordValues(invoice.invoice_line_ids, [self._product_vals(1.0)])

    def test_sections_grouped_by_holder_with_regular_first(self):
        """The invoice keeps each ID holder's share apart, after the regular
        one, under its own section, and totals what the order does."""
        order = self._create_order([(self.pizza, 5.0)])
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[
                self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1"),
                self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz", "PWD-1"),
            ],
            num_persons_sharing=5,
        )

        invoice = self._create_invoice(order)

        self.assertRecordValues(invoice.invoice_line_ids, [
            self._invoice_line_vals("line_section", "Regular Orders"),
            self._product_vals(3.0),
            self._invoice_line_vals("line_section", SC_SECTION),
            self._product_vals(1.0, self.privilege_sc, "Juan Dela Cruz"),
            self._invoice_line_vals("line_section", PWD_SECTION),
            self._product_vals(1.0, self.privilege_pwd, "Abigail Dela Cruz"),
        ])
        self.assertRecordValues(invoice, [{"amount_total": order.amount_total}])
        privileged_lines = invoice.invoice_line_ids.filtered("l10n_ph_discount_privilege_id")
        self.assertRecordValues(privileged_lines, [
            {"l10n_ph_holder_id_number": "SC-1", "discount": 20.0, "l10n_ph_special_discount_amount": 200.0},
            {"l10n_ph_holder_id_number": "PWD-1", "discount": 20.0, "l10n_ph_special_discount_amount": 200.0},
        ])

    def test_general_customer_note_belongs_to_no_section(self):
        """The order's general customer note heads the invoice, ahead of all
        sections, instead of ending up in the last ID holder's section. Line
        notes stay with their line."""
        order = self._create_order([(self.pizza, 2.0)])
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")],
            num_persons_sharing=2,
        )
        order.general_customer_note = "Table 5 birthday"
        order.lines.filtered("l10n_ph_discount_privilege_id").customer_note = "No onions"

        invoice = self._create_invoice(order)

        self.assertRecordValues(invoice.invoice_line_ids, [
            self._invoice_line_vals("line_note", "Table 5 birthday"),
            self._invoice_line_vals("line_section", "Regular Orders"),
            self._product_vals(1.0),
            self._invoice_line_vals("line_section", SC_SECTION),
            self._product_vals(1.0, self.privilege_sc, "Juan Dela Cruz"),
            self._invoice_line_vals("line_note", "No onions"),
        ])

    def test_same_holder_applied_twice_has_one_section(self):
        """An ID holder whose privilege is applied again later on (here on
        an item ordered after the first split) keeps a single section."""
        order = self._create_order([(self.pizza, 1.0)])
        holder_vals = self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")
        order._l10n_ph_apply_discount_privileges(holders_vals=[holder_vals], num_persons_sharing=1)
        self._add_order_line(order, self.pizza, 1.0)
        order._l10n_ph_apply_discount_privileges(holders_vals=[holder_vals], num_persons_sharing=1)

        invoice = self._create_invoice(order)

        self.assertRecordValues(invoice.invoice_line_ids, [
            self._invoice_line_vals("line_section", SC_SECTION),
            self._product_vals(1.0, self.privilege_sc, "Juan Dela Cruz"),
            self._product_vals(1.0, self.privilege_sc, "Juan Dela Cruz"),
        ])

    def test_refund_invoice_keeps_holder_sections(self):
        order = self._create_order([(self.pizza, 5.0)])
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")],
            num_persons_sharing=5,
        )
        order.state = "paid"

        invoice = self._create_invoice(order._refund())

        self.assertRecordValues(invoice.invoice_line_ids, [
            self._invoice_line_vals("line_section", "Regular Orders"),
            self._product_vals(4.0),
            self._invoice_line_vals("line_section", SC_SECTION),
            self._product_vals(1.0, self.privilege_sc, "Juan Dela Cruz"),
        ])
