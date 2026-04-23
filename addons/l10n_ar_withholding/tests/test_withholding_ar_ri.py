# -*- coding: utf-8 -*-
from datetime import datetime
from itertools import count, pairwise

from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.tests import tagged, Form
from odoo import Command
from odoo.exceptions import UserError, ValidationError


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestArWithholdingArRi(TestArCommon):
    """ Notes: In AR, a single partner will usually have 2-4 withholding lines: one "earnings" (scaling or not) and 1 or more IIBB (provincial taxes).
    In real life they should also have a VAT and SUSS withholdings, but this module doesn't really support them very well yet.
    """

    _test_user_groups = (
        'account.group_account_manager',
        'base.group_partner_manager',
    )

    @classmethod
    def setUpClass(cls):

        super().setUpClass()

        cls.env.company.withholding_tax_base_account_id = cls.env.ref('account.%i_base_tax_account' % cls.env.company.id)

        # What is withheld is owed to the tax authority until it is paid over to it.
        cls.withholding_account = cls.env['account.account'].create({
            'name': 'Withholdings to pay',
            'code': 'WTH.001',
            'account_type': 'liability_current',
        })

        cls.tax_wth_seq = cls.env['ir.sequence'].create({
            'implementation': 'standard',
            'name': 'tax wth test',
            'padding': 8,
            'number_increment': 1,
        })
        cls.earnings_withholding_sequence = cls.env['ir.sequence'].create({
            'implementation': 'standard',
            'name': 'tax wth test',
            'padding': 1,
            'number_increment': 1,
        })

        # The VAT the documents are taxed with, which the chart template owns, unlike the withholdings
        # below: what an Argentine document is worth is grouped by the ARCA code of its tax groups.
        cls.tax_21 = cls.env.ref('account.%s_ri_tax_vat_21_ventas' % cls.env.company.id)

        cls.other_currency = cls.setup_other_currency('USD', rounding=0.001, rates=[('2022-12-31', 0.01), ('2023-04-30', 0.005)])

        # The withholding taxes are written out here rather than taken from the chart template, so
        # that what the amounts the tests expect are made of can be read along with them.
        # Purchase side, which is the side Argentina withholds on.
        # 10% levied on the untaxed amount of the documents, and 10% on their total, VAT included.
        cls.tax_wth_purchase_iibb_untaxed = cls._create_withholding_tax(
            'Test IIBB WTH CABA 10%', -10,
            l10n_ar_withholding_tax_type='iibb_untaxed',
            l10n_ar_state_id=cls.env.ref('base.state_ar_c').id,
        )
        cls.tax_wth_purchase_iibb_total = cls._create_withholding_tax(
            'Test IIBB WTH PBA 10%', -10,
            l10n_ar_withholding_tax_type='iibb_total',
            l10n_ar_state_id=cls.env.ref('base.state_ar_b').id,
        )
        # Earnings regimes accumulate over the month, past a non-taxable minimum given in pesos:
        # regime 110 withholds through a progressive scale, regime 35 at a rate.
        cls.tax_wth_purchase_earnings_scale = cls._create_withholding_tax(
            'Test Profits WTH regimen 110', -1,
            l10n_ar_withholding_tax_type='earnings_scale',
            l10n_ar_scale_id=cls.env.ref('l10n_ar_withholding.normal_scale').id,
            l10n_ar_code='110',
            l10n_ar_non_taxable_amount=10000.0,
            withholding_sequence_id=cls.earnings_withholding_sequence.id,
        )
        cls.tax_wth_purchase_earnings = cls._create_withholding_tax(
            'Test Profits WTH regimen 35', -6,
            l10n_ar_withholding_tax_type='earnings',
            l10n_ar_code='35',
            l10n_ar_non_taxable_amount=7870.0,
            withholding_sequence_id=cls.earnings_withholding_sequence.id,
        )
        # Sale side, where a customer withholds from what it owes us and hands over a certificate.
        cls.tax_wth_sale_iibb_untaxed = cls._create_withholding_tax(
            'Test Sales IIBB WTH 1%', -1,
            type_tax_use='sale',
            l10n_ar_withholding_tax_type='iibb_untaxed',
        )
        cls.tax_wth_sale_earnings = cls._create_withholding_tax(
            'Test Sales Profits WTH 1%', -1,
            type_tax_use='sale',
            l10n_ar_withholding_tax_type='earnings',
        )

    @classmethod
    def _create_withholding_tax(cls, name, amount, type_tax_use='purchase', **tax_vals):
        """ A withholding tax of the company, levying its rate on what the payment settles. """
        return cls.env['account.tax'].create({
            'name': name,
            'amount_type': 'percent',
            'amount': amount,
            'type_tax_use': type_tax_use,
            'is_withholding_tax': True,
            'withholding_sequence_id': cls.tax_wth_seq.id,
            'company_id': cls.env.company.id,
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({'repartition_type': 'tax', 'account_id': cls.withholding_account.id}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({'repartition_type': 'tax', 'account_id': cls.withholding_account.id}),
            ],
            **tax_vals,
        })

    def setUp(self):
        super().setUp()
        # Documents are numbered as they are created, a test only needing them to differ.
        self.document_numbers = ('1-%s' % number for number in count(1))

    def create_invoice(self, **invoice_args):
        """ Post a vendor bill of the adhoc partner, of 1,000 taxed at 21% unless told otherwise.
        Whatever `_create_invoice_one_line` takes goes through, the values of the line included.
        """
        invoice_args.setdefault('move_type', 'in_invoice')
        invoice_args.setdefault('partner_id', self.res_partner_adhoc)
        invoice_args.setdefault('invoice_date', '2023-01-01')
        invoice_args.setdefault('l10n_latam_document_number', next(self.document_numbers))
        invoice_args.setdefault('product_id', self.product_a)
        invoice_args.setdefault('price_unit', 1000.0)
        invoice_args.setdefault('tax_ids', self.tax_21)
        invoice_args.setdefault('post', True)
        return self._create_invoice_one_line(**invoice_args)

    def payment_register(self, moves):
        """ The register payment wizard model, opened on the given documents. """
        return self.env['account.payment.register'].with_context(active_model='account.move', active_ids=moves.ids)

    def create_payment_register(self, moves, withholdings=None, **wizard_args):
        """ The register payment wizard, opened on the given documents.

        :param withholdings: a {tax: base amount} replacing the lines the regimes of the partner
            bring, an empty one leaving the payment withholding nothing at all.
        """
        wizard_args.setdefault('payment_date', '2023-01-01')
        wizard = self.payment_register(moves).create(wizard_args)
        if withholdings is not None:
            wizard.withholding_line_ids = [
                Command.clear(),
                *[
                    Command.create({'tax_id': tax.id, 'base_amount': base_amount, 'amount': 0})
                    for tax, base_amount in withholdings.items()
                ],
            ]
            wizard.withholding_line_ids._compute_amount()
        return wizard

    def create_payment(self, checks=None, post=True, **payment_args):
        """ Post a payment of the adhoc partner, taking in or handing over the given
        {check number: amount} when its method is paid in checks. """
        payment_args.setdefault('date', '2023-01-01')
        payment_args.setdefault('partner_id', self.res_partner_adhoc.id)
        if checks:
            payment_args['l10n_latam_new_check_ids'] = [
                Command.clear(),
                *[
                    Command.create({'name': name, 'amount': amount, 'payment_date': payment_args['date']})
                    for name, amount in checks.items()
                ],
            ]
        payment = self.env['account.payment'].create(payment_args)
        if post:
            payment.action_post()
        return payment

    def check_journal(self):
        """ A journal taking in third party checks and handing them over. """
        return self.env['account.journal'].create({
            'name': 'Third Party Checks',
            'type': 'cash',
            'outbound_payment_method_line_ids': [
                Command.create({'payment_method_id': self.env.ref('l10n_latam_check.account_payment_method_out_third_party_checks').id}),
            ],
            'inbound_payment_method_line_ids': [
                Command.create({'payment_method_id': self.env.ref('l10n_latam_check.account_payment_method_new_third_party_checks').id}),
                Command.create({'payment_method_id': self.env.ref('l10n_latam_check.account_payment_method_in_third_party_checks').id}),
            ],
        })

    def own_check_payment_method_line(self, payment_account=None):
        """ The method line handing over own checks, on a journal that pays with them. """
        journal = self.check_journal()
        own_checks = self.env.ref('l10n_latam_check.account_payment_method_own_checks')
        journal.outbound_payment_method_line_ids = [Command.create({
            'payment_method_id': own_checks.id,
            'payment_account_id': payment_account.id if payment_account else False,
        })]
        return journal.outbound_payment_method_line_ids.filtered(
            lambda line: line.payment_method_id == own_checks
        )[:1]

    def test_simple_full_payment(self):
        """Simple full payment in Company currency"""
        moves = self.create_invoice()
        wizard = self.create_payment_register(moves, {self.tax_wth_purchase_iibb_untaxed: sum(moves.mapped('amount_untaxed'))})
        self.assertEqual(wizard.currency_id.round(sum(wizard.withholding_line_ids.mapped('amount'))) + wizard.withholding_net_amount, wizard.amount)
        action = wizard.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            # Liquidity line:
            {'debit': 0.0, 'credit': 1110.0, 'currency_id': wizard.currency_id.id, 'amount_currency': -1110.0, 'reconciled': False},
            # base line:
            {'debit': 0.0, 'credit': 1000.0, 'currency_id': wizard.currency_id.id, 'amount_currency': -1000.0, 'reconciled': False},
            # withholding line:
            {'debit': 0.0, 'credit': 100.0, 'currency_id': wizard.currency_id.id, 'amount_currency': -100.0, 'reconciled': False},
            # base line:
            {'debit': 1000.0, 'credit': 0.0, 'currency_id': wizard.currency_id.id, 'amount_currency': 1000.0, 'reconciled': False},
            # Receivable line:
            {'debit': 1210.0, 'credit': 0.0, 'currency_id': wizard.currency_id.id, 'amount_currency': 1210.0, 'reconciled': True}
        ])
        self.assertEqual(1210, payment.amount)
        self.assertEqual(1110, payment.withholding_net_amount)

    def test_two_payments_same_invoice(self):
        """Test two payments to same invoice"""
        moves = self.create_invoice()
        withholdings = {self.tax_wth_purchase_iibb_untaxed: sum(moves.mapped('amount_untaxed')) * 0.5}

        wizard_1 = self.create_payment_register(moves, withholdings)
        wizard_1.amount = 605.00
        self.assertEqual(wizard_1.currency_id.round(sum(wizard_1.withholding_line_ids.mapped('amount'))) + wizard_1.withholding_net_amount, wizard_1.amount)
        action = wizard_1.action_create_payments()
        payment_1 = self.env['account.payment'].browse(action['res_id'])

        # Alf payments in Company currency
        wizard_2 = self.create_payment_register(moves, withholdings)
        self.assertEqual(605, wizard_2.source_amount)
        self.assertEqual(wizard_2.currency_id.round(sum(wizard_2.withholding_line_ids.mapped('amount'))) + wizard_2.withholding_net_amount, wizard_2.amount)
        action = wizard_2.action_create_payments()
        payment_2 = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment_1.move_id.line_ids.sorted('balance'), [
            # Liquidity line:
            {'debit': 0.0, 'credit': 555.0, 'currency_id': wizard_1.currency_id.id, 'amount_currency': -555.0, 'reconciled': False},
            # base line:
            {'debit': 0.0, 'credit': 500.0, 'currency_id': wizard_1.currency_id.id, 'amount_currency': -500.0, 'reconciled': False},
            # withholding line:
            {'debit': 0.0, 'credit': 50.0, 'currency_id': wizard_1.currency_id.id, 'amount_currency': -50.0, 'reconciled': False},
            # base line:
            {'debit': 500, 'credit': 0.0, 'currency_id': wizard_1.currency_id.id, 'amount_currency': 500, 'reconciled': False},
            # Receivable line:
            {'debit': 605.0, 'credit': 0.0, 'currency_id': wizard_1.currency_id.id, 'amount_currency': 605.0, 'reconciled': True}
        ])
        self.assertEqual(605, payment_1.amount)
        self.assertEqual(555, payment_1.withholding_net_amount)

        self.assertRecordValues(payment_2.move_id.line_ids.sorted('balance'), [
            # Liquidity line:
            {'debit': 0.0, 'credit': 555.0, 'currency_id': wizard_2.currency_id.id, 'amount_currency': -555.0, 'reconciled': False},
            # base line:
            {'debit': 0.0, 'credit': 500.0, 'currency_id': wizard_2.currency_id.id, 'amount_currency': -500.0, 'reconciled': False},
            # withholding line:
            {'debit': 0.0, 'credit': 50.0, 'currency_id': wizard_2.currency_id.id, 'amount_currency': -50.0, 'reconciled': False},
            # base line:
            {'debit': 500, 'credit': 0.0, 'currency_id': wizard_2.currency_id.id, 'amount_currency': 500, 'reconciled': False},
            # Receivable line:
            {'debit': 605.0, 'credit': 0.0, 'currency_id': wizard_2.currency_id.id, 'amount_currency': 605.0, 'reconciled': True}
        ])
        self.assertEqual(605, payment_2.amount)
        self.assertEqual(555, payment_2.withholding_net_amount)

    def test_two_withholdings_one_payment(self):
        """Simple full payment in Company currency and two wht"""
        moves = self.create_invoice(product_id=self.product_b)
        wizard = self.create_payment_register(moves, {
            self.tax_wth_purchase_iibb_untaxed: sum(moves.mapped('amount_untaxed')),
            self.tax_wth_purchase_iibb_total: sum(moves.mapped('amount_total')),
        })
        self.assertEqual(wizard.currency_id.round(sum(wizard.withholding_line_ids.mapped('amount'))) + wizard.withholding_net_amount, wizard.amount)
        action = wizard.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        line_1 = payment.move_id.line_ids.filtered(lambda x: x.tax_line_id.id == self.tax_wth_purchase_iibb_untaxed.id)
        line_2 = payment.move_id.line_ids.filtered(lambda x: x.tax_line_id.id == self.tax_wth_purchase_iibb_total.id)
        self.assertEqual(-100, line_1.amount_currency)
        self.assertEqual(-121, line_2.amount_currency)
        self.assertEqual(1210, payment.amount)
        self.assertEqual(989, payment.withholding_net_amount)

    def test_two_withholdings_different_currency(self):
        """Payment in other currency and two withholdings"""
        moves = self.create_invoice(product_id=self.product_b)
        wizard = self.create_payment_register(moves, {})
        wizard.currency_id = self.other_currency.id
        wizard.amount = 6.05
        wizard.withholding_line_ids = [
            Command.clear(),
            Command.create({'tax_id': self.tax_wth_purchase_iibb_untaxed.id, 'base_amount': 5, 'amount': 0}),
            Command.create({'tax_id': self.tax_wth_purchase_iibb_total.id, 'base_amount': 6.05, 'amount': 0}),
        ]
        wizard.withholding_line_ids._compute_amount()
        self.assertEqual(wizard.currency_id.round(sum(wizard.withholding_line_ids.mapped('amount')) + wizard.withholding_net_amount), wizard.currency_id.round(wizard.amount))
        action = wizard.action_create_payments()

        payment = self.env['account.payment'].browse(action['res_id'])
        line_1 = payment.move_id.line_ids.filtered(lambda x: x.tax_line_id.id == self.tax_wth_purchase_iibb_untaxed.id)
        line_2 = payment.move_id.line_ids.filtered(lambda x: x.tax_line_id.id == self.tax_wth_purchase_iibb_total.id)
        self.assertEqual(-0.50, line_1.amount_currency)
        self.assertEqual(-50, line_1.balance)
        self.assertEqual(-0.605, line_2.amount_currency)
        self.assertEqual(-60.5, line_2.balance)
        self.assertEqual(6.05, payment.amount)
        self.assertEqual(4.945, payment.withholding_net_amount)

    def test_earnings_withholding_applied_with_scale(self):
        """Two payments with same withholding tax (with tax type 'Earnings Scale'). Verify withholding amount."""
        invoice = self.create_invoice(product_id=self.service_iva_21, price_unit=30000.0, tax_ids=None)
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': invoice.company_id.id,
            'tax_id': self.tax_wth_purchase_earnings_scale.id
        })
        wizard = self.create_payment_register(invoice, {self.tax_wth_purchase_earnings_scale: invoice.amount_untaxed})
        self.assertEqual(wizard.withholding_line_ids.amount, 1600)
        wizard.action_create_payments()
        invoice2 = self.create_invoice(product_id=self.service_iva_21, price_unit=40000.0, tax_ids=None)
        wizard = self.create_payment_register(invoice2, {self.tax_wth_purchase_earnings_scale: invoice2.amount_untaxed})
        self.assertEqual(wizard.withholding_line_ids.amount, 7480)
        wizard.action_create_payments()

    def test_earnings_withholding_applied(self):
        """Two payments with same withholding tax (with tax type 'Earnings'). Verify withholding amount."""
        invoice = self.create_invoice(product_id=self.service_iva_21, price_unit=30000.0, tax_ids=None)
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': invoice.company_id.id,
            'tax_id': self.tax_wth_purchase_earnings.id
        })
        wizard = self.create_payment_register(invoice, {self.tax_wth_purchase_earnings: invoice.amount_untaxed})
        self.assertEqual(wizard.withholding_line_ids.amount, 1327.8)
        wizard.action_create_payments()
        invoice2 = self.create_invoice(product_id=self.service_iva_21, price_unit=40000.0, tax_ids=None)
        wizard = self.create_payment_register(invoice2, {self.tax_wth_purchase_earnings: invoice2.amount_untaxed})
        self.assertEqual(wizard.withholding_line_ids.amount, 2400)
        wizard.action_create_payments()

    def test_earnings_accumulation_groups_the_arca_code(self):
        """ Regimes sharing an ARCA code accumulate together: what a sibling tax of the same code
        already withheld this month counts against the base the next payment is levied on.
        """
        tax = self.tax_wth_purchase_earnings
        tax.write({
            'l10n_ar_code': '116',
            'withholding_sequence_id': self.earnings_withholding_sequence.id,
        })
        sibling_tax = tax.copy({
            'name': 'Earnings 116 bis',
            'l10n_ar_code': '116',
            'withholding_sequence_id': self.earnings_withholding_sequence.id,  # not copied over
        })
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': self.env.company.id,
            'tax_id': sibling_tax.id,
        })

        invoice = self.create_invoice(product_id=self.service_iva_21, price_unit=30000.0, tax_ids=None)
        wizard = self.create_payment_register(invoice, payment_date='2023-01-05')
        withholding_line = wizard.withholding_line_ids.filtered(lambda line: line.tax_id == sibling_tax)
        self.assertTrue(withholding_line, "The regime the partner is registered in should be picked up")
        wizard._create_payments()

        accumulation = self.res_partner_adhoc._l10n_ar_get_period_accumulation(
            tax=tax,
            date=datetime.strptime('2023-01-05', '%Y-%m-%d').date(),
        )
        # The sibling regime shares the ARCA code, so it feeds the accumulation of the tax.
        self.assertEqual(accumulation['base'], withholding_line.base_amount)
        self.assertEqual(accumulation['withheld'], withholding_line.amount)

    def test_earnings_accumulation_nets_a_refund(self):
        """ A refund gives back what was paid, so it lowers the accumulation of the regime
        instead of adding up to it, even when it is the only thing the month holds.
        """
        tax = self.tax_wth_purchase_earnings
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': self.env.company.id,
            'tax_id': tax.id,
        })

        # Pay a 30.000 bill: (30.000 - 7.870 non-taxable) * 6%
        invoice = self.create_invoice(product_id=self.service_iva_21, price_unit=30000.0, tax_ids=None)
        wizard = self.create_payment_register(invoice, payment_date='2023-01-05')
        self.assertEqual(wizard.withholding_line_ids.filtered(lambda l: l.tax_id == tax).amount, 1327.8)
        wizard._create_payments()

        # The next month, 10.000 of it is refunded, giving back (10.000 - 7.870) * 6%
        refund = self.create_invoice(
            move_type='in_refund',
            invoice_date='2023-02-05',
            product_id=self.service_iva_21,
            price_unit=10000.0,
            tax_ids=None,
        )
        wizard = self.create_payment_register(refund, payment_date='2023-02-06')
        self.assertEqual(wizard.withholding_line_ids.filtered(lambda l: l.tax_id == tax).amount, 127.8)
        wizard._create_payments()

        accumulation = self.res_partner_adhoc._l10n_ar_get_period_accumulation(
            tax=tax,
            date=datetime.strptime('2023-02-10', '%Y-%m-%d').date(),
        )
        # February holds a refund only: the regime accumulated a give-back, not a payment.
        self.assertEqual(accumulation['base'], -10000.0)
        self.assertEqual(accumulation['withheld'], -127.8)

    def test_earnings_partial_payment_withholding_applied_with_scale(self):
        """Partial payment with withholding tax (with tax type 'Earnings Scale'). Verify withholding amount."""
        invoice = self.create_invoice(product_id=self.service_iva_21, price_unit=30000.0, tax_ids=None)
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': invoice.company_id.id,
            'tax_id': self.tax_wth_purchase_earnings_scale.id
        })
        wizard = self.create_payment_register(invoice, {self.tax_wth_purchase_earnings_scale: invoice.amount_untaxed})
        wizard.amount -= 2420
        self.assertEqual(wizard.withholding_line_ids.amount, 1360)

    def test_earnings_withholding_applied_with_scale_and_minimun_withholdable_amount_set(self):
        """Payment with withholding tax type 'Earnings Scale' and minimun withholdable amount set. Verify withholding amount."""
        invoice = self.create_invoice(product_id=self.service_iva_21, price_unit=30000.0, tax_ids=None)
        self.tax_wth_purchase_earnings_scale.l10n_ar_minimum_threshold = 2000
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': invoice.company_id.id,
            'tax_id': self.tax_wth_purchase_earnings_scale.id
        })
        wizard = self.create_payment_register(invoice, {self.tax_wth_purchase_earnings_scale: invoice.amount_untaxed})
        self.assertEqual(wizard.withholding_line_ids.amount, 0.0)

    def test_foreign_invoice(self):
        """ Ensure a correct behavior when the invoice has a foreign currency and the payment not. """
        in_invoice_wht = self.create_invoice(currency_id=self.other_currency)
        wizard = self.create_payment_register(
            in_invoice_wht,
            {self.tax_wth_purchase_iibb_untaxed: sum(in_invoice_wht.mapped('amount_untaxed'))},
            payment_date='2023-01-01',
            currency_id=self.company_data['currency'].id,
        )
        action = wizard.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            # Liquidity line:
            {'debit': 0.0, 'credit': 120900.0, 'currency_id': wizard.currency_id.id, 'amount_currency': -120900.0, 'reconciled': False},
            # base line:
            {'debit': 0.0, 'credit': 1000.0, 'currency_id': wizard.currency_id.id, 'amount_currency': -1000.0, 'reconciled': False},
            # withholding line:
            {'debit': 0.0, 'credit': 100.0, 'currency_id': wizard.currency_id.id, 'amount_currency': -100.0, 'reconciled': False},
            # base line:
            {'debit': 1000.0, 'credit': 0.0, 'currency_id': wizard.currency_id.id, 'amount_currency': 1000.0, 'reconciled': False},
            # Receivable line:
            {'debit': 121000.0, 'credit': 0.0, 'currency_id': wizard.currency_id.id, 'amount_currency': 121000.0, 'reconciled': True}
        ])

    def test_foreign_invoice_and_payment(self):
        """ Ensure a correct behavior when the invoice and the payment have a foreign currency. """
        in_invoice_wht = self.create_invoice(currency_id=self.other_currency)
        wizard = self.create_payment_register(
            in_invoice_wht,
            {self.tax_wth_purchase_iibb_untaxed: sum(in_invoice_wht.mapped('amount_untaxed'))},
            payment_date='2023-01-01',
            currency_id=self.other_currency.id,
        )
        action = wizard.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            # Liquidity line:
            {'debit': 0.0, 'credit': 111000.0, 'currency_id': wizard.currency_id.id, 'amount_currency': -1110.0, 'reconciled': False},
            # base line:
            {'debit': 0.0, 'credit': 100000.0, 'currency_id': wizard.currency_id.id, 'amount_currency': -1000.0, 'reconciled': False},
            # withholding line:
            {'debit': 0.0, 'credit': 10000.0, 'currency_id': wizard.currency_id.id, 'amount_currency': -100.0, 'reconciled': False},
            # base line:
            {'debit': 100000.0, 'credit': 0.0, 'currency_id': wizard.currency_id.id, 'amount_currency': 1000.0, 'reconciled': False},
            # Receivable line:
            {'debit': 121000.0, 'credit': 0.0, 'currency_id': wizard.currency_id.id, 'amount_currency': 1210.0, 'reconciled': True}
        ])

    def test_earnings_withholding_applied_with_scale_check_payment(self):
        """Payment with third party check with withholding tax type 'Earnings Scale'. Verify withholding amount."""
        check_journal = self.check_journal()
        in_third_party_check = self.create_payment(
            checks={'1': 30762.71},
            amount=30762.71,
            payment_type='inbound',
            journal_id=check_journal.id,
            payment_method_line_id=check_journal.inbound_payment_method_line_ids[0].id,
        )
        invoice = self.create_invoice(product_id=self.service_iva_21, price_unit=40000.0, tax_ids=None)
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': invoice.company_id.id,
            'tax_id': self.tax_wth_purchase_earnings_scale.id
        })
        wizard = self.create_payment_register(invoice, {self.tax_wth_purchase_earnings_scale: invoice.amount_untaxed})
        wizard.journal_id = check_journal.id
        wizard.payment_method_line_id = wizard.journal_id.inbound_payment_method_line_ids[1].id
        wizard.l10n_latam_move_check_ids = in_third_party_check.l10n_latam_new_check_ids
        wizard._compute_amount()
        self.assertEqual(wizard.amount, 31929.25)
        self.assertEqual(wizard.withholding_line_ids.base_amount, 26387.81)
        self.assertEqual(wizard.withholding_line_ids.amount, 1166.54)
        self.assertEqual(wizard.withholding_net_amount, 30762.71)

    def test_withholding_amounts(self):
        """Check computation of withholding tax amount."""
        self.tax_wth_purchase_iibb_untaxed.write({'amount': -4.5})
        moves = self.create_invoice(price_unit=156087.00)
        wizard = self.create_payment_register(moves, {self.tax_wth_purchase_iibb_untaxed: sum(moves.mapped('amount_untaxed'))})
        action = wizard.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            # Liquidity line:
            {'debit': 0.0, 'credit': 181841.35, 'currency_id': wizard.currency_id.id, 'amount_currency': -181841.35, 'reconciled': False},
            # base line:
            {'debit': 0.0, 'credit': 156087.0, 'currency_id': wizard.currency_id.id, 'amount_currency': -156087.0, 'reconciled': False},
            # withholding line:
            {'debit': 0.0, 'credit': 7023.92, 'currency_id': wizard.currency_id.id, 'amount_currency': -7023.92, 'reconciled': False},
            # base line:
            {'debit': 156087.0, 'credit': 0.0, 'currency_id': wizard.currency_id.id, 'amount_currency': 156087.0, 'reconciled': False},
            # Receivable line:
            {'debit': 188865.27, 'credit': 0.0, 'currency_id': wizard.currency_id.id, 'amount_currency': 188865.27, 'reconciled': True}
        ])

    def test_withholding_check_payment_iterative_flush(self):
        """Test the iterative solver cache flush bug.
        A 30,250 ARS vendor bill with 1% withholding tax (250 ARS retention) paid with an
        own check of 30,000 ARS must iteratively converge to 30,250 gross.
        """
        self.tax_wth_purchase_iibb_untaxed.amount = -1.0

        # Setup Journal with Own Checks Outbound Payment Method
        own_check_line = self.own_check_payment_method_line()

        # Create a Vendor Bill of exactly 30,250 (25000 untaxed + 21% VAT = 30250)
        invoice = self.create_invoice(price_unit=25000.0)

        # Add partner tax configuration to guarantee withholdings automatically apply on the wizard
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': invoice.company_id.id,
            'tax_id': self.tax_wth_purchase_iibb_untaxed.id
        })

        with Form(self.payment_register(invoice)) as pay_form:
            pay_form.journal_id = own_check_line.journal_id
            pay_form.payment_method_line_id = own_check_line

            # Add check details triggering onchange combinations
            with pay_form.l10n_latam_new_check_ids.new() as check_line:
                check_line.name = 'CHK-999'
                check_line.payment_date = datetime.today()
                check_line.amount = 30000.0

        wizard = pay_form.save()

        # Validate perfectly converged mathematical values
        self.assertRecordValues(wizard, [{
            'withholding_net_amount': 30000.0,
            'amount': 30250.0,
        }])
        self.assertRecordValues(wizard.withholding_line_ids, [{
            'amount': 250.0,
            'base_amount': 25000.0,
        }])

    def test_payment_register_without_currency(self):
        "check computation of amount and adjustment warning without currency"
        moves = self.create_invoice(price_unit=156087.00)
        wizard = Form(self.create_payment_register(moves, {self.tax_wth_purchase_iibb_untaxed: sum(moves.mapped('amount_untaxed'))}))
        wizard.currency_id = self.env['res.currency']
        self.assertEqual(wizard.amount, 188865.27)
        self.assertNotIn('l10n_ar_adjustment_warning', wizard.actionable_errors or {})

    def test_payment_withholding_kept(self):
        """ Check that resetting a payment doesn't remove any payment withholding line. """
        # Vendor Payment Withholding Tax: 0%
        tax_wth_0 = self.tax_wth_purchase_iibb_total.copy({
            'amount': 0.0,
            'withholding_sequence_id': self.tax_wth_seq.id,
        })
        moves = self.create_invoice(product_id=self.product_b)
        wizard = self.create_payment_register(moves, {
            self.tax_wth_purchase_iibb_total: 1000.0,
            tax_wth_0: 1000.0,
        })
        action = wizard.action_create_payments()

        payment = self.env['account.payment'].browse(action['res_id'])
        # There should be 2 payment withholding lines
        self.assertEqual(len(payment.withholding_line_ids), 2)
        line_1 = payment.withholding_line_ids.filtered(lambda x: x.tax_id.id == self.tax_wth_purchase_iibb_total.id)
        line_2 = payment.withholding_line_ids.filtered(lambda x: x.tax_id.id == tax_wth_0.id)
        self.assertEqual(100.0, line_1.amount)
        self.assertEqual(0.0, line_2.amount)
        # Reset the payment to draft
        payment.action_draft()
        # Payment withholding lines should be the same
        self.assertEqual(len(payment.withholding_line_ids), 2)
        line_1 = payment.withholding_line_ids.filtered(lambda x: x.tax_id.id == self.tax_wth_purchase_iibb_total.id)
        line_2 = payment.withholding_line_ids.filtered(lambda x: x.tax_id.id == tax_wth_0.id)
        self.assertEqual(100.0, line_1.amount)
        self.assertEqual(0.0, line_2.amount)

    def test_withholding_reset_when_no_longer_withholding(self):
        """ A tax that does not withhold anymore levies for no regime. """
        tax = self.tax_wth_purchase_iibb_untaxed
        tax.is_withholding_tax = False
        self.assertFalse(tax.l10n_ar_withholding_tax_type)
        self.assertFalse(tax.l10n_ar_code)

    def test_earnings_scale_tax_requires_a_scale(self):
        """ The scale replaces the rate of the tax, a scale-less one would silently withhold nothing. """
        with self.assertRaisesRegex(ValidationError, "withholds according to an earnings scale"):
            self.tax_wth_purchase_iibb_untaxed.write({
                'l10n_ar_withholding_tax_type': 'earnings_scale',
                'l10n_ar_scale_id': False,
            })

    def test_withholding_regime_reset_on_save(self):
        """ The regime a tax withholds for is dropped when saving a setup that no longer displays it,
        while the form is left free to try setups out. """
        tax = self.tax_wth_purchase_earnings_scale
        scale = tax.l10n_ar_scale_id
        self.assertTrue(tax.l10n_ar_code)
        with Form(tax) as tax_form:
            self.assertEqual(tax_form.l10n_ar_withholding_tax_type, 'earnings_scale')
            tax_form.l10n_ar_withholding_tax_type = 'iibb_untaxed'
            tax_form.l10n_ar_state_id = self.env.ref('base.state_ar_c')
            # nothing is cleared as long as the setup is not saved
            self.assertEqual(tax_form.l10n_ar_scale_id, scale)
        self.assertFalse(tax.l10n_ar_code, "IIBB is not an earnings regime, its ARCA code means nothing")
        self.assertEqual(tax.l10n_ar_scale_id, scale, "the scale is only hidden, the user may switch back to it")

    def test_withholding_regime_reset_on_sale_tax(self):
        """ An ARCA code identifies a regime withheld on the purchase side, a sale tax levies for none. """
        tax = self.tax_wth_purchase_earnings.copy()
        self.assertTrue(tax.l10n_ar_code)
        tax.type_tax_use = 'sale'
        self.assertFalse(tax.l10n_ar_code)
        self.assertTrue(tax.l10n_ar_non_taxable_amount, "only what taxes are searched on is reset")

    def test_sales_withholding_amount_computation(self):
        """ Test that sales withholding tax amount is computed based on tax percentage on payment register """
        sales_tax = self.tax_wth_sale_earnings
        sales_tax.l10n_ar_minimum_threshold = 5000.0
        out_invoice = self.create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_ri,
            price_unit=3410.00,
        )

        wizard = self.create_payment_register(out_invoice, payment_date='2023-01-01', withhold='withhold')

        wizard.withholding_line_ids = [Command.create({
            'tax_id': sales_tax.id,
            'base_amount': 3410.00,
        })]

        line = wizard.withholding_line_ids.filtered(lambda l: l.tax_id == sales_tax)
        self.assertEqual(line.amount, 34.10)

    def test_partner_tax_dates_constraint(self):
        """ Ensure from_date is lower than to_date on l10n_ar.partner.tax """
        with self.assertRaisesRegex(ValidationError, '"From date" must be lower than "To date"'):
            self.env['l10n_ar.partner.tax'].create({
                'partner_id': self.partner_ri.id,
                'tax_id': self.tax_wth_purchase_iibb_untaxed.id,
                'from_date': '2026-07-22',
                'to_date': '2026-07-21',
            })

    def test_earnings_scale_line_from_amount_compute(self):
        """ Each bracket starts where the previous one ends, the lowest one at zero. """
        lines = self.env.ref('l10n_ar_withholding.normal_scale').line_ids.sorted('to_amount')
        self.assertTrue(len(lines) > 1, "The scale needs several brackets to chain them")
        self.assertEqual(lines[0].from_amount, 0.0)
        for previous, current in pairwise(lines):
            self.assertEqual(current.from_amount, previous.to_amount)

    def test_earnings_scale_above_the_last_bracket(self):
        """ ARCA tables end with "de $X en adelante": a base above the last bracket is withheld at
            that bracket instead of escaping the scale. """
        scale = self.env['l10n_ar.earnings.scale'].create({
            'name': 'Two brackets',
            'line_ids': [
                Command.create({'to_amount': 1000.0, 'percentage': 10.0}),
                Command.create({'to_amount': 2000.0, 'percentage': 20.0}),
            ],
        })
        # 10% of 500
        self.assertEqual(scale._l10n_ar_get_tax_amount_from_bracket(500.0), 50.0)
        # 100 + 20% of what exceeds 1000
        self.assertEqual(scale._l10n_ar_get_tax_amount_from_bracket(1500.0), 200.0)
        self.assertEqual(scale._l10n_ar_get_tax_amount_from_bracket(5000.0), 900.0)

    def test_withholding_grouping_warning(self):
        """ Test l10n_ar_withholding_grouping_warning triggers correctly """
        invoice1 = self.create_invoice(partner_id=self.partner_ri)

        other_partner = self.env['res.partner'].create({
            'name': 'Other Partner',
            'l10n_ar_afip_responsibility_type_id': self.env.ref('l10n_ar.res_IVARI').id,
            'vat': '20301234567',
        })
        invoice2 = self.create_invoice(partner_id=other_partner)

        wizard = self.create_payment_register(invoice1 | invoice2, payment_date='2026-07-22')
        self.assertIn('l10n_ar_withholding_grouping_warning', wizard.actionable_errors)

    def test_withholding_only_flow_and_subsequent_accumulation(self):
        """ Test 'Withholding Only' (withhold = 'withhold') flow and its impact on period accumulation for subsequent payments """
        self.tax_wth_purchase_earnings_scale.l10n_ar_minimum_threshold = 0.0
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.partner_ri.id,
            'company_id': self.env.company.id,
            'tax_id': self.tax_wth_purchase_earnings_scale.id,
        })

        invoice1 = self.create_invoice(
            partner_id=self.partner_ri,
            price_unit=10000.0,
        )

        wizard1 = self.create_payment_register(invoice1, payment_date='2023-01-05', withhold='withhold')
        wth_line1 = wizard1.withholding_line_ids.filtered(lambda l: l.tax_id == self.tax_wth_purchase_earnings_scale)
        self.assertTrue(wth_line1)
        self.assertAlmostEqual(wth_line1.base_amount, 10000.0)

        wizard1.action_create_payments()

        invoice2 = self.create_invoice(
            partner_id=self.partner_ri,
            invoice_date='2023-01-10',
            price_unit=20000.0,
        )

        wizard2 = self.create_payment_register(invoice2, payment_date='2023-01-15', withhold='withhold_pay')
        wth_line2 = wizard2.withholding_line_ids.filtered(lambda l: l.tax_id == self.tax_wth_purchase_earnings_scale)
        self.assertTrue(wth_line2)
        self.assertAlmostEqual(wth_line2.base_amount, 20000.0)

    def test_withholding_lines_follow_regime_validity(self):
        """ Moving the payment date out of the validity of a regime clears the line it created,
            while a partner registered in no regime at all keeps what was encoded by hand. """
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': self.env.company.id,
            'tax_id': self.tax_wth_purchase_iibb_untaxed.id,
            'to_date': '2023-01-31',
        })
        invoice = self.create_invoice()

        wizard = self.create_payment_register(invoice, payment_date='2023-01-05')
        self.assertEqual(wizard.withholding_line_ids.tax_id, self.tax_wth_purchase_iibb_untaxed)

        wizard.payment_date = '2023-02-05'
        self.assertFalse(wizard.withholding_line_ids)

        # The same date change leaves a hand encoded withholding alone when no regime is registered.
        invoice_no_regime = self.create_invoice(partner_id=self.partner_ri)
        wizard_no_regime = self.create_payment_register(invoice_no_regime, {self.tax_wth_purchase_iibb_untaxed: 1000.0})
        wizard_no_regime.payment_date = '2023-02-05'
        self.assertEqual(wizard_no_regime.withholding_line_ids.tax_id, self.tax_wth_purchase_iibb_untaxed)

    def test_withholding_sequence_name_always_visible(self):
        """ Test that withholding sequence / certificate number column is always visible for Argentina """
        invoice = self.create_invoice(partner_id=self.partner_ri)
        wizard = self.create_payment_register(invoice, payment_date='2023-01-05')
        wizard.withholding_line_ids = [Command.create({
            'tax_id': self.tax_wth_purchase_iibb_untaxed.id,
            'base_amount': 1000.0,
            'amount': 10.0,
        })]
        self.assertFalse(wizard.withholding_hide_name)

    def test_withholding_and_checks_base_amount(self):
        """ Test that selecting a check payment method does not result in a 0 base amount on withholding lines. """
        self.tax_wth_purchase_iibb_untaxed.amount = -1.0

        own_check_line = self.own_check_payment_method_line(self.company_data['default_account_payable'])

        invoice = self.create_invoice(price_unit=25000.0)

        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': invoice.company_id.id,
            'tax_id': self.tax_wth_purchase_iibb_untaxed.id
        })

        with Form(self.payment_register(invoice)) as pay_form:
            pay_form.journal_id = own_check_line.journal_id
            pay_form.payment_method_line_id = own_check_line

            with pay_form.l10n_latam_new_check_ids.new() as check_line:
                check_line.name = 'CHK-100'
                check_line.payment_date = datetime.today()
                check_line.amount = 30000.0

        wizard = pay_form.save()
        self.assertTrue(wizard.withholding_line_ids)
        self.assertGreater(wizard.withholding_line_ids[0].base_amount, 0)

    def test_withholding_and_no_check_encoded_yet(self):
        """ A check payment is worth what it is paid with: selecting the method before encoding any
        check leaves the wizard at zero, and the withholdings with nothing to be levied on.
        """
        self.tax_wth_purchase_iibb_untaxed.amount = -1.0
        own_check_line = self.own_check_payment_method_line(self.company_data['default_account_payable'])

        invoice = self.create_invoice(price_unit=25000.0)
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': invoice.company_id.id,
            'tax_id': self.tax_wth_purchase_iibb_untaxed.id
        })

        with Form(self.payment_register(invoice)) as pay_form:
            pay_form.journal_id = own_check_line.journal_id
            pay_form.payment_method_line_id = own_check_line
            pay_form.withhold = 'payment'
            # The checks make up the payment and none is encoded yet: nothing to adjust either.
            self.assertFalse(len(pay_form.l10n_latam_new_check_ids))
            self.assertEqual(pay_form.amount, 0.0)
            self.assertNotIn('l10n_ar_adjustment_warning', pay_form.actionable_errors or {})

            with pay_form.l10n_latam_new_check_ids.new() as check:
                check.name = '00000001'
                check.payment_date = '2023-01-05'
                check.amount = 30250.0
            self.assertEqual(pay_form.amount, 30250.0, "What the checks are worth is what is paid")
        # the amount of the checks is no field of the view, it is read on the saved wizard
        self.assertEqual(pay_form.save().l10n_latam_checks_amount, 30250.0)

    def test_withholding_and_checks_issuer_vat_onchange_preserves_amount(self):
        """ Test that updating Issuer VAT on a check does not trigger recomputation or reset of wizard amount. """
        self.tax_wth_purchase_iibb_untaxed.amount = -1.0

        own_check_line = self.own_check_payment_method_line(self.company_data['default_account_payable'])

        invoice = self.create_invoice(price_unit=25000.0)

        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': invoice.company_id.id,
            'tax_id': self.tax_wth_purchase_iibb_untaxed.id
        })

        with Form(self.payment_register(invoice)) as pay_form:
            pay_form.journal_id = own_check_line.journal_id
            pay_form.payment_method_line_id = own_check_line

            with pay_form.l10n_latam_new_check_ids.new() as check_line:
                check_line.name = 'CHK-200'
                check_line.payment_date = datetime.today()
                check_line.amount = 30000.0
                check_line.issuer_vat = '20055361682'

        wizard = pay_form.save()
        self.assertEqual(wizard.amount, 30250.0)

    def test_withholding_paid_with_several_own_checks(self):
        """ A vendor bill partially settled by handing over two own checks.
            The checks fix the net amount paid, so the wizard has to gross it up to also cover the
            1% IIBB withholding, which is computed on the untaxed part of what is settled:
            - Bill: 206.61 untaxed + 21% VAT = 250.00
            - Checks: 50.00 + 150.00 = 200.00 net
            - Gross settled: 200 / (1 - 0.01 / 1.21) = 201.67
            - Withholding: 1% of 201.67 / 1.21 = 1.67
        """
        self.tax_wth_purchase_iibb_untaxed.amount = -1.0

        bank_journal = self.company_data['default_journal_bank']
        own_check_method = self.env.ref('l10n_latam_check.account_payment_method_own_checks')
        own_check_line = bank_journal.outbound_payment_method_line_ids.filtered(
            lambda line: line.payment_method_id == own_check_method
        )

        invoice = self.create_invoice(price_unit=206.61)
        self.assertEqual(invoice.amount_total, 250.0)

        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': invoice.company_id.id,
            'tax_id': self.tax_wth_purchase_iibb_untaxed.id
        })

        with Form(self.payment_register(invoice)) as pay_form:
            pay_form.journal_id = bank_journal
            pay_form.payment_method_line_id = own_check_line

            with pay_form.l10n_latam_new_check_ids.new() as check_line:
                check_line.name = '00000001'
                check_line.payment_date = datetime.today()
                check_line.amount = 50.0

            with pay_form.l10n_latam_new_check_ids.new() as check_line:
                check_line.name = '00000002'
                check_line.payment_date = datetime.today()
                check_line.amount = 150.0

        wizard = pay_form.save()

        withholding_line = wizard.withholding_line_ids.filtered(lambda line: line.tax_id == self.tax_wth_purchase_iibb_untaxed)
        self.assertEqual(len(withholding_line), 1)
        self.assertAlmostEqual(withholding_line.base_amount, 166.67, places=2)
        self.assertAlmostEqual(withholding_line.amount, 1.67, places=2)
        self.assertAlmostEqual(wizard.amount, 201.67, places=2)

        payment = wizard._create_payments()

        self.assertAlmostEqual(payment.amount, 201.67, places=2)
        self.assertAlmostEqual(payment.withholding_line_ids.amount, 1.67, places=2)
        # The checks carry the net amount; the withholding is settled through its own line, not by a check.
        self.assertEqual(payment.l10n_latam_new_check_ids.mapped('name'), ['00000001', '00000002'])
        self.assertAlmostEqual(sum(payment.l10n_latam_new_check_ids.mapped('amount')), 200.0, places=2)
        # Remaining invoice residual = 250.00 - 201.67
        self.assertAlmostEqual(invoice.amount_residual, 48.33, places=2)

    def test_withholding_missing_sequence_number_raises(self):
        """ Test that registering payment with a withholding line having no sequence and no certificate number raises UserError """
        invoice = self.create_invoice(partner_id=self.partner_ri)
        tax_no_seq = self.tax_wth_purchase_iibb_untaxed.copy({'withholding_sequence_id': False})
        wizard = self.create_payment_register(invoice, payment_date='2023-01-05')
        wizard.withholding_line_ids = [Command.create({
            'tax_id': tax_no_seq.id,
            'base_amount': 1000.0,
            'amount': 10.0,
            'name': False,
        })]
        self.assertIn('l10n_ar_withholding_sequence_warning', wizard.actionable_errors)
        with self.assertRaisesRegex(UserError, "Please enter Sequence Number for tax"):
            wizard.action_create_payments()

        wizard.withholding_line_ids.name = 'A-0001'
        self.assertNotIn('l10n_ar_withholding_sequence_warning', wizard.actionable_errors or {})
        self.assertTrue(wizard.action_create_payments())

    def test_sale_withholding_needs_sequence_number(self):
        """ Withholdings are certified whichever side they are taken on: a customer one needs a number too. """
        sale_tax = self.tax_wth_sale_iibb_untaxed.copy({'withholding_sequence_id': False})
        out_invoice = self.create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_ri,
        )

        wizard = self.create_payment_register(out_invoice, payment_date='2023-01-05')
        wizard.withholding_line_ids = [Command.create({
            'tax_id': sale_tax.id,
            'base_amount': 1000.0,
            'amount': 10.0,
            'name': False,
        })]
        self.assertIn('l10n_ar_withholding_sequence_warning', wizard.actionable_errors)
        with self.assertRaisesRegex(UserError, "Please enter Sequence Number for tax"):
            wizard._create_payments()

        wizard.withholding_line_ids.filtered(lambda l: l.tax_id == sale_tax).name = 'B-0001'
        payment = wizard._create_payments()
        self.assertEqual(payment.state, 'paid')
        self.assertEqual(payment.withholding_line_ids.filtered(lambda l: l.tax_id == sale_tax).name, 'B-0001')

    def test_ar_real_case_check_and_withholding_accumulation(self):
        """ Replicate real-world Argentine AFIP case with check payment and withholding:
            - Vendor Invoice: 200,000 ARS untaxed (+21% VAT = 242,000 total)
            - Fixed Check in Drawer: 120,000 ARS
            - Withholding Tax: 10%
            - Verify computed wizard amount, withholding line amount, check amount, and remaining invoice residual.
        """
        wth_tax = self.tax_wth_purchase_iibb_total.copy({
            'amount': -10.0,
            'amount_type': 'percent',
            'withholding_sequence_id': self.earnings_withholding_sequence.id,
        })
        invoice = self.create_invoice(
            partner_id=self.partner_ri,
            price_unit=200000.0,
        )

        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.partner_ri.id,
            'company_id': invoice.company_id.id,
            'tax_id': wth_tax.id,
        })

        own_check_line = self.own_check_payment_method_line(self.company_data['default_account_payable'])

        with Form(self.payment_register(invoice)) as pay_form:
            pay_form.journal_id = own_check_line.journal_id
            pay_form.payment_method_line_id = own_check_line
            with pay_form.l10n_latam_new_check_ids.new() as check_line:
                check_line.name = 'CHK-REAL-001'
                check_line.payment_date = datetime.today()
                check_line.amount = 120000.0
                check_line.issuer_vat = '20055361682'

        wizard = pay_form.save()

        # Settled gross base B = 120000 / (1 - 0.10) = 133333.33
        # Withholding W = 10% of 133333.33 = 13333.33
        # Check C = 120000.00
        wth_line = wizard.withholding_line_ids.filtered(lambda l: l.tax_id == wth_tax)
        self.assertTrue(wth_line)
        self.assertAlmostEqual(wth_line.amount, 13333.33, places=2)
        self.assertAlmostEqual(wizard.amount, 133333.33, places=2)

        payment = wizard._create_payments()
        self.assertAlmostEqual(payment.amount, 133333.33, places=2)

        # Remaining invoice residual = 242000.0 - 133333.33 = 108666.67
        self.assertAlmostEqual(invoice.amount_residual, 108666.67, places=2)

    def test_ar_full_progressive_scale_withholding_and_check(self):
        """ Replicate complete AFIP case with progressive scale tax, non-taxable minimum threshold,
            monthly period accumulation, and fixed check payment.
        """
        tax = self.tax_wth_purchase_earnings_scale
        tax.l10n_ar_minimum_threshold = 2000.0

        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': self.env.company.id,
            'tax_id': tax.id,
        })

        # Month payment 1: prior payment in same month to build accumulation
        invoice1 = self.create_invoice(product_id=self.service_iva_21, price_unit=30000.0, tax_ids=None)
        wizard1 = self.create_payment_register(invoice1, payment_date='2023-01-05')
        wizard1.action_create_payments()

        # Month payment 2: payment with progressive scale tax + check in same month
        invoice2 = self.create_invoice(
            invoice_date='2023-01-10',
            price_unit=50000.0,
        )

        own_check_line = self.own_check_payment_method_line(self.company_data['default_account_payable'])

        with Form(self.payment_register(invoice2)) as pay_form:
            pay_form.payment_date = datetime.strptime('2023-01-15', '%Y-%m-%d').date()
            pay_form.journal_id = own_check_line.journal_id
            pay_form.payment_method_line_id = own_check_line
            with pay_form.l10n_latam_new_check_ids.new() as check_line:
                check_line.name = 'CHK-SCALE-001'
                check_line.payment_date = datetime.strptime('2023-01-15', '%Y-%m-%d').date()
                check_line.amount = 25000.0
                check_line.issuer_vat = '20055361682'

        wizard2 = pay_form.save()

        wth_line = wizard2.withholding_line_ids.filtered(lambda l: l.tax_id == tax)
        self.assertTrue(wth_line)
        self.assertGreater(wth_line.amount, 0.0)
        self.assertAlmostEqual(wizard2.amount, 25000.0 + wth_line.amount, places=2)

        payment2 = wizard2._create_payments()
        self.assertAlmostEqual(payment2.amount, wizard2.amount, places=2)
        self.assertAlmostEqual(invoice2.amount_residual, 60500.0 - wizard2.amount, places=2)

    def test_checks_are_dropped_when_the_payment_stops_being_paid_with_them(self):
        """ A withholding is owed to the tax authority rather than paid to the partner: switching to
            it leaves no check behind, neither on the wizard nor on the payment it creates. """
        own_check_line = self.own_check_payment_method_line(self.company_data['default_account_payable'])

        invoice = self.create_invoice(price_unit=25000.0)
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': invoice.company_id.id,
            'tax_id': self.tax_wth_purchase_iibb_untaxed.id,
        })

        with Form(self.payment_register(invoice)) as pay_form:
            pay_form.journal_id = own_check_line.journal_id
            pay_form.payment_method_line_id = own_check_line
            with pay_form.l10n_latam_new_check_ids.new() as check:
                check.name = '00000001'
                check.payment_date = '2023-01-05'
                check.amount = 30250.0
            self.assertEqual(pay_form.save().l10n_latam_checks_amount, 30250.0)

            # Withholding only moves the payment to a general journal, which pays with no check.
            pay_form.withhold = 'withhold'
        wizard = pay_form.save()

        payment = wizard._create_payments()
        self.assertFalse(payment.l10n_latam_new_check_ids, "A withholding is not paid with checks")

    def test_withholding_only_on_a_partly_settled_document(self):
        """ A withholding-only payment levies on what is left to settle: what was already paid has
            been withheld on by the payments that settled it. """
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.partner_ri.id,
            'company_id': self.env.company.id,
            'tax_id': self.tax_wth_sale_iibb_untaxed.id,
        })
        invoice = self.create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_ri,
            price_unit=100000.0,
        )
        self.assertEqual(invoice.amount_total, 121000.0)

        # A quarter of the document is settled without any withholding.
        paid = self.create_payment_register(invoice, payment_date='2023-01-03', withhold='payment', amount=30250.0)
        paid._create_payments()
        self.assertEqual(invoice.amount_residual, 90750.0)

        wizard = self.create_payment_register(invoice, payment_date='2023-01-05', withhold='withhold')
        wth_line = wizard.withholding_line_ids.filtered(lambda l: l.tax_id == self.tax_wth_sale_iibb_untaxed)
        # Three quarters of the 100,000 untaxed are left to settle, 1% of which is withheld.
        self.assertAlmostEqual(wth_line.base_amount, 75000.0)
        self.assertAlmostEqual(wth_line.amount, 750.0)

    def test_withholding_only_amount_follows_an_edited_base(self):
        """ The base of a withholding-only payment is meant to be edited by hand, to match what the
            customer withheld: what the payment is worth has to follow it. """
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.partner_ri.id,
            'company_id': self.env.company.id,
            'tax_id': self.tax_wth_sale_iibb_untaxed.id,
        })
        invoice = self.create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_ri,
            price_unit=341000.0,
        )

        with Form(self.payment_register(invoice)) as pay_form:
            pay_form.withhold = 'withhold'
            self.assertEqual(pay_form.amount, 3410.0, "1% of the untaxed amount is withheld")
            with pay_form.withholding_line_ids.edit(0) as wth_line:
                wth_line.base_amount = 1000.0
            self.assertEqual(pay_form.amount, 10.0, "The payment is worth what the edited base withholds")
        wizard = pay_form.save()

        self.assertEqual(wizard.amount, 10.0)
        self.assertEqual(wizard.withholding_line_ids.amount, 10.0)
        payment = wizard._create_payments()
        self.assertEqual(payment.amount, 10.0)

    def test_withholding_only_amount_follows_an_edited_withholding(self):
        """ A certificate does not always withhold the rate of its base: what is typed over it is
            what the payment is worth, and the base it was levied on is left alone. """
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.partner_ri.id,
            'company_id': self.env.company.id,
            'tax_id': self.tax_wth_sale_iibb_untaxed.id,
        })
        invoice = self.create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_ri,
            price_unit=341000.0,
        )

        with Form(self.payment_register(invoice)) as pay_form:
            pay_form.withhold = 'withhold'
            with pay_form.withholding_line_ids.edit(0) as wth_line:
                wth_line.amount = 25.0
            self.assertEqual(pay_form.amount, 25.0, "The payment is worth what the certificate withheld")

            # Adjusting the base afterwards levies the rate again, the typed withholding being void.
            with pay_form.withholding_line_ids.edit(0) as wth_line:
                wth_line.base_amount = 1000.0
            self.assertEqual(pay_form.amount, 10.0)
        wizard = pay_form.save()

        self.assertEqual(wizard.withholding_line_ids.base_amount, 1000.0)
        self.assertEqual(wizard.withholding_line_ids.amount, 10.0)

    def test_withholding_only_foreign_currency_conversion(self):
        """ Test 'Withholding Only' (withhold='withhold') with foreign currency (USD).
            Verify that base_amount and withholding line amount are correctly converted using currency rate.
        """
        wth_tax = self.tax_wth_purchase_iibb_total.copy({
            'amount': -10.0,
            'amount_type': 'percent',
            'withholding_sequence_id': self.earnings_withholding_sequence.id,
        })
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.partner_ri.id,
            'company_id': self.env.company.id,
            'tax_id': wth_tax.id,
        })
        invoice = self.create_invoice(
            partner_id=self.partner_ri,
            price_unit=10000.0,
        )

        usd_currency = self.other_currency

        wizard = self.create_payment_register(
            invoice,
            payment_date='2023-01-05',
            withhold='withhold',
            currency_id=usd_currency.id,
        )

        wth_line = wizard.withholding_line_ids.filtered(lambda l: l.tax_id == wth_tax)
        self.assertTrue(wth_line)
        # Total invoice in USD = 12,100 ARS * 0.01 = 121 USD. Base = 121.0 USD, Withholding 10% = 12.1 USD.
        self.assertAlmostEqual(wth_line.base_amount, 121.0, places=2)
        self.assertAlmostEqual(wth_line.amount, 12.1, places=2)

        wizard._onchange_withholding_line_ids()
        payment = wizard._create_payments()
        self.assertAlmostEqual(payment.amount, 12.1, places=2)

    def test_earnings_scale_119_accumulation_below_threshold_first_payment(self):
        """ Test user scenario for Regimen 119 scale:
            Vendor Bill with VAT 21%:
            Payment 1 for 100,000 ARS: below threshold / non-taxable minimum, no WTH taken (amount 0.0).
            Payment 2 for 100,000 ARS: accumulates prior 100,000 ARS payment base.
            Accumulated untaxed base = 165,289.26 ARS.
            Net base after non-taxable (160,000) = 5,289.26 ARS.
            WTH amount must be 5% * 5,289.26 = 264.46 ARS.
        """
        tax_119 = self._create_withholding_tax(
            'Test Profits WTH regimen 119', -1,
            l10n_ar_withholding_tax_type='earnings_scale',
            l10n_ar_scale_id=self.env.ref('l10n_ar_withholding.scale_119').id,
            l10n_ar_code='119',
            l10n_ar_non_taxable_amount=160000.0,
        )

        partner_119 = self.partner_ri.copy({'name': 'Partner 119'})
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': partner_119.id,
            'company_id': self.env.company.id,
            'tax_id': tax_119.id,
        })

        invoice = self.create_invoice(
            partner_id=partner_119,
            price_unit=200000.0,
        )

        wizard1 = self.create_payment_register(invoice, payment_date='2023-01-05', amount=100000.0)
        wth_line1 = wizard1.withholding_line_ids.filtered(lambda l: l.tax_id == tax_119)
        self.assertEqual(wth_line1.amount, 0.0)

        wizard1._create_payments()

        wizard2 = self.create_payment_register(invoice, payment_date='2023-01-10', amount=100000.0)
        wth_line2 = wizard2.withholding_line_ids.filtered(lambda l: l.tax_id == tax_119)
        self.assertTrue(wth_line2)
        self.assertAlmostEqual(wth_line2.amount, 264.46, places=2)

    def test_earnings_no_scale_accumulation_threshold_3_payments(self):
        """ Test fixed percentage earnings tax (Regimen 78) across 3 partial payments on a bill.
        Bill: 278,300 ARS total (230,000 untaxed). Tax 78 threshold: 224,000 ARS. Tax rate: 2%.
        - Payment 1 (100k ARS, 82.6k untaxed): Base 82.6k < 224k -> 0.00 WTH
        - Payment 2 (100k ARS, 82.6k untaxed): Base 165.2k < 224k -> 0.00 WTH
        - Payment 3 (78.3k ARS, 64.7k untaxed): Base 230.0k > 224k -> Net base 6.0k -> 120.00 WTH
        """
        tax_78 = self._create_withholding_tax(
            'Test Profits WTH regimen 78', -2,
            l10n_ar_withholding_tax_type='earnings',
            l10n_ar_code='78',
            l10n_ar_non_taxable_amount=224000.0,
        )
        partner_78 = self.partner_ri.copy({'name': 'Partner 78'})
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': partner_78.id,
            'company_id': self.company_ri.id,
            'tax_id': tax_78.id,
        })
        invoice = self.create_invoice(
            partner_id=partner_78,
            company_id=self.company_ri,
            l10n_latam_document_type_id=self.document_type['invoice_a'].id,
            price_unit=230000.0,
        )

        # Payment 1
        wizard1 = self.create_payment_register(invoice, payment_date='2023-01-05', amount=100000.0)
        wth1 = wizard1.withholding_line_ids.filtered(lambda l: l.tax_id.l10n_ar_code == '78')
        self.assertEqual(wth1.amount, 0.0)
        wizard1._create_payments()

        # Payment 2
        wizard2 = self.create_payment_register(invoice, payment_date='2023-01-10', amount=100000.0)
        wth2 = wizard2.withholding_line_ids.filtered(lambda l: l.tax_id.l10n_ar_code == '78')
        self.assertEqual(wth2.amount, 0.0)
        wizard2._create_payments()

        # Payment 3
        wizard3 = self.create_payment_register(invoice, payment_date='2023-01-15', amount=78300.0)
        wth3 = wizard3.withholding_line_ids.filtered(lambda l: l.tax_id.l10n_ar_code == '78')
        self.assertTrue(wth3)
        self.assertAlmostEqual(wth3.amount, 120.0, places=2)

    def test_earnings_scale_119_accumulation_paid_in_foreign_currency(self):
        """ The scale of regime 119 is an ARCA table in pesos, and so is the base accumulated over
        the month: paying in USD must withhold what paying the same amount in pesos withholds.
        Same invoice and payments as the ARS case, the second one paid in USD:
        1,000 USD = 100,000 ARS, so 264.46 ARS is owed, that is 2.645 USD.
        """
        tax_119 = self._create_withholding_tax(
            'Test Profits WTH regimen 119', -1,
            l10n_ar_withholding_tax_type='earnings_scale',
            l10n_ar_scale_id=self.env.ref('l10n_ar_withholding.scale_119').id,
            l10n_ar_code='119',
            l10n_ar_non_taxable_amount=160000.0,
        )

        partner_119 = self.partner_ri.copy({'name': 'Partner 119'})
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': partner_119.id,
            'company_id': self.env.company.id,
            'tax_id': tax_119.id,
        })

        invoice = self.create_invoice(
            partner_id=partner_119,
            price_unit=200000.0,
        )

        wizard1 = self.create_payment_register(invoice, payment_date='2023-01-05', amount=100000.0)
        self.assertEqual(wizard1.withholding_line_ids.filtered(lambda l: l.tax_id == tax_119).amount, 0.0)
        wizard1._create_payments()

        wizard2 = self.create_payment_register(
            invoice,
            payment_date='2023-01-10',
            currency_id=self.other_currency.id,
            amount=1000.0,
        )
        wth_line = wizard2.withholding_line_ids.filtered(lambda l: l.tax_id == tax_119)
        self.assertAlmostEqual(wth_line.base_amount, 826.446, places=3)
        self.assertAlmostEqual(wth_line.amount, 2.645, places=3)

    def test_earnings_78_non_taxable_amount_paid_in_foreign_currency(self):
        """ The non-taxable minimum of a regime is set in pesos as well, and the base it is taken
        from is what is being paid, whichever currency that is.
        6,050 USD = 605,000 ARS, of which 500,000 untaxed: 2% of what exceeds the 224,000 minimum
        is 5,520 ARS, that is 55.20 USD.
        """
        tax_78 = self._create_withholding_tax(
            'Test Profits WTH regimen 78', -2,
            l10n_ar_withholding_tax_type='earnings',
            l10n_ar_code='78',
            l10n_ar_non_taxable_amount=224000.0,
        )
        partner_78 = self.partner_ri.copy({'name': 'Partner 78'})
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': partner_78.id,
            'company_id': self.company_ri.id,
            'tax_id': tax_78.id,
        })
        invoice = self.create_invoice(
            partner_id=partner_78,
            company_id=self.company_ri,
            l10n_latam_document_type_id=self.document_type['invoice_a'].id,
            price_unit=500000.0,
        )

        wizard = self.create_payment_register(invoice, payment_date='2023-01-05', currency_id=self.other_currency.id)
        wth_line = wizard.withholding_line_ids.filtered(lambda l: l.tax_id == tax_78)
        self.assertAlmostEqual(wth_line.base_amount, 5000.0, places=2)
        self.assertAlmostEqual(wth_line.amount, 55.2, places=2)

    def test_manual_withholding_line_survives_an_amount_edit(self):
        """ The lines the regimes of the partner bring are recomputed as the payment changes, but a
        line added by hand is the encoder's: it is not for the wizard to take it back. """
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.partner_ri.id,
            'company_id': self.env.company.id,
            'tax_id': self.tax_wth_purchase_iibb_untaxed.id,
        })
        invoice = self.create_invoice(
            partner_id=self.partner_ri,
            price_unit=10000.0,
        )

        with Form(self.payment_register(invoice)) as pay_form:
            self.assertEqual(pay_form.withholding_line_ids._records[0]['tax_id'], self.tax_wth_purchase_iibb_untaxed.id)
            with pay_form.withholding_line_ids.new() as wth_line:
                wth_line.tax_id = self.tax_wth_purchase_iibb_total
            self.assertEqual(len(pay_form.withholding_line_ids._records), 2)

            pay_form.amount = 5000.0
            self.assertEqual(len(pay_form.withholding_line_ids._records), 2, "the line added by hand is kept")
        wizard = pay_form.save()
        self.assertEqual(
            wizard.withholding_line_ids.tax_id,
            self.tax_wth_purchase_iibb_untaxed | self.tax_wth_purchase_iibb_total,
        )
