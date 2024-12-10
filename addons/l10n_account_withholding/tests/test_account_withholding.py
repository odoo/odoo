# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nAccountWithholdingTaxes(AccountTestInvoicingCommon):

    def _setup_tax(self, name, amount, sequence=None):
        # Copy a default tax and set it up for withholding
        tax = self.company_data['default_tax_sale'].copy({
            'name': name,
            'amount': amount,
            'type_tax_use': 'sales_wth',
            'l10n_account_withholding_sequence_id': sequence and sequence.id,
        })
        # Add tax grids
        tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').tag_ids = self.env['account.account.tag'].create({
            'name': f'Tax Tag {name}',
            'applicability': 'taxes',
        })
        tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'base').tag_ids = self.env['account.account.tag'].create({
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
        cls.company_data['company'].l10n_account_withholding_tax_base_account_id = cls.env['account.account'].create({
            'code': 'WITHB',
            'name': 'Withholding Tax Base Account',
            'reconcile': True,
            'account_type': 'asset_current',
        })
        # Create a sequence to set on tax C
        cls.withholding_sequence = cls.env['ir.sequence'].create({
            'implementation': 'standard',
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
            # Set the tax to False to avoid computed values.
            'invoice_line_ids': [Command.create({'product_id': cls.product_a.id, 'price_unit': 1000.0, 'tax_ids': False})],
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
            'reconcile': True,
            'account_type': 'asset_current'
        })

    def test_withholding_tax_on_payment(self):
        """
        Post the invoice, then register a payment for it.
        We do not expect default withholding lines.

        We can then add a withholding line, and register the payment, the verify the amounts.
        """
        self.invoice.action_post()
        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=self.invoice.ids
        ).create({
            'payment_date': self.invoice.date,
            'l10n_account_withholding_withhold_tax': True,
        })
        # No default withholding tax on the product = no default line in the wizard.
        self.assertFalse(payment_register.l10n_account_withholding_line_ids)
        # We add a tax.
        payment_register.l10n_account_withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'base_amount': 1000,
            })
        ]
        # The amount on the tax line should have been computed. The net amount too.
        self.assertEqual(payment_register.l10n_account_withholding_line_ids[0].amount, 1000 * 0.01)
        self.assertEqual(payment_register.l10n_account_withholding_net_amount, 1000 - (1000 * 0.01))
        # The amounts are correct, we register the payment then check the entry
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'balance': 990.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': 990.0},
            # Liquidity line:
            {'balance': -1000.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': -1000.0},
            # withholding line:
            {'balance': 10.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': 10.0},
            # base lines:
            {'balance': 1000.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': 1000.0},
            {'balance': -1000.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': -1000.0},
        ])

    def test_withholding_tax_before_payment(self):
        """
        Post the invoice, then register withholding taxes.
        Afterward, register the payment separately.
        """
        self.invoice.action_post()
        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=self.invoice.ids
        ).create({
            'payment_date': self.invoice.date,
            'l10n_account_withholding_withhold_tax': True,
        })
        # We add a tax.
        payment_register.l10n_account_withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'base_amount': 1000,
            })
        ]
        # The amount on the tax line should have been computed. The net amount too.
        self.assertEqual(payment_register.l10n_account_withholding_line_ids[0].amount, 1000 * 0.01)
        self.assertEqual(payment_register.l10n_account_withholding_net_amount, 1000 - (1000 * 0.01))
        # As we only want to register withholding taxes, we change the register payment amount to match the net amount
        payment_register.amount = 1000 * 0.01
        self.assertEqual(payment_register.l10n_account_withholding_net_amount, 0.0)
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
        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=self.invoice.ids
        ).create({
            'payment_date': self.invoice.date,
            'l10n_account_withholding_withhold_tax': True,
        })
        self.assertEqual(payment_register.amount, 990)  # Withholding amount is already "paid"
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'balance': 990.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': 990.0},
            # Liquidity line:
            {'balance': -990.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': -990.0},
        ])

    def test_withholding_tax_foreign_currency(self):
        """
        Test that an invoice in a foreign currency, also paid in such foreign currency, with withholding tax
        Result in the expected amounts.
        """
        self.invoice.currency_id = self.foreign_currency
        self.invoice.action_post()
        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=self.invoice.ids
        ).create({
            'payment_date': self.invoice.date,
            'l10n_account_withholding_withhold_tax': True,
        })
        # We add a tax.
        payment_register.l10n_account_withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'base_amount': 1000,
            })
        ]
        # The amount on the tax line should have been computed. The net amount too.
        self.assertEqual(payment_register.l10n_account_withholding_line_ids[0].amount, 1000 * 0.01)
        self.assertEqual(payment_register.l10n_account_withholding_net_amount, 1000 - (1000 * 0.01))
        # The amounts are correct, we register the payment then check the entry
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'balance': 495.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': 990.0},
            # Liquidity line:
            {'balance': -500.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': -1000.0},
            # withholding line:
            {'balance': 5.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': 10.0},
            # base lines:
            {'balance': 500.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': 1000.0},
            {'balance': -500.0, 'currency_id': payment_register.currency_id.id, 'amount_currency': -1000.0},
        ])

    def test_withholding_tax_default_tax_on_product(self):
        """
        Simply test that an invoice having a product with a default withholding tax will cause
        that tax to appear on a default line in the wizard.
        """
        self.invoice.invoice_line_ids[0].product_id = self.product_b
        self.invoice.invoice_line_ids = [Command.create({'product_id': self.product_b.id, 'price_unit': 400.0, 'tax_ids': False})]
        self.invoice.action_post()
        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=self.invoice.ids
        ).create({
            'payment_date': self.invoice.date,
            'l10n_account_withholding_withhold_tax': True,
        })
        # Base amount is set by default to the sum of balances of the lines with this tax.
        self.assertEqual(payment_register.l10n_account_withholding_line_ids[0].base_amount, 600.0)
        self.assertEqual(payment_register.l10n_account_withholding_line_ids[0].amount, 6.0)

    def test_withholding_tax_default_tax_on_product_fiscal_position(self):
        """
        Test that when a wizard is opened from an invoice using a product having a withholding tax,
        the fiscal position is properly applied.

        The tax set on product is 1%, the mapped one is 2%
        """
        self.invoice.invoice_line_ids[0].product_id = self.product_b
        self.invoice.fiscal_position_id = self.fiscal_pos_withh
        self.invoice.action_post()
        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=self.invoice.ids
        ).create({
            'payment_date': self.invoice.date,
            'l10n_account_withholding_withhold_tax': True,
        })
        # Base amount is set by default to the sum of balances of the lines with this tax.
        self.assertEqual(payment_register.l10n_account_withholding_line_ids[0].tax_id, self.tax_sale_c)

    def test_withholding_tax_cannot_edit_payment(self):
        """
        Withholding taxes detail is lost once the payment is done.
        This means that you can't expect to edit a payment after registering a withholding tax and then all work well.

        This will ensure that this cannot be done, as the expected flow is to cancel the payment and register a new one.
        """
        self.invoice.action_post()
        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=self.invoice.ids
        ).create({
            'payment_date': self.invoice.date,
            'l10n_account_withholding_withhold_tax': True,
        })
        payment_register.l10n_account_withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'base_amount': 1000,
            })
        ]
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        with self.assertRaises(UserError):
            payment.amount = 1500
        payment.action_draft()
        with self.assertRaises(UserError):
            payment.amount = 1500
        payment.action_cancel()

    def test_withholding_not_payment_account_on_method_line(self):
        """ Test that when no payment account is set on the payment method line, the one from the wizard is used. """
        self.invoice.action_post()
        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=self.invoice.ids
        ).create({
            'payment_date': self.invoice.date,
            'l10n_account_withholding_outstanding_account': self.outstanding_account.id,
            'l10n_account_withholding_withhold_tax': True,
        })
        # Remove the account from the payment method
        payment_register.payment_method_line_id.payment_account_id = False
        # We add a tax.
        payment_register.l10n_account_withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'base_amount': 1000,
            })
        ]
        # The amounts are correct, we register the payment then check the entry
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'balance': 990.0, 'account_id': self.outstanding_account.id, 'currency_id': payment_register.currency_id.id, 'amount_currency': 990.0},
            # Liquidity line:
            {'balance': -1000.0, 'account_id': payment.destination_account_id.id, 'currency_id': payment_register.currency_id.id, 'amount_currency': -1000.0},
            # withholding line:
            {'balance': 10.0, 'account_id': self.tax_sale_b.invoice_repartition_line_ids.account_id.id, 'currency_id': payment_register.currency_id.id, 'amount_currency': 10.0},
            # base lines:
            {'balance': 1000.0, 'account_id': self.company_data['company'].l10n_account_withholding_tax_base_account_id.id, 'currency_id': payment_register.currency_id.id, 'amount_currency': 1000.0},
            {'balance': -1000.0, 'account_id': self.company_data['company'].l10n_account_withholding_tax_base_account_id.id, 'currency_id': payment_register.currency_id.id, 'amount_currency': -1000.0},
        ])

    def test_withholding_tax_grids(self):
        """ Test that tax grids are set as expected on the lines when they exist on the taxes. """
        self.invoice.action_post()
        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=self.invoice.ids
        ).create({
            'payment_date': self.invoice.date,
            'l10n_account_withholding_outstanding_account': self.outstanding_account.id,
            'l10n_account_withholding_withhold_tax': True,
        })
        # Remove the account from the payment method
        payment_register.payment_method_line_id.payment_account_id = False
        tax_b_grids = self._get_tax_tag(self.tax_sale_b)
        tax_c_grids = self._get_tax_tag(self.tax_sale_c)
        # We add a tax.
        payment_register.l10n_account_withholding_line_ids = [
            Command.create({
                'tax_id': self.tax_sale_b.id,
                'name': '1',
                'base_amount': 1000,
            }),
            Command.create({
                'tax_id': self.tax_sale_c.id,
                'name': '1',
                'base_amount': 1000,
            })
        ]
        # The amounts are correct, we register the payment then check the entry
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.move_id.line_ids, [
            # Receivable line:
            {'balance': 970.0, 'tax_tag_ids': [], 'currency_id': payment_register.currency_id.id, 'amount_currency': 970.0},
            # Liquidity line:
            {'balance': -1000.0, 'tax_tag_ids': [], 'currency_id': payment_register.currency_id.id, 'amount_currency': -1000.0},
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
        self.invoice.invoice_line_ids = [Command.create({'product_id': self.product_b.id, 'price_unit': 400.0, 'tax_ids': False})]
        self.invoice.action_post()
        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=self.invoice.ids
        ).create({
            'payment_date': self.invoice.date,
            'l10n_account_withholding_withhold_tax': True,
        })
        # Change the base amount of the second line, we also need a name as it doesn't have a sequence.
        payment_register.l10n_account_withholding_line_ids[1].name = '0'
        payment_register.l10n_account_withholding_line_ids[1].base_amount = 550
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
