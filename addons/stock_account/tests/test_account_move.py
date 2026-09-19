from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.stock_account.tests.common import TestStockValuationCommon


@tagged("post_install", "-at_install")
class TestAccountMove(TestStockValuationCommon):
    def test_standard_perpetual_01_mc_01(self):
        product = self.product_standard_auto
        self._use_multi_currencies([("2017-01-01", 2.0)])
        rate = self.other_currency.rate_ids.rate

        move_form = Form(
            self.env["account.move"].with_context(default_move_type="out_invoice")
        )
        move_form.partner_id = self.partner
        move_form.currency_id = self.other_currency
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = product
            line_form.tax_ids.clear()
        invoice = move_form.save()

        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_total)
        self.assertEqual(len(invoice.mapped("line_ids")), 2)
        self.assertEqual(len(invoice.mapped("line_ids.currency_id")), 1)

        invoice._post()

        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_total)
        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_residual)
        self.assertEqual(len(invoice.mapped("line_ids")), 4)
        self.assertEqual(
            len(
                invoice.mapped("line_ids").filtered(lambda l: l.display_type == "cogs")
            ),
            2,
        )
        self.assertEqual(len(invoice.mapped("line_ids.currency_id")), 2)

    def test_fifo_perpetual_01_mc_01(self):
        product = self.product_fifo_auto
        self._use_multi_currencies([("2017-01-01", 2.0)])
        rate = self.other_currency.rate_ids.rate

        move_form = Form(
            self.env["account.move"].with_context(default_move_type="out_invoice")
        )
        move_form.partner_id = self.partner
        move_form.currency_id = self.other_currency
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = product
            line_form.tax_ids.clear()
        invoice = move_form.save()

        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_total)
        self.assertEqual(len(invoice.mapped("line_ids")), 2)
        self.assertEqual(len(invoice.mapped("line_ids.currency_id")), 1)

        invoice._post()
        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_total)
        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_residual)
        self.assertEqual(len(invoice.mapped("line_ids")), 4)
        self.assertEqual(
            len(
                invoice.mapped("line_ids").filtered(lambda l: l.display_type == "cogs")
            ),
            2,
        )
        self.assertEqual(len(invoice.mapped("line_ids.currency_id")), 2)

    def test_average_perpetual_01_mc_01(self):
        product = self.product_avco_auto
        self._use_multi_currencies([("2017-01-01", 2.0)])
        rate = self.other_currency.rate_ids.rate

        move_form = Form(
            self.env["account.move"].with_context(default_move_type="out_invoice")
        )
        move_form.partner_id = self.partner
        move_form.currency_id = self.other_currency
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = product
            line_form.tax_ids.clear()
        invoice = move_form.save()

        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_total)
        self.assertEqual(len(invoice.mapped("line_ids")), 2)
        self.assertEqual(len(invoice.mapped("line_ids.currency_id")), 1)

        invoice._post()

        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_total)
        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_residual)
        self.assertEqual(len(invoice.mapped("line_ids")), 4)
        self.assertEqual(
            len(
                invoice.mapped("line_ids").filtered(lambda l: l.display_type == "cogs")
            ),
            2,
        )
        self.assertEqual(len(invoice.mapped("line_ids.currency_id")), 2)

    def test_storno_accounting(self):
        self._use_multi_currencies([("2017-01-01", 2.0)])

        product = self.product_standard_auto
        self.env.company.account_config_id.account_storno = True
        self.env.company.account_config_id.anglo_saxon_accounting = True

        move = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "invoice_date": fields.Date.from_string("2019-01-01"),
                "partner_id": self.partner.id,
                "currency_id": self.other_currency.id,
                "invoice_line_ids": [
                    (0, None, {"product_id": product.id}),
                ],
            }
        )
        move.action_post()

        stock_output_line = move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        self.assertEqual(stock_output_line.debit, 0)
        self.assertEqual(stock_output_line.credit, -10)

        expense_line = move.line_ids.filtered(
            lambda l: l.account_id == product._get_product_accounts()["expense"]
        )
        self.assertEqual(expense_line.debit, -10)
        self.assertEqual(expense_line.credit, 0)

    def test_standard_manual_tax_edit(self):
        product = self.product_standard_auto
        product.lst_price = 100
        move_form = Form(
            self.env["account.move"].with_context(default_move_type="out_invoice")
        )
        move_form.partner_id = self.partner
        self.company.account_config_id.income_account_id.write(
            {
                "tax_ids": [
                    (6, 0, [self.env.company.account_config_id.account_sale_tax_id.id])
                ]
            }
        )
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = product
        invoice = move_form.save()

        self.assertEqual(invoice.amount_total, 115)
        self.assertEqual(invoice.amount_untaxed, 100)
        self.assertEqual(invoice.amount_tax, 15)

        tax_totals = invoice.tax_totals
        tax_totals["subtotals"][0]["tax_groups"][0]["tax_amount_currency"] = 14.0
        invoice.tax_totals = tax_totals

        self.assertEqual(len(invoice.mapped("line_ids")), 3)
        self.assertEqual(invoice.amount_total, 114)
        self.assertEqual(invoice.amount_untaxed, 100)
        self.assertEqual(invoice.amount_tax, 14)

        invoice._post()

        self.assertEqual(len(invoice.mapped("line_ids")), 5)
        self.assertEqual(invoice.amount_total, 114)
        self.assertEqual(invoice.amount_untaxed, 100)
        self.assertEqual(invoice.amount_tax, 14)

    def test_basic_bill(self):
        self.env.user.company_ids |= self.other_company

        for company in self.company | self.other_company:
            bill_form = Form(
                self.env["account.move"]
                .with_company(company.id)
                .with_context(default_move_type="in_invoice")
            )
            bill_form.partner_id = self.partner
            bill_form.invoice_date = fields.Date.today()
            with bill_form.invoice_line_ids.new() as line:
                line.product_id = self.product_standard
                line.price_unit = 100
            bill = bill_form.save()
            bill.action_post()

            product_accounts = self.product_standard.product_tmpl_id.with_company(
                company.id
            )._get_product_accounts()
            self.assertEqual(
                bill.invoice_line_ids.account_id, product_accounts["expense"]
            )

    def test_cogs_analytic_accounting(self):
        product = self.product_standard_auto
        default_plan = self.env["account.analytic.plan"].create(
            {
                "name": "Default",
            }
        )
        analytic_account = self.env["account.analytic.account"].create(
            {
                "name": "Account 1",
                "plan_id": default_plan.id,
                "company_id": False,
            }
        )

        move = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "invoice_date": fields.Date.from_string("2019-01-01"),
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "analytic_distribution": {
                                analytic_account.id: 100,
                            },
                        }
                    ),
                ],
            }
        )
        move.action_post()

        cogs_line = move.line_ids.filtered(
            lambda l: l.account_id == product._get_product_accounts()["expense"]
        )
        self.assertEqual(
            cogs_line.analytic_distribution, {str(analytic_account.id): 100}
        )

    def test_cogs_account_branch_company(self):
        product = self.product_standard_auto
        branch = self.branch
        test_account = (
            self.env["account.account"]
            .with_company(branch.id)
            .create(
                {
                    "name": "STCK Test Account",
                    "code": "100119",
                    "reconcile": True,
                    "account_type": "asset_current",
                }
            )
        )
        self.category_standard_auto.with_company(
            branch.id
        ).property_valuation = "real_time"
        self.category_standard_auto.with_company(
            branch.id
        ).property_stock_valuation_account_id = test_account

        bill = (
            self.env["account.move"]
            .with_company(branch.id)
            .with_context(default_move_type="in_invoice")
            .create(
                {
                    "partner_id": self.partner.id,
                    "invoice_date": fields.Date.today(),
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": product.id,
                                "price_unit": 100,
                            }
                        ),
                    ],
                }
            )
        )
        self.assertEqual(bill.invoice_line_ids.account_id, test_account)

    def test_apply_inventory_adjustment_on_multiple_quants_simultaneously(self):
        product = self.product_standard_auto
        product_b = product.copy()
        products = product + product_b

        self._use_inventory_location_accounting()

        self.env["stock.quant"]._update_available_quantity(
            product, self.stock_location, 5
        )
        self.env["stock.quant"]._update_available_quantity(
            product_b, self.stock_location, 15
        )

        quants = products.stock_quant_ids
        quants.inventory_quantity = 10.0
        wizard = self.env["stock.inventory.adjustment.name"].create(
            {"quant_ids": quants}
        )
        wizard.action_apply()
        inv_adjustment_journal_items = self.env["account.move.line"].search(
            [("product_id", "in", products.ids)], order="id asc", limit=4
        )
        prod_a_accounts = product.product_tmpl_id._get_product_accounts()
        prod_b_accounts = product_b.product_tmpl_id._get_product_accounts()
        self.assertRecordValues(
            inv_adjustment_journal_items,
            [
                {"account_id": self.account_inventory.id, "product_id": product.id},
                {
                    "account_id": prod_a_accounts["stock_valuation"].id,
                    "product_id": product.id,
                },
                {
                    "account_id": prod_b_accounts["stock_valuation"].id,
                    "product_id": product_b.id,
                },
                {"account_id": self.account_inventory.id, "product_id": product_b.id},
            ],
        )

    @freeze_time("2020-01-22")
    def test_backdate_picking_with_lock_date(self):
        self.env["account.lock_exception"].search([]).sudo().unlink()
        lock_date = fields.Date.from_string("2011-01-01")
        prior_to_lock_date = fields.Datetime.add(lock_date, days=-1)
        post_to_lock_date = fields.Datetime.add(lock_date, days=+1)
        self.env["stock.quant"]._update_available_quantity(
            self.product_standard, self.stock_location, 10
        )
        receipts = receipt, receipt_done = self.env["stock.picking"].create(
            [
                {
                    "location_id": self.supplier_location.id,
                    "location_dest_id": self.stock_location.id,
                    "picking_type_id": self.picking_type_in.id,
                    "owner_id": self.env.company.partner_id.id,
                    "move_ids": [
                        Command.create(
                            {
                                "product_id": self.product_standard.id,
                                "location_id": self.supplier_location.id,
                                "location_dest_id": self.stock_location.id,
                                "product_uom_qty": 1.0,
                            }
                        )
                    ],
                }
                for _ in range(2)
            ]
        )
        receipts.action_confirm()
        receipt_done.button_validate()
        self.env.company.account_config_id.write(
            {
                "sale_lock_date": lock_date,
                "purchase_lock_date": lock_date,
                "tax_lock_date": lock_date,
            }
        )
        receipt.date_planned = prior_to_lock_date
        receipt_done.date_done = prior_to_lock_date

        self.env.company.account_config_id.write(
            {
                "sale_lock_date": False,
                "purchase_lock_date": False,
                "tax_lock_date": False,
                "fiscalyear_lock_date": lock_date,
            }
        )
        receipt.date_planned = post_to_lock_date
        receipt_done.date_done = post_to_lock_date
        receipt.date_planned = prior_to_lock_date
        with self.assertRaises(UserError):
            receipt_done.date_done = prior_to_lock_date

        self.env.company.account_config_id.write(
            {
                "fiscalyear_lock_date": False,
                "hard_lock_date": lock_date,
            }
        )
        receipt.date_planned = post_to_lock_date
        receipt_done.date_done = post_to_lock_date
        receipt.date_planned = prior_to_lock_date
        with self.assertRaises(UserError):
            receipt_done.date_done = prior_to_lock_date

    def test_invoice_with_journal_item_without_label(self):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_standard.id,
                            "name": False,
                        }
                    ),
                ],
            }
        )
        move.action_post()
        self.assertFalse(move.invoice_line_ids.name)
        self.assertEqual(move.state, "posted")
