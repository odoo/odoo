# -*- coding: utf-8 -*-

from lxml import html
from markupsafe import Markup

from odoo import Command

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestGccInvoice(AccountTestInvoicingCommon):

    def test_invoice_narration_translation(self):
        ''' The narration field should be copied translations included'''
        # Activate second lang and parameter needed to display invoice terms
        self.env['res.lang']._activate_lang('ar_001')
        self.env['ir.config_parameter'].sudo().set_bool('account.use_invoice_terms', True)
        gcc_countries = self.env.ref('base.gulf_cooperation_council').country_ids
        self.env.company.write({
            'country_id': gcc_countries[0].id,
            'invoice_terms': 'English Terms',
            'terms_type': 'plain',
        })
        # Add translation to invoice terms
        self.env.company.update_field_translations('invoice_terms', {'en_US': {'English Terms': 'English Terms'}, 'ar_001': {'English Terms': 'Arabic Terms'}})
        # Create invoice with English partner (default)
        invoice_en = self.init_invoice('out_invoice', products=self.product_a)
        self.assertEqual(invoice_en.narration, Markup('<p>English Terms</p>'), 'Invoice narration should show English terms for English partner')
        # Create invoice with Arabic partner
        ar_partner = self.env['res.partner'].create({'name': 'Arabic Partner', 'lang': 'ar_001'})
        invoice_ar = self.init_invoice('out_invoice', products=self.product_a, partner=ar_partner)
        self.assertEqual(invoice_ar.narration, Markup('<p>Arabic Terms</p>'), 'Invoice narration should show Arabic terms for Arabic partner')

    def test_invoice_epd_cash_rounding_amount_lang_sec(self):
        """ The early payment discount amount printed in the secondary language must apply the
        cash rounding of the invoice, as the amount printed in the main language does. """
        self.env['res.lang']._activate_lang('ar_001')
        self.env.company.write({
            'country_id': self.env.ref('base.sa').id,
            'vat': '310175397400003',
            'l10n_gcc_dual_language_invoice': True,
        })
        tax = self.env['account.tax'].create({
            'name': '8.1%',
            'type_tax_use': 'sale',
            'amount': 8.1,
        })
        self.cash_rounding_a.rounding_method = 'HALF-UP'
        payment_term = self.env['account.payment.term'].create({
            'name': "2/7 Net 30",
            'company_id': self.env.company.id,
            'discount_percentage': 2,
            'discount_days': 7,
            'early_discount': True,
        })
        ar_partner = self.env['res.partner'].create({'name': 'Arabic Partner', 'lang': 'ar_001'})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': ar_partner.id,
            'invoice_payment_term_id': payment_term.id,
            'invoice_cash_rounding_id': self.cash_rounding_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'test line',
                'price_unit': 50.00,
                'tax_ids': [Command.set(tax.ids)],
            })],
        })
        invoice.action_post()
        self.assertEqual(invoice.amount_total, 54.05)

        report_html, _report_type = self.env['ir.actions.report']._render_qweb_html('account.account_invoices', invoice.ids)
        epd_en = html.fromstring(report_html).xpath("//div[@name='td_payment_term_en']//span")[0]
        # 54.05 - 2% = 52.969 -> 52.97, cash rounded to 52.95
        self.assertIn('52.95', epd_en.text_content())
