import base64
from unittest.mock import patch

from odoo import api, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestAccountingReporting(AccountTestInvoicingCommon):
    KPI_KEYS = {
        "billable_backlog",
        "open_receivable",
        "overdue_receivable",
        "open_payable",
        "due_payable",
        "cash_application_status",
        "unreconciled_customer_items",
        "unreconciled_vendor_items",
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()
        cls.company_2 = cls.company_data_2["company"]
        cls.foreign_currency = cls.setup_other_currency("USD")
        cls.foreign_currency_pricelist = cls.env["product.pricelist"].create(
            {
                "name": "Reporting USD Pricelist",
                "currency_id": cls.foreign_currency.id,
            }
        )
        cls.customer = cls.env["res.partner"].create(
            {
                "name": "Reporting Customer",
                "company_type": "company",
                "is_company": True,
                "email": "reporting.customer@example.com",
                "od19_is_commercial_customer": True,
            }
        )
        cls.owner = cls.env["res.partner"].create(
            {
                "name": "Reporting Owner",
                "company_type": "company",
                "is_company": True,
                "od19_is_project_owner": True,
            }
        )
        cls.project = (
            cls.env["project.project"]
            .sudo()
            .create(
                {
                    "name": "Reporting Project",
                    "project_owner_id": cls.owner.id,
                }
            )
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Reporting Product",
                "type": "consu",
                "sale_ok": True,
                "purchase_ok": True,
                "list_price": 120.0,
                "standard_price": 80.0,
            }
        )
        # Sale orders and their invoices inherit the customer's pricelist, and
        # OCA's "account_invoice_pricelist" re-prices any line whose quantity is
        # edited. Keep that pricelist in the product's own currency so editing
        # the quantity does not convert the catalogue price.
        cls.customer.property_product_pricelist = cls.env["product.pricelist"].create(
            {
                "name": "Reporting Pricelist",
                "currency_id": cls.product.currency_id.id,
            }
        )
        cls.evidence_type = cls.env["od19.billing.evidence.type"].create(
            {
                "name": "Delivery Proof",
                "trigger_kind": "delivery",
                "required_for_billing": True,
            }
        )
        base_user_group = cls.env.ref("base.group_user")
        account_user_group = cls.env.ref("account.group_account_user")
        Users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.account_user = Users.create(
            {
                "name": "Accounting Reporting User",
                "login": "account.reporting.user@example.com",
                "email": "account.reporting.user@example.com",
                "company_id": cls.env.company.id,
                "company_ids": [(6, 0, [cls.env.company.id])],
                "group_ids": [(6, 0, [base_user_group.id, account_user_group.id])],
            }
        )
        # Confirming a sale order creates a delivery picking, where the
        # delivery label module requires a department code resolved from the
        # current user's employee record. Provide one so confirmation succeeds.
        cls.department = cls.env["hr.department"].sudo().create(
            {"name": "Internal Audit", "code": "IA"}
        )
        cls.employee = cls.env["hr.employee"].sudo().create(
            {
                "name": "Accounting Reporting Employee",
                "user_id": cls.env.uid,
                "department_id": cls.department.id,
            }
        )

    def _fresh_report(self, *, user=None, allowed_company_ids=None):
        uid = user.id if user else self.env.uid
        context = dict(self.env.context)
        if allowed_company_ids is not None:
            context["allowed_company_ids"] = allowed_company_ids
        fresh_env = api.Environment(self.env.cr, uid, context)
        return fresh_env["od19.report.accounting.operational.closure"]

    def _fresh_sale_order(self, order):
        fresh_env = api.Environment(self.env.cr, self.env.uid, dict(self.env.context))
        return fresh_env["sale.order"].browse(order.id)

    def _metric_rows(self, *, company=None, user=None, allowed_company_ids=None):
        company = company or self.env.company
        return self._fresh_report(
            user=user,
            allowed_company_ids=allowed_company_ids,
        ).search(
            [("company_id", "=", company.id)],
        )

    def _metric_map(self, *, company=None, user=None, allowed_company_ids=None):
        return {
            row.metric_key: row
            for row in self._metric_rows(
                company=company,
                user=user,
                allowed_company_ids=allowed_company_ids,
            )
        }

    def _metric_map_without_payment_state_flush(
        self,
        *,
        company=None,
        user=None,
        allowed_company_ids=None,
    ):
        account_move_model = type(self.env["account.move"])
        original_flush_model = account_move_model.flush_model

        def patched_flush_model(model, fnames=None):
            if fnames:
                fnames = [fname for fname in fnames if fname != "payment_state"]
            return original_flush_model(model, fnames)

        with patch.object(account_move_model, "flush_model", patched_flush_model):
            return self._metric_map(
                company=company,
                user=user,
                allowed_company_ids=allowed_company_ids,
            )

    def _metric_amount(self, metric_key, *, company=None, user=None, allowed_company_ids=None):
        row = self._metric_map(
            company=company,
            user=user,
            allowed_company_ids=allowed_company_ids,
        )[metric_key]
        return row.total_amount

    def _metric_count(self, metric_key, *, company=None, user=None, allowed_company_ids=None):
        row = self._metric_map(
            company=company,
            user=user,
            allowed_company_ids=allowed_company_ids,
        )[metric_key]
        return row.item_count

    def _evidence_attachment(self):
        """Create the attachment required to verify a billing evidence."""
        return self.env["ir.attachment"].create(
            {
                "name": "billing-evidence.txt",
                "datas": base64.b64encode(b"billing evidence").decode(),
            }
        )

    def _create_ready_sale_order(self, *, company=None, quantity=1.0, price_unit=120.0):
        company = company or self.env.company
        allowed_company_ids = [company.id]
        sale_order = (
            self.env["sale.order"]
            .with_company(company)
            .with_context(allowed_company_ids=allowed_company_ids)
            .sudo()
            .create(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": self.project.id,
                "od19_project_owner_id": self.owner.id,
            }
        )
        )
        (
            self.env["sale.order.line"]
            .with_company(company)
            .with_context(allowed_company_ids=allowed_company_ids)
            .sudo()
            .create(
            {
                "order_id": sale_order.id,
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_uom_qty": quantity,
                "product_uom_id": self.product.uom_id.id,
                "price_unit": price_unit,
            }
        )
        )
        (
            self.env["od19.billing.evidence"]
            .with_company(company)
            .with_context(allowed_company_ids=allowed_company_ids)
            .sudo()
            .create(
            {
                "name": "BILL-READY",
                "sale_order_id": sale_order.id,
                "evidence_type_id": self.evidence_type.id,
                "is_verified": True,
                "attachment_ids": [(6, 0, self._evidence_attachment().ids)],
            }
        )
        )
        sale_order.action_confirm()
        return sale_order

    def _create_billable_quotation(self, *, state="draft", company=None):
        company = company or self.env.company
        allowed_company_ids = [company.id]
        quotation = (
            self.env["sale.order"]
            .with_company(company)
            .with_context(allowed_company_ids=allowed_company_ids)
            .sudo()
            .create(
                {
                    "partner_id": self.customer.id,
                    "od19_sale_mode": "one_time",
                    "od19_project_id": self.project.id,
                    "od19_project_owner_id": self.owner.id,
                }
            )
        )
        (
            self.env["sale.order.line"]
            .with_company(company)
            .with_context(allowed_company_ids=allowed_company_ids)
            .sudo()
            .create(
                {
                    "order_id": quotation.id,
                    "product_id": self.product.id,
                    "name": self.product.display_name,
                    "product_uom_qty": 1.0,
                    "product_uom_id": self.product.uom_id.id,
                    "price_unit": 120.0,
                }
            )
        )
        (
            self.env["od19.billing.evidence"]
            .with_company(company)
            .with_context(allowed_company_ids=allowed_company_ids)
            .sudo()
            .create(
                {
                    "name": f"BILLABLE-{state.upper()}",
                    "sale_order_id": quotation.id,
                    "evidence_type_id": self.evidence_type.id,
                    "is_verified": True,
                    "attachment_ids": [(6, 0, self._evidence_attachment().ids)],
                }
            )
        )
        if state == "sent":
            quotation.action_quotation_sent()
        return quotation

    def _create_posted_vendor_bill(self, **kwargs):
        """Create and post a vendor bill, supplying the Thai tax invoice
        details the purchase tax localization requires before posting."""
        bill = self._create_invoice(move_type="in_invoice", post=False, **kwargs)
        bill.tax_invoice_ids.write(
            {
                "tax_invoice_number": "TEST-TINV-001",
                "tax_invoice_date": bill.invoice_date or fields.Date.today(),
            }
        )
        bill.action_post()
        return bill

    def _create_posted_invoice_for_order(self, order):
        invoice = order._create_invoices()
        invoice.action_post()
        return invoice

    def _force_payment_state(self, move, payment_state):
        self.env.cr.execute(
            "UPDATE account_move SET payment_state = %s WHERE id = %s",
            [payment_state, move.id],
        )

    def _stored_payment_state(self, move):
        self.env.cr.execute(
            "SELECT payment_state FROM account_move WHERE id = %s",
            [move.id],
        )
        return self.env.cr.fetchone()[0]

    def _create_partially_invoiced_order(self):
        order = self._create_ready_sale_order(quantity=2.0)
        invoice = order._create_invoices()
        invoice.invoice_line_ids.quantity = 1.0
        invoice.action_post()
        return order, invoice

    def test_company_report_excludes_invoiced_and_partially_paid_orders_from_backlog(self):
        before = self._metric_amount("billable_backlog")

        ready_order = self._create_ready_sale_order()
        invoiced_order = self._create_ready_sale_order()
        partial_order = self._create_ready_sale_order()
        invoiced_invoice = self._create_posted_invoice_for_order(invoiced_order)
        partial_invoice = self._create_posted_invoice_for_order(partial_order)
        self._register_payment(partial_invoice, amount=partial_invoice.amount_total / 2)
        vendor_bill = self._create_posted_vendor_bill(
            partner_id=self.partner_a,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=80.0)
            ],
        )

        ready_order = self._fresh_sale_order(ready_order)
        invoiced_order = self._fresh_sale_order(invoiced_order)
        partial_order = self._fresh_sale_order(partial_order)
        partial_invoice = partial_invoice.browse(partial_invoice.id)
        after = self._metric_map()

        self.assertEqual(ready_order.od19_invoice_closure_state, "ready_to_invoice")
        self.assertEqual(invoiced_order.od19_invoice_closure_state, "invoiced")
        self.assertEqual(partial_order.od19_invoice_closure_state, "partially_paid")
        self.assertEqual(
            after["billable_backlog"].total_amount - before,
            ready_order.amount_to_invoice,
        )
        self.assertEqual(
            after["open_receivable"].total_amount,
            invoiced_invoice.amount_residual_signed + partial_invoice.amount_residual_signed,
        )
        self.assertEqual(
            after["open_payable"].total_amount,
            vendor_bill.amount_residual_signed,
        )

    def test_company_report_excludes_draft_and_sent_quotations_from_backlog(self):
        before = self._metric_amount("billable_backlog")

        draft_quotation = self._create_billable_quotation(state="draft")
        sent_quotation = self._create_billable_quotation(state="sent")
        ready_order = self._create_ready_sale_order()

        draft_quotation = self._fresh_sale_order(draft_quotation)
        sent_quotation = self._fresh_sale_order(sent_quotation)
        ready_order = self._fresh_sale_order(ready_order)
        after = self._metric_amount("billable_backlog")

        self.assertEqual(draft_quotation.state, "draft")
        self.assertEqual(sent_quotation.state, "sent")
        self.assertEqual(draft_quotation.od19_billing_readiness_state, "draft")
        self.assertEqual(sent_quotation.od19_billing_readiness_state, "draft")
        self.assertEqual(ready_order.state, "sale")
        self.assertEqual(
            after - before,
            ready_order.amount_to_invoice,
        )

    def test_company_report_uses_remaining_amount_to_invoice_for_partial_invoicing(self):
        before = self._metric_amount("billable_backlog")

        partial_order, partial_invoice = self._create_partially_invoiced_order()

        partial_order = self._fresh_sale_order(partial_order)
        partial_invoice = partial_invoice.browse(partial_invoice.id)
        after = self._metric_amount("billable_backlog")

        self.assertEqual(partial_order.state, "sale")
        self.assertEqual(partial_order.od19_billing_readiness_state, "ready")
        self.assertEqual(partial_order.od19_invoice_closure_state, "invoiced")
        self.assertEqual(partial_order.amount_total, 276.0)
        self.assertEqual(partial_order.amount_to_invoice, 138.0)
        self.assertEqual(partial_invoice.amount_total, 138.0)
        self.assertEqual(
            after - before,
            partial_order.amount_to_invoice,
        )
        self.assertNotEqual(
            after - before,
            partial_order.amount_total,
        )

    def test_company_report_uses_signed_company_residual_amounts(self):
        before_receivable = self._metric_amount("open_receivable")
        before_payable = self._metric_amount("open_payable")

        customer_invoice = self._create_invoice(
            move_type="out_invoice",
            partner_id=self.customer,
            currency_id=self.foreign_currency,
            pricelist_id=self.foreign_currency_pricelist.id,
            post=True,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product, price_unit=100.0)
            ],
        )
        vendor_bill = self._create_posted_vendor_bill(
            partner_id=self.partner_a,
            currency_id=self.foreign_currency,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=80.0)
            ],
        )

        report = self._metric_map()

        self.assertNotEqual(
            customer_invoice.amount_residual,
            -customer_invoice.amount_residual_signed,
        )
        self.assertNotEqual(
            vendor_bill.amount_residual,
            vendor_bill.amount_residual_signed,
        )
        self.assertEqual(
            report["open_receivable"].total_amount - before_receivable,
            customer_invoice.amount_residual_signed,
        )
        self.assertEqual(
            report["open_payable"].total_amount - before_payable,
            vendor_bill.amount_residual_signed,
        )

    def test_company_report_exposes_required_owner_facing_kpis(self):
        ready_order = self._create_ready_sale_order()
        overdue_invoice = self._create_invoice(
            move_type="out_invoice",
            partner_id=self.customer,
            post=True,
            invoice_date="2026-10-01",
            date="2026-10-01",
            invoice_date_due="2026-10-06",
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product, price_unit=210.0)
            ],
        )
        due_bill = self._create_posted_vendor_bill(
            partner_id=self.partner_a,
            invoice_date="2026-10-07",
            date="2026-10-07",
            invoice_date_due="2026-10-07",
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=80.0)
            ],
        )
        cash_application_invoice = self._create_invoice(
            move_type="out_invoice",
            partner_id=self.customer,
            post=True,
            invoice_date="2026-10-07",
            date="2026-10-07",
            invoice_date_due="2026-10-07",
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product, price_unit=50.0)
            ],
        )
        self._register_payment(
            cash_application_invoice,
            amount=cash_application_invoice.amount_total / 2,
        )

        ready_order = self._fresh_sale_order(ready_order)
        report = self._metric_map()

        self.assertTrue(self.KPI_KEYS.issubset(set(report)))
        self.assertEqual(report["billable_backlog"].total_amount, ready_order.amount_to_invoice)
        self.assertEqual(report["open_receivable"].total_amount, overdue_invoice.amount_residual_signed + cash_application_invoice.amount_residual_signed)
        self.assertEqual(
            report["overdue_receivable"].total_amount,
            overdue_invoice.amount_residual_signed
            + cash_application_invoice.amount_residual_signed,
        )
        self.assertEqual(report["open_payable"].total_amount, due_bill.amount_residual_signed)
        self.assertEqual(report["due_payable"].total_amount, due_bill.amount_residual_signed)
        self.assertEqual(report["cash_application_status"].item_count, 1)
        self.assertGreater(report["unreconciled_customer_items"].item_count, 0)
        self.assertGreater(report["unreconciled_vendor_items"].item_count, 0)

    def test_overdue_receivable_includes_residual_exposure_for_partial_in_payment_and_blocked(self):
        before_amount = self._metric_amount("overdue_receivable")
        before_count = self._metric_count("overdue_receivable")

        partial_invoice = self._create_invoice(
            move_type="out_invoice",
            partner_id=self.customer,
            post=True,
            invoice_date="2026-10-01",
            date="2026-10-01",
            invoice_date_due="2026-10-06",
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product, price_unit=120.0)
            ],
        )
        self._register_payment(partial_invoice, amount=partial_invoice.amount_total / 2)

        in_payment_invoice = self._create_invoice(
            move_type="out_invoice",
            partner_id=self.customer,
            post=True,
            invoice_date="2026-10-01",
            date="2026-10-01",
            invoice_date_due="2026-10-06",
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product, price_unit=150.0)
            ],
        )
        self._force_payment_state(in_payment_invoice, "in_payment")

        blocked_invoice = self._create_invoice(
            move_type="out_invoice",
            partner_id=self.customer,
            post=True,
            invoice_date="2026-10-01",
            date="2026-10-01",
            invoice_date_due="2026-10-06",
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product, price_unit=180.0)
            ],
        )
        self._register_payment(blocked_invoice, amount=blocked_invoice.amount_total / 2)
        blocked_invoice.action_toggle_block_payment()

        report = self._metric_map_without_payment_state_flush()

        self.assertEqual(partial_invoice.payment_state, "partial")
        self.assertEqual(self._stored_payment_state(in_payment_invoice), "in_payment")
        self.assertEqual(blocked_invoice.payment_state, "blocked")
        self.assertEqual(
            report["overdue_receivable"].total_amount - before_amount,
            partial_invoice.amount_residual_signed
            + in_payment_invoice.amount_residual_signed
            + blocked_invoice.amount_residual_signed,
        )
        self.assertEqual(
            report["overdue_receivable"].item_count - before_count,
            3,
        )

    def test_due_payable_includes_residual_exposure_for_partial_in_payment_and_blocked(self):
        before_amount = self._metric_amount("due_payable")
        before_count = self._metric_count("due_payable")

        partial_bill = self._create_posted_vendor_bill(
            partner_id=self.partner_a,
            invoice_date="2026-10-07",
            date="2026-10-07",
            invoice_date_due="2026-10-07",
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=80.0)
            ],
        )
        self._register_payment(partial_bill, amount=partial_bill.amount_total / 2)

        in_payment_bill = self._create_posted_vendor_bill(
            partner_id=self.partner_a,
            invoice_date="2026-10-07",
            date="2026-10-07",
            invoice_date_due="2026-10-07",
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=90.0)
            ],
        )
        self._force_payment_state(in_payment_bill, "in_payment")

        blocked_bill = self._create_posted_vendor_bill(
            partner_id=self.partner_a,
            invoice_date="2026-10-07",
            date="2026-10-07",
            invoice_date_due="2026-10-07",
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=100.0)
            ],
        )
        self._register_payment(blocked_bill, amount=blocked_bill.amount_total / 2)
        blocked_bill.action_toggle_block_payment()

        report = self._metric_map_without_payment_state_flush()

        self.assertEqual(partial_bill.payment_state, "partial")
        self.assertEqual(self._stored_payment_state(in_payment_bill), "in_payment")
        self.assertEqual(blocked_bill.payment_state, "blocked")
        self.assertEqual(
            report["due_payable"].total_amount - before_amount,
            partial_bill.amount_residual_signed
            + in_payment_bill.amount_residual_signed
            + blocked_bill.amount_residual_signed,
        )
        self.assertEqual(
            report["due_payable"].item_count - before_count,
            3,
        )

    def test_company_report_visibility_is_limited_to_allowed_companies(self):
        self._create_ready_sale_order()
        self._create_ready_sale_order(company=self.company_2)

        visible_rows = self._metric_rows(
            user=self.account_user,
            allowed_company_ids=self.account_user.company_ids.ids,
        )

        self.assertTrue(visible_rows)
        self.assertEqual(set(visible_rows.mapped("metric_key")), self.KPI_KEYS)
        self.assertNotIn(self.company_2, visible_rows.mapped("company_id"))
        self.assertFalse(
            self._metric_rows(
                company=self.company_2,
                user=self.account_user,
                allowed_company_ids=self.account_user.company_ids.ids,
            )
        )
