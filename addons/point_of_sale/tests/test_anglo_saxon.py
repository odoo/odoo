from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestAngloSaxonCommon(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref("point_of_sale.group_pos_manager")
        cls.PosMakePayment = cls.env["pos.make.payment"]
        cls.PosOrder = cls.env["pos.order"]
        cls.Statement = cls.env["account.bank.statement"]
        cls.company = cls.env.company
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.partner = cls.env["res.partner"].create({"name": "Partner 1"})
        cls.category = cls.env.ref("product.product_category_services")
        cls.category = cls.category.copy(
            {"name": "New category", "property_valuation": "real_time"}
        )
        cls.account = cls.env["account.account"].create(
            {
                "name": "Receivable",
                "code": "RCV00",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        account_expense = cls.env["account.account"].create(
            {
                "name": "Expense",
                "code": "EXP00",
                "account_type": "expense",
                "reconcile": True,
            }
        )
        account_income = cls.env["account.account"].create(
            {
                "name": "Income",
                "code": "INC00",
                "account_type": "income",
                "reconcile": True,
            }
        )
        account_valuation = cls.env["account.account"].create(
            {
                "name": "Valuation",
                "code": "STV00",
                "account_type": "expense",
                "reconcile": True,
            }
        )
        cls.partner.property_account_receivable_id = cls.account
        cls.category.property_account_income_categ_id = account_income
        cls.category.property_account_expense_categ_id = account_expense
        cls.category.property_stock_valuation_account_id = account_valuation
        cls.category.property_stock_journal = cls.env["account.journal"].create(
            {"name": "Stock journal", "type": "sale", "code": "STK00"}
        )
        cls.cash_journal = cls.env["account.journal"].create(
            {"name": "CASH journal", "type": "cash", "code": "CSH02"}
        )
        cls.cash_payment_method = cls.env["pos.payment.method"].create(
            {
                "name": "Cash Test",
                "journal_id": cls.cash_journal.id,
            }
        )
        cls.pos_config = cls.env["pos.config"].create(
            {
                "name": "New POS config",
                "payment_method_ids": cls.cash_payment_method,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "New product",
                "standard_price": 100,
                "available_in_pos": True,
                "is_storable": True,
            }
        )
        cls.company.account_config_id.anglo_saxon_accounting = True
        cls.company.point_of_sale_update_stock_quantities = "real"
        cls.product.categ_id = cls.category
        cls.product.property_account_expense_id = account_expense
        cls.product.property_account_income_id = account_income
        sale_journal = cls.env["account.journal"].create(
            {"name": "POS journal", "type": "sale", "code": "POS00"}
        )
        cls.pos_config.journal_id = sale_journal
        cls.cash_journal = cls.env["account.journal"].create(
            {"name": "CASH journal", "type": "cash", "code": "CSH00"}
        )
        cls.sale_journal = cls.env["account.journal"].create(
            {"name": "SALE journal", "type": "sale", "code": "INV00"}
        )
        cls.pos_config.invoice_journal_id = cls.sale_journal
        cls.cash_payment_method = cls.env["pos.payment.method"].create(
            {
                "name": "Cash Test",
                "journal_id": cls.cash_journal.id,
                "receivable_account_id": cls.account.id,
            }
        )
        cls.pos_config.write(
            {"payment_method_ids": [(6, 0, cls.cash_payment_method.ids)]}
        )


@tagged("post_install", "-at_install")
class TestAngloSaxonFlow(TestAngloSaxonCommon):
    def _enable_delivery_time_cogs(self):
        self.env.ref(
            "stock.stock_location_customers"
        ).valuation_account_id = self.category.property_account_expense_categ_id

    def test_create_account_move_line(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        self.cash_journal.loss_account_id = self.account
        current_session.set_opening_control(0, None)

        self.pos_order_pos0 = self.PosOrder.create(
            {
                "company_id": self.company.id,
                "partner_id": self.partner.id,
                "pricelist_id": self.company.partner_id.property_product_pricelist.id,
                "session_id": self.pos_config.current_session_id.id,
                "lines": [
                    (
                        0,
                        0,
                        {
                            "name": "OL/0001",
                            "product_id": self.product.id,
                            "price_unit": 450,
                            "discount": 0.0,
                            "qty": 1.0,
                            "price_subtotal": 450,
                            "price_subtotal_incl": 450,
                        },
                    )
                ],
                "amount_total": 450,
                "amount_tax": 0,
                "amount_paid": 0,
                "amount_return": 0,
                "last_order_preparation_change": "{}",
            }
        )

        context_make_payment = {
            "active_ids": [self.pos_order_pos0.id],
            "active_id": self.pos_order_pos0.id,
        }
        self.pos_make_payment_0 = self.PosMakePayment.with_context(
            context_make_payment
        ).create(
            {
                "amount": 450.0,
                "payment_method_id": self.cash_payment_method.id,
            }
        )

        context_payment = {"active_id": self.pos_order_pos0.id}
        self.pos_make_payment_0.with_context(context_payment).action_make_payment()

        self.assertEqual(
            self.pos_order_pos0.state, "paid", "Order should be in paid state."
        )
        self.assertEqual(
            self.pos_order_pos0.amount_paid,
            450,
            "Amount paid for the order should be updated.",
        )

        current_session_id = self.pos_config.current_session_id
        current_session_id.update_closing_cash_details(450.0)
        current_session_id.close_session_from_ui()
        self.assertEqual(
            current_session_id.state, "closed", "Check that session is closed"
        )

        self.assertFalse(
            self.pos_order_pos0.account_move, "There should be no invoice in the order."
        )

        expense_account = self.category.property_account_expense_categ_id
        valuation_account = self.category.property_stock_valuation_account_id
        aml = current_session.move_id.line_ids
        aml_output = aml.filtered(lambda l: l.account_id.id == valuation_account.id)
        aml_expense = aml.filtered(lambda l: l.account_id.id == expense_account.id)
        self.assertEqual(
            aml_output.credit,
            self.product.standard_price,
            "Cost of Good Sold entry missing or mismatching",
        )
        self.assertEqual(
            aml_expense.debit,
            self.product.standard_price,
            "Cost of Good Sold entry missing or mismatching",
        )

    def _prepare_pos_order(self):
        self.product.categ_id.property_cost_method = "fifo"
        self.product.standard_price = 5.0
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": self.product.id,
                "inventory_quantity": 5.0,
                "location_id": self.warehouse.lot_stock_id.id,
            }
        ).action_apply_inventory()
        self.product.standard_price = 1.0
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": self.product.id,
                "inventory_quantity": 10.0,
                "location_id": self.warehouse.lot_stock_id.id,
            }
        ).action_apply_inventory()
        self.assertEqual(
            self.product.total_value, 30, "Value should be (5*5 + 5*1) = 30"
        )
        self.assertEqual(self.product.qty_available_virtual, 10)

        self.pos_config.open_ui()
        pos_session = self.pos_config.current_session_id
        pos_session.set_opening_control(0, None)

        pos_order_values = {
            "company_id": self.company.id,
            "partner_id": self.partner.id,
            "pricelist_id": self.company.partner_id.property_product_pricelist.id,
            "session_id": self.pos_config.current_session_id.id,
            "lines": [
                (
                    0,
                    0,
                    {
                        "name": "OL/0001",
                        "product_id": self.product.id,
                        "price_unit": 450,
                        "discount": 0.0,
                        "qty": 7.0,
                        "price_subtotal": 7 * 450,
                        "price_subtotal_incl": 7 * 450,
                    },
                )
            ],
            "amount_total": 7 * 450,
            "amount_tax": 0,
            "amount_paid": 0,
            "amount_return": 0,
            "last_order_preparation_change": "{}",
        }

        return self.PosOrder.create(pos_order_values)

    def test_fifo_valuation_no_invoice(self):
        pos_order_pos0 = self._prepare_pos_order()
        context_make_payment = {
            "active_ids": [pos_order_pos0.id],
            "active_id": pos_order_pos0.id,
        }
        self.pos_make_payment_0 = self.PosMakePayment.with_context(
            context_make_payment
        ).create(
            {
                "amount": 7 * 450.0,
                "payment_method_id": self.cash_payment_method.id,
            }
        )

        context_payment = {"active_id": pos_order_pos0.id}
        self.pos_make_payment_0.with_context(context_payment).action_make_payment()

        current_session_id = self.pos_config.current_session_id
        current_session_id.update_closing_cash_details(7 * 450.0)
        current_session_id.close_session_from_ui()

        session_move = pos_order_pos0.session_id.move_id
        line = session_move.line_ids.filtered(
            lambda l: (
                l.debit
                and l.account_id == self.category.property_account_expense_categ_id
            )
        )
        self.assertEqual(session_move.journal_id, self.pos_config.journal_id)
        self.assertEqual(
            line.debit,
            27,
            "As it is a fifo product, the move's value should be 5*5 + 2*1",
        )

    def test_fifo_valuation_with_invoice(self):
        pos_order_pos0 = self._prepare_pos_order()
        context_make_payment = {
            "active_ids": [pos_order_pos0.id],
            "active_id": pos_order_pos0.id,
        }
        self.pos_make_payment_0 = self.PosMakePayment.with_context(
            context_make_payment
        ).create(
            {
                "amount": 7 * 450.0,
                "payment_method_id": self.cash_payment_method.id,
            }
        )

        context_payment = {"active_id": pos_order_pos0.id}
        self.pos_make_payment_0.with_context(context_payment).action_make_payment()

        pos_order_pos0.action_pos_order_invoice()

        line = pos_order_pos0.account_move.line_ids.filtered(
            lambda l: (
                l.debit
                and l.account_id == self.category.property_account_expense_categ_id
            )
        )
        self.assertEqual(
            pos_order_pos0.account_move.journal_id, self.pos_config.invoice_journal_id
        )
        self.assertEqual(
            line.debit,
            27,
            "As it is a fifo product, the move's value should be 5*5 + 2*1",
        )

    def test_cogs_with_ship_later_no_invoicing(self):
        self._enable_delivery_time_cogs()
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        self.cash_journal.loss_account_id = self.account
        current_session.set_opening_control(0, None)

        self.warehouse.delivery_steps = "pick_ship"

        self.pos_order_pos0 = self.PosOrder.create(
            {
                "company_id": self.company.id,
                "partner_id": self.partner.id,
                "pricelist_id": self.company.partner_id.property_product_pricelist.id,
                "session_id": self.pos_config.current_session_id.id,
                "to_invoice": False,
                "shipping_date": "2023-01-01",
                "lines": [
                    (
                        0,
                        0,
                        {
                            "name": "OL/0001",
                            "product_id": self.product.id,
                            "price_unit": 450,
                            "discount": 0.0,
                            "qty": 1.0,
                            "price_subtotal": 450,
                            "price_subtotal_incl": 450,
                        },
                    )
                ],
                "amount_total": 450,
                "amount_tax": 0,
                "amount_paid": 0,
                "amount_return": 0,
                "last_order_preparation_change": "{}",
            }
        )

        context_make_payment = {
            "active_ids": [self.pos_order_pos0.id],
            "active_id": self.pos_order_pos0.id,
        }
        self.pos_make_payment_0 = self.PosMakePayment.with_context(
            context_make_payment
        ).create(
            {
                "amount": 450.0,
                "payment_method_id": self.cash_payment_method.id,
            }
        )

        context_payment = {"active_id": self.pos_order_pos0.id}
        self.pos_make_payment_0.with_context(context_payment).action_make_payment()

        current_session_id = self.pos_config.current_session_id
        current_session_id.update_closing_cash_details(450.0)
        current_session_id.close_session_from_ui()
        self.assertEqual(
            current_session_id.state, "closed", "Check that session is closed"
        )

        self.assertEqual(
            len(current_session.picking_ids), 1, "There should be 2 pickings"
        )
        current_session.picking_ids.move_ids.write({"quantity": 1, "picked": True})
        current_session.picking_ids.button_validate()
        self.assertEqual(
            len(current_session.picking_ids), 2, "There should be 2 pickings"
        )
        current_session.picking_ids.button_validate()

        valuation_account = self.category.property_stock_valuation_account_id
        expense_account = self.category.property_account_expense_categ_id
        aml = current_session._get_related_account_moves().line_ids
        aml_valuation = aml.filtered(lambda l: l.account_id.id == valuation_account.id)
        aml_expense = aml.filtered(lambda l: l.account_id.id == expense_account.id)

        self.assertEqual(len(aml_valuation), 1)
        self.assertEqual(len(aml_expense), 1)
        self.assertEqual(
            aml_valuation.move_id.journal_id,
            self.category.property_stock_journal,
            "The COGS entry is posted in the product category's stock journal",
        )
        self.assertEqual(aml_valuation.move_id, aml_expense.move_id)
        self.assertFalse(
            (aml_valuation | aml_expense).move_id & current_session.move_id,
        )

        self.assertEqual(
            aml_valuation.credit,
            self.product.standard_price,
            "Cost of Good Sold entry missing or mismatching",
        )
        self.assertEqual(
            aml_valuation.debit, 0.0, "Cost of Good Sold entry missing or mismatching"
        )
        self.assertEqual(
            aml_expense.debit,
            self.product.standard_price,
            "Cost of Good Sold entry missing or mismatching",
        )
        self.assertEqual(
            aml_expense.credit, 0.0, "Cost of Good Sold entry missing or mismatching"
        )

    def test_action_pos_order_invoice(self):
        self.company.point_of_sale_update_stock_quantities = "closing"

        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        self.pos_order_pos0 = self.PosOrder.create(
            {
                "company_id": self.company.id,
                "partner_id": self.partner.id,
                "session_id": self.pos_config.current_session_id.id,
                "lines": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "price_unit": 450,
                            "qty": 1.0,
                            "price_subtotal": 450,
                            "price_subtotal_incl": 450,
                        },
                    )
                ],
                "amount_total": 450,
                "amount_tax": 0,
                "amount_paid": 0,
                "amount_return": 0,
            }
        )
        context_make_payment = {
            "active_ids": [self.pos_order_pos0.id],
            "active_id": self.pos_order_pos0.id,
        }
        self.pos_make_payment_0 = self.PosMakePayment.with_context(
            context_make_payment
        ).create(
            {
                "amount": 450.0,
                "payment_method_id": self.cash_payment_method.id,
            }
        )
        context_payment = {"active_id": self.pos_order_pos0.id}
        self.pos_make_payment_0.with_context(context_payment).action_make_payment()

        self.pos_order_pos0.action_pos_order_invoice()

        valuation_account = self.category.property_stock_valuation_account_id
        expense_account = self.category.property_account_expense_categ_id
        related_amls = current_session._get_related_account_moves().line_ids
        valuation_amls = related_amls.filtered_domain(
            [("account_id", "=", valuation_account.id)]
        )
        expense_amls = related_amls.filtered_domain(
            [("account_id", "=", expense_account.id)]
        )

        self.assertEqual(len(valuation_amls), 1)
        self.assertEqual(valuation_amls.move_id, self.pos_order_pos0.account_move)
        self.assertEqual(valuation_amls.credit, self.product.standard_price)
        self.assertEqual(valuation_amls.debit, 0.0)
        self.assertEqual(len(expense_amls), 1)
        self.assertEqual(expense_amls.debit, self.product.standard_price)
        self.assertEqual(expense_amls.credit, 0.0)

    def test_action_pos_order_invoice_with_discount(self):

        self.pos_config.open_ui()
        pricelist = self.env["product.pricelist"].create(
            {
                "name": "Test Pricelist",
                "item_ids": [
                    Command.create(
                        {
                            "compute_price": "percentage",
                            "percent_price": "5.0",
                            "min_quantity": 0,
                            "applied_on": "3_global",
                        }
                    )
                ],
            }
        )
        self.product.lst_price = 100
        self.pos_order_pos0 = self.PosOrder.create(
            {
                "company_id": self.company.id,
                "partner_id": self.partner.id,
                "session_id": self.pos_config.current_session_id.id,
                "pricelist_id": pricelist.id,
                "lines": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "price_unit": 95,
                            "qty": 1.0,
                            "tax_ids": [(6, 0, self.tax_purchase_a.ids)],
                            "price_subtotal": 90.25,
                            "price_subtotal_incl": 103.79,
                            "discount": 5,
                        },
                    )
                ],
                "amount_total": 103.79,
                "amount_tax": 13.51,
                "amount_paid": 0,
                "amount_return": 0,
                "to_invoice": True,
            }
        )
        context_make_payment = {
            "active_ids": [self.pos_order_pos0.id],
            "active_id": self.pos_order_pos0.id,
        }
        self.pos_make_payment_0 = self.PosMakePayment.with_context(
            context_make_payment
        ).create(
            {
                "amount": 103.79,
                "payment_method_id": self.cash_payment_method.id,
            }
        )
        context_payment = {"active_id": self.pos_order_pos0.id}
        self.pos_make_payment_0.with_context(context_payment).action_make_payment()
        self.assertIn(self.pos_order_pos0.state, ("paid", "done"))

        res = self.pos_order_pos0.action_pos_order_invoice()
        invoice = self.env["account.move"].browse(res["res_id"])
        self.assertTrue(
            "Price discount from 100.00 to 95.00"
            in invoice.invoice_line_ids.filtered(
                lambda l: l.display_type == "line_note"
            ).display_name
        )
        product_line = invoice.invoice_line_ids.filtered(
            lambda l: l.display_type == "product"
        )
        self.assertEqual(product_line.price_unit, 95)
        self.assertEqual(product_line.discount, 5)
        self.assertEqual(product_line.price_subtotal, 90.25)
        self.assertEqual(product_line.price_total, 103.79)

    def test_cogs_with_ship_later_with_backorder(self):
        self._enable_delivery_time_cogs()
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        self.cash_journal.loss_account_id = self.account
        current_session.set_opening_control(0, None)

        self.product_2 = self.env["product.product"].create(
            {
                "name": "New product 2",
                "standard_price": 20,
                "available_in_pos": True,
                "is_storable": True,
                "categ_id": self.category.id,
            }
        )

        self.product_1 = self.env["product.product"].create(
            {
                "name": "New product 1",
                "standard_price": 0,
                "available_in_pos": True,
                "is_storable": True,
                "categ_id": self.category.id,
            }
        )

        self.pos_order_pos0 = self.PosOrder.create(
            {
                "company_id": self.company.id,
                "partner_id": self.partner.id,
                "pricelist_id": self.company.partner_id.property_product_pricelist.id,
                "session_id": self.pos_config.current_session_id.id,
                "to_invoice": False,
                "shipping_date": "2023-01-01",
                "lines": [
                    (
                        0,
                        0,
                        {
                            "name": "OL/0001",
                            "product_id": self.product_1.id,
                            "price_unit": 100,
                            "discount": 0.0,
                            "qty": 1.0,
                            "price_subtotal": 100,
                            "price_subtotal_incl": 100,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "OL/0002",
                            "product_id": self.product_2.id,
                            "price_unit": 200,
                            "discount": 0.0,
                            "qty": 1.0,
                            "price_subtotal": 200,
                            "price_subtotal_incl": 200,
                        },
                    ),
                ],
                "amount_total": 300,
                "amount_tax": 0,
                "amount_paid": 0,
                "amount_return": 0,
                "last_order_preparation_change": "{}",
            }
        )

        context_make_payment = {
            "active_ids": [self.pos_order_pos0.id],
            "active_id": self.pos_order_pos0.id,
        }
        self.pos_make_payment_0 = self.PosMakePayment.with_context(
            context_make_payment
        ).create(
            {
                "amount": 300.0,
                "payment_method_id": self.cash_payment_method.id,
            }
        )

        context_payment = {"active_id": self.pos_order_pos0.id}
        self.pos_make_payment_0.with_context(context_payment).action_make_payment()

        current_session_id = self.pos_config.current_session_id
        current_session_id.update_closing_cash_details(300.0)
        current_session_id.close_session_from_ui()
        self.assertEqual(
            current_session_id.state, "closed", "Check that session is closed"
        )

        current_session.picking_ids.move_ids.filtered(
            lambda m: m.product_id == self.product_2
        ).write({"quantity": 1, "picked": True})
        res_dict = current_session.picking_ids.button_validate()
        self.env["stock.backorder.confirmation"].with_context(
            res_dict["context"]
        ).process()

        out = self.product_1.categ_id.property_stock_valuation_account_id
        exp = self.product_1._get_product_accounts()["expense"]
        cogs_journal = (
            self.product_1.categ_id.property_stock_journal
            or self.company.account_stock_journal_id
        )
        aml = current_session._get_related_account_moves().line_ids
        aml_output = aml.filtered(
            lambda l: l.account_id.id == out.id and l.journal_id == cogs_journal
        )
        aml_expense = aml.filtered(
            lambda l: l.account_id.id == exp.id and l.journal_id == cogs_journal
        )

        self.assertEqual(sum(aml_expense.mapped("debit")), 20)
        self.assertEqual(sum(aml_expense.mapped("credit")), 0)
        self.assertEqual(sum(aml_output.mapped("debit")), 0)
        self.assertEqual(sum(aml_output.mapped("credit")), 20)

        backorder_picking = current_session.picking_ids.filtered(
            lambda p: p.state == "confirmed"
        )
        backorder_picking.move_ids.write({"quantity": 1, "picked": True})
        backorder_picking.button_validate()

        aml = current_session._get_related_account_moves().line_ids
        aml_output = aml.filtered(
            lambda l: l.account_id.id == out.id and l.journal_id == cogs_journal
        )
        aml_expense = aml.filtered(
            lambda l: l.account_id.id == exp.id and l.journal_id == cogs_journal
        )

        self.assertEqual(sum(aml_expense.mapped("debit")), 20)
        self.assertEqual(sum(aml_expense.mapped("credit")), 0)
        self.assertEqual(sum(aml_output.mapped("debit")), 0)
        self.assertEqual(sum(aml_output.mapped("credit")), 20)

    def test_cogs_multi_products_perpetual(self):
        self.category.property_valuation = "real_time"
        self.product.write(
            {"categ_id": self.category, "standard_price": 20, "list_price": 100}
        )
        product2 = self.env["product.product"].create(
            {
                "name": "P2",
                "categ_id": self.category.id,
                "standard_price": 100,
                "list_price": 200,
                "available_in_pos": True,
                "is_storable": True,
            }
        )

        self.pos_config.open_ui()
        pos_session = self.pos_config.current_session_id
        pos_session.set_opening_control(0, None)

        pos_order_values = {
            "company_id": self.company.id,
            "partner_id": self.partner.id,
            "session_id": self.pos_config.current_session_id.id,
            "lines": [
                Command.create(
                    {
                        "product_id": self.product.id,
                        "price_unit": 100,
                        "discount": 0.0,
                        "qty": 1.0,
                        "price_subtotal": 100,
                        "price_subtotal_incl": 100,
                    }
                ),
                Command.create(
                    {
                        "product_id": product2.id,
                        "price_unit": 200,
                        "discount": 0.0,
                        "qty": 1.0,
                        "price_subtotal": 200,
                        "price_subtotal_incl": 200,
                    }
                ),
            ],
            "amount_total": 300,
            "amount_tax": 0,
            "amount_paid": 0,
            "amount_return": 0,
            "last_order_preparation_change": "{}",
            "to_invoice": True,
        }
        pos_order = self.PosOrder.create(pos_order_values)

        context_make_payment = {"active_ids": [pos_order.id], "active_id": pos_order.id}
        pos_payment = self.PosMakePayment.with_context(context_make_payment).create(
            {
                "amount": 300.0,
                "payment_method_id": self.cash_payment_method.id,
            }
        )
        context_payment = {"active_id": pos_order.id}
        pos_payment.with_context(context_payment).action_make_payment()

        valuation_account = self.category.property_stock_valuation_account_id
        valuation_lines = pos_order.account_move.line_ids.filtered(
            lambda line: line.account_id == valuation_account
        )

        self.assertRecordValues(
            valuation_lines.sorted(lambda aml: aml.product_id.id),
            [
                {"product_id": self.product.id, "credit": 20.0},
                {"product_id": product2.id, "credit": 100.0},
            ],
        )
