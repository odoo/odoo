# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import Command, fields


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nArWithholdingArRi(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='ar_ri'):

        super().setUpClass(chart_template_ref=chart_template_ref)

        # Witholding 1: 1% untaxed_amount
        cls.tax_wth_test_1 = cls.env.ref('account.%i_ri_tax_withholding_iibb_caba_applied' % cls.env.company.id)
        cls.tax_wth_test_1.write({
            'l10n_ar_withholding_amount_type': 'untaxed_amount',
            'amount': 10,
            'amount_type': 'percent',
        })

        # Witholding 2: 1% total_amount
        cls.tax_wth_test_2 = cls.env.ref('account.%i_ri_tax_withholding_iibb_ba_applied' % cls.env.company.id)
        cls.tax_wth_test_2.write({
            'l10n_ar_withholding_amount_type': 'total_amount',
            'amount': 10,
            'amount_type': 'percent',
        })

        # Add witholding to product
        cls.product_a.l10n_ar_supplier_withholding_taxes_ids = [Command.set(cls.tax_wth_test_1.ids)]
        cls.product_b.l10n_ar_supplier_withholding_taxes_ids = [Command.set(cls.tax_wth_test_2.ids + cls.tax_wth_test_1.ids)]
        cls.l10n_latam_document_type_id = cls.env['l10n_latam.document.type'].search([], limit =1)
        cls.tax_21 = cls._search_tax(cls, 'iva_21')

        cls.actual_rate = cls.env['res.currency.rate'].create({
            'name': fields.Date.today(),
            'rate': 1/100,
            'currency_id': cls.currency_data['currency'].id,
            'company_id': cls.env.company.id,
        })


        cls.old_rate = cls.env['res.currency.rate'].create({
            'name': '2023-05-01',
            'rate': 1/200,
            'currency_id': cls.currency_data['currency'].id,
            'company_id': cls.env.company.id,
        })


    def in_invoice_wht(self, l10n_latam_document_number):
        in_invoice_wht = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': fields.Date.today(),
            'invoice_date': fields.Date.today(),
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax_21.ids)]})],
            'l10n_latam_document_type_id': self.l10n_latam_document_type_id.id,
            'l10n_latam_document_number': l10n_latam_document_number,

        })
        in_invoice_wht.action_post()
        return in_invoice_wht

    def in_invoice_2_wht(self, l10n_latam_document_number):
        in_invoice_wht = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': fields.Date.today(),
            'invoice_date': fields.Date.today(),
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_b.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.tax_21.ids)]})
            ],
            'l10n_latam_document_type_id': self.l10n_latam_document_type_id.id,
            'l10n_latam_document_number': l10n_latam_document_number,

        })
        in_invoice_wht.action_post()
        return in_invoice_wht

    def in_invoice_3_wht(self, l10n_latam_document_number):
        in_invoice_wht = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': fields.Date.today(),
            'invoice_date': fields.Date.today(),
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_b.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax_21.ids)]})
            ],
            'l10n_latam_document_type_id': self.l10n_latam_document_type_id.id,
            'l10n_latam_document_number': l10n_latam_document_number,

        })
        in_invoice_wht.action_post()
        return in_invoice_wht


    def new_payment_register(self, active_ids, values = {}):
        wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create(values)
        taxes = wizard._get_withholding_tax()
        wizard.withholding_ids = [Command.clear()] + [Command.create({'tax_id': x.id, 'base_amount': 0 , 'amount': 0}) for x in taxes]
        wizard.withholding_ids._compute_base_amount()
        wizard.withholding_ids._compute_amount()
        return wizard

    def _search_tax(self, tax_type, type_tax_use='sale'):
        res = self.env['account.tax'].with_context(active_test=False).search([
            ('type_tax_use', '=', type_tax_use),
            ('company_id', '=', self.env.company.id)], limit=1)
        self.assertTrue(res, '%s Tax was not found' % (tax_type))
        return res

    def test_register_payment_wh(self):

        # Simple full payment in Company currency
        active_ids = self.in_invoice_wht('2-1').ids
        wizard = self.new_payment_register(active_ids)
        self.assertEqual(wizard.currency_id.round(sum(wizard.withholding_ids.mapped('amount'))) + wizard.net_amount, wizard.amount)
        action = wizard.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            # Liquidity line:
            { 'debit': 0.0, 'credit': 1110.0, 'currency_id': wizard.currency_id.id, 'amount_currency': -1110.0, 'reconciled': False},
            # base line:
            { 'debit': 0.0, 'credit': 1000.0, 'currency_id': wizard.currency_id.id, 'amount_currency': -1000.0, 'reconciled': False},
            # witholding line:
            { 'debit': 0.0, 'credit': 100.0, 'currency_id': wizard.currency_id.id, 'amount_currency': -100.0, 'reconciled': False},
            # base line:
            { 'debit': 1000.0, 'credit': 0.0, 'currency_id': wizard.currency_id.id, 'amount_currency': 1000.0, 'reconciled': False},
            # Receivable line:
            { 'debit': 1210.0, 'credit': 0.0, 'currency_id': wizard.currency_id.id, 'amount_currency': 1210.0, 'reconciled': True}
        ])
        self.assertEqual(1210, payment.currency_id.round(sum(payment.withholding_ids.mapped('amount_currency')) * -1  + payment.amount))

        active_ids = self.in_invoice_wht('2-2').ids
        wizard_1 = self.new_payment_register(active_ids)
        wizard_1.amount = 605.00
        self.assertEqual(wizard_1.currency_id.round(sum(wizard_1.withholding_ids.mapped('amount'))) + wizard_1.net_amount, wizard_1.amount)
        action = wizard_1.action_create_payments()
        payment_1 = self.env['account.payment'].browse(action['res_id'])

        # Alf payments in Company currency
        wizard_2 = self.new_payment_register(active_ids)
        self.assertEqual(605, wizard_2.source_amount)
        self.assertEqual(wizard_2.currency_id.round(sum(wizard_2.withholding_ids.mapped('amount'))) + wizard_2.net_amount, wizard_2.amount)
        action = wizard_2.action_create_payments()
        payment_2 = self.env['account.payment'].browse(action['res_id'])

        self.assertRecordValues(payment_1.line_ids.sorted('balance'), [
            # Liquidity line:
            { 'debit': 0.0, 'credit': 555.0, 'currency_id': wizard_1.currency_id.id, 'amount_currency': -555.0, 'reconciled': False},
            # base line:
            { 'debit': 0.0, 'credit': 500.0, 'currency_id': wizard_1.currency_id.id, 'amount_currency': -500.0, 'reconciled': False},
            # witholding line:
            { 'debit': 0.0, 'credit': 50.0, 'currency_id': wizard_1.currency_id.id, 'amount_currency': -50.0, 'reconciled': False},
            # base line:
            { 'debit': 500, 'credit': 0.0, 'currency_id': wizard_1.currency_id.id, 'amount_currency': 500, 'reconciled': False},
            # Receivable line:
            { 'debit': 605.0, 'credit': 0.0, 'currency_id': wizard_1.currency_id.id, 'amount_currency': 605.0, 'reconciled': True}
        ])
        self.assertEqual(605, payment_1.currency_id.round(sum(payment_1.withholding_ids.mapped('amount_currency')) * -1  + payment_1.amount))

        self.assertRecordValues(payment_2.line_ids.sorted('balance'), [
            # Liquidity line:
            { 'debit': 0.0, 'credit': 555.0, 'currency_id': wizard_2.currency_id.id, 'amount_currency': -555.0, 'reconciled': False},
            # base line:
            { 'debit': 0.0, 'credit': 500.0, 'currency_id': wizard_2.currency_id.id, 'amount_currency': -500.0, 'reconciled': False},
            # witholding line:
            { 'debit': 0.0, 'credit': 50.0, 'currency_id': wizard_2.currency_id.id, 'amount_currency': -50.0, 'reconciled': False},
            # base line:
            { 'debit': 500, 'credit': 0.0, 'currency_id': wizard_2.currency_id.id, 'amount_currency': 500, 'reconciled': False},
            # Receivable line:
            { 'debit': 605.0, 'credit': 0.0, 'currency_id': wizard_2.currency_id.id, 'amount_currency': 605.0, 'reconciled': True}
        ])
        self.assertEqual(605, payment_2.currency_id.round(sum(payment_2.withholding_ids.mapped('amount_currency')) * -1  + payment_2.amount))

        # Simple full payment in Company currency and two wht
        active_ids = self.in_invoice_2_wht('2-3').ids
        wizard = self.new_payment_register(active_ids)
        self.assertEqual(wizard.currency_id.round(sum(wizard.withholding_ids.mapped('amount'))) + wizard.net_amount, wizard.amount)
        action = wizard.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        line_1 = payment.withholding_ids.filtered(lambda x: x.tax_line_id.id == self.tax_wth_test_1.id)
        line_2 = payment.withholding_ids.filtered(lambda x: x.tax_line_id.id == self.tax_wth_test_2.id)
        self.assertEqual(-100, line_1.amount_currency)
        self.assertEqual(-121, line_2.amount_currency)
        self.assertEqual(1210, payment.currency_id.round(sum(payment.withholding_ids.mapped('amount_currency')) * -1  + payment.amount))

        # Alf payment in other currency and two wht
        active_ids = self.in_invoice_2_wht('2-4').ids
        wizard = self.new_payment_register(active_ids)
        wizard.currency_id = self.currency_data['currency'].id
        wizard.amount = 6.05

        self.assertEqual(wizard.currency_id.round(sum(wizard.withholding_ids.mapped('amount')) + wizard.net_amount), wizard.currency_id.round(wizard.amount))
        action = wizard.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        line_1 = payment.withholding_ids.filtered(lambda x: x.tax_line_id.id == self.tax_wth_test_1.id)
        line_2 = payment.withholding_ids.filtered(lambda x: x.tax_line_id.id == self.tax_wth_test_2.id)
        self.assertEqual(-0.50, line_1.amount_currency)
        self.assertEqual(-50, line_1.balance)
        self.assertEqual(-0.605, line_2.amount_currency)
        self.assertEqual(-60.5, line_2.balance)
        self.assertEqual(6.05, payment.currency_id.round(sum(payment.withholding_ids.mapped('amount_currency')) * -1  + payment.amount))


        # no company currency payment for no company currency inv and two wht
        inv_1 = self.in_invoice_3_wht('2-5')
        wizard = self.new_payment_register(inv_1.ids)
        wizard.payment_date = '2023-05-01'
        wizard.currency_id = self.currency_data['currency'].id
        wizard.amount = 60.5
        self.assertEqual(wizard.currency_id.round(sum(wizard.withholding_ids.mapped('amount')) + wizard.net_amount), wizard.currency_id.round(wizard.amount))
        action = wizard.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        line_1 = payment.withholding_ids.filtered(lambda x: x.tax_line_id.id == self.tax_wth_test_1.id)
        line_2 = payment.withholding_ids.filtered(lambda x: x.tax_line_id.id == self.tax_wth_test_2.id)
        self.assertEqual(-5.0, line_1.amount_currency)
        self.assertEqual(-6.05, line_2.amount_currency)
        self.assertEqual(60.5, payment.currency_id.round(sum(payment.withholding_ids.mapped('amount_currency')) * -1  + payment.amount))

        # company currency payment for no company currency inv and two wht
        inv_2 = self.in_invoice_3_wht('2-6')
        wizard = self.new_payment_register(inv_2.ids)
        wizard.payment_date = '2023-05-01'
        wizard.currency_id = self.env.company.currency_id.id
        wizard.amount = 12100
        self.assertEqual(wizard.currency_id.round(sum(wizard.withholding_ids.mapped('amount')) + wizard.net_amount), wizard.currency_id.round(wizard.amount))
        action = wizard.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        line_1 = payment.withholding_ids.filtered(lambda x: x.tax_line_id.id == self.tax_wth_test_1.id)
        line_2 = payment.withholding_ids.filtered(lambda x: x.tax_line_id.id == self.tax_wth_test_2.id)
        self.assertEqual(-1000, line_1.amount_currency)
        self.assertEqual(-1210, line_2.amount_currency)
        self.assertEqual(12100, payment.currency_id.round(sum(payment.withholding_ids.mapped('amount_currency')) * -1  + payment.amount))


        self.assertEqual(inv_1.amount_residual, inv_2.amount_residual)

