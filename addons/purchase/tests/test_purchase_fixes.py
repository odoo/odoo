from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.purchase.controllers.portal import CustomerPortal


@tagged("-at_install", "post_install")
class TestPurchasePortalRfqDomain(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rfq = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner_a.id,
                "line_ids": [
                    Command.create(
                        {"product_id": cls.product_a.id, "product_qty": 1.0},
                    ),
                ],
            },
        )
        cls.confirmed = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner_a.id,
                "line_ids": [
                    Command.create(
                        {"product_id": cls.product_a.id, "product_qty": 1.0},
                    ),
                ],
            },
        )
        cls.confirmed.action_confirm()

    def test_rfq_state_domain_is_draft(self):
        domain = CustomerPortal()._purchase_get_page_state_domain("rfq")
        self.assertEqual(domain, [("state", "=", "draft")])

    def test_rfq_domain_matches_unconfirmed_orders(self):
        domain = CustomerPortal()._purchase_get_page_state_domain("rfq")
        matched = self.env["purchase.order"].search(
            domain + [("id", "in", (self.rfq | self.confirmed).ids)],
        )
        self.assertIn(self.rfq, matched, "Draft RFQ should show on /my/rfq")
        self.assertNotIn(
            self.confirmed,
            matched,
            "Confirmed PO should not show on /my/rfq",
        )

    def test_rfq_report_ref_uses_quotation_for_draft(self):
        self.assertEqual(
            CustomerPortal._purchase_detail_report_ref(self.rfq),
            "purchase.report_purchase_quotation",
        )
        self.assertEqual(
            CustomerPortal._purchase_detail_report_ref(self.confirmed),
            "purchase.action_report_purchase_order",
        )


@tagged("-at_install", "post_install")
class TestPurchaseMassCancel(AccountTestInvoicingCommon):
    def _make_po(self, confirm=False):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {"product_id": self.product_a.id, "product_qty": 1.0},
                    ),
                ],
            },
        )
        if confirm:
            po.action_confirm()
        return po

    def _wizard(self, orders):
        return self.env["purchase.mass.cancel.orders"].create(
            {"order_ids": [Command.set(orders.ids)]},
        )

    def test_mass_cancel_drafts(self):
        pos = self._make_po() | self._make_po()
        self._wizard(pos).action_mass_cancel()
        self.assertEqual(set(pos.mapped("state")), {"cancel"})

    def test_mass_cancel_blocks_locked_order(self):
        locked = self._make_po(confirm=True)
        locked.action_lock()
        with self.assertRaises(UserError):
            self._wizard(locked).action_mass_cancel()
        self.assertEqual(locked.state, "done", "Locked PO must survive mass-cancel")

    def test_mass_cancel_blocks_posted_bill(self):
        po = self._make_po(confirm=True)
        bill = po.create_invoice()
        bill.invoice_date = bill.invoice_date or po.date_order.date()
        bill.action_post()
        self.assertEqual(bill.state, "posted")
        with self.assertRaises(UserError):
            self._wizard(po).action_mass_cancel()
        self.assertEqual(po.state, "done", "Invoiced PO must survive mass-cancel")

    def test_mass_cancel_skips_already_cancelled(self):
        live = self._make_po()
        already = self._make_po()
        already.action_cancel()
        self._wizard(live | already).action_mass_cancel()
        self.assertEqual(live.state, "cancel")
        self.assertEqual(already.state, "cancel")


