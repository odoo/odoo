# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.account.tests.common import TestTaxCommon
from odoo.addons.analytic.tests.common import AnalyticCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nAccountWithholdingTaxesNew(TestTaxCommon, AnalyticCommon):

    @classmethod
    def setUpClass(cls):
        """ Prepare a few taxes that we will use in the following test cases. """
        super().setUpClass()
        # We will have two withholding taxes, one for each mode.
        cls.tax_wth_seq = cls.env['ir.sequence'].create({
            'implementation': 'no_gap',
            'name': 'Withholding tax excluded Sequence',
            'padding': 4,
            'number_increment': 1,
        })
        cls.tax_wth_excluded = cls.percent_tax(cls, 10, price_include_override='tax_excluded', is_withholding_tax_on_payment=True, withholding_sequence_id=cls.tax_wth_seq.id)
        cls.tax_wth_included = cls.percent_tax(cls, 10, price_include_override='tax_included', is_withholding_tax_on_payment=True, withholding_sequence_id=cls.tax_wth_seq.id)
        # Then a set of 4 "vat" tax that are is_base_affected.
        cls.tax_vat_excl_affecting = cls.percent_tax(cls, 15, price_include_override='tax_excluded', include_base_amount=True, is_withholding_tax_on_payment=True)
        cls.tax_vat_excl_not_affecting = cls.percent_tax(cls, 15, price_include_override='tax_excluded', is_withholding_tax_on_payment=True)
        cls.tax_vat_incl_affecting = cls.percent_tax(cls, 15, price_include_override='tax_included', include_base_amount=True, is_withholding_tax_on_payment=True)
        cls.tax_vat_incl_not_affecting = cls.percent_tax(cls, 15, price_include_override='tax_included', is_withholding_tax_on_payment=True)
        # And finally two "vat" taxes that are not is_base_affected
        cls.tax_vat_excl_not_affected = cls.percent_tax(cls, 15, price_include_override='tax_excluded', is_base_affected=False, is_withholding_tax_on_payment=True)
        cls.tax_vat_incl_not_affected = cls.percent_tax(cls, 15, price_include_override='tax_included', is_base_affected=False, is_withholding_tax_on_payment=True)

    # ----------------------------------------------------
    # Note: follows the numbering in the test file for now
    # ----------------------------------------------------

    def test_case_2(self):
        """ tax_vat_excl_affecting, tax_wth_included """
        # Set the sequence explicitly to match our test case.
        self.tax_vat_excl_affecting.sequence = 1
        self.tax_wth_included.sequence = 2

        invoice = self.init_invoice('out_invoice', post=True, amounts=[900], taxes=[self.tax_vat_excl_affecting, self.tax_wth_included])
        # Assert the invoice line values.
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [{
                'price_subtotal': 1000.00,
                'price_total': 1150.00,
            }]
        )
        # Assert the invoice values.
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
        # Assert the wizard values.
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'base_amount': 1150.00,
            'amount': 115.00,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1000.0}])
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1150.00,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1035.00,     'tax_ids': []},
            {'balance': -1150.00,    'tax_ids': []},
            {'balance': 115.00,       'tax_ids': []},
            {'balance': 1150.00,     'tax_ids': self.tax_wth_included.ids},
            {'balance': -1150.00,    'tax_ids': []},
        ])

    def test_case_3(self):
        """ tax_vat_incl_affecting, tax_wth_included """
        # Set the sequence explicitly to match our test case.
        self.tax_vat_incl_affecting.sequence = 1
        self.tax_wth_included.sequence = 2

        invoice = self.init_invoice('out_invoice', post=True, amounts=[900], taxes=[self.tax_vat_incl_affecting, self.tax_wth_included])
        # Assert the invoice line values.
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [{
                'price_subtotal': 869.57,
                'price_total': 1000.00,
            }]
        )
        # Assert the invoice values.
        self.assertRecordValues(invoice, [{
            'amount_untaxed': 869.57,
            'amount_tax': 130.43,
            'amount_total': 1000.00,
        }])
        self.assert_invoice_tax_totals_summary(
            invoice,
            {
                'base_amount_currency': 869.57,
                'tax_amount_currency': 130.43,
                'total_amount_currency': 1000.00,
            },
            soft_checking=True,
        )
        # Assert the wizard values.
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'base_amount': 1000.00,
            'amount': 100.00,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 900.00}])
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 900.00,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 900.00,     'tax_ids': []},
            {'balance': -1000.00,    'tax_ids': []},
            {'balance': 100.00,       'tax_ids': []},
            {'balance': 1000.00,     'tax_ids': self.tax_wth_included.ids},
            {'balance': -1000.00,    'tax_ids': []},
        ])

    def test_case_4(self):
        """ tax_vat_excl_not_affecting, tax_wth_included """
        # Set the sequence explicitly to match our test case.
        self.tax_vat_excl_not_affecting.sequence = 1
        self.tax_wth_included.sequence = 2

        invoice = self.init_invoice('out_invoice', post=True, amounts=[900], taxes=[self.tax_vat_excl_not_affecting, self.tax_wth_included])
        # Assert the invoice line values.
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [{
                'price_subtotal': 1000.00,
                'price_total': 1150.00,
            }]
        )
        # Assert the invoice values.
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
        # Assert the wizard values.
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'base_amount': 1000.00,
            'amount': 100.00,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1050.00}])
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1050.00,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1050.00,     'tax_ids': []},
            {'balance': -1150.00,    'tax_ids': []},
            {'balance': 100.00,       'tax_ids': []},
            {'balance': 1000.00,     'tax_ids': self.tax_wth_included.ids},
            {'balance': -1000.00,    'tax_ids': []},
        ])

    def test_case_5(self):
        """ tax_vat_incl_not_affecting, tax_wth_included """
        # Set the sequence explicitly to match our test case.
        self.tax_vat_incl_not_affecting.sequence = 1
        self.tax_wth_included.sequence = 2

        invoice = self.init_invoice('out_invoice', post=True, amounts=[900], taxes=[self.tax_vat_incl_not_affecting, self.tax_wth_included])
        # Assert the invoice line values.
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [{
                'price_subtotal': 869.57,
                'price_total': 1000.00,
            }]
        )
        # Assert the invoice values.
        self.assertRecordValues(invoice, [{
            'amount_untaxed': 869.57,
            'amount_tax': 130.43,
            'amount_total': 1000.00,
        }])
        self.assert_invoice_tax_totals_summary(
            invoice,
            {
                'base_amount_currency': 869.57,
                'tax_amount_currency': 130.43,
                'total_amount_currency': 1000.00,
            },
            soft_checking=True,
        )
        # Assert the wizard values.
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'base_amount': 869.57,
            'amount': 86.96,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 913.04}])
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 913.04,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 913.04,     'tax_ids': []},
            {'balance': -1000.00,    'tax_ids': []},
            {'balance': 86.96,       'tax_ids': []},
            {'balance': 869.57,     'tax_ids': self.tax_wth_included.ids},
            {'balance': -869.57,    'tax_ids': []},
        ])

    def test_case_7(self):
        """ tax_vat_excl_affecting, tax_wth_excluded """
        # Set the sequence explicitly to match our test case.
        self.tax_vat_excl_affecting.sequence = 1
        self.tax_wth_excluded.sequence = 2

        invoice = self.init_invoice('out_invoice', post=True, amounts=[1000], taxes=[self.tax_vat_excl_affecting, self.tax_wth_excluded])
        # Assert the invoice line values.
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [{
                'price_subtotal': 1000.00,
                'price_total': 1150.00,
            }]
        )
        # Assert the invoice values.
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
        # Assert the wizard values.
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'base_amount': 1150.00,
            'amount': 115.00,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1035.00}])
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1035.00,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1035.00,     'tax_ids': []},
            {'balance': -1150.00,    'tax_ids': []},
            {'balance': 115.00,       'tax_ids': []},
            {'balance': 1150.00,     'tax_ids': self.tax_wth_excluded.ids},
            {'balance': -1150.00,    'tax_ids': []},
        ])

    def test_case_8(self):
        """ tax_vat_incl_affecting, tax_wth_excluded """
        # Set the sequence explicitly to match our test case.
        self.tax_vat_incl_affecting.sequence = 1
        self.tax_wth_excluded.sequence = 2

        invoice = self.init_invoice('out_invoice', post=True, amounts=[1000], taxes=[self.tax_vat_incl_affecting, self.tax_wth_excluded])
        # Assert the invoice line values.
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [{
                'price_subtotal': 869.57,
                'price_total': 1000.00,
            }]
        )
        # Assert the invoice values.
        self.assertRecordValues(invoice, [{
            'amount_untaxed': 869.57,
            'amount_tax': 130.43,
            'amount_total': 1000.00,
        }])
        self.assert_invoice_tax_totals_summary(
            invoice,
            {
                'base_amount_currency': 869.57,
                'tax_amount_currency': 130.43,
                'total_amount_currency': 1000.00,
            },
            soft_checking=True,
        )
        # Assert the wizard values.
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'base_amount': 1000.00,
            'amount': 100.00,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 900.00}])
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 900.00,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 900.00,     'tax_ids': []},
            {'balance': -1000.00,    'tax_ids': []},
            {'balance': 100.00,       'tax_ids': []},
            {'balance': 1000.00,     'tax_ids': self.tax_wth_excluded.ids},
            {'balance': -1000.00,    'tax_ids': []},
        ])

    def test_case_9(self):
        """ tax_vat_excl_not_affecting, tax_wth_excluded """
        # Set the sequence explicitly to match our test case.
        self.tax_vat_excl_not_affecting.sequence = 1
        self.tax_wth_excluded.sequence = 2

        invoice = self.init_invoice('out_invoice', post=True, amounts=[1000], taxes=[self.tax_vat_excl_not_affecting, self.tax_wth_excluded])
        # Assert the invoice line values.
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [{
                'price_subtotal': 1000.00,
                'price_total': 1150.00,
            }]
        )
        # Assert the invoice values.
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
        # Assert the wizard values.
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'base_amount': 1000.00,
            'amount': 100.00,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1050.00}])
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1050.00,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1050.00,     'tax_ids': []},
            {'balance': -1150.00,    'tax_ids': []},
            {'balance': 100.00,       'tax_ids': []},
            {'balance': 1000.00,     'tax_ids': self.tax_wth_excluded.ids},
            {'balance': -1000.00,    'tax_ids': []},
        ])

    def test_case_10(self):
        """ tax_vat_incl_not_affecting, tax_wth_excluded """
        # Set the sequence explicitly to match our test case.
        self.tax_vat_incl_not_affecting.sequence = 1
        self.tax_wth_excluded.sequence = 2

        invoice = self.init_invoice('out_invoice', post=True, amounts=[1000], taxes=[self.tax_vat_incl_not_affecting, self.tax_wth_excluded])
        # Assert the invoice line values.
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [{
                'price_subtotal': 869.57,
                'price_total': 1000.00,
            }]
        )
        # Assert the invoice values.
        self.assertRecordValues(invoice, [{
            'amount_untaxed': 869.57,
            'amount_tax': 130.43,
            'amount_total': 1000.00,
        }])
        self.assert_invoice_tax_totals_summary(
            invoice,
            {
                'base_amount_currency': 869.57,
                'tax_amount_currency': 130.43,
                'total_amount_currency': 1000.00,
            },
            soft_checking=True,
        )
        # Assert the wizard values.
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'base_amount': 869.57,
            'amount': 86.96,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 913.04}])
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 913.04,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 913.04,     'tax_ids': []},
            {'balance': -1000.00,    'tax_ids': []},
            {'balance': 86.96,       'tax_ids': []},
            {'balance': 869.57,     'tax_ids': self.tax_wth_excluded.ids},
            {'balance': -869.57,    'tax_ids': []},
        ])

    def test_case_11(self):
        """ tax_vat_excl_not_affected, tax_wth_included """
        # Set the sequence explicitly to match our test case.
        self.tax_wth_included.sequence = 1
        self.tax_vat_excl_not_affected.sequence = 2

        invoice = self.init_invoice('out_invoice', post=True, amounts=[900], taxes=[self.tax_wth_included, self.tax_vat_excl_not_affected])
        # Assert the invoice line values.
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [{
                'price_subtotal': 1000.00,
                'price_total': 1135.00,
            }]
        )
        # Assert the invoice values.
        self.assertRecordValues(invoice, [{
            'amount_untaxed': 1000.00,
            'amount_tax': 135.00,
            'amount_total': 1135.00,
        }])
        self.assert_invoice_tax_totals_summary(
            invoice,
            {
                'base_amount_currency': 1000.00,
                'tax_amount_currency': 135.00,
                'total_amount_currency': 1135.00,
            },
            soft_checking=True,
        )
        # Assert the wizard values.
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'base_amount': 1000.00,
            'amount': 100.00,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1035.00}])
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1035.00,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1035.00,     'tax_ids': []},
            {'balance': -1135.00,    'tax_ids': []},
            {'balance': 100.00,       'tax_ids': []},
            {'balance': 1000.00,     'tax_ids': self.tax_wth_included.ids},
            {'balance': -1000.00,    'tax_ids': []},
        ])

    def test_case_12(self):
        """ tax_vat_incl_not_affected, tax_wth_included """
        # Set the sequence explicitly to match our test case.
        self.tax_wth_included.sequence = 1
        self.tax_vat_incl_not_affected.sequence = 2

        invoice = self.init_invoice('out_invoice', post=True, amounts=[900], taxes=[self.tax_wth_included, self.tax_vat_incl_not_affected])
        # Assert the invoice line values.
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [{
                'price_subtotal': 882.61,
                'price_total': 1000.00,
            }]
        )
        # Assert the invoice values.
        self.assertRecordValues(invoice, [{
            'amount_untaxed': 882.61,
            'amount_tax': 117.39,
            'amount_total': 1000.00,
        }])
        self.assert_invoice_tax_totals_summary(
            invoice,
            {
                'base_amount_currency': 882.61,
                'tax_amount_currency': 117.39,
                'total_amount_currency': 1000.00,
            },
            soft_checking=True,
        )
        # Assert the wizard values.
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'base_amount': 1000.00,
            'amount': 100.00,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 900.00}])
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 900.00,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 900.00,     'tax_ids': []},
            {'balance': -1000.00,    'tax_ids': []},
            {'balance': 100.00,       'tax_ids': []},
            {'balance': 1000.00,     'tax_ids': self.tax_wth_included.ids},
            {'balance': -1000.00,    'tax_ids': []},
        ])

    def test_case_13(self):
        """ tax_vat_excl_not_affected, tax_wth_excluded """
        # Set the sequence explicitly to match our test case.
        self.tax_wth_excluded.sequence = 1
        self.tax_vat_excl_not_affected.sequence = 2

        invoice = self.init_invoice('out_invoice', post=True, amounts=[1000], taxes=[self.tax_wth_excluded, self.tax_vat_excl_not_affected])
        # Assert the invoice line values.
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [{
                'price_subtotal': 1000.00,
                'price_total': 1150.00,
            }]
        )
        # Assert the invoice values.
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
        # Assert the wizard values.
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'base_amount': 1000.00,
            'amount': 100.00,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 1050.00}])
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 1050.00,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 1050.00,     'tax_ids': []},
            {'balance': -1150.00,    'tax_ids': []},
            {'balance': 100.00,       'tax_ids': []},
            {'balance': 1000.00,     'tax_ids': self.tax_wth_included.ids},
            {'balance': -1000.00,    'tax_ids': []},
        ])

    def test_case_14(self):
        """ tax_vat_incl_not_affected, tax_wth_excluded """
        # Set the sequence explicitly to match our test case.
        self.tax_wth_excluded.sequence = 1
        self.tax_vat_incl_not_affected.sequence = 2

        invoice = self.init_invoice('out_invoice', post=True, amounts=[1000], taxes=[self.tax_wth_excluded, self.tax_vat_incl_not_affected])
        # Assert the invoice line values.
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [{
                'price_subtotal': 869.57,
                'price_total': 1000.00,
            }]
        )
        # Assert the invoice values.
        self.assertRecordValues(invoice, [{
            'amount_untaxed': 869.57,
            'amount_tax': 130.43,
            'amount_total': 1000.00,
        }])
        self.assert_invoice_tax_totals_summary(
            invoice,
            {
                'base_amount_currency': 869.57,
                'tax_amount_currency': 130.43,
                'total_amount_currency': 1000.00,
            },
            soft_checking=True,
        )
        # Assert the wizard values.
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'base_amount': 1000.00,
            'amount': 100.00,
        }])
        self.assertRecordValues(wizard, [{'withholding_net_amount': 900.00}])
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{
            'amount': 900.00,
        }])
        self.assertRecordValues(payment.move_id.line_ids, [
            {'balance': 900.00,     'tax_ids': []},
            {'balance': -1000.00,    'tax_ids': []},
            {'balance': 100.00,       'tax_ids': []},
            {'balance': 1000.00,     'tax_ids': self.tax_wth_included.ids},
            {'balance': -1000.00,    'tax_ids': []},
        ])
