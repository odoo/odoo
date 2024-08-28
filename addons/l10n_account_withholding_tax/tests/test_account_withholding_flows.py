# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged, Form

from odoo.addons.account.tests.common import TestTaxCommon
from odoo.addons.analytic.tests.common import AnalyticCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nAccountWithholdingTaxesFlows(TestTaxCommon, AnalyticCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Set the withholding account so that we don't have to worry about it.
        cls.company_data['company'].withholding_tax_base_account_id = cls.env['account.account'].create({
            'code': 'WITHB',
            'name': 'Withholding Tax Base Account',
            'reconcile': True,
            'account_type': 'asset_current',
        })
        # We create a sequence for the same reason, so that we can forget about it.
        cls.withholding_sequence = cls.env['ir.sequence'].create({
            'implementation': 'no_gap',
            'name': 'Withholding Sequence',
            'padding': 4,
            'number_increment': 1,
        })
        cls.foreign_currency = cls.setup_other_currency('EUR')
        cls.outstanding_account = cls.env['account.account'].create({
            'name': "Outstanding Payments",
            'code': 'OSTP420',
            'reconcile': False,  # On purpose for testing.
            'account_type': 'asset_current'
        })

    def test_no_withholding_tax_invoice_but_included_one_on_payment(self):
        """ Test a flow where not withholding tax is set on the invoice line, but one is added to the payment register. """
        invoice_tax = self.percent_tax(15)
        withholding_tax = self.percent_tax(-1, is_withholding_tax_on_payment=True, withholding_sequence_id=self.withholding_sequence.id)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(invoice_tax.ids)],
            })],
        })
        invoice.action_post()

        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        with Form(payment_register) as payment_register_form:
            payment_register_form.should_withhold_tax = True
            with payment_register_form.withholding_line_ids.new() as line:
                line.tax_id = withholding_tax
                line.base_amount = 1000.0

        self.assertRecordValues(payment_register.withholding_line_ids, [{
            'base_amount': 1000.0,
            'amount': 10.0,
        }])
        self.assertRecordValues(payment_register, [{'withholding_net_amount': 1140.0}])

        payment = payment_register._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1150.0,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1140.0,     'tax_ids': []},
            {'balance': -1150.0,    'tax_ids': []},
            {'balance': 10.0,       'tax_ids': []},
            {'balance': 1000.0,     'tax_ids': withholding_tax.ids},
            {'balance': -1000.0,    'tax_ids': []},
        ])

    def test_withholding_tax_before_payment(self):
        """
        Post the invoice, then register withholding taxes.
        Afterward, register the payment separately.
        """
        invoice_tax = self.percent_tax(15)
        withholding_tax = self.percent_tax(-1, is_withholding_tax_on_payment=True, withholding_sequence_id=self.withholding_sequence.id)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(invoice_tax.ids)],
            })],
        })
        invoice.action_post()

        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        with Form(payment_register) as payment_register_form:
            payment_register_form.should_withhold_tax = True
            with payment_register_form.withholding_line_ids.new() as line:
                line.tax_id = withholding_tax
                line.base_amount = 1000.0
        self.assertRecordValues(payment_register, [{
            'amount': 1150.0,
            'withholding_net_amount': 1140.0,
        }])
        self.assertRecordValues(payment_register.withholding_line_ids, [{
            'original_base_amount': 1000.0,
            'original_tax_amount': 10.0,
            'base_amount': 1000.0,
            'amount': 10.0,
        }])

        with Form(payment_register) as payment_register_form:
            payment_register_form.amount = 10
        self.assertRecordValues(payment_register, [{
            'amount': 10.0,
            'withholding_net_amount': 0.0,
        }])
        self.assertRecordValues(payment_register.withholding_line_ids, [{
            'original_base_amount': 1000.0,
            'original_tax_amount': 10.0,
            'base_amount': 1000.0,
            'amount': 10.0,
        }])

        payment = payment_register._create_payments()
        self.assertRecordValues(payment.move_id.line_ids, [
            # Liquidity line:
            {'balance': 0.0},
            # Receivable line:
            {'balance': -10.0},
            # withholding line:
            {'balance': 10.0},
            # base lines:
            {'balance': 1000.0},
            {'balance': -1000.0},
        ])

        # We then register payment a second time, only for the actual payment.
        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(payment_register, [{
            'amount': 1140.0,
            'withholding_net_amount': 1140.0,
        }])
        self.assertFalse(payment_register.withholding_line_ids)

        payment = payment_register._create_payments()
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'balance': 1140.0},
            # Liquidity line:
            {'balance': -1140.0},
        ])

    def test_withholding_tax_amounts_manipulation(self):
        """ Test manipulating the withholding tax amounts in various way, including using foreign currencies. """
        comp_curr = self.env.company.currency_id
        foreign_curr = self.foreign_currency

        invoice_tax = self.percent_tax(15)
        withholding_tax1 = self.percent_tax(
            amount=-1,
            is_withholding_tax_on_payment=True,
            withholding_sequence_id=self.withholding_sequence.id,
        )
        withholding_tax2 = self.percent_tax(
            amount=-2,
            is_withholding_tax_on_payment=True,
            withholding_sequence_id=self.withholding_sequence.id,
        )

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'currency_id': foreign_curr.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'tax_ids': [Command.set((invoice_tax + withholding_tax1).ids)],
            })],
        })
        invoice.action_post()
        self.assertRecordValues(invoice, [{
            'amount_untaxed': 2000.0,
            'amount_tax': 300.0,
            'amount_total': 2300.0,
        }])

        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(payment_register, [{
            'amount': 2300.0,
            'withholding_net_amount': 2280.0,
            'source_amount': 1150.0,
            'source_amount_currency': 2300.0,
        }])
        self.assertRecordValues(payment_register.withholding_line_ids, [{
            'original_base_amount': 2000.0,
            'original_tax_amount': 20.0,
            'base_amount': 2000.0,
            'amount': 20.0,
        }])

        with Form(payment_register) as payment_register_form:
            # We need the custom user amount to be set for proper computation of comodel_percentage_paid_factor later on
            # when the currency changes
            payment_register_form.amount = 1150

        self.assertRecordValues(payment_register.withholding_line_ids, [{
            'original_base_amount': 2000.0,
            'original_tax_amount': 20.0,
            'base_amount': 1000.0,
            'amount': 10.0,
        }])

        with Form(payment_register) as payment_register_form:
            with payment_register_form.withholding_line_ids.new() as line:
                line.tax_id = withholding_tax2
                line.base_amount = 500.0

        self.assertRecordValues(payment_register.withholding_line_ids, [
            {
                'original_base_amount': 2000.0,
                'original_tax_amount': 20.0,
                'base_amount': 1000.0,
                'amount': 10.0,
            },
            {
                'original_base_amount': 500.0,
                'original_tax_amount': 10.0,
                'base_amount': 500.0,
                'amount': 10.0,
            },
        ])

        with Form(payment_register) as payment_register_form:
            # Uses the form emulator as we mix custom amounts and currency changes, which is handled by a onchange
            payment_register_form.currency_id = comp_curr

        self.assertRecordValues(payment_register, [{
            'amount': 575.0,
            'withholding_net_amount': 560.0,
            'source_amount': 1150.0,
            'source_amount_currency': 2300.0,
        }])
        # The manual line amount is not updated from a currency change; this is a current limitation
        self.assertRecordValues(payment_register.withholding_line_ids, [{
                'original_base_amount': 1000.0,
                'original_tax_amount': 10.0,
                'base_amount': 500.0,
                'amount': 5.0,
            },
            {
                'original_base_amount': 500.0,
                'original_tax_amount': 10.0,
                'base_amount': 500.0,
                'amount': 10.0,
        }])

        with Form(payment_register) as payment_register_form:
            payment_register_form.currency_id = foreign_curr
            payment_register_form.amount = 230

        self.assertRecordValues(payment_register, [{
            'amount': 230.0,
            'withholding_net_amount': 218.0,
            'source_amount': 1150.0,
            'source_amount_currency': 2300.0,
        }])
        self.assertRecordValues(payment_register.withholding_line_ids, [{
                'original_base_amount': 2000.0,
                'original_tax_amount': 20.0,
                'base_amount': 200.0,
                'amount': 2.0,
            },
            {
                'original_base_amount': 500.0,
                'original_tax_amount': 10.0,
                'base_amount': 500.0,
                'amount': 10.0,
        }])

        with Form(payment_register) as payment_register_form:
            with payment_register_form.withholding_line_ids.edit(0) as line:
                line.base_amount = 150.0
        self.assertRecordValues(payment_register.withholding_line_ids, [{
                'original_base_amount': 2000.0,
                'original_tax_amount': 20.0,
                'base_amount': 150.0,
                'amount': 1.5,
            },
            {
                'original_base_amount': 500.0,
                'original_tax_amount': 10.0,
                'base_amount': 500.0,
                'amount': 10.0,
        }])

        with Form(payment_register) as payment_register_form:
            with payment_register_form.withholding_line_ids.edit(0) as line:
                line.amount = 2.0
        self.assertRecordValues(payment_register, [{
            'amount': 230.0,
            'withholding_net_amount': 218.0,
        }])
        self.assertRecordValues(payment_register.withholding_line_ids, [{
                'original_base_amount': 2000.0,
                'original_tax_amount': 20.0,
                'base_amount': 150.0,
                'amount': 2.0,
            },
            {
                'original_base_amount': 500.0,
                'original_tax_amount': 10.0,
                'base_amount': 500.0,
                'amount': 10.0,
        }])

        payment = payment_register._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 230.0,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            # Liquidity line:
            {'balance': 109.0,      'currency_id': foreign_curr.id,     'amount_currency': 218.0},
            # Receivable line:
            {'balance': -115.0,     'currency_id': foreign_curr.id,     'amount_currency': -230.0},
            # withholding line:
            {'balance': 1.0,        'currency_id': foreign_curr.id,     'amount_currency': 2.0},
            {'balance': 5.0,        'currency_id': foreign_curr.id,     'amount_currency': 10.0},
            # base lines:
            {'balance': 75.0,       'currency_id': foreign_curr.id,     'amount_currency': 150.0},
            {'balance': -75.0,      'currency_id': foreign_curr.id,     'amount_currency': -150.0},
            {'balance': 250.0,       'currency_id': foreign_curr.id,     'amount_currency': 500.0},
            {'balance': -250.0,      'currency_id': foreign_curr.id,     'amount_currency': -500.0},
        ])

    def test_withholding_tax_default_tax_on_product(self):
        """
        Simply test that an invoice having a product with a default withholding tax will cause
        that tax to appear on a default line in the wizard.
        """
        self.product_b.taxes_id = self.percent_tax(-1, is_withholding_tax_on_payment=True, withholding_sequence_id=self.withholding_sequence.id)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_b.id,
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 400.0,
                }),
            ],
        })
        invoice.action_post()

        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(payment_register, [{
            'amount': 600.0,
            'withholding_net_amount': 594.0,
        }])
        self.assertRecordValues(payment_register.withholding_line_ids, [{
            'base_amount': 600.0,
            'amount': 6.0,
        }])

    def test_withholding_not_payment_account_on_method_line(self):
        """ Test that when no payment account is set on the payment method line, the one from the wizard is used. """
        invoice_tax = self.percent_tax(15)
        withholding_tax = self.percent_tax(-1, is_withholding_tax_on_payment=True, withholding_sequence_id=self.withholding_sequence.id)
        self.company_data['default_journal_bank'].inbound_payment_method_line_ids.payment_account_id = False

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(invoice_tax.ids)],
            })],
        })
        invoice.action_post()

        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        with Form(payment_register) as payment_register_form:
            payment_register_form.should_withhold_tax = True
            with payment_register_form.withholding_line_ids.new() as line:
                line.tax_id = withholding_tax
                line.base_amount = 1000.0
            payment_register_form.withholding_outstanding_account_id = self.outstanding_account

        payment = payment_register._create_payments()
        outstanding = self.outstanding_account
        receivable = self.company_data['default_account_receivable']
        withholding_account = self.env.company.withholding_tax_base_account_id

        self.assertRecordValues(payment.move_id.line_ids, [
            # Liquidity line:
            {'balance': 1140.0,     'account_id': outstanding.id},
            # Receivable line:
            {'balance': -1150.0,    'account_id': receivable.id},
            # withholding line:
            {'balance': 10.0,       'account_id': withholding_account.id},
            # base lines:
            {'balance': 1000.0,     'account_id': withholding_account.id},
            {'balance': -1000.0,    'account_id': withholding_account.id},
        ])

    def test_withholding_tax_grids(self):
        """ Test that tax grids are set as expected on the lines when they exist on the taxes. """
        base_tag_1 = self.env['account.account.tag'].create({
            'name': 'Base Tag 1',
            'applicability': 'taxes',
        })
        base_tag_2 = self.env['account.account.tag'].create({
            'name': 'Base Tag 2',
            'applicability': 'taxes',
        })
        tax_tag_1 = self.env['account.account.tag'].create({
            'name': 'Tax Tag 1',
            'applicability': 'taxes',
        })
        tax_tag_2 = self.env['account.account.tag'].create({
            'name': 'Tax Tag 2',
            'applicability': 'taxes',
        })

        invoice_tax = self.percent_tax(15)
        withholding_tax = self.percent_tax(
            amount=-1,
            is_withholding_tax_on_payment=True,
            withholding_sequence_id=self.withholding_sequence.id,
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0, 'tag_ids': base_tag_1.ids}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0, 'tag_ids': tax_tag_1.ids}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0, 'tag_ids': base_tag_1.ids}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0, 'tag_ids': tax_tag_1.ids}),
            ],
        )
        withholding_tax_2 = self.percent_tax(
            amount=-2,
            is_withholding_tax_on_payment=True,
            withholding_sequence_id=self.withholding_sequence.id,
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0, 'tag_ids': base_tag_2.ids}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0, 'tag_ids': tax_tag_2.ids}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0, 'tag_ids': base_tag_2.ids}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0, 'tag_ids': tax_tag_2.ids}),
            ],
        )

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(invoice_tax.ids)],
            })],
        })
        invoice.action_post()

        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        with Form(payment_register) as payment_register_form:
            payment_register_form.should_withhold_tax = True
            with payment_register_form.withholding_line_ids.new() as line:
                line.tax_id = withholding_tax
                line.base_amount = 1000.0
            with payment_register_form.withholding_line_ids.new() as line:
                line.tax_id = withholding_tax_2
                line.base_amount = 1000.0

        payment = payment_register._create_payments()
        self.assertRecordValues(payment.move_id.line_ids, [
            # Liquidity line:
            {'balance': 1120.0,     'tax_tag_ids': []},
            # Receivable line:
            {'balance': -1150.0,    'tax_tag_ids': []},
            # withholding line:
            {'balance': 10.0,       'tax_tag_ids': tax_tag_1.ids},
            {'balance': 20.0,       'tax_tag_ids': tax_tag_2.ids},
            # base lines:
            {'balance': 1000.0,     'tax_tag_ids': base_tag_1.ids},
            {'balance': -1000.0,    'tax_tag_ids': []},
            {'balance': 1000.0,     'tax_tag_ids': base_tag_2.ids},
            {'balance': -1000.0,    'tax_tag_ids': []},
        ])

    # We need the date to be fixed for the EPD part; to the date of the invoice.
    @freeze_time('2024-01-01')
    def test_register_payment__with_installments(self):
        """ When registering a payment with payment terms, the withholding amount should follow the terms. """
        withholding_tax = self.percent_tax(
            amount=-3,
            is_withholding_tax_on_payment=True,
            withholding_sequence_id=self.withholding_sequence.id,
        )
        self.product_a.taxes_id = withholding_tax

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_payment_term_id': self.env.ref('account.account_payment_term_advance_60days').id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
            })],
        })
        invoice.action_post()

        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(payment_register, [{
            'amount': 300.0,
            'withholding_net_amount': 291.0,
        }])
        self.assertRecordValues(payment_register.withholding_line_ids, [{
            'base_amount': 300.0,
            'amount': 9.0,
        }])

        payment = payment_register._create_payments()
        self.assertRecordValues(payment.move_id.line_ids, [
            # Liquidity line:
            {'balance': 291.0},
            # Receivable line:
            {'balance': -300.0},
            # withholding line:
            {'balance': 9.0},
            # base lines:
            {'balance': 300.0},
            {'balance': -300.0},
        ])

    def test_withholding_tax_repartition_line(self):
        """ Ensure that a withholding tax with multiple tax repartition line triggers multiple lines in the final entry
        with correct tax tag, amount and account.
        """
        withholding_tax = self.percent_tax(
            -1,
            is_withholding_tax_on_payment=True,
            withholding_sequence_id=self.withholding_sequence.id,
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 60.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 40.0}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 60.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 40.0}),
            ],
        )
        self.product_b.taxes_id = withholding_tax
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_b.id,
            })],
        })
        invoice.action_post()

        # We then open the wizard, and expect a single withholding line (There is only one tax!)
        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(payment_register, [{
            'amount': 200.0,
            'withholding_net_amount': 198.0,
        }])
        self.assertRecordValues(payment_register.withholding_line_ids, [{
            'original_base_amount': 200.0,
            'original_tax_amount': 2.0,
            'base_amount': 200.0,
            'amount': 2.0,
        }])

        payment = payment_register._create_payments()
        self.assertRecordValues(payment.move_id.line_ids, [
            # Liquidity line:
            {'balance': 198.0},
            # Receivable line:
            {'balance': -200.0},
            # withholding lines:
            {'balance': 1.2},
            {'balance': 0.8},
            # base line:
            {'balance': 200.0},
            # Counterpart:
            {'balance': -200.0},
        ])

    def test_withholding_analytic_distribution(self):
        """ Ensure that the analytic distribution set on an invoice line is correctly applied to the final entry if the
        withholding tax is set to affect analytics.
        """
        withholding_tax = self.percent_tax(
            amount=-1,
            is_withholding_tax_on_payment=True,
            withholding_sequence_id=self.withholding_sequence.id,
            analytic=True,
        )
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_b.id,
                'tax_ids': withholding_tax.ids,
                'analytic_distribution': {
                    self.analytic_account_3.id: 50,
                    self.analytic_account_4.id: 50,
                }
            })],
        })
        invoice.action_post()

        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(payment_register, [{
            'amount': 200.0,
            'withholding_net_amount': 198.0,
        }])
        self.assertRecordValues(payment_register.withholding_line_ids, [{
            'original_base_amount': 200.0,
            'original_tax_amount': 2.0,
            'base_amount': 200.0,
            'amount': 2.0,
            'analytic_distribution': {
                str(self.analytic_account_3.id): 50,
                str(self.analytic_account_4.id): 50,
            },
        }])

        payment = payment_register._create_payments()
        self.assertRecordValues(payment.move_id.line_ids, [
            # Liquidity line:
            {'balance': 198.0,    'analytic_distribution': False},
            # Receivable line:
            {'balance': -200.0,   'analytic_distribution': False},
            # withholding lines:
            {'balance': 2.0,      'analytic_distribution': {
                str(self.analytic_account_3.id): 50,
                str(self.analytic_account_4.id): 50,
            }},
            # base line:
            {'balance': 200.0,    'analytic_distribution': {
                str(self.analytic_account_3.id): 50,
                str(self.analytic_account_4.id): 50,
            }},
            # Counterpart:
            {'balance': -200.0,   'analytic_distribution': False},
        ])

    def test_withholding_analytic_distribution_two_invoice_line(self):
        """ Test that two invoice line with the same product/taxes but different analytic distribution will result in two
        withholding tax lines.
        """
        withholding_tax = self.percent_tax(
            amount=-1,
            is_withholding_tax_on_payment=True,
            withholding_sequence_id=self.withholding_sequence.id,
            analytic=True,
        )
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_b.id,
                'tax_ids': withholding_tax.ids,
                'analytic_distribution': {
                    self.analytic_account_3.id: 50.0,
                    self.analytic_account_4.id: 50.0,
                }
            }),
            Command.create({
                'product_id': self.product_b.id,
                'tax_ids': withholding_tax.ids,
                'analytic_distribution': {
                    self.analytic_account_3.id: 25.0,
                    self.analytic_account_4.id: 75.0,
                }
            })
            ],
        })
        invoice.action_post()

        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(payment_register, [{
            'amount': 400.0,
            'withholding_net_amount': 396.0,
        }])
        self.assertRecordValues(payment_register.withholding_line_ids, [
            {
                'base_amount': 200.0,
                'amount': 2.0,
                'analytic_distribution': {
                    str(self.analytic_account_3.id): 50.0,
                    str(self.analytic_account_4.id): 50.0,
                },
            },
            {
                'base_amount': 200.0,
                'amount': 2.0,
                'analytic_distribution': {
                    str(self.analytic_account_3.id): 25.0,
                    str(self.analytic_account_4.id): 75.0,
                },
            },
        ])

        payment = payment_register._create_payments()
        self.assertRecordValues(payment.move_id.line_ids, [
            # Liquidity line:
            {'balance': 396.0,    'analytic_distribution': False},
            # Receivable line:
            {'balance': -400.0,   'analytic_distribution': False},
            # withholding lines:
            {'balance': 2.0,      'analytic_distribution': {
                str(self.analytic_account_3.id): 50.0,
                str(self.analytic_account_4.id): 50.0,
            }},
            {'balance': 2.0,      'analytic_distribution': {
                str(self.analytic_account_3.id): 25.0,
                str(self.analytic_account_4.id): 75.0,
            }},
            # base line:
            {'balance': 200.0,    'analytic_distribution': {
                str(self.analytic_account_3.id): 50.0,
                str(self.analytic_account_4.id): 50.0,
            }},
            {'balance': -200.0,   'analytic_distribution': False},
            {'balance': 200.0,    'analytic_distribution': {
                str(self.analytic_account_3.id): 25.0,
                str(self.analytic_account_4.id): 75.0,
            }},
            {'balance': -200.0,   'analytic_distribution': False},
        ])

    def test_outstanding_account_marked_as_reconcilable(self):
        """ Ensure that an account set as outstanding account in the wizard will be marked as reconcilable if it is not yet done. """
        tax = self.percent_tax(
            amount=-1,
            is_withholding_tax_on_payment=True,
            withholding_sequence_id=self.withholding_sequence.id,
        )
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'currency_id': self.foreign_currency.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'tax_ids': [Command.set(tax.ids)],
            })],
        })
        invoice.action_post()

        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({'withholding_outstanding_account_id': self.outstanding_account.id})
        payment_register._create_payments()
        self.assertRecordValues(self.outstanding_account, [{'reconcile': True}])

    @freeze_time('2024-01-01')
    def test_payment_synchronize_to_moves(self):
        """ Test that the payment and the journal entry behind it are synchronized as expected when the payment record is updated. """
        invoice_tax = self.percent_tax(15)
        withholding_tax = self.percent_tax(-1, is_withholding_tax_on_payment=True, withholding_sequence_id=self.withholding_sequence.id)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(invoice_tax.ids)],
            })],
        })
        invoice.action_post()

        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        with Form(payment_register) as payment_register_form:
            payment_register_form.should_withhold_tax = True
            with payment_register_form.withholding_line_ids.new() as line:
                line.tax_id = withholding_tax
                line.base_amount = 1000.0

        payment = payment_register._create_payments()
        self.assertRecordValues(payment.move_id.line_ids, [
            # Liquidity line:
            {'name': 'Manual Payment: INV/2024/00001',          'balance': 1140.0},
            # Receivable line:
            {'name': 'Manual Payment: INV/2024/00001',          'balance': -1150.0},
            # withholding line:
            {'name': 'WH Tax: 0001',                 'balance': 10.0},
            # base lines:
            {'name': 'WH Base: 0001',                'balance': 1000.0},
            {'name': 'WH Base Counterpart: 0001',    'balance': -1000.0},
        ])

        payment.action_draft()
        with Form(payment) as payment_form:
            with payment_form.withholding_line_ids.edit(0) as line:
                line.name = '0005'
                line.base_amount = 500.0
        self.assertRecordValues(payment.withholding_line_ids, [{
            'base_amount': 500.0,
            'amount': 5.0,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            # Liquidity line:
            {'name': 'Manual Payment: INV/2024/00001',      'balance': 1145.0},
            # Receivable line:
            {'name': 'Manual Payment: INV/2024/00001',      'balance': -1150.0},
            # withholding line:
            {'name': 'WH Tax: 0005',                        'balance': 5.0},
            # base lines:
            {'name': 'WH Base: 0005',                       'balance': 500.0},
            {'name': 'WH Base Counterpart: 0005',           'balance': -500.0},
        ])

    def test_display_withholding(self):
        """ Simple test that checks if display_withholding is set or not depending on the state of the database. """
        available_withholding_taxes = self.percent_tax(-1, is_withholding_tax_on_payment=True, withholding_sequence_id=self.withholding_sequence.id)
        payment = self.env['account.payment'].create({
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
        })
        self.assertTrue(payment.display_withholding)
        available_withholding_taxes.unlink()
        payment = self.env['account.payment'].create({
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
        })
        self.assertFalse(payment.display_withholding)

    def test_withholding_line_base_amount(self):
        """ Test that a withholding line base amount cannot be less than or equal to 0 """
        self.product_a.taxes_id = self.percent_tax(-1, is_withholding_tax_on_payment=True, withholding_sequence_id=self.withholding_sequence.id)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
            })],
        })
        invoice.action_post()

        payment_register = self.env['account.payment.register'] \
            .with_context(active_model='account.move', active_ids=invoice.ids) \
            .create({})
        with self.assertRaises(UserError):
            with Form(payment_register) as payment_register_form:
                with payment_register_form.withholding_line_ids.edit(0) as line:
                    line.base_amount = -25.0

    def test_compute_outstanding_account_id(self):
        """ Test the correct behavior of the compute_outstanding_account_id method on the wizard.
        We should not have any default values the first time we register a payment with an outstanding account.
        The second time, the register payment wizard should find the previous outstanding account and use it as default.
        """
        self.company_data['default_journal_bank'].inbound_payment_method_line_ids.payment_account_id = False
        withholding_tax = self.percent_tax(
            amount=-1,
            is_withholding_tax_on_payment=True,
            withholding_sequence_id=self.withholding_sequence.id,
        )

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(withholding_tax.ids)],
            })],
        })
        invoice.action_post()

        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({'withholding_outstanding_account_id': self.outstanding_account.id})
        payment_register._create_payments()

        invoice.mapped('line_ids').remove_move_reconcile()

        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(payment_register, [{
            'withholding_outstanding_account_id': self.outstanding_account.id,
        }])

    def test_cannot_register_negative_payment(self):
        """ Test that you cannot register a payment where the withholding amount is higher than the payment amount. """
        withholding_tax = self.percent_tax(-1, is_withholding_tax_on_payment=True, withholding_sequence_id=self.withholding_sequence.id)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(withholding_tax.ids)],
            })],
        })
        invoice.action_post()

        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        with Form(payment_register) as payment_register_form:
            with payment_register_form.withholding_line_ids.new() as line:
                line.tax_id = withholding_tax
                line.base_amount = 999999.0
        with self.assertRaisesRegex(UserError, 'The withholding net amount cannot be negative.'):
            payment_register._create_payments()

    def test_placeholder_computation(self):
        """ Ensure that the placeholder computation is working as expected when changed in the form view.. """
        withholding_tax = self.percent_tax(
            -1,
            is_withholding_tax_on_payment=True,
            withholding_sequence_id=self.withholding_sequence.id,
        )
        withholding_tax_2 = self.percent_tax(
            -2,
            is_withholding_tax_on_payment=True,
            withholding_sequence_id=self.withholding_sequence.id,
        )
        self.product_a.taxes_id = withholding_tax
        self.product_b.taxes_id = withholding_tax_2

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_payment_term_id": self.env.ref("account.account_payment_term_advance_60days").id,
                "invoice_line_ids": [
                    Command.create({
                        "product_id": self.product_a.id,
                        "price_unit": 1000.0,
                    }),
                    Command.create({
                        "product_id": self.product_b.id,
                        "price_unit": 500.0,
                    }),
                ],
            }
        )
        invoice.action_post()

        AccountPaymentRegister = self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice.ids
        )
        with Form(AccountPaymentRegister) as payment_register_form:
            # By default, the placeholders will have the correct values due to the sequence.
            lines = payment_register_form.withholding_line_ids._records
            self.assertEqual(lines[0]['placeholder_value'], '0001')
            self.assertEqual(lines[1]['placeholder_value'], '0002')

            with payment_register_form.withholding_line_ids.edit(0) as line_form:
                line_form.name = "0008"  # Manual override

            # We expect the placeholder to hold the correct value for line 0, and to restart counting at line 1
            lines = payment_register_form.withholding_line_ids._records
            self.assertEqual(lines[0]['placeholder_value'], False)
            self.assertEqual(lines[1]['placeholder_value'], '0001')

            with payment_register_form.withholding_line_ids.edit(0) as line_form:
                line_form.name = ""  # reset

            # We expect the placeholder to recompute as they were at the start
            lines = payment_register_form.withholding_line_ids._records
            self.assertEqual(lines[0]['placeholder_value'], '0001')
            self.assertEqual(lines[1]['placeholder_value'], '0002')

    def test_manual_adjustments(self):
        """ Ensure that when manually adjusting the base or tax amount of a line, the manually set amount is saved. """
        withholding_tax = self.percent_tax(-2, is_withholding_tax_on_payment=True, withholding_sequence_id=self.withholding_sequence.id)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(withholding_tax.ids)],
            })],
        })
        invoice.action_post()

        AccountPaymentRegister = self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice.ids
        )
        with Form(AccountPaymentRegister) as payment_register_form:
            line = payment_register_form.withholding_line_ids._records[0]
            self.assertEqual(line['base_amount'], 1000)
            self.assertEqual(line['amount'], 20)
            with payment_register_form.withholding_line_ids.edit(0) as line_form:
                line_form.name = "0008"
                line_form.base_amount = 500
            self.assertEqual(line['base_amount'], 500)
            self.assertEqual(line['amount'], 10)
            with payment_register_form.withholding_line_ids.edit(0) as line_form:
                line_form.amount = 11
            self.assertEqual(line['base_amount'], 500)
            self.assertEqual(line['amount'], 11)