@tagged("-at_install", "post_install")
class TestPurchaseMergeConsolidation(AccountTestInvoicingCommon):
    def _rfq_with_date(self, date_commitment):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {"product_id": self.product_a.id, "product_qty": 3.0},
                    ),
                ],
            },
        )
        po.line_ids.date_commitment = date_commitment
        return po

    def test_same_date_lines_consolidate(self):
        po1 = self._rfq_with_date("2026-07-20 12:00:00")
        po2 = self._rfq_with_date("2026-07-20 12:00:00")
        (po1 | po2).action_merge()
        target = po1 if po1.state != "cancel" else po2
        product_lines = target.line_ids.filtered(lambda l: not l.display_type)
        self.assertEqual(len(product_lines), 1, "matching dates should merge")
        self.assertEqual(product_lines.product_qty, 6.0, "quantities summed")

    def test_mismatched_date_lines_stay_separate(self):
        po1 = self._rfq_with_date("2026-07-20 12:00:00")
        po2 = self._rfq_with_date("2026-07-25 12:00:00")
        (po1 | po2).action_merge()
        target = po1 if po1.state != "cancel" else po2
        product_lines = target.line_ids.filtered(lambda l: not l.display_type)
        self.assertEqual(
            len(product_lines),
            2,
            "dates > 24h apart must not consolidate",
        )


@tagged("-at_install", "post_install")
class TestPurchaseSellerCache(AccountTestInvoicingCommon):
    def test_seller_lookup_cached_across_identical_lines(self):
        pol_model = self.env["purchase.order.line"]
        model_cls = type(pol_model)
        original = model_cls._get_select_sellers_params
        misses = []

        def counting(line_self):
            misses.append(line_self.product_id.id)
            return original(line_self)

        with patch.object(model_cls, "_get_select_sellers_params", counting):
            self.env["purchase.order"].create(
                {
                    "partner_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {"product_id": self.product_a.id, "product_qty": 2.0},
                        )
                        for _ in range(5)
                    ],
                },
            )

        self.assertEqual(
            len(misses),
            1,
            "Five identical-key lines should resolve the seller only once "
            f"(got {len(misses)} lookups)",
        )


@tagged("-at_install", "post_install")
class TestSrmTag(AccountTestInvoicingCommon):
    def test_hierarchical_display_name(self):
        parent = self.env["srm.tag"].create({"name": "Strategic"})
        child = self.env["srm.tag"].create(
            {"name": "Key Vendor", "parent_id": parent.id},
        )
        self.assertEqual(child.display_name, "Strategic / Key Vendor")
        self.assertEqual(parent.display_name, "Strategic")

    def test_recursion_is_rejected(self):
        a = self.env["srm.tag"].create({"name": "A"})
        b = self.env["srm.tag"].create({"name": "B", "parent_id": a.id})
        with self.assertRaises(UserError):
            a.parent_id = b
            a.flush_recordset()

    def test_order_tag_relation_is_bidirectional(self):
        tag = self.env["srm.tag"].create({"name": "Preferred"})
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "tag_ids": [Command.link(tag.id)],
                "line_ids": [
                    Command.create(
                        {"product_id": self.product_a.id, "product_qty": 1.0},
                    ),
                ],
            },
        )
        self.assertIn(po, tag.order_ids)
        self.assertIn(tag, po.tag_ids)

    def test_parent_delete_cascades_to_children(self):
        parent = self.env["srm.tag"].create({"name": "Root"})
        child = self.env["srm.tag"].create(
            {"name": "Leaf", "parent_id": parent.id},
        )
        parent.unlink()
        self.assertFalse(child.exists())


@tagged("-at_install", "post_install")
class TestBillPoLinkTracking(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.po = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner_a.id,
                "line_ids": [
                    Command.create(
                        {"product_id": cls.product_a.id, "product_qty": 1.0},
                    ),
                ],
            },
        )
        cls.po.action_confirm()

    def _new_bill(self):
        return self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "price_unit": 100,
                        },
                    ),
                ],
            },
        )

    def _has_modified_note(self, move):
        return any("modified from" in (m.body or "") for m in move.message_ids)

    def test_linking_po_via_write_posts_note(self):
        bill = self._new_bill()
        self.assertFalse(self._has_modified_note(bill))
        bill.write(
            {
                "invoice_line_ids": [
                    Command.update(
                        bill.invoice_line_ids.id,
                        {"purchase_line_ids": [Command.link(self.po.line_ids.id)]},
                    ),
                ],
            },
        )
        self.assertTrue(
            self._has_modified_note(bill),
            "linking a PO via invoice_line_ids write should post the note",
        )

    def test_non_line_write_does_not_post_note(self):
        bill = self._new_bill()
        bill.write({"ref": "SOME-REF"})
        self.assertFalse(
            self._has_modified_note(bill),
            "a ref-only write must not post a PO-modified note",
        )


