from odoo.tests import tagged
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestAccountMoveLineMapping(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.acc_sale_dom = cls.env['account.account'].create({
            'code': 'TEST7000', 'name': 'Domestic Sales', 'account_type': 'income'})
        cls.acc_sale_exp = cls.env['account.account'].create({
            'code': 'TEST7001', 'name': 'Export Sales', 'account_type': 'income'})
        cls.acc_disc_dom = cls.env['account.account'].create({
            'code': 'TEST6570', 'name': 'Discount Loss', 'account_type': 'expense'})
        cls.acc_disc_exp = cls.env['account.account'].create({
            'code': 'TEST6571', 'name': 'Export Discount Loss', 'account_type': 'expense'})
        cls.acc_manual = cls.env['account.account'].create({
            'code': 'TEST6000', 'name': 'Office Supplies (Manual)', 'account_type': 'expense'})
        cls.sale_journal = cls.env['account.chart.template'].ref('sale')
        cls.bank_journal = cls.env['account.chart.template'].ref('bank')
        cls.fiscal_position = cls.env['account.fiscal.position'].create({'name': 'Export Mapping'})
        cls.partner = cls.env['res.partner'].create({
            'name': 'Export Customer',
            'property_account_position_id': cls.fiscal_position.id,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Test Desk',
            'property_account_income_id': cls.acc_sale_dom.id,
        })

    def _create_test_move(self, line_vals, extra_move_vals=None):
        """Helper to quickly generate a test invoice with specific line values."""
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.sale_journal.id,
            'invoice_line_ids': [Command.create(line_vals)],
        } | (extra_move_vals or {}))

    def _register_payment(self, invoice, payment_vals):
        """Helper registering a payment on the invoice through the wizard and returning the payments."""
        wizard = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=invoice.ids
        ).create({
            'journal_id': self.bank_journal.id,
            'payment_method_line_id': self.bank_journal.inbound_payment_method_line_ids[:1].id,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.acc_manual.id,
            **payment_vals,
        })
        return wizard._create_payments()

    # --- DO apply fiscal position mapping ---

    def test_journal_defaults_do_apply(self):
        """Invoice with line with no product and no account forces compute fallback mapping."""
        self.sale_journal.default_account_id = self.acc_sale_dom
        self.fiscal_position.account_ids = [
            Command.create({'account_src_id': self.acc_sale_dom.id, 'account_dest_id': self.acc_sale_exp.id}),
        ]

        move = self._create_test_move({
            'name': 'Empty line testing journal fallback',
            'price_unit': 100.0,
        })
        self.assertEqual(move.invoice_line_ids.account_id, self.acc_sale_exp)

    def test_product_fallback_do_apply(self):
        """Product line maps account correctly."""
        self.fiscal_position.account_ids = [
            Command.create({'account_src_id': self.acc_sale_dom.id, 'account_dest_id': self.acc_sale_exp.id}),
        ]

        move = self._create_test_move({
            'product_id': self.product.id,
            'price_unit': 100.0,
        })
        self.assertEqual(move.invoice_line_ids.account_id, self.acc_sale_exp)

    def test_system_default_invoice_discount_do_apply(self):
        """Invoice line discounts use the fiscal position mapped account instead of the company default."""
        self.company.write({
            'account_discount_expense_allocation_id': self.acc_disc_dom.id,
        })
        self.fiscal_position.account_ids = [
            Command.create({'account_src_id': self.acc_sale_dom.id, 'account_dest_id': self.acc_sale_exp.id}),
            Command.create({'account_src_id': self.acc_disc_dom.id, 'account_dest_id': self.acc_disc_exp.id}),
        ]

        move = self._create_test_move({
            'product_id': self.product.id,
            'price_unit': 100.0,
            'discount': 10.0,
        })

        discount_line = move.line_ids.filtered(lambda l: l.display_type == 'discount')
        self.assertTrue(discount_line, "Discount line was not dynamically generated.")
        self.assertEqual(discount_line.account_id, self.acc_sale_exp | self.acc_disc_exp)

    def test_system_default_epd_loss_do_apply(self):
        """The Early Payment Discount write-off uses the mapped account upon payment reconciliation."""
        self.company.write({
            'account_journal_early_pay_discount_loss_account_id': self.acc_disc_dom.id,
        })
        self.sale_journal.default_account_id = self.acc_sale_dom
        self.bank_journal.inbound_payment_method_line_ids.payment_account_id = self.acc_manual
        self.fiscal_position.account_ids = [
            Command.create({'account_src_id': self.acc_disc_dom.id, 'account_dest_id': self.acc_disc_exp.id}),
        ]

        epd_term = self.env['account.payment.term'].create({
            'name': '2/10 Net 30',
            'early_discount': True,
            'early_pay_discount_computation': 'mixed',
            'discount_percentage': 2.0,
            'discount_days': 10,
            'line_ids': [
                Command.create({'value': 'percent', 'value_amount': 100.0, 'nb_days': 30}),
            ]
        })

        invoice = self._create_test_move(
            {
                'name': 'Empty line testing journal fallback',
                'price_unit': 100.0,
            },
            {'invoice_payment_term_id': epd_term.id, 'invoice_date': '2026-10-01'}
        )
        invoice.action_post()

        payment = self._register_payment(invoice, {'payment_date': '2026-10-05'})

        accounts_in_payment = payment.move_id.line_ids.account_id
        self.assertIn(self.acc_disc_exp, accounts_in_payment)
        self.assertNotIn(
            self.acc_disc_dom,
            accounts_in_payment,
            "The mapping failed: The base domestic EPD account was used instead of the mapped export account."
        )

    def test_system_default_exchange_difference_do_apply(self):
        """Exchange difference moves apply fiscal position mapping to the base exchange account."""
        acc_exch_dom = self.env['account.account'].create({
            'code': 'TEST6560', 'name': 'Exchange Loss', 'account_type': 'expense'})
        acc_exch_exp = self.env['account.account'].create({
            'code': 'TEST6561', 'name': 'Export Exchange Loss', 'account_type': 'expense'})
        self.company.write({
            'expense_currency_exchange_account_id': acc_exch_dom.id,
        })
        self.bank_journal.inbound_payment_method_line_ids.payment_account_id = self.acc_manual
        self.fiscal_position.account_ids = [
            Command.create({'account_src_id': acc_exch_dom.id, 'account_dest_id': acc_exch_exp.id}),
        ]

        foreign_currency = self.env['res.currency'].with_context(active_test=False).search([('id', '!=', self.company.currency_id.id)], limit=1)
        foreign_currency.active = True

        self.env['res.currency.rate'].create({
            'name': '2026-01-01', 'currency_id': foreign_currency.id, 'rate': 2.0, 'company_id': self.company.id
        })
        self.env['res.currency.rate'].create({
            'name': '2026-02-01', 'currency_id': foreign_currency.id, 'rate': 3.0, 'company_id': self.company.id
        })

        invoice = self._create_test_move(
            {'product_id': self.product.id, 'price_unit': 100.0},
            {'currency_id': foreign_currency.id, 'invoice_date': '2026-01-10'}
        )
        invoice.action_post()

        self._register_payment(invoice, {'payment_date': '2026-02-02', 'amount': 98.0})

        exch_move = invoice.line_ids.exchange_move_ids
        self.assertTrue(exch_move, "Exchange difference move was not generated.")

        exch_line = exch_move.line_ids.filtered(lambda l: l.account_id == acc_exch_exp)
        self.assertTrue(exch_line, "Mapped Exchange Loss account was not used.")

    # --- DO NOT apply fiscal position mapping ---

    def test_manual_override_do_not_apply(self):
        """User manually setting an account does not apply fiscal position mapping"""
        self.fiscal_position.write({
            'account_ids': [
                Command.create({'account_src_id': self.acc_manual.id, 'account_dest_id': self.acc_sale_exp.id})
            ]
        })

        move = self._create_test_move({
            'name': 'Random Manual Account',
            'account_id': self.acc_manual.id,
            'price_unit': 15.0,
        })
        self.assertEqual(move.invoice_line_ids.account_id, self.acc_manual)
