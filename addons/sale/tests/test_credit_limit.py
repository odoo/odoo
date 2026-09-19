from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import Form, tagged, users

from odoo.addons.sale.tests.common import TestSaleCommon


@tagged("post_install", "-at_install")
class TestSaleOrderCreditLimit(TestSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.account_config_id.account_use_credit_limit = True

        buck_currency = cls.env["res.currency"].create(
            {
                "name": "TB",
                "symbol": "TB",
            }
        )
        cls.env["res.currency.rate"].create(
            {
                "name": "2023-01-01",
                "rate": 2.0,
                "currency_id": buck_currency.id,
                "company_id": cls.env.company.id,
            }
        )

        cls.buck_pricelist = cls.env["product.pricelist"].create(
            {
                "name": "Test Buck Pricelist",
                "currency_id": buck_currency.id,
            }
        )

        cls.company_data_2 = cls.setup_other_company()

        cls.sales_user = cls.company_data["default_user_salesman"]
        cls.sales_user.write(
            {
                "login": "notaccountman",
                "email": "bad@accounting.com",
            }
        )

        cls.empty_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner_a.id,
            }
        )

    def test_credit_limit_multi_company(self):
        company2 = self.company_data_2["company"]

        company2.account_config_id.account_use_credit_limit = True

        sale_order = company2.env["sale.order"].create(
            {
                "company_id": company2.id,
                "partner_id": self.partner_a.id,
                "partner_invoice_id": self.partner_a.id,
                "partner_shipping_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.company_data_2["product_order_no"].id,
                            "price_unit": 1000.0,
                        }
                    )
                ],
            }
        )

        self.assertEqual(self.partner_a.with_company(company2).credit_to_invoice, 0.0)
        sale_order.action_confirm()

        self.partner_a.invalidate_recordset(["credit", "credit_to_invoice"])
        self.assertEqual(
            self.partner_a.with_company(company2).credit_to_invoice, 1000.0
        )
        partner_a_multi_company = self.partner_a.with_context(
            allowed_company_ids=[self.env.company.id, company2.id]
        )
        self.assertEqual(partner_a_multi_company.credit_to_invoice, 0.0)
        self.assertEqual(self.partner_a.credit_to_invoice, 0.0)

    def test_warning_on_invoice_with_downpayment(self):
        self.env.company.account_config_id.account_use_credit_limit = True
        self.partner_a.credit_limit = 1000.0

        sale_order = self.empty_order
        sale_order.write(
            {
                "line_ids": [
                    Command.create(
                        {
                            "name": self.company_data["product_order_no"].name,
                            "product_id": self.company_data["product_order_no"].id,
                            "product_qty": 1,
                            "price_unit": 1000.0,
                            "tax_ids": False,
                        }
                    )
                ]
            }
        )

        self.assertEqual(self.partner_a.credit, 0.0)
        self.assertEqual(self.partner_a.credit_to_invoice, 0.0)

        sale_order.action_confirm()
        self.partner_a.invalidate_recordset(["credit", "credit_to_invoice"])
        self.assertEqual(self.partner_a.credit, 0.0)
        self.assertEqual(self.partner_a.credit_to_invoice, 1000.0)

        self.env["sale.advance.payment.inv"].with_context(
            {
                "active_model": "sale.order",
                "active_ids": [sale_order.id],
                "active_id": sale_order.id,
                "default_journal_id": self.company_data["default_journal_sale"].id,
            }
        ).create(
            {
                "advance_payment_method": "percentage",
                "amount": 50,
            }
        ).create_invoices()

        invoice = sale_order.invoice_ids

        self.assertEqual(invoice.partner_credit_warning, "")

        invoice.invoice_line_ids.quantity = 3
        self.assertEqual(
            invoice.partner_credit_warning,
            "partner_a has reached its credit limit of: $\xa01,000.00\n"
            "Total amount due (including this document): $\xa01,500.00",
        )

        invoice.invoice_line_ids.quantity = 1
        invoice.action_post()

        self.env["account.move.reversal"].with_company(self.env.company).with_context(
            active_model="account.move",
            active_ids=invoice.ids,
        ).create(
            {
                "journal_id": invoice.journal_id.id,
            }
        ).reverse_moves()

        credit_note = sale_order.invoice_ids[1]
        credit_note.action_post()

        self.assertEqual(sale_order.amount_taxinc_to_invoice, sale_order.amount_total)

    def test_credit_limit_multicurrency(self):
        self.partner_a.credit_limit = 50

        self.assertRecordValues(
            self.partner_a,
            [
                {
                    "credit": 0.0,
                    "credit_to_invoice": 0.0,
                }
            ],
        )

        order = self.empty_order
        order.write(
            {
                "pricelist_id": self.buck_pricelist.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.company_data["product_order_no"].id,
                            "product_qty": 1,
                            "price_unit": 45.0,
                            "tax_ids": False,
                        }
                    )
                ],
            }
        )
        self.assertEqual(order.amount_total / order.currency_rate, 22.5)
        self.assertEqual(order.partner_credit_warning, "")

        order.write(
            {
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.company_data["product_order_no"].id,
                            "product_qty": 1,
                            "price_unit": 65.0,
                            "tax_ids": False,
                        }
                    )
                ],
            }
        )
        self.assertEqual(order.amount_total / order.currency_rate, 55)
        self.assertEqual(
            order.partner_credit_warning,
            "partner_a has reached its credit limit of: $\xa050.00\n"
            "Total amount due (including this document): $\xa055.00",
        )

        order.action_confirm()
        self.partner_a.invalidate_recordset(["credit", "credit_to_invoice"])
        self.assertRecordValues(
            self.partner_a,
            [
                {
                    "credit": 0.0,
                    "credit_to_invoice": 55.0,
                }
            ],
        )

        invoice = order._create_invoices(final=True)
        self.partner_a.invalidate_recordset(["credit", "credit_to_invoice"])
        self.assertEqual(
            invoice.partner_credit_warning,
            "partner_a has reached its credit limit of: $\xa050.00\n"
            "Total amount due (including this document): $\xa055.00",
        )

        invoice.action_post()
        self.partner_a.invalidate_recordset(["credit", "credit_to_invoice"])
        self.assertRecordValues(
            self.partner_a,
            [
                {
                    "credit": 55.0,
                    "credit_to_invoice": 0.0,
                }
            ],
        )

    def test_invoice_independent_of_credit_to_invoice(self):
        self.env.company.account_config_id.account_use_credit_limit = True
        self.partner_a.credit_limit = 1000.0

        sale_order = self.empty_order
        sale_order.write(
            {
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.company_data["product_order_no"].id,
                            "price_unit": 1000.0,
                        }
                    )
                ]
            }
        )

        self.assertRecordValues(
            self.partner_a,
            [
                {
                    "credit": 0.0,
                    "credit_to_invoice": 0.0,
                }
            ],
        )

        sale_order.action_confirm()
        self.partner_a.invalidate_recordset(["credit", "credit_to_invoice"])
        self.assertRecordValues(
            self.partner_a,
            [
                {
                    "credit": 0.0,
                    "credit_to_invoice": 1000.0,
                }
            ],
        )

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "test line",
                            "quantity": 1,
                            "price_unit": 100.0,
                            "tax_ids": False,
                        },
                    )
                ],
            }
        )
        self.assertRecordValues(
            self.partner_a,
            [
                {
                    "credit": 0.0,
                    "credit_to_invoice": 1000.0,
                }
            ],
        )

        self.assertEqual(
            invoice.partner_credit_warning,
            "partner_a has reached its credit limit of: $\xa01,000.00\n"
            "Total amount due (including sales orders and this document): $\xa01,100.00",
        )

        invoice.invoice_line_ids[0].price_unit = 2000
        self.assertEqual(
            invoice.partner_credit_warning,
            "partner_a has reached its credit limit of: $\xa01,000.00\n"
            "Total amount due (including sales orders and this document): $\xa03,000.00",
        )

        invoice.action_post()
        self.partner_a.invalidate_recordset(["credit", "credit_to_invoice"])
        self.assertRecordValues(
            self.partner_a,
            [
                {
                    "credit": 2000.0,
                    "credit_to_invoice": 1000.0,
                }
            ],
        )

    def test_credit_limit_and_warning_overinvoiced_sales_order(self):
        self.env.company.account_config_id.account_use_credit_limit = True
        self.partner_a.credit_limit = 1000.0

        self.empty_order.write(
            {
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.company_data["product_order_no"].id,
                            "price_unit": 1000.0,
                        }
                    )
                ]
            }
        )
        sale_orders = self.empty_order + self.empty_order.copy()

        self.assertRecordValues(
            self.partner_a,
            [
                {
                    "credit": 0.0,
                    "credit_to_invoice": 0.0,
                }
            ],
        )

        for order in sale_orders:
            order.action_confirm()

        self.partner_a.invalidate_recordset(["credit", "credit_to_invoice"])
        self.assertRecordValues(
            self.partner_a,
            [
                {
                    "credit": 0.0,
                    "credit_to_invoice": 2000.0,
                }
            ],
        )

        sale_order = sale_orders[0]
        self.assertEqual(sale_order.amount_taxinc_to_invoice, 1000.0)
        invoice = sale_order._create_invoices(final=True)
        self.partner_a.invalidate_recordset(["credit", "credit_to_invoice"])
        self.assertEqual(invoice.amount_total, 1000.0)
        invoice.invoice_line_ids[0].price_unit = 2000.0

        self.assertEqual(
            invoice.partner_credit_warning,
            "partner_a has reached its credit limit of: $\xa01,000.00\n"
            "Total amount due (including sales orders and this document): $\xa03,000.00",
        )

        invoice.action_post()
        self.partner_a.invalidate_recordset(["credit", "credit_to_invoice"])
        self.assertRecordValues(
            self.partner_a,
            [
                {
                    "credit": 2000.0,
                    "credit_to_invoice": 1000.0,
                }
            ],
        )

    @users("notaccountman")
    def test_credit_limit_access(self):
        self.empty_order.user_id = self.env.user
        order = self.empty_order.with_env(self.env)

        with self.assertRaises(AccessError, msg="We shouldn't have access to credit"):
            order.partner_id.credit_limit = 1e12
        order.sudo().partner_id.credit_limit = self.product_a.list_price

        with Form(order) as order_form:
            with order_form.line_ids.new() as sol:
                sol.product_id = self.product_a
                sol.tax_ids.clear()
            self.assertFalse(
                order_form.partner_credit_warning,
                "No credit warning should be displayed (yet)",
            )
            with order_form.line_ids.edit(0) as sol:
                sol.tax_ids.add(self.tax_sale_a)
            self.assertTrue(
                order_form.partner_credit_warning,
                "Credit warning should be displayed",
            )

    def test_commercial_partner_credit(self):
        company_a = self.env["res.partner"].create(
            {
                "name": "Company A",
                "is_company": True,
                "credit_limit": 10000.0,
                "child_ids": [
                    Command.link(self.partner_a.id),
                    Command.create(
                        {
                            "name": "Company A Invoice",
                            "type": "invoice",
                        }
                    ),
                ],
            }
        )
        invoice_partner = company_a.child_ids.filtered(lambda p: p.type == "invoice")

        order = self.empty_order
        order.line_ids = [
            Command.create(
                {
                    "product_id": self.company_data["product_order_no"].id,
                    "price_unit": 600.0,
                    "tax_ids": False,
                }
            )
        ]
        orders = order + order.copy({"partner_invoice_id": invoice_partner.id})
        orders.action_confirm()

        self.assertFalse(
            self.partner_a.credit_to_invoice,
            "Credit should only apply to the commercial entity",
        )
        self.assertFalse(company_a.credit)
        self.assertEqual(company_a.credit_to_invoice, 1200.0)

        invoices = orders._create_invoices()
        invoices.action_post()
        company_a.invalidate_recordset()
        self.assertFalse(company_a.credit_to_invoice)
        self.assertEqual(company_a.credit, 1200.0)