@tagged("-at_install", "post_install")
class TestPurchaseOverInvoiceState(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.svc_ordered = cls.env["product.product"].create(
            {
                "name": "Svc ordered",
                "type": "service",
                "bill_policy": "ordered",
                "purchase_ok": True,
                "standard_price": 100.0,
            },
        )
        cls.svc_transferred = cls.env["product.product"].create(
            {
                "name": "Svc transferred",
                "type": "service",
                "bill_policy": "transferred",
                "purchase_ok": True,
                "standard_price": 100.0,
            },
        )

    def _confirmed_po(self, product, qty):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": qty,
                            "price_unit": 100,
                        },
                    ),
                ],
            },
        )
        po.action_confirm()
        return po

    def _post_bill(self, po, product, qty):
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "quantity": qty,
                            "price_unit": 100,
                            "purchase_line_ids": [Command.set(po.line_ids.ids)],
                        },
                    ),
                ],
            },
        )
        bill.action_post()
        return bill

    def test_ordered_over_billed_is_over_done(self):
        po = self._confirmed_po(self.svc_ordered, 1)
        self._post_bill(po, self.svc_ordered, 2)
        self.assertEqual(po.line_ids.invoice_state, "over done")
        self.assertEqual(po.invoice_state, "over done")

    def test_transferred_over_billed_is_to_do(self):
        po = self._confirmed_po(self.svc_transferred, 5)
        po.line_ids.qty_transferred = 1.0
        self._post_bill(po, self.svc_transferred, 2)
        self.assertEqual(po.line_ids.invoice_state, "to do")
        self.assertEqual(po.invoice_state, "to do")

    def test_reduce_qty_below_invoiced_is_over_done(self):
        po = self._confirmed_po(self.svc_ordered, 5)
        line = po.line_ids
        self._post_bill(po, self.svc_ordered, 5)
        self.assertEqual(line.qty_invoiced, 5.0)
        self.assertEqual(line.invoice_state, "done")

        line.product_qty = 3
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(line.qty_to_invoice, -2.0)
        self.assertEqual(line.invoice_state, "over done")
        self.assertEqual(po.invoice_state, "over done")


@tagged("-at_install", "post_install")
class TestPurchaseAmountToInvoice(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.svc_ordered = cls.env["product.product"].create(
            {
                "name": "Svc ordered notax",
                "type": "service",
                "bill_policy": "ordered",
                "purchase_ok": True,
                "standard_price": 100.0,
                "supplier_taxes_id": [Command.clear()],
            },
        )
        cls.svc_transferred = cls.env["product.product"].create(
            {
                "name": "Svc transferred notax",
                "type": "service",
                "bill_policy": "transferred",
                "purchase_ok": True,
                "standard_price": 100.0,
                "supplier_taxes_id": [Command.clear()],
            },
        )

    def test_amount_to_invoice_with_discount(self):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.svc_ordered.id,
                            "product_qty": 5,
                            "price_unit": 100,
                            "discount": 10,
                            "tax_ids": [Command.clear()],
                        },
                    ),
                ],
            },
        )
        po.action_confirm()
        self.assertEqual(po.amount_taxinc_to_invoice, 450.0)

        bill = po.create_invoice()
        bill.invoice_date = "2026-01-01"
        bill.invoice_line_ids.quantity = 3
        bill.action_post()
        self.assertEqual(po.amount_taxinc_to_invoice, 180.0)

    def test_amount_to_invoice_price_unit_change(self):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.svc_transferred.id,
                            "product_qty": 5,
                            "price_unit": 100,
                            "tax_ids": [Command.clear()],
                        },
                    ),
                ],
            },
        )
        po.action_confirm()
        line = po.line_ids
        line.qty_transferred = 5.0

        bill = po.create_invoice()
        self.assertEqual(line.qty_invoiced, 5.0)
        self.assertEqual(line.qty_to_invoice, 0.0)
        self.assertEqual(line.amount_taxinc_to_invoice, line.price_total)
        self.assertEqual(line.amount_taxinc_invoiced, 0.0)

        bill.invoice_date = "2026-01-01"
        bill.invoice_line_ids.price_unit /= 2
        bill.action_post()
        self.assertEqual(line.qty_invoiced, 5.0)
        self.assertEqual(line.amount_taxinc_to_invoice, 0.0)
        self.assertEqual(line.amount_taxinc_invoiced, line.price_total / 2)


