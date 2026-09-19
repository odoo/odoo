from odoo import Command, fields
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestBillsPrediction(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company.account_config_id.predict_bill_product = True

        cls.test_partners = cls.env["res.partner"].create(
            [{"name": "test partner %s" % i} for i in range(7)]
        )

        accounts_data = [
            {
                "code": "test%s" % i,
                "name": name,
                "account_type": "expense",
            }
            for i, name in enumerate(
                (
                    "Test Maintenance and Repair",
                    "Test Purchase of services, studies and preparatory work",
                    "Test Various Contributions",
                    "Test Rental Charges",
                    "Test Purchase of commodity",
                )
            )
        ]

        cls.test_accounts = cls.env["account.account"].create(accounts_data)

        cls.frozen_today = fields.Date.today()

    def _create_bill(
        self, vendor, line_name, expected_account, account_to_set=None, post=True
    ):
        invoice_form = Form(
            self.env["account.move"].with_context(default_move_type="in_invoice")
        )
        invoice_form.partner_id = vendor
        invoice_form.invoice_date = self.frozen_today
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.account_id = self.company_data[
                "default_journal_purchase"
            ].default_account_id

            invoice_line_form.quantity = 1.0
            invoice_line_form.price_unit = 42.0
            invoice_line_form.name = line_name
        invoice = invoice_form.save()
        invoice_line = invoice.invoice_line_ids

        self.assertEqual(
            invoice_line.account_id,
            expected_account,
            "Account '%s' should have been predicted instead of '%s'"
            % (
                expected_account.display_name,
                invoice_line.account_id.display_name,
            ),
        )

        if account_to_set:
            invoice_line.account_id = account_to_set

        if post:
            invoice.action_post()
        return invoice

    def test_account_prediction_flow(self):
        default_account = self.company_data[
            "default_journal_purchase"
        ].default_account_id
        self._create_bill(
            self.test_partners[0], "Maintenance and repair", self.test_accounts[0]
        )
        self._create_bill(
            self.test_partners[5],
            "Subsidies obtained",
            default_account,
            account_to_set=self.test_accounts[1],
        )
        self._create_bill(
            self.test_partners[6],
            "Prepare subsidies file",
            default_account,
            account_to_set=self.test_accounts[1],
        )
        self._create_bill(
            self.test_partners[6], "Prepare subsidies file", self.test_accounts[1]
        )
        self._create_bill(
            self.test_partners[1], "Contributions January", self.test_accounts[2]
        )
        self._create_bill(
            self.test_partners[2],
            "Coca-cola",
            default_account,
            account_to_set=self.test_accounts[4],
        )
        self._create_bill(
            self.test_partners[1], "Contribution February", self.test_accounts[2]
        )
        self._create_bill(
            self.test_partners[3],
            "Electricity Bruxelles",
            default_account,
            account_to_set=self.test_accounts[3],
        )
        self._create_bill(
            self.test_partners[3], "Electricity Grand-Rosière", self.test_accounts[3]
        )
        self._create_bill(
            self.test_partners[2], "Purchase of coca-cola", self.test_accounts[4]
        )
        self._create_bill(
            self.test_partners[4],
            "Crate of coca-cola",
            default_account,
            account_to_set=self.test_accounts[4],
        )
        self._create_bill(
            self.test_partners[4], "Crate of coca-cola", self.test_accounts[4]
        )
        self._create_bill(self.test_partners[1], "March", self.test_accounts[2])

    def test_account_prediction_from_label_expected_behavior(self):
        default_account = self.company_data[
            "default_journal_purchase"
        ].default_account_id
        payable_account = self.company_data["default_account_payable"].copy()
        payable_account.write(
            {"name": f"Account payable - {self.test_accounts[0].name}"}
        )

        self._create_bill(
            self.test_partners[0],
            self.test_partners[0].name,
            default_account,
            post=False,
        )

        self._create_bill(
            self.test_partners[0],
            "Drinks",
            default_account,
            account_to_set=self.test_accounts[0],
        )

        self._create_bill(
            self.test_partners[0],
            "Desert",
            self.test_accounts[0],
            account_to_set=self.test_accounts[1],
        )

        self._create_bill(self.test_partners[0], "Drinks too", self.test_accounts[0])

        invoice = self._create_bill(
            self.test_partners[0], "Main course", default_account
        )
        invoice.action_draft()

        with Form(invoice) as move_form:
            with move_form.invoice_line_ids.edit(0) as line_form:
                line_form.account_id = self.test_accounts[2]
                line_form.name = "Apple"
                self.assertEqual(line_form.account_id, self.test_accounts[2])

                line_form.name = "Second desert"
                self.assertEqual(line_form.account_id, self.test_accounts[1])

    def test_account_prediction_with_product(self):
        product = self.env["product.product"].create(
            {
                "name": "product_a",
                "lst_price": 1000.0,
                "standard_price": 800.0,
                "property_account_income_id": self.company_data[
                    "default_account_revenue"
                ].id,
                "property_account_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
            }
        )

        invoice_form = Form(
            self.env["account.move"].with_context(default_move_type="in_invoice")
        )
        invoice_form.partner_id = self.test_partners[0]
        invoice_form.invoice_date = self.frozen_today
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.product_id = product
            invoice_line_form.name = "Maintenance and repair"
        invoice = invoice_form.save()

        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    "name": "Maintenance and repair",
                    "product_id": product.id,
                    "account_id": self.company_data["default_account_expense"].id,
                }
            ],
        )

    def test_product_prediction_price_subtotal_computation(self):
        invoice_form = Form(
            self.env["account.move"].with_context(default_move_type="in_invoice")
        )
        invoice_form.partner_id = self.test_partners[0]
        invoice_form.invoice_date = self.frozen_today
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.product_id = self.product_a
        invoice = invoice_form.save()
        invoice.action_post()

        self.product_a.supplier_taxes_id = [Command.set(self.tax_purchase_b.ids)]

        invoice_form = Form(
            self.env["account.move"].with_context(default_move_type="in_invoice")
        )
        invoice_form.partner_id = self.test_partners[0]
        invoice_form.invoice_date = self.frozen_today
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.name = "product_a"
        invoice = invoice_form.save()

        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    "quantity": 1.0,
                    "price_unit": 800.0,
                    "price_subtotal": 800.0,
                    "balance": 800.0,
                    "tax_ids": self.tax_purchase_b.ids,
                }
            ],
        )

        invoice_form = Form(
            self.env["account.move"].with_context(default_move_type="in_invoice")
        )
        invoice_form.partner_id = self.test_partners[0]
        invoice_form.invoice_date = self.frozen_today
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.price_unit = 42.0
            invoice_line_form.name = "product_a"
        invoice = invoice_form.save()

        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    "quantity": 1.0,
                    "price_unit": 42.0,
                    "price_subtotal": 42.0,
                    "balance": 42.0,
                    "tax_ids": self.tax_purchase_b.ids,
                }
            ],
        )

        invoice_form = Form(
            self.env["account.move"].with_context(default_move_type="in_invoice")
        )
        invoice_form.partner_id = self.test_partners[0]
        invoice_form.invoice_date = self.frozen_today
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.tax_ids = self.tax_purchase_a
            invoice_line_form.name = "product_a"
        invoice = invoice_form.save()

        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    "quantity": 1.0,
                    "price_unit": 800.0,
                    "price_subtotal": 800.0,
                    "balance": 800.0,
                    "tax_ids": self.tax_purchase_a.ids,
                }
            ],
        )

    def test_deductible_amount_prediction(self):
        default_account = self.company_data[
            "default_journal_purchase"
        ].default_account_id
        bill_1 = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "invoice_date": fields.Date.today(),
                "partner_id": self.test_partners[0].id,
                "line_ids": [
                    Command.create(
                        {
                            "name": "Laptop",
                            "deductible_amount": 80.0,
                            "account_id": default_account.id,
                            "quantity": 1,
                            "price_unit": 100.0,
                        }
                    ),
                    Command.create(
                        {
                            "name": "T-shirt",
                            "deductible_amount": 50.0,
                            "account_id": default_account.id,
                            "quantity": 1,
                            "price_unit": 100.0,
                        }
                    ),
                    Command.create(
                        {
                            "name": "T-shirt",
                            "deductible_amount": 60.0,
                            "account_id": default_account.id,
                            "quantity": 1,
                            "price_unit": 100.0,
                        }
                    ),
                ],
            }
        )
        bill_1.action_post()

        bill_form = Form(
            self.env["account.move"].with_context(default_move_type="in_invoice")
        )
        bill_form.partner_id = self.test_partners[0]
        labels = ["Laptop", "Laptops", "Laptopp", "T-shirt", "Mobile"]
        for label in labels:
            with bill_form.invoice_line_ids.new() as invoice_line_form:
                invoice_line_form.name = label
        bill_2 = bill_form.save()
        self.assertRecordValues(
            bill_2.invoice_line_ids,
            [
                {"name": "Laptop", "deductible_amount": 80.0},
                {"name": "Laptops", "deductible_amount": 80.0},
                {"name": "Laptopp", "deductible_amount": 100.0},
                {"name": "T-shirt", "deductible_amount": 100.0},
                {"name": "Mobile", "deductible_amount": 100.0},
            ],
        )

        self.env.user.group_ids -= self.env.ref(
            "account.group_partial_purchase_deductibility"
        )
        bill_form = Form(
            self.env["account.move"].with_context(default_move_type="in_invoice")
        )
        bill_form.partner_id = self.test_partners[0]
        labels = ["Laptop", "Laptops"]
        for label in labels:
            with bill_form.invoice_line_ids.new() as invoice_line_form:
                invoice_line_form.name = label
        bill_3 = bill_form.save()
        self.assertRecordValues(
            bill_3.invoice_line_ids,
            [
                {"name": "Laptop", "deductible_amount": 100.0},
                {"name": "Laptops", "deductible_amount": 100.0},
            ],
        )
