# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.account.tests.common import TestTaxCommon
from odoo.addons.analytic.tests.common import AnalyticCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nAccountWithholdingTaxesNew(TestTaxCommon, AnalyticCommon):

    # -------------------------------------------------
    # Tests basic scenarios described in account_tax.py
    # -------------------------------------------------

    def test_scenario_1(self):
        """
            Tax A: Price-excluded withholding tax of 10%

            Product Line                                  Withholding Line                  Payment Total
            ______________________________________       __________________________                   900
           | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
           |        900 | A    |     1000 |  1000 |     |        1000 |        100 |
            ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
            The withholding tax being price-excluded, the subtotal is adapted to include the tax.
            This is so that the tax does not affect the invoice at the time of registering.
            When registering the withholding tax, we calculate the tax amount and reduce the payment from
            this amount.
        """
        tax_a = self.percent_tax(10, price_include_override='tax_excluded', is_withholding_tax_on_payment=True)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'price_unit': 900.0,
                'tax_ids': [Command.set(tax_a.ids)],
            })],
        })
        invoice.action_post()
        self.assertRecordValues(invoice, [{
            'amount_untaxed': 1000.0,
            'amount_tax': 0.0,
            'amount_total': 1000.0,
        }])
        self.assert_invoice_tax_totals_summary(
            invoice,
            {
                'base_amount_currency': 1000.0,
                'tax_amount_currency': 0.0,
                'total_amount_currency': 1000.0,
            },
            soft_checking=True,
        )
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1000.0,
            'base_amount': 1000.0,
            'amount': 100.0,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 900.0}])

        wizard.withholding_line_ids[0].name = '123'
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 900.0,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 900.0,     'tax_ids': []},
            {'balance': -1000.0,    'tax_ids': []},
            {'balance': 100.0,       'tax_ids': []},
            {'balance': 1000.0,     'tax_ids': tax_a.ids},
            {'balance': -1000.0,    'tax_ids': []},
        ])

    def test_scenario_2(self):
        """
            Tax A: Price-excluded withholding tax of 10%
            Tax C: Price-excluded tax of 15%, which affects the base of other taxes

            Product Line                                  Withholding Line                  Payment Total
            ______________________________________       __________________________                  1035
           | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
           |        900 | C, A |     1000 |  1150 |     |        1150 |        115 |
            ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
            We recompute the subtotal as above, and then apply the price-excluded tax based on that subtotal.
            On the withholding line, we calculate the tax amount based on the TOTAL PRICE of the line.
        """
        tax_a = self.percent_tax(10, price_include_override='tax_excluded', is_withholding_tax_on_payment=True, sequence=2)
        tax_c = self.percent_tax(15, price_include_override='tax_excluded', include_base_amount=True, sequence=1)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'price_unit': 900.0,
                'tax_ids': [Command.set((tax_a | tax_c).ids)],
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
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1150.0,
            'base_amount': 1150.0,
            'amount': 115.0,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1035.0}])

        wizard.withholding_line_ids[0].name = '123'
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1035.0,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1035.0,     'tax_ids': []},
            {'balance': -1150.0,    'tax_ids': []},
            {'balance': 115.0,       'tax_ids': []},
            {'balance': 1150.0,     'tax_ids': tax_a.ids},
            {'balance': -1150.0,    'tax_ids': []},
        ])

    def test_scenario_3(self):
        """
            Tax A: Price-excluded withholding tax of 10%
            Tax E: Price-included tax of 15%, which affects the base of other taxes

            Product Line                                  Withholding Line                  Payment Total
            ______________________________________       __________________________                   900
           | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
           |        900 | E, A |   869.57 |  1000 |     |        1000 |        100 |
            ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
            In this case, the subtotal will be computed to exclude the 15% tax E from the subtotal you would
            have with only the withholding tax (1000).
            The payment registration will be the same as for Scenario 1.
        """
        tax_a = self.percent_tax(10, price_include_override='tax_excluded', is_withholding_tax_on_payment=True, sequence=2)
        tax_e = self.percent_tax(15, price_include_override='tax_included', include_base_amount=True, sequence=1)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'price_unit': 900.0,
                'tax_ids': [Command.set((tax_a | tax_e).ids)],
            })],
        })
        invoice.action_post()
        self.assertRecordValues(invoice, [{
            'amount_untaxed': 869.57,
            'amount_tax': 130.43,
            'amount_total': 1000.0,
        }])
        self.assert_invoice_tax_totals_summary(
            invoice,
            {
                'base_amount_currency': 869.57,
                'tax_amount_currency': 130.43,
                'total_amount_currency': 1000.0,
            },
            soft_checking=True,
        )
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1000.0,
            'base_amount': 1000.0,
            'amount': 100.0,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 900.0}])

        wizard.withholding_line_ids[0].name = '123'
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 900.0,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 900.0,     'tax_ids': []},
            {'balance': -1000.0,    'tax_ids': []},
            {'balance': 100.0,       'tax_ids': []},
            {'balance': 1000.0,     'tax_ids': tax_a.ids},
            {'balance': -1000.0,    'tax_ids': []},
        ])

    def test_scenario_4(self):
        """
            Tax A: Price-excluded withholding tax of 10%
            Tax D: Price-excluded tax of 15%, which does not affect the base of other taxes

            Product Line                                  Withholding Line                  Payment Total
            ______________________________________       __________________________                  1050
           | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
           |        900 | D, A |    1000  |  1150 |     |        1000 |        100 |
            ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
            Similar to Scenario 2, but in this case the withholding tax base is not affected by the regular
            tax.
        """
        tax_a = self.percent_tax(10, price_include_override='tax_excluded', is_withholding_tax_on_payment=True, sequence=2)
        tax_d = self.percent_tax(15, price_include_override='tax_excluded', sequence=1)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'price_unit': 900.0,
                'tax_ids': [Command.set((tax_a | tax_d).ids)],
            })],
        })
        invoice.action_post()
        self.assertRecordValues(invoice, [{
            'amount_untaxed': 1000.0,
            'amount_tax': 115.0,
            'amount_total': 1150.0,
        }])
        self.assert_invoice_tax_totals_summary(
            invoice,
            {
                'base_amount_currency': 1000.0,
                'tax_amount_currency': 115.0,
                'total_amount_currency': 1115.0,
            },
            soft_checking=True,
        )
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1000.0,
            'base_amount': 1000.0,
            'amount': 100.0,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 900.0}])

        wizard.withholding_line_ids[0].name = '123'
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 900.0,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 900.0,     'tax_ids': []},
            {'balance': -1000.0,    'tax_ids': []},
            {'balance': 100.0,       'tax_ids': []},
            {'balance': 1000.0,     'tax_ids': tax_a.ids},
            {'balance': -1000.0,    'tax_ids': []},
        ])

    def test_scenario_5(self):
        """
            Tax A: Price-excluded withholding tax of 10%
            Tax F: Price-included tax of 15%, which does not affect the base of other taxes

            Product Line                                  Withholding Line                  Payment Total
            ______________________________________       __________________________                913.04
           | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
           |        900 | F, A |  869.57  |  1000 |     |      869.57 |      86.96 |
            ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
            Similar to Scenario 3, but in this case the withholding tax base is not affected by the regular
            tax.
        """
        tax_a = self.percent_tax(10, price_include_override='tax_excluded', is_withholding_tax_on_payment=True, sequence=2)
        tax_f = self.percent_tax(15, price_include_override='tax_included', sequence=1)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'price_unit': 900.0,
                'tax_ids': [Command.set((tax_a | tax_f).ids)],
            })],
        })
        invoice.action_post()
        self.assertRecordValues(invoice, [{
            'amount_untaxed': 869.57,
            'amount_tax': 130.43,
            'amount_total': 1000.0,
        }])
        self.assert_invoice_tax_totals_summary(
            invoice,
            {
                'base_amount_currency': 869.57,
                'tax_amount_currency': 130.43,
                'total_amount_currency': 1000.0,
            },
            soft_checking=True,
        )
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 869.57,
            'base_amount': 869.57,
            'amount': 86.96,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 913.04}])

        wizard.withholding_line_ids[0].name = '123'
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 913.04,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 913.04,     'tax_ids': []},
            {'balance': -1000.0,    'tax_ids': []},
            {'balance': 86.96,       'tax_ids': []},
            {'balance': 869.57,     'tax_ids': tax_a.ids},
            {'balance': -869.57,    'tax_ids': []},
        ])

    def test_scenario_6(self):
        """
            Tax B: Price-included withholding tax of 10%

            Product Line                                  Withholding Line                  Payment Total
            ______________________________________       __________________________                   900
           | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
           |       1000 | B    |     1000 |  1000 |     |        1000 |        100 |
            ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
            With price-included withholding tax (the default), there is no effect on the invoice.
            The main difference with price-excluded is that in these cases, the subtotal will match the price unit * quantity.
            The withholding line amounts are the same as for price-excluded taxes. (this will be the case for each scenario)
            This means that when calculating the withholding line amount for price-included withholding tax,
            the calculation should treat these as tax-excluded taxes.
        """
        tax_b = self.percent_tax(10, price_include_override='tax_included', is_withholding_tax_on_payment=True)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'price_unit': 1000.0,
                'tax_ids': [Command.set(tax_b.ids)],
            })],
        })
        invoice.action_post()
        self.assertRecordValues(invoice, [{
            'amount_untaxed': 1000.0,
            'amount_tax': 0.0,
            'amount_total': 1000.0,
        }])
        self.assert_invoice_tax_totals_summary(
            invoice,
            {
                'base_amount_currency': 1000.0,
                'tax_amount_currency': 0.0,
                'total_amount_currency': 1000.0,
            },
            soft_checking=True,
        )
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1000.0,
            'base_amount': 1000.0,
            'amount': 100.0,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 900.0}])

        wizard.withholding_line_ids[0].name = '123'
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 900.0,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 900.0,     'tax_ids': []},
            {'balance': -1000.0,    'tax_ids': []},
            {'balance': 100.0,       'tax_ids': []},
            {'balance': 1000.0,     'tax_ids': tax_b.ids},
            {'balance': -1000.0,    'tax_ids': []},
        ])

    def test_scenario_7(self):
        """
            Tax B: Price-included withholding tax of 10%
            Tax C: Price-excluded tax of 15%, which affects the base of other taxes

            Product Line                                  Withholding Line                  Payment Total
            ______________________________________       __________________________                  1035
           | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
           |       1000 | C, B |     1000 |  1150 |     |        1150 |        115 |
            ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
        """
        tax_b = self.percent_tax(10, price_include_override='tax_included', is_withholding_tax_on_payment=True, sequence=2)
        tax_c = self.percent_tax(15, price_include_override='tax_excluded', include_base_amount=True, sequence=1)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'price_unit': 1000.0,
                'tax_ids': [Command.set((tax_b | tax_c).ids)],
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
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1150.0,
            'base_amount': 1150.0,
            'amount': 115.0,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1035.0}])

        wizard.withholding_line_ids[0].name = '123'
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1035.0,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1035.0,     'tax_ids': []},
            {'balance': -1150.0,    'tax_ids': []},
            {'balance': 115.0,       'tax_ids': []},
            {'balance': 1150.0,     'tax_ids': tax_b.ids},
            {'balance': -1150.0,    'tax_ids': []},
        ])

    def test_scenario_8(self):
        """
            Tax B: Price-included withholding tax of 10%
            Tax E: Price-included tax of 15%, which affects the base of other taxes

            Product Line                                  Withholding Line                  Payment Total
            ______________________________________       __________________________                   900
           | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
           |       1000 | E, B |   869.57 |  1000 |     |        1000 |        100 |
            ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
        """
        tax_b = self.percent_tax(10, price_include_override='tax_included', is_withholding_tax_on_payment=True, sequence=2)
        tax_e = self.percent_tax(15, price_include_override='tax_included', include_base_amount=True, sequence=1)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'price_unit': 1000.0,
                'tax_ids': [Command.set((tax_b | tax_e).ids)],
            })],
        })
        invoice.action_post()
        self.assertRecordValues(invoice, [{
            'amount_untaxed': 869.57,
            'amount_tax': 130.43,
            'amount_total': 1000.0,
        }])
        self.assert_invoice_tax_totals_summary(
            invoice,
            {
                'base_amount_currency': 869.57,
                'tax_amount_currency': 130.43,
                'total_amount_currency': 1000.0,
            },
            soft_checking=True,
        )
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1000.0,
            'base_amount': 1000.0,
            'amount': 100.0,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 900.0}])

        wizard.withholding_line_ids[0].name = '123'
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 900.0,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 900.0,     'tax_ids': []},
            {'balance': -1000.0,    'tax_ids': []},
            {'balance': 100.0,       'tax_ids': []},
            {'balance': 1000.0,     'tax_ids': tax_b.ids},
            {'balance': -1000.0,    'tax_ids': []},
        ])

    def test_scenario_9(self):
        """
            Tax B: Price-included withholding tax of 10%
            Tax D: Price-excluded tax of 15%, which does not affect the base of other taxes

            Product Line                                  Withholding Line                  Payment Total
            ______________________________________       __________________________                  1050
           | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
           |       1000 | D, B |    1000  |  1150 |     |        1000 |        100 |
            ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
        """
        tax_b = self.percent_tax(10, price_include_override='tax_included', is_withholding_tax_on_payment=True, sequence=2)
        tax_d = self.percent_tax(15, price_include_override='tax_excluded', sequence=1)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'price_unit': 1000.0,
                'tax_ids': [Command.set((tax_b | tax_d).ids)],
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
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 1000.0,
            'base_amount': 1000.0,
            'amount': 100.0,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1050.0}])

        wizard.withholding_line_ids[0].name = '123'
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1050.0,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1050.0,     'tax_ids': []},
            {'balance': -1150.0,    'tax_ids': []},
            {'balance': 100.0,       'tax_ids': []},
            {'balance': 1000.0,     'tax_ids': tax_b.ids},
            {'balance': -1000.0,    'tax_ids': []},
        ])

    def test_scenario_10(self):
        """
            Tax B: Price-included withholding tax of 10%
            Tax F: Price-included tax of 15%, which does not affect the base of other taxes

            Product Line                                  Withholding Line                  Payment Total
            ______________________________________       __________________________                913.04
           | Price Unit | Tax  | SubTotal | Total |     | Base Amount | Tax Amount |
           |       1000 | F, B |  869.57  |  1000 |     |      869.57 |      86.96 |
            ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯      ¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯
        """
        tax_b = self.percent_tax(10, price_include_override='tax_included', is_withholding_tax_on_payment=True, sequence=2)
        tax_f = self.percent_tax(15, price_include_override='tax_included', sequence=1)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'price_unit': 900.0,
                'tax_ids': [Command.set((tax_b | tax_f).ids)],
            })],
        })
        invoice.action_post()
        self.assertRecordValues(invoice, [{
            'amount_untaxed': 869.57,
            'amount_tax': 130.43,
            'amount_total': 1000.0,
        }])
        self.assert_invoice_tax_totals_summary(
            invoice,
            {
                'base_amount_currency': 869.57,
                'tax_amount_currency': 130.43,
                'total_amount_currency': 1000.0,
            },
            soft_checking=True,
        )
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'original_base_amount': 869.57,
            'base_amount': 869.57,
            'amount': 86.96,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 913.04}])

        wizard.withholding_line_ids[0].name = '123'
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 913.04,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 913.04,     'tax_ids': []},
            {'balance': -1000.0,    'tax_ids': []},
            {'balance': 86.96,       'tax_ids': []},
            {'balance': 869.57,     'tax_ids': tax_b.ids},
            {'balance': -869.57,    'tax_ids': []},
        ])
