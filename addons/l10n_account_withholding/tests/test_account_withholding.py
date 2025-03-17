# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo import Command
from odoo.addons.account.tests.common import TestTaxCommon
from odoo.addons.analytic.tests.common import AnalyticCommon
from odoo.exceptions import UserError, RedirectWarning
from odoo.tests import tagged, Form


# todo to reimplement later on

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nAccountWithholdingTaxes(TestTaxCommon, AnalyticCommon):

    def _setup_tax(self, name, amount, sequence=None, tax_type='sale', price_include='tax_included', base_tag=None, tax_tag=None):
        # Copy a default tax and set it up for withholding
        tax = self.company_data['default_tax_sale'].copy({
            'name': name,
            'amount': amount,
            'type_tax_use': tax_type,
            'price_include_override': price_include,
            'is_withholding_tax_on_payment': True,
            'withholding_sequence_id': sequence and sequence.id,
        })
        # Add tax grids
        tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').tag_ids = tax_tag or self.env['account.account.tag'].create({
            'name': f'Tax Tag {name}',
            'applicability': 'taxes',
        })
        tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'base').tag_ids = base_tag or self.env['account.account.tag'].create({
            'name': f'Base Tag {name}',
            'applicability': 'taxes',
        })
        return tax

    def _get_tax_tag(self, tax):
        return {
            'tax': tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').tag_ids.ids,
            'base': tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'base').tag_ids.ids,
        }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Set the withholding account
        cls.company_data['company'].withholding_tax_base_account_id = cls.env['account.account'].create({
            'code': 'WITHB',
            'name': 'Withholding Tax Base Account',
            'reconcile': True,
            'account_type': 'asset_current',
        })
        # Create a sequence to set on tax C
        # Note that we use no gap for the sake of testing, in order to have the sequences be rollbacked between tests.
        cls.withholding_sequence = cls.env['ir.sequence'].create({
            'implementation': 'no_gap',
            'name': 'Withholding Sequence',
            'padding': 4,
            'number_increment': 1,
        })
        # Prepare two withholding taxes.
        cls.tax_sale_b = cls._setup_tax(cls, 'Withholding Tax', 1)
        cls.tax_sale_c = cls._setup_tax(cls, 'Withholding Tax 2', 2, cls.withholding_sequence)
        # Prepare one draft invoice for the tests.
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2024-01-01',
            'invoice_date': '2024-01-01',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [Command.create({'product_id': cls.product_a.id, 'price_unit': 1000.0})],
        })
        # Set a withholding tax on product B to test later.
        cls.product_b.taxes_id = cls.tax_sale_b
        # We'll need a foreign currency
        cls.foreign_currency = cls.setup_other_currency('EUR')
        # Fiscal position
        cls.fiscal_pos_withh = cls.env['account.fiscal.position'].create({
            'name': 'fiscal_pos_withh',
            'tax_ids': ([(0, None, {'tax_src_id': cls.tax_sale_b.id, 'tax_dest_id': cls.tax_sale_c.id})]),
        })
        # Outstanding account
        cls.outstanding_account = cls.env['account.account'].create({
            'name': "Outstanding Payments",
            'code': 'OSTP420',
            'reconcile': False,  # On purpose for testing.
            'account_type': 'asset_current'
        })
        # Second tax sale account for cases where we want multiple repartition lines
        cls.tax_sale_account = cls.company_data['default_account_tax_sale'].copy()

    def _register_payment(self, create_vals=None):
        """ Simply post the invoice, and then return a payment register wizard.
        Can optionally take create_vals if some specific fields are required on the wizard at creation, or allows to
        enable withholding tax right away.
        Also allows to create a default withholding tax line on the way.

        These options are useful to avoid repeating some basic setting up each time we don't care about the specificities
        but only about what happens after.
        """
        if self.invoice.state != 'posted':
            self.invoice.action_post()
        wizard = self.env['account.payment.register'].with_context(
            active_model='account.move.line', active_ids=self.invoice.line_ids.ids
        ).create(create_vals or {})
        return wizard

    @freeze_time('2024-01-01')
    def test_no_withholding_tax_invoice_but_included_one_on_payment(self):
        invoice_tax = self.percent_tax(15)

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
        self.assertRecordValues(invoice, [{
            'amount_untaxed': 1000.0,
            'amount_tax': 150.0,
            'amount_total': 1150.0,
        }])
        self.assert_invoice_tax_totals_summary(
            invoice,
            {
                'base_amount_currency': 1000.0,
                'tax_amount_currency': 150.0,
                'total_amount_currency': 1150.0,
            },
            soft_checking=True,
        )

        withholding_tax = self.percent_tax(1, price_include_override='tax_included', is_withholding_tax_on_payment=True)

        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        wizard.write({
            'withhold_tax': True,
            'withholding_line_ids': [
                Command.create({
                    'name': 'withholding tax',
                    'tax_id': withholding_tax.id,
                    # TODO: to me, 'account_id' is computed so it should work without specifying it
                    'account_id': self.env.company.withholding_tax_base_account_id.id,
                    'original_base_amount': 1000.0,
                }),
            ],
        })
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1000.0,
            'base_amount': 1000.0,
            'amount': 10.0,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1140.0}])

        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1140.0,
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
        payment_register = self._register_payment()
        payment_register.withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'original_base_amount': 1000,
                'account_id': self.company_data['company'].withholding_tax_base_account_id.id,
            })
        ]
        self.assertEqual(payment_register.withholding_net_amount, 1150 - (1000 * 0.01))
        # As we only want to register withholding taxes, we change the register payment amount to match the net amount
        payment_register.amount = 1000 * 0.01
        # Changing the amount in the wizard recomputed the withholding amount, but we want it to stay 1000
        payment_register.withholding_line_ids[0].base_amount = 1000
        # The amount on the tax line should have been computed. The net amount too.
        self.assertEqual(payment_register.withholding_line_ids[0].amount, 1000 * 0.01)
        self.assertEqual(payment_register.withholding_net_amount, 0.0)
        # We register the withholding payment
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'balance': 0.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': 0.0},
            # Liquidity line:
            {'balance': -10.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': -10.0},
            # withholding line:
            {'balance': 10.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': 10.0},
            # base lines:
            {'balance': 1000.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': 1000.0},
            {'balance': -1000.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': -1000.0},
        ])
        # We then register payment a second time, only for the actual payment.
        payment_register = self._register_payment(enable_withholding=True)
        self.assertEqual(payment_register.amount, 1140)  # Withholding amount is already "paid"
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'balance': 1140.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': 1140.0},
            # Liquidity line:
            {'balance': -1140.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': -1140.0},
        ])

    def test_withholding_tax_foreign_currency(self):
        """
        Test that an invoice in a foreign currency, also paid in such foreign currency, with withholding tax
        Result in the expected amounts.
        """
        self.invoice.currency_id = self.foreign_currency
        # reset so that it applies exchange rate
        self.invoice.invoice_line_ids = [Command.clear()] + [Command.create({'product_id': self.product_a.id})]
        self.invoice.action_post()
        payment_register = self._register_payment()
        payment_register.withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'original_base_amount': 1000,
                'account_id': self.company_data['company'].withholding_tax_base_account_id.id,
            })
        ]
        self.assertEqual(payment_register.amount, 2300)
        # The amount on the tax line should have been computed. The net amount too.
        self.assertEqual(payment_register.withholding_line_ids[0].base_amount, 2000)
        self.assertEqual(payment_register.withholding_line_ids[0].amount, 2000 * 0.01)
        self.assertEqual(payment_register.withholding_net_amount, 2300 - (2000 * 0.01))
        # The amounts are correct, we register the payment then check the entry
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'balance': 1140.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': 2280.0},
            # Liquidity line:
            {'balance': -1150.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': -2300.0},
            # withholding line:
            {'balance': 10.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': 20.0},
            # base lines:
            {'balance': 1000.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': 2000.0},
            {'balance': -1000.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': -2000.0},
        ])

    def test_withholding_tax_default_tax_on_product(self):
        """
        Simply test that an invoice having a product with a default withholding tax will cause
        that tax to appear on a default line in the wizard.
        """
        self.invoice.invoice_line_ids[0].product_id = self.product_b
        self.invoice.invoice_line_ids = [Command.create({'product_id': self.product_b.id, 'price_unit': 400.0})]
        payment_register = self._register_payment(enable_withholding=True)
        # Base amount is set by default to the sum of balances of the lines with this tax.
        self.assertEqual(payment_register.withholding_line_ids[0].base_amount, 600.0)
        self.assertEqual(payment_register.withholding_line_ids[0].amount, 6.0)

    def test_withholding_tax_default_tax_on_product_fiscal_position(self):
        """
        Test that when a wizard is opened from an invoice using a product having a withholding tax,
        the fiscal position is properly applied.

        The tax set on product is 1%, the mapped one is 2%
        """
        self.invoice.invoice_line_ids[0].product_id = self.product_b
        self.invoice.fiscal_position_id = self.fiscal_pos_withh
        payment_register = self._register_payment(enable_withholding=True)
        # Base amount is set by default to the sum of balances of the lines with this tax.
        self.assertEqual(payment_register.withholding_line_ids[0].tax_id, self.tax_sale_c)

    def test_withholding_not_payment_account_on_method_line(self):
        """ Test that when no payment account is set on the payment method line, the one from the wizard is used. """
        payment_register = self._register_payment(
            create_vals={'outstanding_account_id': self.outstanding_account.id},
            with_default_line=True,
        )
        payment_register.withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'original_base_amount': 1000,
                'account_id': self.company_data['company'].withholding_tax_base_account_id.id,
            })
        ]
        # Remove the account from the payment method
        payment_register.payment_method_line_id.payment_account_id = False
        # The amounts are correct, we register the payment then check the entry
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'balance': 1140.0, 'account_id': self.outstanding_account.id, 'currency_id': payment_register.currency_id.id, 'amount_currency': 1140.0},
            # Liquidity line:
            {'balance': -1150.0, 'account_id': payment.destination_account_id.id, 'currency_id': payment_register.currency_id.id, 'amount_currency': -1150.0},
            # withholding line:
            {'balance': 10.0, 'account_id': self.tax_sale_b.invoice_repartition_line_ids.account_id.id, 'currency_id': payment_register.currency_id.id, 'amount_currency': 10.0},
            # base lines:
            {'balance': 1000.0, 'account_id': self.company_data['company'].withholding_tax_base_account_id.id, 'currency_id': payment_register.currency_id.id, 'amount_currency': 1000.0},
            {'balance': -1000.0, 'account_id': self.company_data['company'].withholding_tax_base_account_id.id, 'currency_id': payment_register.currency_id.id, 'amount_currency': -1000.0},
        ])

    def test_withholding_tax_grids(self):
        """ Test that tax grids are set as expected on the lines when they exist on the taxes. """
        payment_register = self._register_payment(
            create_vals={'outstanding_account_id': self.outstanding_account.id},
            enable_withholding=True,
        )
        # Remove the account from the payment method
        payment_register.payment_method_line_id.payment_account_id = False
        tax_b_grids = self._get_tax_tag(self.tax_sale_b)
        tax_c_grids = self._get_tax_tag(self.tax_sale_c)
        # We add two taxes.
        payment_register.withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'original_base_amount': 1000,
                'account_id': self.company_data['company'].withholding_tax_base_account_id.id,
            }),
            Command.create({
                'tax_id': self.tax_sale_c.id,
                'name': '1',
                'original_base_amount': 1000,
                'account_id': self.company_data['company'].withholding_tax_base_account_id.id,
            })
        ]
        # The amounts are correct, we register the payment then check the entry
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'balance': 1120.0, 'tax_tag_ids': [], 'currency_id': payment_register.currency_id.id, 'amount_currency': 1120.0},
            # Liquidity line:
            {'balance': -1150.0, 'tax_tag_ids': [], 'currency_id': payment_register.currency_id.id, 'amount_currency': -1150.0},
            # withholding line:
            {'balance': 10.0, 'tax_tag_ids': tax_b_grids['tax'], 'currency_id': payment_register.currency_id.id, 'amount_currency': 10.0},
            {'balance': 20.0, 'tax_tag_ids': tax_c_grids['tax'], 'currency_id': payment_register.currency_id.id, 'amount_currency': 20.0},
            # base lines:
            {'balance': 1000.0, 'tax_tag_ids': tax_b_grids['base'] + tax_c_grids['base'], 'currency_id': payment_register.currency_id.id, 'amount_currency': 1000.0},
            {'balance': -1000.0, 'tax_tag_ids': [], 'currency_id': payment_register.currency_id.id, 'amount_currency': -1000.0},
        ])

    def test_withholding_tax_multiple_base(self):
        """ Test two use two taxes with different base amount and ensure that the lines are correct. """
        self.product_a.taxes_id = self.tax_sale_c
        self.invoice.invoice_line_ids = [
            Command.clear(),
            Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0}),
            Command.create({'product_id': self.product_b.id, 'price_unit': 400.0}),
        ]
        payment_register = self._register_payment(enable_withholding=True)
        # Change the base amount of the second line, we also need a name as it doesn't have a sequence.
        payment_register.withholding_line_ids[1].name = '0'
        payment_register.withholding_line_ids[1].original_base_amount = 550
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])

        tax_b_grids = self._get_tax_tag(self.tax_sale_b)
        tax_c_grids = self._get_tax_tag(self.tax_sale_c)
        # We expect two base line, and one counterpart line.
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'balance': 1374.5, 'tax_tag_ids': [], 'currency_id': payment_register.currency_id.id, 'amount_currency': 1374.5},
            # Liquidity line:
            {'balance': -1400.0, 'tax_tag_ids': [], 'currency_id': payment_register.currency_id.id, 'amount_currency': -1400.0},
            # withholding lines:
            {'balance': 20.0, 'tax_tag_ids': tax_c_grids['tax'], 'currency_id': payment_register.currency_id.id, 'amount_currency': 20.0},
            {'balance': 5.5, 'tax_tag_ids': tax_b_grids['tax'], 'currency_id': payment_register.currency_id.id, 'amount_currency': 5.5},
            # base lines:
            {'balance': 1000.0, 'tax_tag_ids': tax_c_grids['base'], 'currency_id': payment_register.currency_id.id, 'amount_currency': 1000.0},
            {'balance': 550.0, 'tax_tag_ids': tax_b_grids['base'], 'currency_id': payment_register.currency_id.id, 'amount_currency': 550.0},
            # Counterpart
            {'balance': -1550.0, 'tax_tag_ids': [], 'currency_id': payment_register.currency_id.id, 'amount_currency': -1550.0},
        ])

    # We need the date to be fixed for the EPD part; to the date of the invoice.
    @freeze_time('2024-01-01')
    def test_register_payment_payment_terms(self):
        """ When registering a payment with payment terms, the withholding amount should follow the terms. """
        self.product_a.taxes_id = self.tax_sale_c
        self.invoice.invoice_line_ids = [
            Command.clear(),
            Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0}),
        ]
        self.invoice.invoice_payment_term_id = self.env.ref('account.account_payment_term_advance_60days')
        payment_register = self._register_payment(enable_withholding=True)
        # We expect the withholding amount to, just like the payment amount, be 30% of the full amount.
        self.assertEqual(payment_register.amount, 1000 * 0.3)
        self.assertEqual(payment_register.withholding_line_ids[0].base_amount, 1000 * 0.3)

    def test_complete_flow_in_form(self):
        """ Use a form emulator to test various use cases.
        It helps to ensure that the view is not broken, as we are working with two transient models which require invisible
        fields to work well.
        """
        self.product_a.taxes_id = self.tax_sale_c
        self.invoice.invoice_line_ids = [
            Command.clear(),
            Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0}),
        ]
        payment_register = self._register_payment()
        payment_register.withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'original_base_amount': 1000,
                'account_id': self.company_data['company'].withholding_tax_base_account_id.id,
            })
        ]
        with Form(payment_register) as payment_register_form:
            # Edit manually a line.
            with payment_register_form.withholding_line_ids.edit(1) as line_form:
                line_form.base_amount = 750
            lines = payment_register_form.withholding_line_ids._records
            self.assertEqual(lines[1]['custom_user_amount'], 750)
            self.assertEqual(lines[1]['custom_user_currency_id'], payment_register_form.currency_id.id)
            # Change the amount
            payment_register_form.amount /= 2
            lines = payment_register_form.withholding_line_ids._records
            self.assertEqual(lines[0]['base_amount'], 500)
            self.assertEqual(lines[1]['base_amount'], 750)
            # Change the currency
            payment_register_form.currency_id = self.foreign_currency
            lines = payment_register_form.withholding_line_ids._records
            self.assertEqual(lines[0]['base_amount'], 1000)
            self.assertEqual(lines[1]['base_amount'], 1500)

    def test_withholding_tax_base_affected(self):
        """ Ensure that a withholding tax is affected by VAT if the setting of the taxes has been set in that direction. """
        # Add a VAT to the invoice
        self.product_b.taxes_id += self.tax_sale_c
        self.invoice.invoice_line_ids[0].product_id = self.product_b
        self.invoice.invoice_line_ids[0].tax_ids |= self.tax_sale_a
        # We expect an invoice line of 200 + 30 of tax

        # Case 1: include base amount is not set.
        # We then want the withholding tax to be based on the amount VAT exclusive.
        payment_register = self._register_payment()
        self.assertEqual(payment_register.withholding_line_ids[0].base_amount, 200.0)
        self.assertEqual(payment_register.withholding_line_ids[0].amount, 2.0)
        self.assertEqual(payment_register.withholding_line_ids[1].base_amount, 200.0)
        self.assertEqual(payment_register.withholding_line_ids[1].amount, 4.0)

        # Case 2: include base amount is set.
        # We then want the withholding tax to be based on the amount VAT inclusive.
        self.tax_sale_a.include_base_amount = True
        payment_register = self._register_payment()
        self.assertEqual(payment_register.withholding_line_ids[0].base_amount, 230.0)
        self.assertEqual(payment_register.withholding_line_ids[0].amount, 2.3)
        self.assertEqual(payment_register.withholding_line_ids[1].base_amount, 230.0)
        self.assertEqual(payment_register.withholding_line_ids[1].amount, 4.6)

        # Case 3: The first withholding tax is also set to affect base amount, which should be affecting the second withholding tax.
        self.tax_sale_b.include_base_amount = True
        payment_register = self._register_payment()
        self.assertEqual(payment_register.withholding_line_ids[0].base_amount, 230.0)
        self.assertEqual(payment_register.withholding_line_ids[0].amount, 2.3)
        self.assertEqual(payment_register.withholding_line_ids[1].base_amount, 232.3)
        self.assertEqual(payment_register.withholding_line_ids[1].amount, 4.65)

    def test_withholding_tax_repartition_line(self):
        """ Ensure that a withholding tax with multiple tax repartition line triggers multiple lines in the final entry
        with correct tax tag, amount and account.
        """
        # Re-set the tax repartition lines to include two tax lines.
        self.tax_sale_b.write({
            'invoice_repartition_line_ids': [
                Command.clear(),
                Command.create({'repartition_type': 'base'}),
                Command.create({
                    'factor_percent': 60,
                    'repartition_type': 'tax',
                    'account_id': self.company_data['default_account_tax_sale'].id,
                }),
                Command.create({
                    'factor_percent': 40,
                    'repartition_type': 'tax',
                    'account_id': self.tax_sale_account.id,
                }),
            ],
            'refund_repartition_line_ids': [
                Command.clear(),
                Command.create({'repartition_type': 'base'}),
                Command.create({
                    'factor_percent': 60,
                    'repartition_type': 'tax',
                    'account_id': self.company_data['default_account_tax_sale'].id,
                }),
                Command.create({
                    'factor_percent': 40,
                    'repartition_type': 'tax',
                    'account_id': self.tax_sale_account.id,
                }),
            ],
        })
        self.invoice.invoice_line_ids[0].product_id = self.product_b
        # We then open the wizard, and expect a single withholding line (There is only one tax!)
        payment_register = self._register_payment()
        self.assertEqual(len(payment_register.withholding_line_ids), 1)
        # Let's not forget to set the sequence
        payment_register.withholding_line_ids[0].name = '0'
        # We create the payment, and here we expect two tax lines, one with 60% of the tax amount and one with 40% of it.
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'balance': 198.0},
            # Liquidity line:
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
        # Enable the option on the tax.
        self.tax_sale_b.analytic = True
        # Add an analytic distribution to the invoice line, as well as a product with withholding taxes.
        self.invoice.invoice_line_ids[0].product_id = self.product_b
        self.invoice.invoice_line_ids[0].analytic_distribution = {
            self.analytic_account_3.id: 50,
            self.analytic_account_4.id: 50,
        }
        payment_register = self._register_payment()
        # We expect one withholding tax line, which should hold the distribution.
        self.assertEqual(len(payment_register.withholding_line_ids), 1)
        self.assertEqual(payment_register.withholding_line_ids.analytic_distribution, {
            str(self.analytic_account_3.id): 50,
            str(self.analytic_account_4.id): 50,
        })
        # Let's not forget to set the sequence
        payment_register.withholding_line_ids[0].name = '0'
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        # The analytic distribution should have been forwarder to the withholding tax line
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'balance': 198.0, 'analytic_distribution': False},
            # Liquidity line:
            {'balance': -200.0, 'analytic_distribution': False},
            # withholding lines:
            {'balance': 2.0, 'analytic_distribution': {
                str(self.analytic_account_3.id): 50,
                str(self.analytic_account_4.id): 50,
            }},
            # base line:
            {'balance': 200.0, 'analytic_distribution': False},
            # Counterpart:
            {'balance': -200.0, 'analytic_distribution': False},
        ])

    def test_withholding_analytic_distribution_two_invoice_line(self):
        """ Test that two invoice line with the same product/taxes but different analytic distribution will result in two
        withholding tax lines.
        """
        # Enable the option on the tax.
        self.tax_sale_b.analytic = True
        # Add an analytic distribution to the invoice line, as well as a product with withholding taxes.
        self.invoice.invoice_line_ids[0].product_id = self.product_b
        self.invoice.invoice_line_ids[0].analytic_distribution = {
            self.analytic_account_3.id: 50,
            self.analytic_account_4.id: 50,
        }
        self.invoice.invoice_line_ids = [Command.create({'product_id': self.product_b.id, 'analytic_distribution': {
            self.analytic_account_3.id: 25,
            self.analytic_account_4.id: 75,
        }})]
        payment_register = self._register_payment()
        # We expect one withholding tax line, which should hold the distribution.
        self.assertEqual(len(payment_register.withholding_line_ids), 2)
        self.assertEqual(payment_register.withholding_line_ids[0].analytic_distribution, {
            str(self.analytic_account_3.id): 50,
            str(self.analytic_account_4.id): 50,
        })
        self.assertEqual(payment_register.withholding_line_ids[1].analytic_distribution, {
            str(self.analytic_account_3.id): 25,
            str(self.analytic_account_4.id): 75,
        })
        # Let's not forget to set the sequence
        payment_register.withholding_line_ids[0].name = '0'
        payment_register.withholding_line_ids[1].name = '1'
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        # The analytic distribution should have been forwarder to the withholding tax line
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'balance': 396.0, 'analytic_distribution': False},
            # Liquidity line:
            {'balance': -400.0, 'analytic_distribution': False},
            # withholding lines:
            {'balance': 2.0, 'analytic_distribution': {
                str(self.analytic_account_3.id): 50,
                str(self.analytic_account_4.id): 50,
            }},
            {'balance': 2.0, 'analytic_distribution': {
                str(self.analytic_account_3.id): 25,
                str(self.analytic_account_4.id): 75,
            }},
            # base line:
            {'balance': 400.0, 'analytic_distribution': False},
            # Counterpart:
            {'balance': -400.0, 'analytic_distribution': False},
        ])

    def test_outstanding_account_marked_as_reconcilable(self):
        """ Ensure that an account set as outstanding account in the wizard will be marked as reconcilable if it is not yet done. """
        payment_register = self._register_payment(
            create_vals={'outstanding_account_id': self.outstanding_account.id},
        )
        payment_register.withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'original_base_amount': 1000,
                'account_id': self.company_data['company'].withholding_tax_base_account_id.id,
            })
        ]
        # reconcile should have switched to true.
        self.assertTrue(self.outstanding_account.reconcile)

    def test_withholding_tax_base_name(self):
        """ Ensure that the tax base line name makes sense and contains the number of all involved taxes. """
        # There already is one line with the product_a. We add a withholding tax on it.
        self.product_a.taxes_id = self.tax_sale_c
        self.invoice.invoice_line_ids = [
            Command.clear(),
            Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0}),
            Command.create({'product_id': self.product_b.id}),
            Command.create({'product_id': self.product_b.id}),
            Command.create({'product_id': self._create_product(name='product', taxes_id=self._setup_tax('Withholding Tax 3', 3)).id, 'price_unit': 400}),
        ]
        # 2 line, 1 with 2 repartition line 1 based
        payment_register = self._register_payment()
        # Only the first line's tax has a sequence
        payment_register.withholding_line_ids[1].name = '1'
        payment_register.withholding_line_ids[2].name = '2'

        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'name': 'Manual Payment: INV/2024/00001', 'balance': 1764.0},
            # Liquidity line:
            {'name': 'Manual Payment: INV/2024/00001', 'balance': -1800.0},
            # withholding lines:
            {'name': '0001', 'balance': 20.0},
            {'name': '1', 'balance': 4.0},
            {'name': '2', 'balance': 12.0},
            # base line:
            {'name': 'WH Base: 0001', 'balance': 1000.0},
            {'name': 'WH Base: 1, 2', 'balance': 400.0},
            # Counterpart:
            {'name': 'WH Base Counterpart for "Withholding Tax Base Account"', 'balance': -1400.0},
        ])

    def test_base_for_tax_grid(self):
        """ Ensure that the base line will be correct when you have two taxes of the same base amount and base tags.
        In this case, we expect to have one base line with the base amount doubled.
        """
        shared_base_tag = self.env['account.account.tag'].create({
            'name': 'Shared Base Tag',
            'applicability': 'taxes',
        })
        other_base_tag = self.env['account.account.tag'].create({
            'name': 'Other Base Tag',
            'applicability': 'taxes',
        })
        wth_tax_1 = self._setup_tax('WTH tax 1', 2, tax_type='sale', base_tag=shared_base_tag)
        wth_tax_2 = self._setup_tax('WTH tax 2', 3, tax_type='sale', base_tag=shared_base_tag | other_base_tag)
        wth_tax_3 = self._setup_tax('WTH tax 3', 3, tax_type='sale', base_tag=other_base_tag)
        self.product_a.taxes_id = wth_tax_1
        self.product_b.taxes_id = wth_tax_2 | wth_tax_3
        # Also add three lines with product_b which has another withholding tax. Two of the lines will be summed for the base, the last one will have a different base.
        self.invoice.invoice_line_ids = [
            Command.clear(),
            Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0}),
            Command.create({'product_id': self.product_b.id, 'price_unit': 1000.0}),
        ]
        payment_register = self._register_payment()  # Add a default manual line with another tax
        payment_register.withholding_line_ids[0].name = '1'
        payment_register.withholding_line_ids[1].name = '2'
        payment_register.withholding_line_ids[2].name = '3'
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        tax_1_grids = self._get_tax_tag(wth_tax_1)
        tax_2_grids = self._get_tax_tag(wth_tax_2)
        tax_3_grids = self._get_tax_tag(wth_tax_3)
        tax_4_grids = self._get_tax_tag(self.tax_sale_b)
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'balance': 1910.0, 'tax_tag_ids': []},
            # Liquidity line:
            {'balance': -2000.0, 'tax_tag_ids': []},
            # withholding lines:
            {'balance': 20.0, 'tax_tag_ids': tax_1_grids['tax']},
            {'balance': 30.0, 'tax_tag_ids': tax_2_grids['tax']},
            {'balance': 30.0, 'tax_tag_ids': tax_3_grids['tax']},
            {'balance': 10.0, 'tax_tag_ids': tax_4_grids['tax']},
            # base lines:
            {'balance': 1000.0, 'tax_tag_ids': tax_1_grids['base'] + tax_3_grids['base'] + tax_4_grids['base']},
            {'balance': 1000.0, 'tax_tag_ids': tax_2_grids['base']},
            # Counterpart:
            {'balance': -2000.0, 'tax_tag_ids': []},
        ])

    def test_payment_synchronize_to_moves(self):
        """ Test that the payment and the journal entry behind it are synchronized as expected when the payment record is updated. """
        # First create a payment and assert the lines.
        payment_register = self._register_payment()
        payment_register.withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'original_base_amount': 1000,
                'account_id': self.company_data['company'].withholding_tax_base_account_id.id,
            })
        ]
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'name': 'Manual Payment: INV/2024/00001', 'balance': 1140.0},
            # Liquidity line:
            {'name': 'Manual Payment: INV/2024/00001', 'balance': -1150.0},
            # withholding line:
            {'name': '1', 'balance': 10.0},
            # base lines:
            {'name': 'WH Base: 1', 'balance': 1000.0},
            {'name': 'WH Base Counterpart for "Withholding Tax Base Account"', 'balance': -1000.0},
        ])
        # Next, we edit the payment's withholding line and assert that the lines are updated as expected.
        # Usage of Command.update is to ensure that the payment's write is triggered.
        payment.action_draft()
        payment.withholding_line_ids = [(
            # We can use .id as we know there is only one line.
            Command.update(payment.withholding_line_ids.id, {
                'name': '0001',
                'base_amount': 500.0,
            })
        )]
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'name': 'Manual Payment: INV/2024/00001', 'balance': 1140.0},
            # Liquidity line:
            {'name': 'Manual Payment: INV/2024/00001', 'balance': -1145.0},
            # withholding line:
            {'name': '0001', 'balance': 5.0},
            # base lines:
            {'name': 'WH Base: 0001', 'balance': 500.0},
            {'name': 'WH Base Counterpart for "Withholding Tax Base Account"', 'balance': -500.0},
        ])

    def test_display_withholding(self):
        """ Simple test that checks if display_withholding is set or not depending on the state of the database. """
        domain = self.env['account.withholding.line']._get_withholding_tax_domain(company=self.company_data['company'], payment_type='inbound')
        available_withholding_taxes = self.env['account.tax'].search(domain)
        payment = self.env['account.payment'].create({
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
        })
        self.assertTrue(payment.display_withholding)
        self.fiscal_pos_withh.unlink()
        available_withholding_taxes.unlink()
        payment = self.env['account.payment'].create({
            'amount': 50.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
        })
        self.assertFalse(payment.display_withholding)

    def test_withholding_line_base_amount(self):
        """ Test that a withholding line base amount cannot be less than or equal to 0 """
        payment_register = self._register_payment()
        payment_register.withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'original_base_amount': 1000,
                'account_id': self.company_data['company'].withholding_tax_base_account_id.id,
            })
        ]
        with self.assertRaises(UserError):
            payment_register.withholding_line_ids[0].base_amount = -25.0

    def test_custom_base_amount(self):
        """ Test that editing the base amount saves it as a custom amount, and that reverting it to the default amount clear the custom fields. """
        payment_register = self._register_payment()
        payment_register.withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'original_base_amount': 1000,
                'account_id': self.company_data['company'].withholding_tax_base_account_id.id,
            })
        ]
        with Form(payment_register) as payment_register_form:
            # Edit manually a line.
            with payment_register_form.withholding_line_ids.edit(0) as line_form:
                default_base_amount = line_form.base_amount
                line_form.base_amount = 750
            lines = payment_register_form.withholding_line_ids._records
            self.assertEqual(lines[0]['custom_user_amount'], 750)
            self.assertEqual(lines[0]['custom_user_currency_id'], payment_register_form.currency_id.id)
            # Reset the amount
            with payment_register_form.withholding_line_ids.edit(0) as line_form:
                line_form.base_amount = default_base_amount
            lines = payment_register_form.withholding_line_ids._records
            self.assertFalse(lines[0]['custom_user_amount'])
            self.assertFalse(lines[0]['custom_user_currency_id'])

    def test_prepare_withholding_line_vals_data_errors(self):
        """ Ensure that the correct error is raised when the configuration is incorrect, and we try to sync the payment lines. """
        # Start by testing that an error if raised when the account is missing on the tax repartition line.
        self.tax_sale_b.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').account_id = False
        payment_register = self._register_payment()
        payment_register.withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'original_base_amount': 1000,
                'account_id': self.company_data['company'].withholding_tax_base_account_id.id,
            })
        ]
        withholding_tax_line = payment_register.withholding_line_ids[0]
        with self.assertRaisesRegex(UserError, f'Please define a tax account on the distribution of the tax {self.tax_sale_b.name}'):
            withholding_tax_line._prepare_withholding_line_vals_data()

    def test_compute_outstanding_account_id(self):
        """ Test the correct behavior of the compute_outstanding_account_id method on the wizard.
        We should not have any default values the first time we register a payment with an outstanding account.
        The second time, the register payment wizard should find the previous outstanding account and use it as default.
        """
        payment_register = self._register_payment()
        payment_register.withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'original_base_amount': 1000,
                'account_id': self.company_data['company'].withholding_tax_base_account_id.id,
            })
        ]
        self.assertFalse(payment_register.outstanding_account_id)  # False by default due to no precedence.
        # We only use payments for which the payment method line has no account as reference for the default.
        payment_register.payment_method_line_id.payment_account_id = False
        payment_register.outstanding_account_id = self.outstanding_account
        payment_register.action_create_payments()  # With the payment created, our reference should be set for next time.
        # Remove the reconciliation so that we can re-register payment.
        self.invoice.mapped('line_ids').remove_move_reconcile()
        payment_register = self._register_payment()
        payment_register.withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'original_base_amount': 1000,
                'account_id': self.company_data['company'].withholding_tax_base_account_id.id,
            })
        ]
        self.assertEqual(payment_register.outstanding_account_id, self.outstanding_account)

    def test_cannot_register_negative_payment(self):
        """ Test that you cannot register a payment where the withholding amount is higher than the payment amount. """
        payment_register = self._register_payment()
        payment_register.withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'original_base_amount': 1000,
                'account_id': self.company_data['company'].withholding_tax_base_account_id.id,
            })
        ]
        payment_register.withholding_line_ids[0].base_amount = 999999
        with self.assertRaisesRegex(UserError, 'The net amount cannot be negative.'):
            payment_register.action_create_payments()
