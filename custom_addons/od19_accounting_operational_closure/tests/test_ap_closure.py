from lxml import etree

from odoo import api, fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestAccountingAPClosure(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create(
            {"name": "AP Closure Vendor", "company_type": "company"}
        )
        cls.service = cls.env["product.product"].create(
            {
                "name": "Accepted Service",
                "type": "service",
                "purchase_ok": True,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Receipt Product",
                "type": "consu",
                "purchase_ok": True,
            }
        )
        cls.purchase_form_view = cls.env.ref("purchase.purchase_order_form")
        cls.admin_user = cls.env.ref("base.user_admin")
        # Receipt validation goes through ``stock.picking``, where the delivery
        # label module requires a department code resolved from the current
        # user's employee record. Provide one so the receipt can be validated.
        cls.department = cls.env["hr.department"].create(
            {"name": "Internal Audit", "code": "IA"}
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "AP Closure Employee",
                "user_id": cls.env.uid,
                "department_id": cls.department.id,
            }
        )

    def _fresh_purchase_order(self, order):
        fresh_env = api.Environment(self.env.cr, self.env.uid, dict(self.env.context))
        return fresh_env["purchase.order"].browse(order.id)

    def _get_purchase_form_arch(self):
        view_data = self.env["purchase.order"].get_view(
            view_id=self.purchase_form_view.id, view_type="form"
        )
        return etree.fromstring(view_data["arch"])

    def _force_order_state(self, order, state):
        self.env.cr.execute(
            "UPDATE purchase_order SET state = %s WHERE id = %s",
            (state, order.id),
        )
        order.invalidate_recordset(["state", "od19_vendor_bill_closure_state"])
        return self._fresh_purchase_order(order)

    def _register_payment(self, move, **kwargs):
        return (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=move.ids)
            .create({"group_payment": True, **kwargs})
            ._create_payments()
        )

    def _post_vendor_bill(self, bill):
        """Post a vendor bill after supplying the Thai tax invoice details that
        the purchase tax localization requires before posting."""
        bill.tax_invoice_ids.write(
            {
                "tax_invoice_number": "TEST-TINV-001",
                "tax_invoice_date": bill.invoice_date or fields.Date.today(),
            }
        )
        bill.action_post()
        return bill

    def _receive_full_order(self, order):
        picking = order.picking_ids[:1]
        self.assertTrue(picking)
        picking.move_ids.write({"picked": True})
        result = picking.button_validate()
        self.assertFalse(
            isinstance(result, dict),
            "Expected receipt validation without immediate wizard flow.",
        )
        order.invalidate_recordset(
            ["receipt_status", "od19_vendor_bill_closure_state"]
        )
        order.order_line.invalidate_recordset(["qty_received"])
        return self._fresh_purchase_order(order)

    def _create_po(self, product, *, confirm=True, quantity=1.0, price_unit=500.0):
        order = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": product.display_name,
                "product_id": product.id,
                "product_qty": quantity,
                "price_unit": price_unit,
                "date_planned": "2026-10-07 00:00:00",
                "product_uom_id": product.uom_id.id,
            }
        )
        if confirm:
            order.action_od19_submit_for_approval()
            order.with_user(self.admin_user).action_od19_approve()
            order.button_confirm()
        return order

    def test_service_po_waits_for_acceptance_before_vendor_bill(self):
        order = self._fresh_purchase_order(self._create_po(self.service))
        self.assertEqual(order.od19_vendor_bill_closure_state, "waiting_service_acceptance")

    def test_service_po_moves_to_ready_to_bill_after_acceptance(self):
        order = self._create_po(self.service)
        order.order_line.action_od19_accept_service()
        order = self._fresh_purchase_order(order)
        self.assertEqual(order.od19_vendor_bill_closure_state, "ready_to_bill")

    def test_done_service_po_still_waits_for_acceptance(self):
        order = self._create_po(self.service)
        order = self._force_order_state(order, "done")
        self.assertEqual(order.od19_vendor_bill_closure_state, "waiting_service_acceptance")

    def test_product_po_is_not_ready_to_bill_before_receipt(self):
        order = self._fresh_purchase_order(self._create_po(self.product))
        self.assertEqual(order.receipt_status, "pending")
        self.assertEqual(order.order_line.qty_received, 0.0)
        self.assertEqual(order.od19_vendor_bill_closure_state, "waiting_commitment")

    def test_product_po_moves_to_ready_to_bill_after_receipt(self):
        order = self._create_po(self.product)
        order = self._receive_full_order(order)
        self.assertEqual(order.receipt_status, "full")
        self.assertEqual(order.order_line.qty_received, order.order_line.product_qty)
        self.assertEqual(order.od19_vendor_bill_closure_state, "ready_to_bill")

    def test_product_po_with_bill_before_receipt_stays_waiting_commitment(self):
        self.product.purchase_method = "purchase"
        order = self._fresh_purchase_order(self._create_po(self.product))
        self.assertEqual(order.receipt_status, "pending")
        self.assertEqual(order.order_line.qty_received, 0.0)
        self.assertEqual(order.od19_vendor_bill_closure_state, "waiting_commitment")

        bill = self.env["account.move"].browse(order.action_create_invoice()["res_id"])
        bill.invoice_date = "2026-10-07"
        self._post_vendor_bill(bill)

        order = self._fresh_purchase_order(order)
        bill = bill.browse(bill.id)
        self.assertEqual(bill.od19_operational_closure_state, "posted")
        self.assertEqual(order.od19_vendor_bill_closure_state, "waiting_commitment")

        self._register_payment(bill, amount=bill.amount_total / 2)
        order = self._fresh_purchase_order(order)
        bill = bill.browse(bill.id)
        self.assertEqual(bill.od19_operational_closure_state, "partially_paid")
        self.assertEqual(order.od19_vendor_bill_closure_state, "waiting_commitment")

        self._register_payment(bill, amount=bill.amount_residual)
        order = self._fresh_purchase_order(order)
        bill = bill.browse(bill.id)
        self.assertEqual(bill.od19_operational_closure_state, "paid")
        self.assertEqual(order.od19_vendor_bill_closure_state, "waiting_commitment")

    def test_service_acceptance_requires_committed_po(self):
        order = self._create_po(self.service, confirm=False)
        with self.assertRaises(UserError):
            order.order_line.action_od19_accept_service()

    def test_direct_write_of_service_accepted_is_rejected(self):
        order = self._create_po(self.service)
        with self.assertRaises(UserError):
            order.order_line.write({"od19_service_accepted": True})

    def test_material_change_requires_fresh_service_acceptance(self):
        order = self._create_po(self.service)
        line = order.order_line
        line.action_od19_accept_service()
        line.with_context(od19_skip_approval_invalidation=True).write(
            {"name": "Changed Service Scope"}
        )
        order = self._fresh_purchase_order(order)
        self.assertFalse(order.order_line.od19_service_accepted)
        self.assertEqual(order.od19_vendor_bill_closure_state, "waiting_service_acceptance")

    def test_service_acceptance_is_not_copied_to_duplicate_order(self):
        order = self._create_po(self.service)
        order.order_line.action_od19_accept_service()
        duplicate = order.copy()
        self.assertFalse(duplicate.order_line.od19_service_accepted)
        self.assertEqual(duplicate.od19_vendor_bill_closure_state, "waiting_commitment")

    def test_purchase_order_partial_blocked_bill_stays_partially_paid(self):
        self.product.purchase_method = "purchase"
        order = self._create_po(self.product)
        order = self._receive_full_order(order)
        bill = self.env["account.move"].browse(order.action_create_invoice()["res_id"])
        bill.invoice_date = "2026-10-07"
        self._post_vendor_bill(bill)

        self._register_payment(bill, amount=bill.amount_total / 2)
        bill.action_toggle_block_payment()

        order = self._fresh_purchase_order(order)
        bill = bill.browse(bill.id)
        self.assertEqual(bill.payment_state, "blocked")
        self.assertEqual(bill.od19_operational_closure_state, "partially_paid")
        self.assertEqual(order.od19_vendor_bill_closure_state, "partially_paid")

    def test_paid_bill_does_not_close_order_with_remaining_bill_work(self):
        self.product.purchase_method = "purchase"
        order = self._create_po(self.product, quantity=2.0)
        order = self._receive_full_order(order)
        bill = self.env["account.move"].browse(order.action_create_invoice()["res_id"])
        # Reduce the billed quantity to 1 of the 2 received units. The price unit
        # must be written together with the quantity: changing the quantity makes
        # Odoo recompute ``price_unit`` from the product's vendor price list,
        # which is empty here, so a separate write would reset it to 0.
        bill.invoice_line_ids.write({"quantity": 1.0, "price_unit": 500.0})
        bill.invoice_date = "2026-10-07"
        self._post_vendor_bill(bill)
        self._register_payment(bill, amount=bill.amount_total)

        order = self._fresh_purchase_order(order)
        bill = bill.browse(bill.id)
        self.assertEqual(bill.payment_state, "paid")
        self.assertEqual(order.invoice_status, "to invoice")
        self.assertEqual(order.amount_untaxed, 1000.0)
        self.assertEqual(order.od19_vendor_bill_closure_state, "partially_paid")

    def test_purchase_order_form_places_ap_closure_fields_once(self):
        arch = self._get_purchase_form_arch()
        closure_state_fields = arch.xpath(
            "//field[@name='invoice_status']/following-sibling::field[@name='od19_vendor_bill_closure_state']"
        )
        acceptance_required_fields = arch.xpath(
            "//field[@name='order_line']"
            "//field[@name='od19_service_acceptance_required']"
        )
        acceptance_state_fields = arch.xpath(
            "//field[@name='order_line']//field[@name='od19_service_accepted']"
        )
        accept_buttons = arch.xpath(
            "//field[@name='order_line']//button[@name='action_od19_accept_service']"
        )
        self.assertEqual(len(closure_state_fields), 1)
        self.assertEqual(len(acceptance_required_fields), 1)
        self.assertEqual(len(acceptance_state_fields), 1)
        self.assertEqual(len(accept_buttons), 1)
        self.assertEqual(acceptance_state_fields[0].get("readonly"), "1")
