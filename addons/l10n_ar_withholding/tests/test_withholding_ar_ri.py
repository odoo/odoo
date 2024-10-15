# -*- coding: utf-8 -*-
from odoo.addons.l10n_ar.tests.common import TestAr
from odoo.tests import tagged
from odoo import Command


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nArWithholdingArRi(TestAr):

    @classmethod
    def setUpClass(cls, chart_template_ref='ar_ri'):

        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.tax_wth_seq = cls.env['ir.sequence'].create({
            'implementation': 'standard',
            'name': 'tax wth test',
            'padding': 8,
            'number_increment': 1,
        })
        # Withholding 1: 1% untaxed_amount
        cls.tax_wth_test_1 = cls.env.ref('account.%i_ri_tax_withholding_iibb_caba_applied' % cls.env.company.id)
        cls.tax_wth_test_1.write({
            'amount': 10,
            'amount_type': 'percent',
            'l10n_ar_withholding_sequence_id': cls.tax_wth_seq.id,
        })

        # Withholding 2: 1% total_amount
        cls.tax_wth_test_2 = cls.env.ref('account.%i_ri_tax_withholding_iibb_ba_applied' % cls.env.company.id)
        cls.tax_wth_test_2.write({
            'amount': 10,
            'amount_type': 'percent',
            'l10n_ar_withholding_sequence_id': cls.tax_wth_seq.id,
        })

        cls.tax_21 = cls.env.ref('account.%s_ri_tax_vat_21_ventas' % cls.env.company.id)

        cls.actual_rate = cls.env['res.currency.rate'].create({
            'name': '2023-01-01',
            'rate': 1/100,
            'currency_id': cls.currency_data['currency'].id,
            'company_id': cls.env.company.id,
        })

        cls.future_rate = cls.env['res.currency.rate'].create({
            'name': '2023-05-01',
            'rate': 1/200,
            'currency_id': cls.currency_data['currency'].id,
            'company_id': cls.env.company.id,
        })

    def in_invoice_wht(self, l10n_latam_document_number):
        in_invoice_wht = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2023-01-01',
            'invoice_date': '2023-01-01',
            'partner_id': self.res_partner_adhoc.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax_21.ids)]})],
            'l10n_latam_document_number': l10n_latam_document_number,

        })
        in_invoice_wht.action_post()
        return in_invoice_wht

    def in_invoice_2_wht(self, l10n_latam_document_number):
        in_invoice_wht = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2023-01-01',
            'invoice_date': '2023-01-01',
            'partner_id': self.res_partner_adhoc.id,
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_b.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax_21.ids)]})
            ],
            'l10n_latam_document_number': l10n_latam_document_number,

        })
        in_invoice_wht.action_post()
        return in_invoice_wht

    def new_payment_register(self, move_ids, taxes):
        wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=move_ids.ids).create({'payment_date': '2023-01-01'})
        wizard.l10n_ar_withholding_ids = [Command.clear()] + [Command.create({'tax_id': x['id'], 'base_amount': x['base_amount'], 'amount': 0}) for x in taxes]
        wizard.l10n_ar_withholding_ids._compute_amount()
        return wizard

    def test_01_simple_full_payment(self):
        """Simple full payment in Company currency"""
        moves = self.in_invoice_wht('2-1')
        taxes = [{'id': self.tax_wth_test_1.id, 'base_amount': sum(moves.mapped('amount_untaxed'))}]
        wizard = self.new_payment_register(moves, taxes)
        self.assertEqual(wizard.currency_id.round(sum(wizard.l10n_ar_withholding_ids.mapped('amount'))) + wizard.l10n_ar_net_amount, wizard.amount)
        action = wizard.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
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
        self.assertEqual(1210, payment.currency_id.round(sum(payment.l10n_ar_withholding_ids.mapped('amount_currency')) * -1  + payment.amount))

    def test_02_two_payments_same_invoice(self):
        """Test two payments to same invoice"""
        moves = self.in_invoice_wht('2-2')
        taxes = [{'id': self.tax_wth_test_1.id, 'base_amount': sum(moves.mapped('amount_untaxed')) * 0.5}]

        wizard_1 = self.new_payment_register(moves, taxes)
        wizard_1.amount = 605.00
        self.assertEqual(wizard_1.currency_id.round(sum(wizard_1.l10n_ar_withholding_ids.mapped('amount'))) + wizard_1.l10n_ar_net_amount, wizard_1.amount)
        action = wizard_1.action_create_payments()
        payment_1 = self.env['account.payment'].browse(action['res_id'])

        # Alf payments in Company currency
        wizard_2 = self.new_payment_register(moves, taxes)
        self.assertEqual(605, wizard_2.source_amount)
        self.assertEqual(wizard_2.currency_id.round(sum(wizard_2.l10n_ar_withholding_ids.mapped('amount'))) + wizard_2.l10n_ar_net_amount, wizard_2.amount)
        action = wizard_2.action_create_payments()
        payment_2 = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment_1.line_ids.sorted('balance'), [
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
        self.assertEqual(605, payment_1.currency_id.round(sum(payment_1.l10n_ar_withholding_ids.mapped('amount_currency')) * -1  + payment_1.amount))

        self.assertRecordValues(payment_2.line_ids.sorted('balance'), [
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
        self.assertEqual(605, payment_2.currency_id.round(sum(payment_2.l10n_ar_withholding_ids.mapped('amount_currency')) * -1  + payment_2.amount))

    def test_03_two_withholdings_one_payment(self):
        """Simple full payment in Company currency and two wht"""
        moves = self.in_invoice_2_wht('2-3')
        taxes = [{'id': self.tax_wth_test_1.id, 'base_amount': sum(moves.mapped('amount_untaxed'))}, {'id': self.tax_wth_test_2.id, 'base_amount': sum(moves.mapped('amount_total'))}]

        wizard = self.new_payment_register(moves, taxes)
        self.assertEqual(wizard.currency_id.round(sum(wizard.l10n_ar_withholding_ids.mapped('amount'))) + wizard.l10n_ar_net_amount, wizard.amount)
        action = wizard.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        line_1 = payment.l10n_ar_withholding_ids.filtered(lambda x: x.tax_line_id.id == self.tax_wth_test_1.id)
        line_2 = payment.l10n_ar_withholding_ids.filtered(lambda x: x.tax_line_id.id == self.tax_wth_test_2.id)
        self.assertEqual(-100, line_1.amount_currency)
        self.assertEqual(-121, line_2.amount_currency)
        self.assertEqual(1210, payment.currency_id.round(sum(payment.l10n_ar_withholding_ids.mapped('amount_currency')) * -1  + payment.amount))

    def test_04_two_withholdings_different_currency(self):
        """Payment in other currency and two withholdings"""
        moves = self.in_invoice_2_wht('2-4')
        taxes = [{'id': self.tax_wth_test_1.id, 'base_amount': 5}, {'id': self.tax_wth_test_2.id, 'base_amount': 6.05}]
        wizard = self.new_payment_register(moves, [])
        wizard.currency_id = self.currency_data['currency'].id
        wizard.amount = 6.05
        wizard.l10n_ar_withholding_ids = [Command.clear()] + [Command.create({'tax_id': x['id'], 'base_amount': x['base_amount'], 'amount': 0}) for x in taxes]
        wizard.l10n_ar_withholding_ids._compute_amount()
        self.assertEqual(wizard.currency_id.round(sum(wizard.l10n_ar_withholding_ids.mapped('amount')) + wizard.l10n_ar_net_amount), wizard.currency_id.round(wizard.amount))
        action = wizard.action_create_payments()

        payment = self.env['account.payment'].browse(action['res_id'])
        line_1 = payment.l10n_ar_withholding_ids.filtered(lambda x: x.tax_line_id.id == self.tax_wth_test_1.id)
        line_2 = payment.l10n_ar_withholding_ids.filtered(lambda x: x.tax_line_id.id == self.tax_wth_test_2.id)
        self.assertEqual(-0.50, line_1.amount_currency)
        self.assertEqual(-50, line_1.balance)
        self.assertEqual(-0.605, line_2.amount_currency)
        self.assertEqual(-60.5, line_2.balance)
        self.assertEqual(6.05, payment.currency_id.round(sum(payment.l10n_ar_withholding_ids.mapped('amount_currency')) * -1  + payment.amount))

    def test_05_foreign_invoice(self):
        """ Ensure a correct behavior when the invoice has a foreign currency and the payment not. """
        in_invoice_wht = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2023-01-01',
            'invoice_date': '2023-01-01',
            'currency_id': self.currency_data['currency'].id,
            'partner_id': self.res_partner_adhoc.id,
            'invoice_line_ids': [Command.create(
                {'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax_21.ids)]}
            )],
            'l10n_latam_document_number': '2-1',
        })
        in_invoice_wht.action_post()
        wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=in_invoice_wht.ids).create({
            'payment_date': '2023-01-01',
            'currency_id': self.company_data['currency'].id,
            'l10n_ar_withholding_ids': [Command.create({'tax_id': self.tax_wth_test_1.id, 'base_amount': sum(in_invoice_wht.mapped('amount_untaxed')), 'amount': 0})],
        })
        wizard.l10n_ar_withholding_ids._compute_amount()
        action = wizard.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
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

    def test_06_foreign_invoice_and_payment(self):
        """ Ensure a correct behavior when the invoice and the payment have a foreign currency. """
        in_invoice_wht = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2023-01-01',
            'invoice_date': '2023-01-01',
            'currency_id': self.currency_data['currency'].id,
            'partner_id': self.res_partner_adhoc.id,
            'invoice_line_ids': [Command.create(
                {'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax_21.ids)]}
            )],
            'l10n_latam_document_number': '2-1',
        })
        in_invoice_wht.action_post()
        wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=in_invoice_wht.ids).create({
            'payment_date': '2023-01-01',
            'currency_id': self.currency_data['currency'].id,
            'l10n_ar_withholding_ids': [Command.create({'tax_id': self.tax_wth_test_1.id, 'base_amount': sum(in_invoice_wht.mapped('amount_untaxed')), 'amount': 0})],
        })
        wizard.l10n_ar_withholding_ids._compute_amount()
        action = wizard.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
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