@tagged("-at_install", "post_install")
class TestPurchaseInvoiceSections(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.svc = cls.env["product.product"].create(
            {
                "name": "Svc ordered notax",
                "type": "service",
                "bill_policy": "ordered",
                "purchase_ok": True,
                "standard_price": 100.0,
                "supplier_taxes_id": [Command.clear()],
            },
        )

    def _po(self, line_cmds):
        po = self.env["purchase.order"].create(
            {"partner_id": self.partner_a.id, "line_ids": line_cmds},
        )
        po.action_confirm()
        return po

    def _product_cmd(self):
        return Command.create(
            {
                "product_id": self.svc.id,
                "product_qty": 5,
                "price_unit": 100,
                "tax_ids": [Command.clear()],
            },
        )

    def test_section_before_product_is_billed(self):
        po = self._po(
            [
                Command.create({"display_type": "line_section", "name": "Sec A"}),
                self._product_cmd(),
            ]
        )
        bill = po.create_invoice()
        sections = bill.invoice_line_ids.filtered(
            lambda l: l.display_type == "line_section",
        )
        self.assertEqual(sections.mapped("name"), ["Sec A"])

    def test_trailing_section_not_billed(self):
        po = self._po(
            [
                self._product_cmd(),
                Command.create({"display_type": "line_section", "name": "Trailing"}),
            ]
        )
        bill = po.create_invoice()
        names = bill.invoice_line_ids.filtered(
            lambda l: l.display_type == "line_section",
        ).mapped("name")
        self.assertNotIn("Trailing", names, "trailing section must not be billed")


@tagged("-at_install", "post_install")
class TestPurchaseQtyInvoicedParity(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.svc = cls.env["product.product"].create(
            {
                "name": "Svc ordered notax",
                "type": "service",
                "bill_policy": "ordered",
                "purchase_ok": True,
                "standard_price": 100.0,
                "supplier_taxes_id": [Command.clear()],
            },
        )
        cls.svc_tr = cls.env["product.product"].create(
            {
                "name": "Svc transferred notax",
                "type": "service",
                "bill_policy": "transferred",
                "purchase_ok": True,
                "standard_price": 100.0,
                "supplier_taxes_id": [Command.clear()],
            },
        )

    def _confirmed_po(self, product, qty):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": qty,
                            "price_unit": 100,
                            "tax_ids": [Command.clear()],
                        },
                    ),
                ],
            },
        )
        po.action_confirm()
        return po

    def test_qty_invoiced_default_rounding(self):
        po = self._confirmed_po(self.svc, 5)
        bill = po.create_invoice()
        bill.invoice_date = "2026-01-01"
        self.assertEqual(po.line_ids.qty_invoiced, 5.0, "a draft bill counts")
        bill.invoice_line_ids.quantity = 5.13
        bill.action_post()
        self.assertEqual(po.line_ids.qty_invoiced, 5.13)

    def test_qty_invoiced_uom_ceil_rounding(self):
        po = self._confirmed_po(self.svc, 5)
        bill = po.create_invoice()
        bill.invoice_date = "2026-01-01"
        bill.invoice_line_ids.quantity = 5.13
        bill.action_post()
        line = po.line_ids
        self.assertEqual(line.qty_invoiced, 5.13)

        line.product_uom_id.rounding = 0.1
        line.product_uom_id.flush_recordset(["rounding"])
        line.env.add_to_compute(line._fields["qty_invoiced"], line)
        self.assertEqual(line.qty_invoiced, 5.2)

    def test_amount_to_invoice_multiple_po(self):
        po1 = self._confirmed_po(self.svc_tr, 10)
        po2 = self._confirmed_po(self.svc_tr, 20)
        po1.line_ids.qty_transferred = 10
        po2.line_ids.qty_transferred = 20
        bills = (po1 | po2).create_invoice()
        bills.invoice_date = "2026-01-01"
        bills.action_post()
        self.assertEqual(po1.amount_taxinc_to_invoice, 0.0)
        self.assertEqual(po2.amount_taxinc_to_invoice, 0.0)


