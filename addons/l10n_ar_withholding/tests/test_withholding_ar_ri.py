# -*- coding: utf-8 -*-
from odoo.addons.l10n_ar.tests.common import TestAr
from odoo.tests import tagged
from odoo import Command
from datetime import datetime


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nArWithholdingArRi(TestAr):

    @classmethod
    def setUpClass(cls):

        super().setUpClass()

        cls.tax_wth_seq = cls.env['ir.sequence'].create({
            'implementation': 'standard',
            'name': 'tax wth test',
            'padding': 8,
            'number_increment': 1,
        })
        # Withholding 1: 1% untaxed_amount
        cls.tax_wth_test_1 = cls.env.ref('account.%i_ex_tax_withholding_iibb_caba_applied' % cls.env.company.id)
        cls.tax_wth_test_1.write({
            'amount': 10,
            'amount_type': 'percent',
            'l10n_ar_withholding_sequence_id': cls.tax_wth_seq.id,
        })

        # Withholding 2: 1% total_amount
        cls.tax_wth_test_2 = cls.env.ref('account.%i_ex_tax_withholding_iibb_ba_applied' % cls.env.company.id)
        cls.tax_wth_test_2.write({
            'amount': 10,
            'amount_type': 'percent',
            'l10n_ar_withholding_sequence_id': cls.tax_wth_seq.id,
        })

        cls.tax_21 = cls.env.ref('account.%s_ri_tax_vat_21_ventas' % cls.env.company.id)

        cls.other_currency = cls.setup_other_currency('USD', rounding=0.001, rates=[('2023-01-01', 0.01), ('2023-05-01', 0.005)])
        cls.tax_wth_earnings_incurred_scale_test_5 = cls.env.ref('account.%i_ex_tax_withholding_profits_regimen_110_insc' % cls.env.company.id)
        cls.tax_wth_earnings_incurred_test_6 = cls.env.ref('account.%i_ex_tax_withholding_profits_regimen_35_insc' % cls.env.company.id)
        cls.earnings_withholding_sequence = cls.env['ir.sequence'].create({
            'implementation': 'standard',
            'name': 'tax wth test',
            'padding': 1,
            'number_increment': 1,
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

    def in_invoice_3_wht(self):
        invoice = self.env['account.move'].create({
            "ref": "Invoice from partner Adhoc service",
            "partner_id": self.res_partner_adhoc.id,
            "move_type": "in_invoice",
            "invoice_line_ids": [(0, 0, {
                'product_id': self.service_iva_21.id,
                'price_unit': 30000.0,
                'quantity': 1
            })],
            "invoice_date": datetime.today(),
            "l10n_latam_document_number": '1-1',
        })
        invoice.action_post()
        return invoice

    def in_invoice_4_wht(self):
        invoice = self.env['account.move'].create({
            "ref": "Invoice from partner Adhoc service",
            "partner_id": self.res_partner_adhoc.id,
            "move_type": "in_invoice",
            "invoice_line_ids": [(0, 0, {
                'product_id': self.service_iva_21.id,
                'price_unit': 40000.0,
                'quantity': 1
            })],
            "invoice_date": datetime.today(),
            "l10n_latam_document_number": '1-2',
        })
        invoice.action_post()
        return invoice

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
        self.assertEqual(605, payment_1.currency_id.round(sum(payment_1.l10n_ar_withholding_ids.mapped('amount_currency')) * -1  + payment_1.amount))

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
        wizard.currency_id = self.other_currency.id
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

    def test_05_earnings_withholding_applied_with_scale(self):
        """Two payments with same withholding tax (with tax type 'Earnings Scale'). Verify withholding amount."""
        invoice = self.in_invoice_3_wht()
        self.tax_wth_earnings_incurred_scale_test_5.l10n_ar_withholding_sequence_id = self.earnings_withholding_sequence
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': invoice.company_id.id,
            'tax_id': self.tax_wth_earnings_incurred_scale_test_5.id
        })
        taxes = [{'id': invoice.partner_id.l10n_ar_partner_tax_ids.tax_id.id, 'base_amount': invoice.amount_untaxed}]
        wizard = self.new_payment_register(invoice, taxes)
        self.assertEqual(wizard.l10n_ar_withholding_ids.amount, 1600)
        wizard.action_create_payments()
        invoice2 = self.in_invoice_4_wht()
        taxes = [{'id': invoice2.partner_id.l10n_ar_partner_tax_ids.tax_id.id, 'base_amount': invoice2.amount_untaxed}]
        wizard = self.new_payment_register(invoice2, taxes)
        self.assertEqual(wizard.l10n_ar_withholding_ids.amount, 7480)
        wizard.action_create_payments()

    def test_06_earnings_withholding_applied(self):
        """Two payments with same withholding tax (with tax type 'Earnings'). Verify withholding amount."""
        invoice = self.in_invoice_3_wht()
        self.tax_wth_earnings_incurred_test_6.l10n_ar_withholding_sequence_id = self.earnings_withholding_sequence
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': invoice.company_id.id,
            'tax_id': self.tax_wth_earnings_incurred_test_6.id
        })
        taxes = [{'id': invoice.partner_id.l10n_ar_partner_tax_ids.tax_id.id, 'base_amount': invoice.amount_untaxed}]
        wizard = self.new_payment_register(invoice, taxes)
        self.assertEqual(wizard.l10n_ar_withholding_ids.amount, 1327.8)
        wizard.action_create_payments()
        invoice2 = self.in_invoice_4_wht()
        taxes = [{'id': invoice2.partner_id.l10n_ar_partner_tax_ids.tax_id.id, 'base_amount': invoice2.amount_untaxed}]
        wizard = self.new_payment_register(invoice2, taxes)
        self.assertEqual(wizard.l10n_ar_withholding_ids.amount, 2400)
        wizard.action_create_payments()

    def test_07_earnings_partial_payment_withholding_applied_with_scale(self):
        """Partial payment with withholding tax (with tax type 'Earnings Scale'). Verify withholding amount."""
        invoice = self.in_invoice_3_wht()
        self.tax_wth_earnings_incurred_scale_test_5.l10n_ar_withholding_sequence_id = self.earnings_withholding_sequence
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': invoice.company_id.id,
            'tax_id': self.tax_wth_earnings_incurred_scale_test_5.id
        })
        taxes = [{'id': invoice.partner_id.l10n_ar_partner_tax_ids.tax_id.id, 'base_amount': invoice.amount_untaxed}]
        wizard = self.new_payment_register(invoice, taxes)
        wizard.amount -= 2420
        self.assertEqual(wizard.l10n_ar_withholding_ids.amount, 1360)

    def test_08_earnings_withholding_applied_with_scale_and_minimun_withholdable_amount_set(self):
        """Payment with withholding tax type 'Earnings Scale' and minimun withholdable amount set. Verify withholding amount."""
        invoice = self.in_invoice_3_wht()
        self.tax_wth_earnings_incurred_scale_test_5.l10n_ar_withholding_sequence_id = self.earnings_withholding_sequence
        self.tax_wth_earnings_incurred_scale_test_5.l10n_ar_minimum_threshold = 2000
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': self.res_partner_adhoc.id,
            'company_id': invoice.company_id.id,
            'tax_id': self.tax_wth_earnings_incurred_scale_test_5.id
        })
        taxes = [{'id': invoice.partner_id.l10n_ar_partner_tax_ids.tax_id.id, 'base_amount': invoice.amount_untaxed}]
        wizard = self.new_payment_register(invoice, taxes)
        self.assertEqual(wizard.l10n_ar_withholding_ids.amount, 0.0)

    def test_09_foreign_invoice(self):
        """ Ensure a correct behavior when the invoice has a foreign currency and the payment not. """
        in_invoice_wht = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2023-01-01',
            'invoice_date': '2023-01-01',
            'currency_id': self.other_currency.id,
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

    def test_10_foreign_invoice_and_payment(self):
        """ Ensure a correct behavior when the invoice and the payment have a foreign currency. """
        in_invoice_wht = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2023-01-01',
            'invoice_date': '2023-01-01',
            'currency_id': self.other_currency.id,
            'partner_id': self.res_partner_adhoc.id,
            'invoice_line_ids': [Command.create(
                {'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax_21.ids)]}
            )],
            'l10n_latam_document_number': '2-1',
        })
        in_invoice_wht.action_post()
        wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=in_invoice_wht.ids).create({
            'payment_date': '2023-01-01',
            'currency_id': self.other_currency.id,
            'l10n_ar_withholding_ids': [Command.create({'tax_id': self.tax_wth_test_1.id, 'base_amount': sum(in_invoice_wht.mapped('amount_untaxed')), 'amount': 0})],
        })
        wizard.l10n_ar_withholding_ids._compute_amount()
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
