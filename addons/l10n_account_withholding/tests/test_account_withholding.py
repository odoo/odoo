# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nAccountWithholdingTaxes(AccountTestInvoicingCommon):

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
        cls.tax_sale_b.write({
            'name': 'Withholding Tax',
            'amount': '1',
            'type_tax_use': 'none',
            'l10n_account_withholding_type': 'customer',
        })
        cls.tax_sale_c = cls.company_data['default_tax_sale'].copy()
        cls.tax_sale_c.write({
            'name': 'Withholding Tax 2',
            'amount': '2',
            'type_tax_use': 'none',
            'l10n_account_withholding_type': 'customer',
            'l10n_account_withholding_sequence_id': cls.withholding_sequence.id,
        })
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
        cls.foreign_currency = cls.setup_other_currency('EUR', rounding=0.1)
        # Fiscal position
        cls.fiscal_pos_withh = cls.env['account.fiscal.position'].create({
            'name': 'fiscal_pos_withh',
            'tax_ids': ([(0, None, {'tax_src_id': cls.tax_sale_b.id, 'tax_dest_id': cls.tax_sale_c.id})]),
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
        self.assertRecordValues(payment.line_ids, [
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
        self.assertRecordValues(payment.line_ids, [
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
        })
        self.assertEqual(payment_register.amount, 990)  # Withholding amount is already "paid"
        action = payment_register.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.line_ids, [
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
        self.assertRecordValues(payment.line_ids, [
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

    def test_withholding_tax_tax_configuration(self):
        """ Simple test ensuring that the l10n_account_withholding_type is reset when type_tax_use is changed from none """
        self.tax_sale_c.type_tax_use = 'sale'
        self.assertFalse(self.tax_sale_c.l10n_account_withholding_type)
