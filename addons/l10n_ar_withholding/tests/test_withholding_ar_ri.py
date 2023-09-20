# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged, Form
from odoo import Command, fields
from odoo.tests.common import TransactionCase, Form


@tagged('post_install', '-at_install')
class TestL10nArWithholdingArRi(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='ar_ri'):

        super().setUpClass(chart_template_ref=chart_template_ref)

        # Sequence Witholding Tax
        cls.tax_wth_seq_test_1 = cls.env['ir.sequence'].create({
        'implementation': 'standard',
        'name': 'tax wth test',
        'padding': 8,
        'number_increment' :1,
        })

        # Witholding 1: 1% untaxed_amount
        cls.tax_wth_test_1 = cls.env.ref('account.%i_ri_tax_withholding_iibb_caba_applied' % cls.env.company.id).copy()
        cls.tax_wth_test_1.write({
            'l10n_ar_withholding_amount_type': 'untaxed_amount',
            'amount': 1,
            'amount_type': 'percent',
            'l10n_ar_withholding_sequence_id': cls.tax_wth_seq_test_1.id,
        })

        # Witholding 2: 1% total_amount
        cls.tax_wth_test_2 = cls.env.ref('account.%i_ri_tax_withholding_iibb_caba_applied' % cls.env.company.id).copy()
        cls.tax_wth_test_2.write({
            'l10n_ar_withholding_amount_type': 'total_amount',
            'amount': 1,
            'amount_type': 'percent',
            'l10n_ar_withholding_sequence_id': cls.tax_wth_seq_test_1.id,
        })

        # Add witholding to product
        cls.product_a.l10n_ar_supplier_withholding_taxes_ids = [Command.set(cls.tax_wth_test_1.ids)]
        cls.product_b.l10n_ar_supplier_withholding_taxes_ids = [Command.set(cls.tax_wth_test_2.ids)]


        cls.l10n_latam_document_type_id = cls.env['l10n_latam.document.type'].search([], limit =1)
        cls.tax_21 = cls._search_tax(cls, 'iva_21')

        # invoices
        cls.in_invoice_wht_1 = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': fields.Date.today(),
            'invoice_date': fields.Date.today(),
            'partner_id': cls.partner_a.id,
            'currency_id': cls.currency_data['currency'].id,

            'invoice_line_ids': [Command.create({'product_id': cls.product_a.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(cls.tax_21.ids)]})],
            'l10n_latam_document_type_id': cls.l10n_latam_document_type_id.id,
            'l10n_latam_document_number': '1-1000',

        })

        cls.in_invoice_wht_1.action_post()
        cls.in_invoice_wht_2 = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2023-09-01',
            'invoice_date': '2023-09-01',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_b.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(cls.tax_21.ids)]})],
            'l10n_latam_document_type_id': cls.l10n_latam_document_type_id.id,
            'l10n_latam_document_number': '1-1001',
        })
        cls.in_invoice_wht_2.action_post()

        cls.in_invoice_wht_3 = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2023-09-01',
            'invoice_date': '2023-09-01',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [
                (0, 0, {'product_id': cls.product_b.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(cls.tax_21.ids)]}),
                (0, 0, {'product_id': cls.product_b.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(cls.tax_21.ids)]})
            ],
            'l10n_latam_document_type_id': cls.l10n_latam_document_type_id.id,
            'l10n_latam_document_number': '1-1002',
        })
        cls.in_invoice_wht_3.action_post()


    def _search_tax(self, tax_type, type_tax_use='sale'):
        res = self.env['account.tax'].with_context(active_test=False).search([
            ('type_tax_use', '=', type_tax_use),
            ('company_id', '=', self.env.company.id),
            ('tax_group_id', '=', self.env.ref(f'account.{self.env.company.id}_tax_group_{tax_type}').id)], limit=1)
        self.assertTrue(res, '%s Tax was not found' % (tax_type))
        return res

    def test_register_payment_wh(self):

        active_ids = self.in_invoice_wht_1.ids

        # SIMPLE FULL PAYMENT
        wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).new({})
        taxes = wizard.line_ids.move_id.invoice_line_ids.product_id.l10n_ar_supplier_withholding_taxes_ids.filtered(lambda y: y.company_id == wizard.company_id)
        wizard.withholding_ids =[Command.clear()] + [Command.create({'tax_id': x.id, 'base_amount': 0 , 'amount': 0}) for x in taxes]
        wizard.withholding_ids._compute_base_amount()
        wizard.withholding_ids._compute_amount()
        return 
        self.assertEqual(wizard.currency_id.round(sum(wizard.withholding_ids.mapped('amount'))) + wizard.net_amount, wizard.amount)
        action = wizard.action_create_payments()
        payment = self.env['account.payment'].browse(action['res_id'])
        import pdb; pdb.set_trace()
        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            # Liquidity line:
            { 'debit': 0.0, 'credit': 1205.0, 'currency_id': wizard.currency_id.id, 'amount_currency': -1205.0, 'reconciled': False}, 
            # base line:
            { 'debit': 0.0, 'credit': 1000.0, 'currency_id': wizard.currency_id.id, 'amount_currency': -1000.0, 'reconciled': False}, 
            # witholding line:
            { 'debit': 0.0, 'credit': 5.0, 'currency_id': wizard.currency_id.id, 'amount_currency': -5.0, 'reconciled': False}, 
            # base line:
            { 'debit': 1000.0, 'credit': 0.0, 'currency_id': wizard.currency_id.id, 'amount_currency': 1000.0, 'reconciled': False}, 
            # Receivable line:
            { 'debit': 1210.0, 'credit': 0.0, 'currency_id': wizard.currency_id.id, 'amount_currency': 1210.0, 'reconciled': True}
        ])

        # MULTI PAYMENTS
        # active_ids = self.in_invoice_wht_2.ids + self.in_invoice_wht_3.ids
        # wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).new({'group_payment': True,})
        # self.assertTrue(wizard.can_group_payments)
        # wizard.group_payment = True

        # taxes = wizard.line_ids.move_id.invoice_line_ids.product_id.l10n_ar_supplier_withholding_taxes_ids.filtered(lambda y: y.company_id == wizard.company_id)
        # wizard.withholding_ids =[Command.clear()] + [Command.create({'tax_id': x.id, 'base_amount': 0 , 'amount': 0}) for x in taxes]
        # wizard.withholding_ids._compute_base_amount()
        # wizard.withholding_ids._compute_amount()

        # self.assertEqual(wizard.currency_id.round(sum(wizard.withholding_ids.mapped('amount')) + wizard.net_amount), wizard.amount)

        # action = wizard.action_create_payments()