@tagged("-at_install", "post_install")
class TestTransferredQtyPostingGuard(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.svc_tr = cls.env["product.product"].create(
            {
                "name": "Svc billed on received",
                "type": "service",
                "bill_policy": "transferred",
                "purchase_ok": True,
                "standard_price": 100.0,
                "supplier_taxes_id": [Command.clear()],
            },
        )

    def _confirmed_po_with_received(self, qty, received):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.svc_tr.id,
                            "product_qty": qty,
                            "price_unit": 100,
                            "tax_ids": [Command.clear()],
                        },
                    ),
                ],
            },
        )
        po.action_confirm()
        po.line_ids.qty_transferred = received
        return po

    def test_guard_does_not_erase_a_manual_transferred_qty(self):
        line = self._confirmed_po_with_received(10, 5).line_ids
        self.assertEqual(line.qty_transferred_method, "manual")

        line._assert_transferred_uom_convertible()

        self.assertEqual(
            line.qty_transferred, 5, "The guard must not write the field it checks"
        )
        self.assertEqual(line.qty_to_invoice, 5)

    def test_guard_posts_no_chatter_message(self):
        po = self._confirmed_po_with_received(10, 5)
        messages_before = len(po.message_ids)

        po.line_ids._assert_transferred_uom_convertible()

        self.assertEqual(len(po.message_ids), messages_before)

    def test_billing_a_service_line_uses_the_received_qty(self):
        po = self._confirmed_po_with_received(10, 5)
        self.assertEqual(po.invoice_state, "to do")

        bill = po.create_invoice()
        self.assertEqual(
            bill.invoice_line_ids.quantity,
            5,
            "The bill line must carry the received qty",
        )
        bill.invoice_date = "2026-01-01"
        bill.action_post()

        self.assertEqual(po.line_ids.qty_invoiced, 5)
        self.assertEqual(po.line_ids.qty_transferred, 5)
        self.assertEqual(po.invoice_state, "done")

    def test_guard_still_raises_on_an_impossible_conversion(self):
        line = self._confirmed_po_with_received(10, 5).line_ids
        hour = self.env.ref("uom.product_uom_hour")
        with patch.object(
            type(line),
            "_prepare_qty_transferred",
            lambda self: self.product_uom_id.with_context(
                uom_reconcile_strict=True
            )._get_quantity_reconcile(1.0, hour),
        ):
            with self.assertRaises(UserError):
                line._assert_transferred_uom_convertible()


