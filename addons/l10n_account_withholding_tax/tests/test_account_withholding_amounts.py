# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_account_withholding_tax.tests.common import TestWithholdTaxCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nAccountWithholdingTaxesAmounts(TestWithholdTaxCommon):
    """ This test file focuses solely on testing taxes amounts in various use cases (vat, wth, base affected,...). """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].tax_calculation_rounding_method = 'round_per_line'

    def test_case_a(self):
        vat_tax_incl_affecting = self.percent_tax(15, price_include_override='tax_included', include_base_amount=True)
        wth_tax_affecting = self.percent_tax(-10, include_base_amount=True, is_withholding_tax_on_payment=True)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'account_id': self.purchase_account.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(vat_tax_incl_affecting.ids)],
            })],
        })
        invoice.action_post()
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1000.0,
            'base_amount': 1000.0,
            'amount': 100.0,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 900.0}])

        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1000.0,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 900.0,     'tax_ids': []},
            {'balance': -1000.0,   'tax_ids': []},
            {'balance': 100.0,     'tax_ids': []},
            {'balance': 1000.0,    'tax_ids': []},
            {'balance': -1000.0,   'tax_ids': wth_tax_affecting.ids},
        ])

    def test_case_b(self):
        vat_tax_incl = self.percent_tax(15, price_include_override='tax_included')
        wth_tax_affecting = self.percent_tax(-10, include_base_amount=True, is_withholding_tax_on_payment=True)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'account_id': self.purchase_account.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(vat_tax_incl.ids)],
            })],
        })
        invoice.action_post()
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 869.57,
            'base_amount': 869.57,
            'amount': 86.96,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 913.04}])

        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1000.0,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 913.04,    'tax_ids': []},
            {'balance': -1000.0,   'tax_ids': []},
            {'balance': 86.96,     'tax_ids': []},
            {'balance': 869.57,    'tax_ids': []},
            {'balance': -869.57,   'tax_ids': wth_tax_affecting.ids},
        ])

    def test_case_c(self):
        vat_tax_affecting = self.percent_tax(15, include_base_amount=True)
        wth_tax_affecting = self.percent_tax(-10, include_base_amount=True, is_withholding_tax_on_payment=True)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'account_id': self.purchase_account.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(vat_tax_affecting.ids)],
            })],
        })
        invoice.action_post()
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1150.0,
            'base_amount': 1150.0,
            'amount': 115.0,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1035.0}])

        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1150.0,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1035.0,    'tax_ids': []},
            {'balance': -1150.0,   'tax_ids': []},
            {'balance': 115.0,     'tax_ids': []},
            {'balance': 1150.0,    'tax_ids': []},
            {'balance': -1150.0,   'tax_ids': wth_tax_affecting.ids},
        ])

    def test_case_d(self):
        vat_tax = self.percent_tax(15)
        wth_tax_affecting = self.percent_tax(-10, include_base_amount=True, is_withholding_tax_on_payment=True)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'account_id': self.purchase_account.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(vat_tax.ids)],
            })],
        })
        invoice.action_post()
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1000.0,
            'base_amount': 1000.0,
            'amount': 100.0,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1050.0}])

        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1150.0,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1050.0,    'tax_ids': []},
            {'balance': -1150.0,   'tax_ids': []},
            {'balance': 100.0,     'tax_ids': []},
            {'balance': 1000.0,    'tax_ids': []},
            {'balance': -1000.0,   'tax_ids': wth_tax_affecting.ids},
        ])

    def test_case_e(self):
        vat_tax_incl_affecting = self.percent_tax(15, price_include_override='tax_included', include_base_amount=True)
        vat_tax_affecting = self.percent_tax(15, include_base_amount=True)
        wth_tax_affecting = self.percent_tax(-10, include_base_amount=True, is_withholding_tax_on_payment=True)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'account_id': self.purchase_account.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set((vat_tax_incl_affecting | vat_tax_affecting).ids)],
            })],
        })
        invoice.action_post()
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1150.0,
            'base_amount': 1150.0,
            'amount': 115.0,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1035.0}])

        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1150.0,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1035.0,    'tax_ids': []},
            {'balance': -1150.0,   'tax_ids': []},
            {'balance': 115.0,     'tax_ids': []},
            {'balance': 1150.0,    'tax_ids': []},
            {'balance': -1150.0,   'tax_ids': wth_tax_affecting.ids},
        ])

    def test_case_f(self):
        vat_tax_incl_affecting = self.percent_tax(15, price_include_override='tax_included', include_base_amount=True)
        vat_tax = self.percent_tax(15)
        wth_tax_affecting = self.percent_tax(-10, include_base_amount=True, is_withholding_tax_on_payment=True)
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'account_id': self.purchase_account.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set((vat_tax_incl_affecting | vat_tax).ids)],
            })],
        })
        invoice.action_post()
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1000.0,
            'base_amount': 1000.0,
            'amount': 100.0,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1050.0}])

        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1150.0,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1050.0,    'tax_ids': []},
            {'balance': -1150.0,   'tax_ids': []},
            {'balance': 100.0,     'tax_ids': []},
            {'balance': 1000.0,    'tax_ids': []},
            {'balance': -1000.0,   'tax_ids': wth_tax_affecting.ids},
        ])

    def test_case_g(self):
        vat_tax_incl_affecting = self.percent_tax(15, price_include_override='tax_included', include_base_amount=True)
        vat_tax_affecting_affected = self.percent_tax(15, include_base_amount=True, is_base_affected=False)
        wth_tax_affecting = self.percent_tax(-10, include_base_amount=True, is_withholding_tax_on_payment=True)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'account_id': self.purchase_account.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set((vat_tax_incl_affecting | vat_tax_affecting_affected).ids)],
            })],
        })
        invoice.action_post()
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1130.44,
            'base_amount': 1130.44,
            'amount': 113.04,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1017.4}])

        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1130.44,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1017.4,    'tax_ids': []},
            {'balance': -1130.44,   'tax_ids': []},
            {'balance': 113.04,     'tax_ids': []},
            {'balance': 1130.44,    'tax_ids': []},
            {'balance': -1130.44,   'tax_ids': wth_tax_affecting.ids},
        ])

    def test_case_h(self):
        vat_tax_incl_affecting = self.percent_tax(15, price_include_override='tax_included', include_base_amount=True)
        vat_tax_affected = self.percent_tax(15, is_base_affected=False)
        wth_tax_affecting = self.percent_tax(-10, include_base_amount=True, is_withholding_tax_on_payment=True)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'account_id': self.purchase_account.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set((vat_tax_incl_affecting | vat_tax_affected).ids)],
            })],
        })
        invoice.action_post()
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1000.00,
            'base_amount': 1000.00,
            'amount': 100.00,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1030.44}])

        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1130.44,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1030.44,    'tax_ids': []},
            {'balance': -1130.44,   'tax_ids': []},
            {'balance': 100.00,     'tax_ids': []},
            {'balance': 1000.00,    'tax_ids': []},
            {'balance': -1000.00,   'tax_ids': wth_tax_affecting.ids},
        ])

    def test_case_i(self):
        vat_tax_incl = self.percent_tax(15, price_include_override='tax_included')
        vat_tax_affecting = self.percent_tax(15, include_base_amount=True)
        wth_tax_affecting = self.percent_tax(-10, include_base_amount=True, is_withholding_tax_on_payment=True)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'account_id': self.purchase_account.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set((vat_tax_incl | vat_tax_affecting).ids)],
            })],
        })
        invoice.action_post()
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1000.01,
            'base_amount': 1000.01,
            'amount': 100.00,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1030.44}])

        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1130.44,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1030.44,    'tax_ids': []},
            {'balance': -1130.44,   'tax_ids': []},
            {'balance': 100.00,     'tax_ids': []},
            {'balance': 1000.01,    'tax_ids': []},
            {'balance': -1000.01,   'tax_ids': wth_tax_affecting.ids},
        ])

    def test_case_j(self):
        vat_tax_incl = self.percent_tax(15, price_include_override='tax_included')
        vat_tax = self.percent_tax(15)
        wth_tax_affecting = self.percent_tax(-10, include_base_amount=True, is_withholding_tax_on_payment=True)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'account_id': self.purchase_account.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set((vat_tax_incl | vat_tax).ids)],
            })],
        })
        invoice.action_post()
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 869.57,
            'base_amount': 869.57,
            'amount': 86.96,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1043.48}])

        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1130.44,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1043.48,    'tax_ids': []},
            {'balance': -1130.44,   'tax_ids': []},
            {'balance': 86.96,      'tax_ids': []},
            {'balance': 869.57,     'tax_ids': []},
            {'balance': -869.57,    'tax_ids': wth_tax_affecting.ids},
        ])

    # Note, tests were written based on a spreadsheet that was worked on collaboratively, which is why test case K was skipped.

    def test_case_l(self):
        vat_tax_incl_affecting = self.percent_tax(15, price_include_override='tax_included', include_base_amount=True)
        wth_tax_affecting = self.percent_tax(-10, include_base_amount=True, is_withholding_tax_on_payment=True)
        vat_tax_affecting = self.percent_tax(15, include_base_amount=True)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'account_id': self.purchase_account.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set((vat_tax_incl_affecting | wth_tax_affecting | vat_tax_affecting).ids)],
            })],
        })
        invoice.action_post()
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1000.00,
            'base_amount': 1000.00,
            'amount': 100.00,
        }])

        self.assertRecordValues(wizard, [{'withholding_net_amount': 1050.00}])

        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1150.00,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1050.00,    'tax_ids': []},
            {'balance': -1150.00,   'tax_ids': []},
            {'balance': 100.00,      'tax_ids': []},
            {'balance': 1000.00,     'tax_ids': []},
            {'balance': -1000.00,    'tax_ids': wth_tax_affecting.ids},
        ])

    def test_invoice_total_unaffected(self):
        """ Ensure that the invoice total is not affected by a withholding tax set on the line. """
        vat_tax = self.percent_tax(15)
        self.percent_tax(-10, include_base_amount=True, is_withholding_tax_on_payment=True)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'account_id': self.purchase_account.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(vat_tax.ids)],
            })],
        })
        invoice.action_post()
        # Simply check the total, we should see a base of 1000, affected by tax d, but not tax g
        self.assertRecordValues(invoice, [{
            'amount_untaxed': 1000.00,
            'amount_tax': 150.00,
            'amount_total': 1150.00,
        }])
        self.assert_invoice_tax_totals_summary(
            invoice,
            {
                'base_amount_currency': 1000.00,
                'tax_amount_currency': 150.00,
                'total_amount_currency': 1150.00,
            },
            soft_checking=True,
        )