@tagged("-at_install", "post_install")
class TestInvoiceAnalysisVisibility(AccountTestInvoicingCommon):
    def _billing_buyer(self):
        return self.env["res.users"].create(
            {
                "name": "Billing buyer",
                "login": "billing_buyer",
                "company_id": self.env.company.id,
                "company_ids": [Command.set(self.env.company.ids)],
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("account.group_account_invoice").id,
                            self.env.ref("purchase.group_purchase_user_all").id,
                        ]
                    )
                ],
            }
        )

    def _posted_customer_invoice(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "quantity": 3,
                            "price_unit": 100,
                        },
                    ),
                ],
            },
        )
        invoice.action_post()
        return invoice

    def test_billing_user_with_a_purchase_group_still_sees_customer_invoices(self):
        user = self._billing_buyer()
        invoice = self._posted_customer_invoice()

        self.assertTrue(
            self.env["account.move"].with_user(user).search([("id", "=", invoice.id)]),
            "Precondition: the move itself is visible in Billing",
        )
        self.assertTrue(
            self.env["account.invoice.report"]
            .with_user(user)
            .search([("move_id", "=", invoice.id)]),
            "A customer invoice visible in Billing must be visible in its analysis",
        )

    def test_analysis_is_never_narrower_than_the_moves_it_reports_on(self):
        user = self._billing_buyer()
        moves = self.env["account.move"]
        for move_type, partner in (
            ("out_invoice", self.partner_a),
            ("out_refund", self.partner_a),
            ("in_invoice", self.partner_b),
            ("in_refund", self.partner_b),
        ):
            move = self.env["account.move"].create(
                {
                    "move_type": move_type,
                    "partner_id": partner.id,
                    "invoice_date": "2026-01-01",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": self.product_a.id,
                                "quantity": 1,
                                "price_unit": 10,
                            },
                        ),
                    ],
                },
            )
            move.action_post()
            moves |= move

        visible_moves = (
            self.env["account.move"].with_user(user).search([("id", "in", moves.ids)])
        )
        analysed_moves = (
            self.env["account.invoice.report"]
            .with_user(user)
            .search([("move_id", "in", moves.ids)])
            .move_id
        )
        self.assertEqual(
            analysed_moves,
            visible_moves,
            "Invoice Analysis must cover exactly the moves the user can read",
        )


@tagged("-at_install", "post_install")
class TestPurchaseMailTemplate(AccountTestInvoicingCommon):
    def _make_po(self):
        return self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {"product_id": self.product_a.id, "product_qty": 1.0},
                    ),
                ],
            },
        )

    def test_returns_a_record_not_an_id(self):
        template = self._make_po()._get_mail_template()
        self.assertEqual(template._name, "mail.template")

    def test_matches_the_contract_used_by_sale_and_account(self):
        po_template = self._make_po()._get_mail_template()
        move_template = self.init_invoice(
            "out_invoice",
            products=self.product_a,
        )._get_mail_template()
        self.assertEqual(po_template._name, move_template._name)

        if "sale.order" not in self.env:
            return
        sale_order = (
            self.env["sale.order"]
            .sudo()
            .create(
                {"partner_id": self.partner_a.id},
            )
        )
        so_template = sale_order._get_mail_template()
        self.assertEqual(po_template._name, so_template._name)

    def test_rfq_and_confirmed_use_different_templates(self):
        order = self._make_po()
        rfq_template = order._get_mail_template()
        order.action_confirm()
        done_template = order._get_mail_template()
        self.assertEqual(
            rfq_template,
            self.env.ref("purchase.email_template_edi_purchase"),
        )
        self.assertEqual(
            done_template,
            self.env.ref("purchase.email_template_edi_purchase_done"),
        )
        self.assertNotEqual(rfq_template, done_template)

    def test_send_action_carries_the_template_id(self):
        order = self._make_po()
        action = order.action_send_rfq()
        self.assertEqual(action["res_model"], "mail.compose.message")
        self.assertEqual(
            action["context"]["default_template_id"],
            self.env.ref("purchase.email_template_edi_purchase").id,
        )

    def test_template_language_wins(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        order = self._make_po()
        template = self.env.ref("purchase.email_template_edi_purchase")
        template.lang = "fr_FR"
        ctx = {
            "default_template_id": template.id,
            "default_model": "purchase.order",
            "default_res_ids": order.ids,
        }
        self.assertEqual(order._get_mail_composer_lang(ctx), "fr_FR")

    def test_language_falls_back_without_composer_keys(self):
        order = self._make_po().with_context(lang="en_US")
        self.assertEqual(order._get_mail_composer_lang({}), "en_US")

    def test_language_falls_back_when_template_has_none(self):
        order = self._make_po()
        template = self.env.ref("purchase.email_template_edi_purchase")
        template.lang = False
        ctx = {
            "default_template_id": template.id,
            "default_model": "purchase.order",
            "default_res_ids": order.ids,
        }
        self.assertEqual(
            order.with_context(lang="en_US")._get_mail_composer_lang(ctx),
            "en_US",
        )
